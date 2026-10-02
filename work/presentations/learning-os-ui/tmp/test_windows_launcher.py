from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[4]
OUTPUTS = ROOT / "outputs"


def load_launcher():
    sys.path.insert(0, str(OUTPUTS))
    try:
        spec = importlib.util.spec_from_file_location("learning_os_desktop_test", OUTPUTS / "learning-os-desktop.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(OUTPUTS))


class WindowsLauncherTests(unittest.TestCase):
    def setUp(self):
        self.launcher = load_launcher()

    def test_app_root_uses_localappdata_without_current_working_directory(self):
        path = self.launcher.app_root({"LOCALAPPDATA": r"C:\\QA Root 中文 Space"})
        self.assertEqual(path, Path(r"C:\\QA Root 中文 Space") / "Learning OS")

    def test_resource_root_prefers_pyinstaller_resource_directory(self):
        sentinel = Path(tempfile.gettempdir()) / "learning-os-meipass-test"
        original = getattr(sys, "_MEIPASS", None)
        sys._MEIPASS = str(sentinel)
        try:
            self.assertEqual(self.launcher.resource_root(), sentinel.resolve())
        finally:
            if original is None:
                del sys._MEIPASS
            else:
                sys._MEIPASS = original

    def test_dynamic_package_dependency_manifest_imports_service_requirements(self):
        dependency = __import__("learning_os_package_dependencies")
        required = dependency.PACKAGED_DYNAMIC_IMPORTS
        self.assertIn(dependency.ThreadPoolExecutor, required)
        self.assertIn(dependency.ThreadingHTTPServer, required)
        self.assertIn(dependency.sqlite3, required)

    def test_windowed_runtime_replaces_missing_standard_streams(self):
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = None
        sys.stderr = None
        try:
            self.launcher.ensure_standard_streams()
            self.assertIsNotNone(sys.stdout)
            self.assertIsNotNone(sys.stderr)
            self.assertTrue(hasattr(sys.stderr, "write"))
        finally:
            if sys.stdout is not None:
                sys.stdout.close()
            if sys.stderr is not None:
                sys.stderr.close()
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def test_static_port_without_api_is_reported_as_a_conflict(self):
        with patch.object(self.launcher, "port_is_listening", side_effect=[True, False]):
            with self.assertRaisesRegex(RuntimeError, "Static port 4173"):
                self.launcher.existing_service_is_ready()

    def test_logger_creates_rotating_log_in_local_app_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            logger, log_path = self.launcher.configure_logger(Path(temporary))
            try:
                logger.info("launcher-test-event")
                for handler in logger.handlers:
                    handler.flush()
                self.assertTrue(log_path.is_file())
                self.assertIn("launcher-test-event", log_path.read_text(encoding="utf-8"))
            finally:
                for handler in list(logger.handlers):
                    handler.close()
                    logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
