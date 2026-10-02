import importlib.util
import threading
import unittest
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / "outputs" / "learning-os-static.py"


def load_module():
    spec = importlib.util.spec_from_file_location("learning_os_static", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StaticServerTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.server = self.module.create_server("127.0.0.1", 0, ROOT / "outputs")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_root_serves_learning_os_product_without_cache(self):
        with urllib.request.urlopen(f"{self.base_url}/", timeout=5) as response:
            body = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")
        self.assertIn("错题专栏", body)
        self.assertIn("learning-os-app.js", body)

    def test_legacy_handwriting_prototype_remains_directly_accessible(self):
        with urllib.request.urlopen(f"{self.base_url}/learning-os-ui-prototype.html", timeout=5) as response:
            body = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
        self.assertIn("planCurrentRecognitionChunks", body)

    def test_canvas_model_is_not_cached(self):
        with urllib.request.urlopen(
            f"{self.base_url}/learning-os-canvas-model.js?v=20260721-2", timeout=5
        ) as response:
            body = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")
        self.assertIn("planRecognitionChunks", body)


if __name__ == "__main__":
    unittest.main()
