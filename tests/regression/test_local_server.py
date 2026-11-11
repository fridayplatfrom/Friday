import http.client
import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace

import pytest
from tiny_experts.web.server import TinyExpertServerHandler


@pytest.fixture
def local_server():
    class Handler(TinyExpertServerHandler):
        orchestrator = SimpleNamespace(
            process_detailed=lambda **data: {"query": data["query"], "execution_mode": "local_non_llm"},
            dispatch_universal_core=lambda query, **kw: {"query": query, "core": "core_6_structured_synthesis", "workflow_payload": kw.get("workflow_payload")},
            experts={}, sessions={}, book_engine=SimpleNamespace(index=[]),
        )
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_port
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def request(port, path, body, **headers):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request("POST", path, body, {"Content-Type": "application/json", **headers})
    response = connection.getresponse()
    data = response.read()
    result = response.status, dict(response.getheaders()), data
    connection.close()
    return result


def test_same_origin_chat_works_without_wildcard_cors(local_server):
    status, headers, body = request(local_server, "/api/chat", json.dumps({"query": "12 + 8"}), Origin=f"http://127.0.0.1:{local_server}")
    assert status == 200
    assert json.loads(body)["query"] == "12 + 8"
    assert "Access-Control-Allow-Origin" not in headers


def test_cross_origin_and_rebinding_hosts_are_rejected(local_server):
    assert request(local_server, "/api/chat", "{}", Origin="https://unrelated.example")[0] == 403
    assert request(local_server, "/api/chat", "{}", Host=f"unrelated.example:{local_server}")[0] == 403


def test_oversized_and_malformed_json_are_rejected(local_server):
    assert request(local_server, "/api/chat", "{}", **{"Content-Length": str(9 * 1024 * 1024)})[0] == 413
    assert request(local_server, "/api/chat", "not-json")[0] == 400
    assert request(local_server, "/api/chat", "[]")[0] == 400


def test_ingestion_refreshes_the_running_catalog(isolated_state):
    from tiny_experts import TinyExpertOrchestrator
    app = TinyExpertOrchestrator()
    class Handler(TinyExpertServerHandler):
        orchestrator = app
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, _, body = request(server.server_port, "/api/ingest", json.dumps({
            "title": "Zephyrroot Observation Notes", "shelf": "botany",
            "text": "Zephyrroot is a fictional plant used only to test catalog refresh. Its leaves are described in these local observation notes.",
            "metadata": {"authors": ["Example Author"], "source_url": "https://example.invalid/test-notes"},
            "document_id": "zephyrroot-test",
        }))
        assert status == 200, body
        matches = app.catalog_engine.search_books("Zephyrroot")
        assert matches and matches[0]["title"] == "Zephyrroot Observation Notes"
        assert matches[0]["authors"] == ["Example Author"]
        assert matches[0]["review_status"] == "unreviewed"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_universal_endpoint_dispatches_7_cores(local_server):
    status, _, body = request(
        local_server,
        "/api/universal",
        json.dumps({"query": "Build an Excel spreadsheet for GST invoices", "workflow_payload": {"sheet_title": "GST"}}),
        Origin=f"http://127.0.0.1:{local_server}",
    )
    assert status == 200
    parsed = json.loads(body)
    assert parsed["core"] == "core_6_structured_synthesis"
    assert parsed["workflow_payload"] == {"sheet_title": "GST"}
    assert request(local_server, "/api/universal", json.dumps({"query": "   "}))[0] == 400

