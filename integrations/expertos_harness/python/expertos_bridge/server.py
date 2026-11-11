"""Loopback-only ExpertOS bridge, no internet/listening by default.

Launch with a strong random token in EXPERTOS_BRIDGE_TOKEN. No user data is sent
outside localhost. Runtime never accepts arbitrary shell commands or browser JS.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
from . import experts

MAX_BODY = 96_000
ROUTES = {
    "/v1/route": experts.route,
    "/v1/plan": experts.plan,
    "/v1/form/map": experts.controls_map,
    "/v1/form/verify": experts.verify_values,
    "/v1/recover": experts.recovery,
    "/v1/universal": experts.universal_dispatch,
    "/v1/action/propose": lambda data: {"status": "model_unavailable", "action": None},
}

class BridgeServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 8
    allow_reuse_address = False
    def __init__(self, address, token, expert_data=None, action_model=None, allow_experimental=False):
        if address[0] not in ("127.0.0.1", "::1"):
            raise ValueError("Only loopback is supported")
        if not isinstance(token, str) or len(token) < 32:
            raise ValueError("EXPERTOS_BRIDGE_TOKEN must be at least 32 characters")
        super().__init__(address, Handler)
        self.bridge_token = token
        self.expert_data = expert_data
        self.action_model = action_model
        self.allow_experimental = allow_experimental

class Handler(BaseHTTPRequestHandler):
    server_version = "ExpertOSBridge/0.1"
    sys_version = ""
    def log_message(self, fmt, *args):
        # Do not log source data, token, query strings or form values.
        pass

    def _headers(self, status, content_len):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(content_len))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()

    def _send(self, status, result):
        data = json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self._headers(status, len(data))
        self.wfile.write(data)

    def _authorized(self):
        value = self.headers.get("Authorization", "")
        # compare_digest prevents token-prefix/substring bugs
        return secrets.compare_digest(value.encode(), ("Bearer " + self.server.bridge_token).encode())

    def _secure_request(self):
        if self.path != self.path.split("?", 1)[0] or self.headers.get("Origin"):
            self._send(400, {"status":"invalid_request"})
            return False
        if not self._authorized():
            self._send(401, {"status": "unauthorized"})
            return False
        return True

    def do_GET(self):
        if not self._secure_request():
            return
        if self.path == "/health":
            self._send(200, {"status": "ok", "service": "expertos-bridge", "version": "0.1"})
        elif self.path == "/v1/experts":
            self._send(200, {"status": "ok", "experts": experts.EXPERTS})
        else:
            self._send(404, {"status": "not_found"})

    def do_POST(self):
        if not self._secure_request():
            return
        if self.path not in ROUTES and self.path != "/v1/source/read":
            self._send(404, {"status": "not_found"})
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if content_type != "application/json":
            self._send(415, {"status": "invalid_content_type"})
            return
        length_str = self.headers.get("Content-Length", "")
        try:
            length = int(length_str)
        except ValueError:
            length = -1
        if length < 2 or length > MAX_BODY:
            self._send(413, {"status": "invalid_content_length"})
            return
        try:
            obj = json.loads(self.rfile.read(length))
            if not isinstance(obj, dict):
                raise ValueError("Expected JSON object")
        except (ValueError, UnicodeError):
            self._send(400, {"status": "invalid_json"})
            return
        try:
            if self.path == "/v1/action/propose":
                result = self._propose_action(obj)
            elif self.path == "/v1/source/read":
                result = self._source_read(obj)
            else:
                result = ROUTES[self.path](obj)
            self._send(200, result)
        except (ValueError, OSError) as exc:
            self._send(422, {"status": "rejected", "error_type": type(exc).__name__})
        except Exception:
            self._send(500, {"status": "server_error"})

    def _propose_action(self, obj):
        if not self.server.action_model:
            return {"status": "model_unavailable", "action": None}
        from .action_policy import predict
        if not isinstance(obj.get("task"), str) or not isinstance(obj.get("context"), str):
            return {"status": "invalid_input", "action": None}
        if len(obj["task"]) > 2048 or len(obj["context"]) > 8192:
            return {"status": "invalid_input", "action": None}
        return predict(self.server.action_model, obj["task"], obj["context"],
                       allow_experimental=self.server.allow_experimental)

    def _source_read(self, obj):
        document_id, question = obj.get("document_id"), obj.get("question")
        if not isinstance(document_id, str) or len(document_id) > 250 or not isinstance(question, str) or len(question) > 2048:
            return {"status": "invalid_input", "answer": None}
        if not self.server.expert_data:
            return {"status": "source_library_unavailable", "answer": None}
        # Import existing BookEngine lazily; no neural model is silently enabled.
        from tiny_experts.pipeline.book_engine import BookEngine
        engine = BookEngine(data_dir=self.server.expert_data, include_demo_seeds=False)
        try:
            found = engine.lookup_document(document_id, question, top_k=3)
            return {"status": found["status"], "answer": None,
                    "passages": [{k: v for k, v in p.items() if k in
                                  {"passage_id", "document_id", "text", "content_hash", "source_type", "review_status"}}
                                 for p in found["passages"]],
                    "model_status": "retrieval_only"}
        finally:
            engine.close()

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1"])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--source-library", default=None)
    parser.add_argument("--action-model", default=None)
    parser.add_argument("--allow-experimental", action="store_true")
    args = parser.parse_args(argv)
    token = os.environ.get("EXPERTOS_BRIDGE_TOKEN", "")
    server = BridgeServer((args.host, args.port), token, args.source_library, args.action_model, args.allow_experimental)
    print(f"ExpertOS bridge listening on {args.host}:{server.server_port}", flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
if __name__ == "__main__":
    main()
