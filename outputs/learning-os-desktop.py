"""Windows desktop launcher for the local-first Learning OS."""

from __future__ import annotations

import importlib.util
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import socket
import sys
import threading
import time
import traceback
import webbrowser

# This normal import is intentional: the service modules below are loaded from
# hyphenated filenames, which PyInstaller cannot statically analyze on its own.
import learning_os_package_dependencies  # noqa: F401


APP_NAME = "Learning OS"
HOST = "127.0.0.1"
STATIC_PORT = 4173
API_PORT = 4174
STARTUP_TIMEOUT_SECONDS = 15
LOG_MAX_BYTES = 512 * 1024
LOG_BACKUP_COUNT = 3


def ensure_standard_streams() -> None:
    """Keep stdlib HTTP handlers functional in PyInstaller windowed builds."""
    for stream_name in ("stdout", "stderr"):
        if getattr(sys, stream_name, None) is None:
            setattr(sys, stream_name, open(os.devnull, "w", encoding="utf-8"))


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)).resolve()


def app_root(environ: dict[str, str] | None = None) -> Path:
    environment = os.environ if environ is None else environ
    return Path(environment.get("LOCALAPPDATA", Path.home())) / APP_NAME


def configure_logger(root: Path) -> tuple[logging.Logger, Path]:
    log_directory = root / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / "launcher.log"
    logger = logging.getLogger("learning_os.launcher")
    logger.setLevel(logging.INFO)
    for existing_handler in logger.handlers:
        existing_handler.close()
    logger.handlers.clear()
    handler = RotatingFileHandler(
        log_path,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger, log_path


def port_is_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.25)
        return probe.connect_ex((HOST, port)) == 0


def existing_service_is_ready() -> bool:
    static_ready = port_is_listening(STATIC_PORT)
    api_ready = port_is_listening(API_PORT)
    if static_ready != api_ready:
        if static_ready:
            raise RuntimeError(f"Static port {STATIC_PORT} is occupied but API port {API_PORT} is not ready")
        raise RuntimeError(f"API port {API_PORT} is occupied but static port {STATIC_PORT} is not ready")
    return static_ready


def wait_for_services(logger: logging.Logger) -> bool:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        static_ready = port_is_listening(STATIC_PORT)
        api_ready = port_is_listening(API_PORT)
        logger.info("health-check static=%s api=%s", static_ready, api_ready)
        if static_ready and api_ready:
            return True
        time.sleep(0.2)
    return False


def show_startup_error(stage: str, error: Exception, log_path: Path) -> None:
    detail = str(error).strip() or type(error).__name__
    detail = detail[:240]
    message = (
        f"{APP_NAME} failed during {stage}.\n\n"
        f"{type(error).__name__}: {detail}\n\n"
        f"Diagnostic log: {log_path}"
    )
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, f"{APP_NAME} startup error", 0x10)
    except Exception:
        # The diagnostic log remains available if a Windows error dialog cannot open.
        pass


def load_module(filename: str, name: str):
    root = resource_root()
    path = root / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required packaged resource is missing: {path.name}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load packaged resource: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- Graceful shutdown machinery -------------------------------------------------
# A single module-level stop event lets the main thread block on a *named* event (so tests
# can assert the app no longer relies on an anonymous one-shot Event wait) and lets a
# controlled shutdown be triggered from a signal handler or the local API without killing any
# other process.
stop_event = threading.Event()
_cleanup_lock = threading.Lock()
_services_cleaned = False


def shutdown_services() -> None:
    """Idempotently stop and release the in-process local services.

    Safe to call from request_shutdown() (e.g. via the local API or a signal) and again from
    main()'s finally block. Never raises, so cleanup can never break process exit.
    """
    global _services_cleaned
    with _cleanup_lock:
        if _services_cleaned:
            return
        _services_cleaned = True
    static_srv = globals().get("static_server")
    api_srv = globals().get("api_server")
    if static_srv is not None:
        try:
            static_srv.shutdown()
        except Exception:
            pass
        try:
            static_srv.server_close()
        except Exception:
            pass
    if api_srv is not None:
        service = getattr(api_srv, "service", None)
        if service is not None:
            try:
                service.close()
            except Exception:
                pass
        try:
            api_srv.shutdown()
        except Exception:
            pass
        try:
            api_srv.server_close()
        except Exception:
            pass


def request_shutdown() -> None:
    """Request a controlled, in-app exit.

    Idempotent: calling it more than once is safe. Sets the stop event and releases the
    loopback ports (4173/4174) so the process can return normally. Does NOT call os._exit()
    and does NOT terminate any other process (by name or by PID).
    """
    stop_event.set()
    shutdown_services()


def _install_signal_handlers() -> None:
    """Register SIGINT/SIGTERM to request a graceful shutdown.

    Must be called from the main thread. Failures are ignored (e.g. when not in the main
    thread); request_shutdown() remains reachable through the local API either way.
    """

    def _handler(signum, frame):  # noqa: ARG001
        request_shutdown()

    try:
        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)
    except (ValueError, OSError):
        pass


def main() -> int:
    ensure_standard_streams()
    root = app_root()
    logger, log_path = configure_logger(root)
    assets = resource_root()
    data_root = root / "data"
    logger.info(
        "launcher-start exe=%s assets=%s cwd=%s app-root=%s data-root=%s",
        sys.executable,
        assets,
        Path.cwd(),
        root,
        data_root,
    )

    api_server = None
    static_server = None
    try:
        if existing_service_is_ready():
            logger.info("existing-local-services static-port=%s api-port=%s", STATIC_PORT, API_PORT)
            webbrowser.open(f"http://{HOST}:{STATIC_PORT}/")
            return 0
        logger.info("loading-packaged-service-modules")
        data_root.mkdir(parents=True, exist_ok=True)
        api = load_module("learning-os-api.py", "learning_os_api")
        static = load_module("learning-os-static.py", "learning_os_static")
        logger.info("creating-local-services host=%s api-port=%s static-port=%s", HOST, API_PORT, STATIC_PORT)
        api_server = api.ThreadingHTTPServer((HOST, API_PORT), api.LearningOSHandler)
        api_server.service = api.LearningOSService(data_root)
        static_server = static.create_server(HOST, STATIC_PORT, assets)
        # Expose for controlled shutdown and wire the in-app stop primitive so the local
        # API (/api/v2/shutdown) and signal handlers can request a clean exit.
        api_server.request_shutdown = request_shutdown
        globals()["api_server"] = api_server
        globals()["static_server"] = static_server
        threading.Thread(target=api_server.serve_forever, daemon=True).start()
        threading.Thread(target=static_server.serve_forever, daemon=True).start()
        _install_signal_handlers()
        if not wait_for_services(logger):
            raise TimeoutError(
                f"Local services did not listen on {STATIC_PORT}/{API_PORT} within {STARTUP_TIMEOUT_SECONDS} seconds"
            )
        logger.info("services-ready static-port=%s api-port=%s", STATIC_PORT, API_PORT)
        webbrowser.open(f"http://{HOST}:{STATIC_PORT}/")
        stop_event.wait()
        return 0
    except Exception as error:
        logger.error("launcher-failed stage=bootstrap type=%s detail=%s", type(error).__name__, str(error)[:240])
        logger.debug("launcher-traceback\n%s", traceback.format_exc())
        show_startup_error("local service bootstrap", error, log_path)
        return 1
    finally:
        shutdown_services()


if __name__ == "__main__":
    raise SystemExit(main())
