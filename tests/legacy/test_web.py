import unittest
import threading
import time
import urllib.request
import json
import base64
from io import BytesIO
from PIL import Image

from tiny_experts.web.server import TinyExpertServerHandler, ThreadingHTTPServer
from tiny_experts.orchestrator import TinyExpertOrchestrator

class TestWebInterface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orchestrator = TinyExpertOrchestrator(verbose=False)
        TinyExpertServerHandler.orchestrator = cls.orchestrator
        cls.port = 8765
        cls.server = ThreadingHTTPServer(("127.0.0.1", cls.port), TinyExpertServerHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_get_index(self):
        url = f"http://127.0.0.1:{self.port}/"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            content = resp.read().decode("utf-8")
            self.assertIn("Tiny Expert AI System", content)
            self.assertIn("dropzone", content)

    def test_api_status(self):
        url = f"http://127.0.0.1:{self.port}/api/status"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "online")
            self.assertEqual(data["active_experts_count"], 24)

    def test_api_chat_and_reset(self):
        url = f"http://127.0.0.1:{self.port}/api/chat"
        payload = json.dumps({
            "query": "What is this plant with three shiny leaves? Is it toxic?",
            "session_id": "test_web_session"
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("thinking_trace", data)
            self.assertIn("Poison Ivy", data["rendered_card"])
            self.assertIn("vision", data["active_experts"])

        # Test reset endpoint
        reset_url = f"http://127.0.0.1:{self.port}/api/reset"
        reset_payload = json.dumps({"session_id": "test_web_session"}).encode("utf-8")
        reset_req = urllib.request.Request(reset_url, data=reset_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(reset_req) as resp:
            self.assertEqual(resp.status, 200)
            reset_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(reset_data["status"], "ok")

    def test_api_chat_with_image(self):
        # Create a tiny 100x100 dummy test image in memory
        img = Image.new("RGB", (100, 100), color=(34, 139, 34))
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64_str = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

        url = f"http://127.0.0.1:{self.port}/api/chat"
        payload = json.dumps({
            "query": "Identify this photo and check its toxicity",
            "image_base64": b64_str,
            "session_id": "test_img_session"
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("thinking_trace", data)
            self.assertIn("vision", data["active_experts"])
            self.assertTrue(data["telemetry"]["vision"]["detected"])

if __name__ == "__main__":
    unittest.main()
