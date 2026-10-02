"""Cloud Hermes Core — service composition & entrypoint (Track A owns runtime).

OWNER: Track A (Gateway/Runtime). Wires config + db + events + memory + execution + auth +
provider into HermesService and starts/stops the HTTP server. Structured logging.
"""
from __future__ import annotations

import argparse
import logging
import sys
import threading

from . import app as app_mod
from .auth import AuthService
from .config import Config
from .db import CloudDatabase
from .events import EventStore
from .execution_node import ExecutionQueue
from .memory import MemoryStore
from .provider import build_provider
from .run_orchestrator import HermesService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [hermes.cloud] %(message)s",
)
LOG = logging.getLogger("hermes.cloud")


class CloudHermesApp:
    def __init__(self, config: Config, provider=None):
        self.config = config
        self.db = CloudDatabase(config.db_path)
        self.events = EventStore(self.db)
        self.memory = MemoryStore(self.db, self.events)
        self.execution = ExecutionQueue(self.db, self.events)
        self.auth = AuthService(self.db, self.events, config)
        self.auth.ensure_admin_exists()
        self.service = HermesService(self.db, self.events, self.memory, self.execution, self.auth, config, provider=provider)
        self.server = None

    def bootstrap_admin(self, token: str, username: str, password: str) -> None:
        self.auth.bootstrap_admin(token, username, password)

    def start(self, host: str | None = None, port: int | None = None) -> None:
        self.server = app_mod.make_server(self.config, self.service, host=host, port=port)
        LOG.info("Hermes Cloud Core listening on %s:%s (env=%s, provider_configured=%s, mock=%s)",
                 host or self.config.bind_host, port or self.config.port,
                 self.config.env, self.config.provider_configured(), self.config.mock_provider)
        self.server.serve_forever()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        try:
            self.db.close()
        except Exception:
            pass

    def url(self, port: int) -> str:
        return f"http://{self.config.bind_host}:{port}"


def build_composition(config: Config, provider=None) -> CloudHermesApp:
    """Build the full composition (used by tests with an injected provider)."""
    return CloudHermesApp(config, provider=provider)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes Cloud Core V1")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--env", default=None)
    parser.add_argument("--db", default=None)
    parser.add_argument("--bootstrap-admin", nargs=3, metavar=("TOKEN", "USERNAME", "PASSWORD"),
                        help="One-time admin init: token username password")
    args = parser.parse_args(argv)

    config = Config.from_env()
    if args.env:
        config.env = args.env
    if args.db:
        config.db_path = args.db

    if config.is_production() and not config.secret_key:
        LOG.error("HERMES_SECRET_KEY is required in production. Refusing to start.")
        return 2

    app = CloudHermesApp(config)
    if args.bootstrap_admin:
        token, username, password = args.bootstrap_admin
        try:
            app.bootstrap_admin(token, username, password)
            LOG.info("Admin user %s initialized.", username)
        except Exception as e:
            LOG.error("Admin bootstrap failed: %s", e)
            return 3
        # One-shot bootstrap: initialize the admin and exit. Do NOT fall through to
        # app.start() (which would block serving forever and break `docker compose run
        # --rm ... --bootstrap-admin` used by deploy/rollback verification).
        return 0

    try:
        app.start(host=args.host, port=args.port)
    except KeyboardInterrupt:
        LOG.info("Shutting down.")
    finally:
        app.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
