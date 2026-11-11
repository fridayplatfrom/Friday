"""Pinned-DNS, certificate-verified, GET-only public HTTPS transport.

No redirects, cookies, proxy discovery, credentials or dynamic code execution.
DNS resolution itself relies on the OS resolver; isolate workers and bound their
whole-process lifetime as well as per-socket deadlines.
"""
from dataclasses import dataclass
import http.client
import ipaddress
import re
import socket
import ssl
import time
from urllib.parse import urlsplit,urlunsplit,parse_qsl,quote,unquote
from ..knowledge_core.store import CoreError, AccessDenied

USER_AGENT='ExpertOSBot/0.2'


def safe_url(url,allowed_hosts):
    if not isinstance(url,str) or not url or len(url)>2048 or any(ord(c)<33 for c in url) or '\\' in url:
        raise AccessDenied('Invalid or oversized URL')
    try:
        p=urlsplit(url);host=p.hostname.encode('idna').decode().lower() if p.hostname else None;port=p.port
    except (ValueError,UnicodeError) as exc:raise AccessDenied('Invalid URL') from exc
    if p.scheme!='https' or not host or p.username is not None or p.password is not None or port not in (None,443):
        raise AccessDenied('Only public HTTPS without credentials is permitted')
    if host not in allowed_hosts or host.endswith('.') or re.fullmatch(r'[0-9.]+',host) or ':' in host:
        raise AccessDenied('Host is not explicitly allowed')
    if re.search(r'%(?![0-9a-fA-F]{2})',p.path+p.query):raise AccessDenied('Malformed percent escape')
    decoded=p.path
    for _ in range(3):decoded=unquote(decoded)
    if any(part in {'.','..'} for part in decoded.split('/')) or '\\' in decoded or re.search(r'(?i)%2f|%5c',p.path):
        raise AccessDenied('Ambiguous path normalization is not permitted')
    pairs=parse_qsl(p.query,keep_blank_values=True)
    if len(pairs)>16 or any(re.search(r'(?i)^(token|access_token|api_key|password|session|authorization|auth)$',k) for k,v in pairs):
        raise AccessDenied('Credential-like or excessive query parameters')
    path=quote(p.path or '/',safe='/%:@!$&\'()*+,;=-._~')
    query=quote(p.query,safe='=&%:@!$\'()*+,;/?-._~')
    return urlunsplit(('https',host,path,query,''))


class FetchError(CoreError):
    pass


@dataclass
class Response:
    url: str
    status: int
    headers: dict
    body: bytes


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self,host,address,timeout):
        super().__init__(host,port=443,timeout=timeout,context=ssl.create_default_context())
        self.address=address
    def connect(self):
        raw=socket.create_connection((self.address,443),self.timeout)
        try:self.sock=self._context.wrap_socket(raw,server_hostname=self.host)
        except BaseException:raw.close();raise


class SecureFetcher:
    def __init__(self,*,allow_network=False,timeout=15):
        if type(timeout) not in (int,float) or not 0<timeout<=60:raise CoreError('Invalid network timeout')
        self.allow_network=allow_network is True;self.timeout=timeout

    def fetch(self,url,*,allowed_hosts,max_bytes,headers=None):
        if not self.allow_network:raise AccessDenied('Live network access is disabled')
        if type(max_bytes) is not int or not 1<=max_bytes<=8*1024**2:raise CoreError('Invalid response limit')
        url=safe_url(url,allowed_hosts);p=urlsplit(url);host=p.hostname;conn=None
        deadline=time.monotonic()+self.timeout
        try:
            addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
            if not addresses:raise FetchError('No public source address')
            for entry in addresses:
                address=ipaddress.ip_address(entry[4][0])
                if not address.is_global or address.is_multicast or address.is_unspecified:
                    raise AccessDenied('Source DNS contains a non-public address')
            remaining=deadline-time.monotonic()
            if remaining<=0:raise FetchError('Source resolution deadline exceeded')
            conn=PinnedHTTPS(host,addresses[0][4][0],remaining)
            h={'User-Agent':USER_AGENT,'Accept':'text/html,text/plain,application/json,application/xml',
               'Accept-Encoding':'identity','Connection':'close'}
            for k,v in (headers or {}).items():
                if k not in {'If-None-Match','If-Modified-Since'} or not isinstance(v,str) or len(v)>512 or '\r' in v or '\n' in v:
                    raise AccessDenied('Invalid conditional request header')
                h[k]=v
            conn.request('GET',(p.path or '/')+('?' +p.query if p.query else ''),headers=h)
            response=conn.getresponse();head={k.lower():v for k,v in response.getheaders()}
            # Redirect responses are returned, NEVER followed implicitly.
            if response.status in {301,302,303,307,308,304}:return Response(url,response.status,head,b'')
            if head.get('content-encoding','identity').lower() not in {'','identity'}:
                raise FetchError('Compressed response rejected; identity was requested')
            length=head.get('content-length')
            try:expected=int(length) if length is not None else None
            except ValueError as exc:raise FetchError('Invalid Content-Length') from exc
            if expected is not None and not 0<=expected<=max_bytes:raise FetchError('Response exceeds byte budget')
            chunks=[];size=0
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise FetchError('Source response deadline exceeded')
                if conn.sock:conn.sock.settimeout(remaining)
                chunk=response.read(min(65536,max_bytes+1-size))
                if not chunk:break
                size+=len(chunk)
                if size>max_bytes:raise FetchError('Response exceeds byte budget')
                chunks.append(chunk)
            if expected is not None and size!=expected:raise FetchError('Truncated response')
            return Response(url,response.status,head,b''.join(chunks))
        except (OSError,http.client.HTTPException) as exc:
            raise FetchError('Public source connection failed: '+type(exc).__name__) from exc
        finally:
            if conn:conn.close()
