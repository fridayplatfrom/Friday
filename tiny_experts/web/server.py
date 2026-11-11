"""Loopback-only UI with bounded requests, serialized mutable expert state, and native DeepSeek Harness streaming endpoints."""
import base64
import binascii
import io
import json
import logging
import os
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from PIL import Image, UnidentifiedImageError
from ..orchestrator import ComponentOrchestrator
from ..harness_engine import TinyExpertHarnessEngine

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
LOGGER = logging.getLogger(__name__)


class TinyExpertServerHandler(SimpleHTTPRequestHandler):
    orchestrator = None
    state_lock = threading.RLock()
    max_request_bytes = 8 * 1024 * 1024
    max_image_pixels = 16_000_000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _allowed_host(self):
        expected_port = self.server.server_port
        return self.headers.get("Host", "").lower() in {
            f"127.0.0.1:{expected_port}",
            f"localhost:{expected_port}",
            "127.0.0.1",
            "localhost",
        }

    def do_GET(self):
        if not self._allowed_host():
            self._send_json(403, {"error": "Only the local application host is allowed."})
            return
        path = urlsplit(self.path).path
        if path == "/api/status":
            app = type(self).orchestrator
            from ..capability_registry import describe_components
            components = getattr(app, "components", getattr(app, "experts", {})) if app else {}
            self._send_json(200, {
                "status": "online",
                "system": "Tiny Expert System",
                "active_experts_count": len(app.experts) if app else 0,
                "registered_components_count": len(components),
                "components": describe_components(components),
                "memory_sessions_active": len(app.sessions) if app else 0,
                "total_indexed_passages": len(app.book_engine.index) if app else 0,
                "execution_mode": "local_non_llm",
                "harness_integration": "native_llm_adapter_active",
            })
        elif path in {"/api/harness/models", "/v1/models", "/anthropic/v1/models"}:
            self._send_json(200, {
                "object": "list",
                "data": TinyExpertHarnessEngine.MODEL_CATALOG,
            })
        elif path in {"/", "/index.html"}:
            self.path = "/index.html"
            super().do_GET()
        else:
            self._send_json(404, {"error": "Endpoint not found."})

    def do_POST(self):
        if not self._allowed_host():
            self._send_json(403, {"error": "Only the local application host is allowed."})
            return
        path = urlsplit(self.path).path
        is_harness_endpoint = path.startswith("/api/harness/") or path.startswith("/v1/") or path.startswith("/anthropic/")
        origin = self.headers.get("Origin")
        if not is_harness_endpoint and origin and origin != "http://" + self.headers.get("Host", ""):
            self._send_json(403, {"error": "Cross-origin requests are not allowed."})
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json(415, {"error": "Content-Type must be application/json."})
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if length < 0 or length > self.max_request_bytes:
            self.close_connection = True
            self._send_json(413, {"error": "Invalid or oversized request body."})
            return
        try:
            self.connection.settimeout(60 if is_harness_endpoint else 15)
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("JSON body must be an object.")
            with type(self).state_lock:
                if type(self).orchestrator is None:
                    type(self).orchestrator = ComponentOrchestrator()
                self._handle_post(path, data)
        except (ValueError, TypeError, KeyError, UnicodeDecodeError, binascii.Error,
                UnidentifiedImageError, Image.DecompressionBombError) as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception:
            LOGGER.exception("Local expert request failed")
            self._send_json(500, {"error": "The request failed. See the local server log for details."})

    def _handle_post(self, path, data):
        app = type(self).orchestrator
        if path == "/api/reset":
            session_id = data.get("session_id", "default_session")
            if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
                raise ValueError("Invalid session ID.")
            app.reset_session(session_id)
            self._send_json(200, {"status": "ok", "message": "Session memory cleared."})
        elif path == "/api/ingest":
            from ..pipeline.ingestion import LiteratureIngestionPipeline
            text = data.get("text", "")
            title = data.get("title", "Imported document")
            if not isinstance(text, str) or not text.strip() or not isinstance(title, str):
                raise ValueError("Provide document text and a text title.")
            pipeline = LiteratureIngestionPipeline(book_engine=app.book_engine, catalog_engine=app.catalog_engine)
            result = pipeline.ingest_text(
                raw_text=text,
                source_title=title,
                shelf=data.get("shelf"),
                metadata=data.get("metadata"),
                document_id=data.get("document_id"),
            )
            self._send_json(200, result)
        elif path == "/api/chat":
            image = None
            encoded = data.get("image_base64")
            if encoded:
                if not isinstance(encoded, str):
                    raise ValueError("Image must be a base64 string.")
                payload = encoded.split(",", 1)[-1]
                raw = base64.b64decode(payload, validate=True)
                with Image.open(io.BytesIO(raw)) as opened:
                    if opened.width * opened.height > self.max_image_pixels:
                        raise ValueError("Image exceeds 16 million pixels.")
                    image = opened.convert("RGB")
            result = app.process_detailed(
                query=data.get("query", ""),
                image=image,
                session_id=data.get("session_id", "default_session"),
                show_thinking=True,
                output_format="card",
            )
            self._send_json(200, result)
        elif path == "/api/universal":
            query = data.get("query", "")
            if not isinstance(query, str) or not query.strip():
                raise ValueError("Provide a nonempty query string.")
            result = app.dispatch_universal_core(
                query=query,
                workflow_payload=data.get("workflow_payload") if isinstance(data.get("workflow_payload"), dict) else None,
                as_of=data.get("as_of") if isinstance(data.get("as_of"), str) else None,
            )
            self._send_json(200, result)
        elif path == "/api/harness/chat":
            LOGGER.info("HARNESS CHAT POST DATA: %s", json.dumps(data)[:600])
            turn_out = TinyExpertHarnessEngine.answer_harness_request(
                app,
                messages=data.get("messages") if isinstance(data.get("messages"), list) else None,
                query=data.get("query") if isinstance(data.get("query"), str) else None,
                purpose=data.get("purpose") if isinstance(data.get("purpose"), str) else None,
                image_path=data.get("image_path") if isinstance(data.get("image_path"), str) else None,
                image_base64=data.get("image_base64") if isinstance(data.get("image_base64"), str) else None,
                reasoning_effort=str(data.get("reasoningEffort") or "high"),
            )
            self._send_json(200, turn_out)
        elif path == "/api/harness/stream":
            self._stream_harness_request(data)
        elif path in {"/v1/chat/completions", "/v1/messages", "/anthropic/v1/messages"}:
            turn_out = TinyExpertHarnessEngine.answer_harness_request(
                app,
                messages=data.get("messages") if isinstance(data.get("messages"), list) else None,
                query=data.get("query") if isinstance(data.get("query"), str) else None,
                purpose=data.get("purpose") if isinstance(data.get("purpose"), str) else None,
                reasoning_effort=str(data.get("reasoning_effort") or "high"),
            )
            if data.get("stream"):
                self._send_harness_sse(turn_out)
            else:
                self._send_json(200, {
                    "id": f"chatcmpl-tinyexpert-{int(time.time() * 1000)}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": str(data.get("model") or "tiny-expert-physics-v1"),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "reasoning_content": turn_out["reasoning_trace"],
                                "content": turn_out["answer_markdown"],
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": turn_out["usage"]["inputTokens"],
                        "completion_tokens": turn_out["usage"]["outputTokens"],
                        "total_tokens": turn_out["usage"]["inputTokens"] + turn_out["usage"]["outputTokens"],
                    },
                    "metadata": turn_out["metadata"],
                })
        else:
            self._send_json(404, {"error": "Endpoint not found."})

    def _start_harness_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

    def _write_harness_event(self, chunk_obj):
        payload = f"data: {json.dumps(chunk_obj, ensure_ascii=False)}\n\n".encode("utf-8")
        self.wfile.write(payload)
        self.wfile.flush()

    def _stream_harness_request(self, data):
        messages = data.get("messages") if isinstance(data.get("messages"), list) else []
        purpose = data.get("purpose") if isinstance(data.get("purpose"), str) else None
        is_title = TinyExpertHarnessEngine.extract_prompt_and_context(messages, purpose=purpose)["is_session_title"]
        prefix = "Running local expert tools; the execution report follows when computation completes.\n"
        self._start_harness_sse()
        try:
            if not is_title:
                self._write_harness_event({"type": "block-start", "index": 0, "blockType": "reasoning"})
                self._write_harness_event({"type": "reasoning-delta", "index": 0, "text": prefix})
            turn = TinyExpertHarnessEngine.answer_harness_request(
                type(self).orchestrator, messages=messages,
                query=data.get("query") if isinstance(data.get("query"), str) else None,
                purpose=purpose,
                image_path=data.get("image_path") if isinstance(data.get("image_path"), str) else None,
                image_base64=data.get("image_base64") if isinstance(data.get("image_base64"), str) else None,
                reasoning_effort=str(data.get("reasoningEffort") or "high"),
            )
            self._send_harness_sse(turn, headers_sent=True,
                                   reasoning_prefix=prefix if not is_title else "")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            LOGGER.info("Harness client disconnected")
        except Exception:
            LOGGER.exception("Harness streaming request failed")
            try:
                self._write_harness_event({"type": "error", "message": "Local expert computation failed; see the server log."})
            except (OSError, ValueError):
                pass

    def _send_harness_sse(self, turn_out, *, headers_sent=False, reasoning_prefix=""):
        """Send native events; computation is bounded, text is not LLM-generated."""
        if not headers_sent:
            self._start_harness_sse()
        write_event = self._write_harness_event

        reasoning_chunks = turn_out.get("reasoning_chunks") or []
        answer_chunks = turn_out.get("answer_chunks") or []
        is_title = bool(turn_out.get("is_session_title"))

        text_block_index = 0
        if not is_title and (reasoning_chunks or reasoning_prefix):
            if not reasoning_prefix:
                write_event({"type": "block-start", "index": 0, "blockType": "reasoning"})
            for r_chunk in reasoning_chunks:
                write_event({"type": "reasoning-delta", "index": 0, "text": r_chunk})
            write_event({
                "type": "block-end",
                "index": 0,
                "block": {"type": "reasoning", "text": reasoning_prefix + turn_out.get("reasoning_trace", "")},
            })
            text_block_index = 1

        write_event({"type": "block-start", "index": text_block_index, "blockType": "text"})
        for a_chunk in answer_chunks:
            write_event({"type": "text-delta", "index": text_block_index, "text": a_chunk})
        write_event({
            "type": "block-end",
            "index": text_block_index,
            "block": {"type": "text", "text": turn_out.get("answer_markdown", "")},
        })
        write_event({"type": "usage", "usage": turn_out.get("usage", {"inputTokens": 16, "outputTokens": 64})})
        write_event({"type": "finish", "reason": {"kind": "stop"}})
        self.close_connection = True

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _send_json(self, status_code, data):
        response = json.dumps(data, allow_nan=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        LOGGER.info("HTTP %s", args[0] if args else "request")


def run_server(port=8000, open_browser=True):
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535.")
    TinyExpertServerHandler.orchestrator = ComponentOrchestrator(verbose=True)
    server = ThreadingHTTPServer(("127.0.0.1", port), TinyExpertServerHandler)
    server.daemon_threads = True
    url = f"http://127.0.0.1:{port}"
    print(f"Local non-LLM expert system: {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        while True:
            try:
                server.serve_forever()
                break
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as exc:
                LOGGER.error("Server encountered transient error: %s", exc, exc_info=True)
                time.sleep(0.2)
    finally:
        server.server_close()
