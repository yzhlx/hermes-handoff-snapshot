"""Browser-driven verification of the user-accessible graceful-exit entry.

This is the process-level complement to the backend suite: it starts the real static and API
servers in-process, loads the UI in headless Chromium, and verifies that a normal user can
discover the exit button, must confirm before exiting, and that confirming sends a real POST
to the loopback API which shuts the services down and releases 4173/4174.

Closing the browser tab is intentionally NOT the exit trigger; only the confirmed button is.
"""

import http.server
import importlib.util
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
PAGE_URL = "http://127.0.0.1:4173/"


def load_launcher():
    if str(OUTPUTS) not in sys.path:
        sys.path.insert(0, str(OUTPUTS))
    spec = importlib.util.spec_from_file_location(
        "learning_os_desktop_exitui", OUTPUTS / "learning-os-desktop.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wait_port_closed(port, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                return True
        time.sleep(0.05)
    return False


class ExitEntryUITests(unittest.TestCase):
    def setUp(self):
        self.module = load_launcher()
        self._saved_localappdata = os.environ.get("LOCALAPPDATA")
        self.isolated = Path(tempfile.mkdtemp(prefix="exit_ui_"))
        os.environ["LOCALAPPDATA"] = str(self.isolated)
        self.profile = Path(tempfile.mkdtemp(prefix="exit_ui_profile_"))
        self._start_servers()
        from playwright.sync_api import sync_playwright

        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile),
            channel="chrome",
            headless=True,
        )
        self.page = self.context.new_page()
        self.page.goto(PAGE_URL, wait_until="load")

    def _start_servers(self):
        static = self.module.load_module("learning-os-static.py", "learning_os_static_exitui")
        api = self.module.load_module("learning-os-api.py", "learning_os_api_exitui")
        self.module.static_server = static.create_server(
            self.module.HOST, self.module.STATIC_PORT, OUTPUTS
        )
        self.module.api_server = http.server.ThreadingHTTPServer(
            (self.module.HOST, self.module.API_PORT), api.LearningOSHandler
        )
        self.module.api_server.request_shutdown = self.module.request_shutdown
        threading.Thread(target=self.module.static_server.serve_forever, daemon=True).start()
        threading.Thread(target=self.module.api_server.serve_forever, daemon=True).start()
        self.assertTrue(self.module.port_is_listening(self.module.STATIC_PORT))
        self.assertTrue(self.module.port_is_listening(self.module.API_PORT))

    def tearDown(self):
        try:
            self.context.close()
        except Exception:
            pass
        try:
            self.playwright.stop()
        except Exception:
            pass
        try:
            self.module.shutdown_services()
        except Exception:
            pass
        self.module._services_cleaned = False
        self.module.stop_event = threading.Event()
        self.module.__dict__.pop("static_server", None)
        self.module.__dict__.pop("api_server", None)
        if self._saved_localappdata is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self._saved_localappdata
        shutil.rmtree(self.isolated, ignore_errors=True)
        shutil.rmtree(self.profile, ignore_errors=True)

    def test_exit_entry_discoverable_and_confirmed(self):
        page = self.page
        # Open the settings page (the natural home of the exit entry).
        page.evaluate("showPage('settings')")
        page.wait_for_selector("#exitAppButton", state="visible", timeout=10_000)
        self.assertTrue(page.is_visible("#exitAppButton"))

        # Clicking the exit button must open the confirmation dialog (confirm before exit).
        page.click("#exitAppButton", force=True)
        page.wait_for_selector("#exitConfirmDialog", state="visible", timeout=5_000)
        self.assertTrue(page.evaluate("document.querySelector('#exitConfirmDialog').open"))

        # The destructive action is gated behind the confirm button only.
        self.assertTrue(page.is_visible("#confirmExit"))
        self.assertTrue(page.is_visible("#cancelExit"))

        # Cancel must close the dialog without shutting down.
        page.click("#cancelExit", force=True)
        page.wait_for_selector("#exitConfirmDialog", state="hidden", timeout=5_000)
        self.assertTrue(self.module.port_is_listening(self.module.API_PORT))

        # Confirm triggers a real POST to the loopback API and shuts the app down.
        page.click("#exitAppButton", force=True)
        page.wait_for_selector("#exitConfirmDialog", state="visible", timeout=5_000)
        page.click("#confirmExit", force=True)
        page.wait_for_function(
            "document.querySelector('#exitStatus').textContent.includes('已退出')",
            timeout=10_000,
        )
        # The background services must actually stop and release the ports.
        self.assertTrue(_wait_port_closed(self.module.API_PORT))
        self.assertTrue(_wait_port_closed(self.module.STATIC_PORT))


if __name__ == "__main__":
    unittest.main()
