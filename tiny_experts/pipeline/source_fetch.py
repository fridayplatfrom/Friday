"""Public HTTPS source loader with pinned DNS and explicit, unreviewed receipts."""
import hashlib
import http.client
import ipaddress
import socket
import ssl
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

DEFAULT_HOSTS = frozenset({"www.gutenberg.org", "gutenberg.org", "en.wikipedia.org", "pubchem.ncbi.nlm.nih.gov"})
MAX_BYTES = 8 * 1024 * 1024

class SourceFetchError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code

def validate_public_url(url, allowed_hosts=DEFAULT_HOSTS):
    if not isinstance(url, str) or not url or len(url) > 2048 or any(ord(c) < 33 for c in url):
        raise SourceFetchError("invalid_url", "A bounded HTTPS URL without whitespace is required")
    try:
        parts = urlsplit(url)
        host, port = parts.hostname, parts.port
    except ValueError as error:
        raise SourceFetchError("invalid_url", "Malformed URL") from error
    if parts.scheme != "https" or not host or parts.username or parts.password or port not in (None, 443) or parts.fragment:
        raise SourceFetchError("blocked_url", "Only HTTPS port 443 without credentials or fragments is allowed")
    if host.lower() not in allowed_hosts:
        raise SourceFetchError("blocked_host", "Host is not in the source allowlist")
    return parts

def resolve_public_address(host):
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as error:
        raise SourceFetchError("network_unavailable", "Source hostname could not be resolved") from error
    if not addresses:
        raise SourceFetchError("network_unavailable", "No source address was resolved")
    for entry in addresses:
        address = ipaddress.ip_address(entry[4][0])
        if not address.is_global:
            raise SourceFetchError("blocked_address", "Source resolved to a non-public address")
    return addresses[0][4][0]

class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        super().__init__(host, port=443, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise

def fetch_public_text(url, *, allowed_hosts=DEFAULT_HOSTS, max_bytes=MAX_BYTES, timeout=15.0):
    start = time.monotonic()
    receipt = {"requested_url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
               "verification_status": "unverified", "review_status": "unreviewed"}
    connection = None
    try:
        if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_BYTES:
            raise SourceFetchError("invalid_limit", "max_bytes must be between 1 and 8 MiB")
        if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not 0 < timeout <= 60:
            raise SourceFetchError("invalid_limit", "timeout must be in (0, 60]")
        deadline, current = start + timeout, url
        for redirects in range(4):
            parts = validate_public_url(current, allowed_hosts)
            address = resolve_public_address(parts.hostname)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SourceFetchError("timeout", "Source request deadline exceeded")
            connection = _PinnedHTTPS(parts.hostname, address, remaining)
            path = (parts.path or "/") + ("?" + parts.query if parts.query else "")
            connection.request("GET", path, headers={"User-Agent": "TinyExpertSystem/0.3 (source research)",
                                                      "Accept": "text/plain, application/json",
                                                      "Accept-Encoding": "identity"})
            response = connection.getresponse()
            receipt.update(http_status=response.status, final_url=current)
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                connection.close()
                connection = None
                if not location or redirects == 3:
                    raise SourceFetchError("redirect_error", "Too many redirects or missing location")
                current = urljoin(current, location)
                continue
            if response.status != 200:
                raise SourceFetchError("http_error", f"Source returned HTTP {response.status}")
            content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type not in {"text/plain", "text/markdown", "application/json"}:
                raise SourceFetchError("unsupported_content", "Only plaintext, markdown and JSON are supported")
            if response.getheader("Content-Encoding", "identity").lower() not in {"identity", ""}:
                raise SourceFetchError("unsupported_encoding", "Compressed responses are not accepted")
            declared = response.getheader("Content-Length")
            try:
                expected = int(declared) if declared is not None else None
            except ValueError as error:
                raise SourceFetchError("invalid_length", "Invalid Content-Length") from error
            if expected is not None and (expected < 0 or expected > max_bytes):
                raise SourceFetchError("too_large", "Source exceeds limit")
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise SourceFetchError("timeout", "Source download deadline exceeded")
                if connection.sock is not None:
                    connection.sock.settimeout(remaining)
                chunk = response.read(min(65536, max_bytes + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise SourceFetchError("too_large", "Source exceeds limit")
                chunks.append(chunk)
            raw = b"".join(chunks)
            if expected is not None and len(raw) != expected:
                raise SourceFetchError("truncated_response", "Incomplete response")
            try:
                decoded = raw.decode("utf-8-sig")
            except UnicodeError as error:
                raise SourceFetchError("invalid_text", "Invalid UTF-8") from error
            if not decoded.strip() or "\x00" in decoded:
                raise SourceFetchError("invalid_text", "Empty or binary source")
            receipt.update(status="downloaded", content_type=content_type,
                           byte_count=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                           text_sha256=hashlib.sha256(decoded.encode("utf-8")).hexdigest(),
                           elapsed_seconds=time.monotonic() - start)
            return {"status": "downloaded", "text": decoded, "receipt": receipt}
        raise SourceFetchError("redirect_error", "Too many redirects")
    except (SourceFetchError, OSError, http.client.HTTPException) as error:
        receipt.update(status="failed",
                       error_code=error.code if isinstance(error, SourceFetchError) else "network_error",
                       error=str(error), elapsed_seconds=time.monotonic() - start)
        return {"status": "failed", "text": None, "receipt": receipt}
    finally:
        if connection is not None:
            connection.close()

def check_sources(sources):
    return {name: fetch_public_text(url)["receipt"] for name, url in sources.items()}
