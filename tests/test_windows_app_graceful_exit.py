"""Graceful-exit test suite for the Windows launcher.

Covers the controlled-shutdown contract required by the fix:
  - request_shutdown() exists, is idempotent, releases 4173/4174, and sets the stop event;
  - SIGINT/SIGTERM handlers request a shutdown;
  - the main thread no longer blocks on an anonymous threading.Event().wait();
  - cleanup runs exactly once and main() returns normally;
  - the loopback shutdown endpoint is POST-only, origin-checked, and rejects foreign origins;
  - the user-facing exit entry (button + confirm dialog) exists in the UI;
  - the canvas draft capability is untouched by the exit fix.

The launcher is imported (not executed) so no real browser or long-lived server is started
outside the explicit, daemon-threaded servers created by these tests.
"""

import http.server
import importlib.util
import os
import signal
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
LAUNCHER = OUTPUTS / "learning-os-desktop.py"


def load_launcher():
    # The launcher imports learning_os_package_dependencies at module level; make outputs
    # importable. main() only runs under __main__, so importing is side-effect free.
    if str(OUTPUTS) not in sys.path:
        sys.path.insert(0, str(OUTPUTS))
    spec = importlib.util.spec_from_file_location("learning_os_desktop", LAUNCHER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reset_state(module):
    module._services_cleaned = False
    module.stop_event = threading.Event()
    module.__dict__.pop("static_server", None)
    module.__dict__.pop("api_server", None)


@contextmanager
def launcher_servers(module):
    """Start the same two servers main() starts, in-process, without opening a browser."""
    static = module.load_module("learning-os-static.py", "learning_os_static")
    api = module.load_module("learning-os-api.py", "learning_os_api")
    isolated_root = Path(tempfile.mkdtemp(prefix="exit_qa_"))
    data_root = isolated_root / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    module.static_server = static.create_server(module.HOST, module.STATIC_PORT, OUTPUTS)
    module.api_server = http.server.ThreadingHTTPServer(
        (module.HOST, module.API_PORT), api.LearningOSHandler
    )
    # Wire the in-app stop primitive exactly as main() does.
    module.api_server.request_shutdown = module.request_shutdown
    t_static = threading.Thread(target=module.static_server.serve_forever, daemon=True)
    t_api = threading.Thread(target=module.api_server.serve_forever, daemon=True)
    t_static.start()
    t_api.start()
    try:
        yield (module.static_server, module.api_server)
    finally:
        for server in (module.static_server, module.api_server):
            try:
                server.server_close()
            except Exception:
                pass
        _reset_state(module)


def _shutdown_http(method, module, origin):
    url = f"http://{module.HOST}:{module.API_PORT}/api/v2/shutdown"
    body = None if method == "GET" else b"{}"
    req = urllib.request.Request(url, data=body, method=method)
    if origin:
        req.add_header("Origin", origin)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def _wait_port_closed(port, timeout=3.0):
    """Wait until a loopback port stops listening (clean shutdown is not instantaneous)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                return True
        time.sleep(0.05)
    return False


class WindowsAppGracefulExitTests(unittest.TestCase):
    def test_launcher_exposes_request_shutdown(self):
        module = load_launcher()
        self.assertTrue(
            hasattr(module, "request_shutdown"),
            "Launcher must expose request_shutdown() for a controlled, in-app exit",
        )
        self.assertTrue(
            isinstance(getattr(module, "stop_event", None), threading.Event),
            "Launcher must expose a named stop_event the main thread waits on",
        )

    def test_graceful_shutdown_releases_ports(self):
        module = load_launcher()
        _reset_state(module)
        with launcher_servers(module):
            self.assertTrue(module.port_is_listening(module.STATIC_PORT))
            self.assertTrue(module.port_is_listening(module.API_PORT))
            module.request_shutdown()
            self.assertFalse(module.port_is_listening(module.STATIC_PORT))
            self.assertFalse(module.port_is_listening(module.API_PORT))
            self.assertTrue(module.stop_event.is_set())

    def test_request_shutdown_idempotent(self):
        module = load_launcher()
        _reset_state(module)
        with launcher_servers(module):
            self.assertTrue(module.port_is_listening(module.STATIC_PORT))
            self.assertTrue(module.port_is_listening(module.API_PORT))
            module.request_shutdown()
            self.assertTrue(module.stop_event.is_set())
            self.assertFalse(module.port_is_listening(module.STATIC_PORT))
            self.assertFalse(module.port_is_listening(module.API_PORT))
            # A second call must be safe and not error.
            module.request_shutdown()
            self.assertFalse(module.port_is_listening(module.STATIC_PORT))
            self.assertFalse(module.port_is_listening(module.API_PORT))

    def test_stop_event_unblocks_main_wait(self):
        module = load_launcher()
        _reset_state(module)
        self.assertFalse(module.stop_event.wait(timeout=0.2))
        threading.Timer(0.1, module.request_shutdown).start()
        # The named stop event must release the main-thread wait triggered by a shutdown.
        self.assertTrue(module.stop_event.wait(timeout=2.0))

    def test_signal_handlers_request_exit(self):
        module = load_launcher()
        _reset_state(module)
        with mock.patch("signal.signal") as sig:
            module._install_signal_handlers()
            handlers = {call.args[0]: call.args[1] for call in sig.call_args_list}
            self.assertIn(signal.SIGINT, handlers)
            self.assertIn(signal.SIGTERM, handlers)
            # Invoking the SIGINT handler must request a shutdown.
            module.stop_event = threading.Event()
            module._services_cleaned = False
            handlers[signal.SIGINT](signal.SIGINT, None)
            self.assertTrue(module.stop_event.is_set())

    def test_no_anonymous_event_wait(self):
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertNotIn(
            "threading.Event().wait()",
            source,
            "Main thread must not block on an anonymous threading.Event().wait()",
        )
        self.assertIn("stop_event.wait()", source, "Main thread must wait on the named stop_event")
        self.assertIn("request_shutdown", source)

    def test_cleanup_runs_once(self):
        module = load_launcher()
        _reset_state(module)
        closes = {"n": 0}

        class FakeServer:
            service = None

            def shutdown(self):
                pass

            def server_close(self):
                closes["n"] += 1

        module.static_server = FakeServer()
        module.api_server = FakeServer()
        # First call closes both servers (2 close calls).
        module.shutdown_services()
        first_pass = closes["n"]
        self.assertEqual(first_pass, 2)
        # A second call and a request_shutdown() must NOT close anything again (idempotent).
        module.shutdown_services()
        module.request_shutdown()
        self.assertEqual(closes["n"], first_pass)

    def test_main_returns_zero_on_controlled_shutdown(self):
        module = load_launcher()
        _reset_state(module)
        module.stop_event.set()  # simulate a shutdown already requested
        isolated = Path(tempfile.mkdtemp(prefix="exit_main_"))
        saved = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = str(isolated)
        try:
            with mock.patch.object(module, "webbrowser") as wb:
                wb.open = lambda *a, **k: None
                self.assertFalse(module.port_is_listening(module.STATIC_PORT))
                self.assertFalse(module.port_is_listening(module.API_PORT))
                rc = module.main()
            self.assertEqual(rc, 0)
        finally:
            if saved is None:
                os.environ.pop("LOCALAPPDATA", None)
            else:
                os.environ["LOCALAPPDATA"] = saved
            try:
                module.shutdown_services()
            except Exception:
                pass
            _reset_state(module)

    def test_shutdown_endpoint_post_only(self):
        module = load_launcher()
        _reset_state(module)
        with launcher_servers(module):
            # GET must NOT trigger shutdown.
            status, _ = _shutdown_http("GET", module, "http://127.0.0.1:4173")
            self.assertNotEqual(status, 200)
            self.assertTrue(module.port_is_listening(module.API_PORT))
            # POST with a valid same-origin request triggers a clean shutdown.
            status, body = _shutdown_http("POST", module, "http://127.0.0.1:4173")
            self.assertEqual(status, 200)
            self.assertIn("shutting_down", body)
            # The response is sent before the in-app shutdown runs, so poll for release.
            self.assertTrue(_wait_port_closed(module.API_PORT))
            self.assertTrue(_wait_port_closed(module.STATIC_PORT))

    def test_shutdown_endpoint_rejects_foreign_origin(self):
        module = load_launcher()
        _reset_state(module)
        with launcher_servers(module):
            status, _ = _shutdown_http("POST", module, "http://evil.example.com")
            self.assertEqual(status, 403)
            self.assertTrue(module.port_is_listening(module.API_PORT))
            self.assertTrue(module.port_is_listening(module.STATIC_PORT))
            status2, _ = _shutdown_http("POST", module, None)
            self.assertEqual(status2, 403)
            self.assertTrue(module.port_is_listening(module.API_PORT))

    def test_exit_entry_exists_in_html(self):
        html = (OUTPUTS / "learning-os-app.html").read_text(encoding="utf-8")
        self.assertIn('id="exitAppButton"', html, "Settings page must expose an exit button")
        self.assertIn('id="exitStatus"', html)

    def test_exit_confirm_dialog_exists(self):
        html = (OUTPUTS / "learning-os-app.html").read_text(encoding="utf-8")
        self.assertIn('id="exitConfirmDialog"', html, "Exit must require a confirm dialog")
        self.assertIn('id="confirmExit"', html)
        self.assertIn('id="cancelExit"', html)
        # The JS must wire the button -> confirm dialog -> POST to the loopback API.
        js = (OUTPUTS / "learning-os-app.js").read_text(encoding="utf-8")
        self.assertIn("exitAppButton", js)
        self.assertIn("exitConfirmDialog", js)
        self.assertIn("request('/shutdown'", js)

    def test_canvas_draft_capability_intact(self):
        module = load_launcher()
        ws = OUTPUTS / "learning-os-handwriting-workspace.js"
        content = ws.read_text(encoding="utf-8")
        self.assertIn("draftStorageKey", content, "Canvas draft persistence must remain intact")
        before = ws.stat().st_mtime
        _reset_state(module)
        module.request_shutdown()
        after = ws.stat().st_mtime
        self.assertEqual(before, after, "Exit fix must not modify the canvas workspace source")


if __name__ == "__main__":
    unittest.main()
