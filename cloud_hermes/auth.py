"""Cloud Hermes Core — authentication & sessions (Track D owns).

OWNER: Track D (Security/Deployment). Implements AUTH-CONTRACT:
- PBKDF2-HMAC-SHA256 password hash (per-user salt), never plaintext.
- DB-backed sessions with expiry; only the SHA-256 of the token is stored.
- Bearer access token for non-browser clients; HttpOnly+Secure+SameSite cookie for browser.
- CSRF token for cookie state-changing requests.
- Login attempt rate limiting. Session/device revocation. Audited login/logout events.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import secrets
import time
import uuid

from .db import CloudDatabase, _utc_now
from .events import EventStore
from .errors import HermesError, auth_required, status_for


PBKDF2_ITER = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITER)
    return f"pbkdf2_sha256${PBKDF2_ITER}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iter_s, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iter_s))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, db: CloudDatabase, events: EventStore, config):
        self.db = db
        self.events = events
        self.config = config
        # in-memory rate-limit window keyed by (username,ip)
        self._attempts: dict[tuple[str, str], list[float]] = {}

    # ---- admin bootstrap ----
    def bootstrap_admin(self, token: str, username: str, password: str) -> None:
        """One-time admin init using ADMIN_INIT_TOKEN; idempotent if already initialized."""
        if not self.config.admin_init_token:
            raise HermesError("INTERNAL_ERROR", "Admin init token not configured.", 500)
        if not hmac.compare_digest(token, self.config.admin_init_token):
            raise HermesError("AUTH_INVALID", "Invalid admin init token.", 401)
        row = self.db.query_one("SELECT * FROM users WHERE username=?", (username,))
        if row and row["admin_initialized"]:
            return  # already initialized (idempotent across restarts on the same DB)
        if row:
            self.db.execute("UPDATE users SET password_hash=?, admin_initialized=1 WHERE id=?", (hash_password(password), row["id"]))
        else:
            uid = f"user_{uuid.uuid4().hex}"
            self.db.execute(
                "INSERT INTO users(id, username, password_hash, role, created_at, admin_initialized) VALUES(?,?,?,?,?,?)",
                (uid, username, hash_password(password), "admin", _utc_now(), 1),
            )

    def ensure_admin_exists(self) -> None:
        row = self.db.query_one("SELECT id FROM users LIMIT 1")
        if not row:
            # create a disabled placeholder so bootstrap is required
            self.db.execute(
                "INSERT INTO users(id, username, password_hash, role, created_at, admin_initialized) VALUES(?,?,?,?,?,?)",
                (f"user_{uuid.uuid4().hex}", "__pending__", hash_password(secrets.token_hex(16)), "admin", _utc_now(), 0),
            )

    # ---- login ----
    def _rate_limited(self, username: str, ip: str) -> bool:
        now = time.time()
        key = (username, ip)
        window = self._attempts.get(key, [])
        cutoff = now - self.config.login_rate_limit_window_seconds
        window = [t for t in window if t > cutoff]
        self._attempts[key] = window
        return len(window) >= self.config.login_rate_limit_count

    def _record_attempt(self, username: str, ip: str) -> None:
        key = (username, ip)
        self._attempts.setdefault(key, []).append(time.time())

    def login(self, username: str, password: str, device_id: str | None, ip: str) -> dict:
        if self._rate_limited(username, ip):
            self.events.append("LoginBlocked", "auth", f"login:{username}:{ip}",
                               {"username": username, "ip": ip}, actor="system", source="auth")
            raise HermesError("RATE_LIMITED", "Too many failed login attempts. Try again later.", status_for("RATE_LIMITED"))
        row = self.db.query_one("SELECT * FROM users WHERE username=?", (username,))
        if not row or not verify_password(password, row["password_hash"]):
            self._record_attempt(username, ip)
            self.events.append("LoginFailed", "auth", f"login:{username}:{ip}",
                               {"username": username, "ip": ip}, actor="system", source="auth")
            raise HermesError("AUTH_INVALID", "Invalid username or password.", status_for("AUTH_INVALID"))
        token = secrets.token_hex(32)
        csrf = secrets.token_hex(16)
        expires = int(time.time()) + self.config.access_token_ttl_seconds
        self.db.execute(
            "INSERT INTO sessions(id, user_id, token_hash, device_id, csrf_token, created_at, expires_at, revoked) "
            "VALUES(?,?,?,?,?,?,?,0)",
            (f"sess_{uuid.uuid4().hex}", row["id"], _token_hash(token), device_id, csrf, _utc_now(),
             time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expires))),
        )
        self.events.append("LoginSucceeded", "auth", row["id"],
                           {"username": username, "device_id": device_id, "ip": ip},
                           actor=username, source="auth", correlation_id=row["id"])
        return {"access_token": token, "csrf_token": csrf, "expires_at": expires, "user_id": row["id"]}

    def _parse_expiry(self, expires_at: str) -> int:
        try:
            import datetime
            dt = datetime.datetime.strptime(expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
            return int(dt.timestamp())
        except Exception:
            return 0

    def authenticate(self, authorization: str | None, cookie_token: str | None) -> dict:
        """Return the session row (dict) for a valid, unexpired, unrevoked session, else raise."""
        token = None
        if authorization:
            parts = authorization.split(" ", 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1].strip()
        if not token and cookie_token:
            token = cookie_token
        if not token:
            raise auth_required()
        row = self.db.query_one(
            "SELECT * FROM sessions WHERE token_hash=? AND revoked=0", (_token_hash(token),)
        )
        if not row:
            raise HermesError("AUTH_INVALID", "Invalid or revoked session.", status_for("AUTH_INVALID"))
        if self._parse_expiry(row["expires_at"]) < int(time.time()):
            raise HermesError("AUTH_EXPIRED", "Session expired. Please log in again.", status_for("AUTH_EXPIRED"))
        return dict(row)

    def csrf_valid(self, session: dict, csrf_header: str | None) -> bool:
        if not csrf_header:
            return False
        return hmac.compare_digest(csrf_header, session.get("csrf_token") or "")

    def logout(self, session: dict) -> None:
        self.db.execute("UPDATE sessions SET revoked=1 WHERE id=?", (session["id"],))
        self.events.append("Logout", "auth", session["user_id"],
                           {"session_id": session["id"]}, actor=session.get("user_id"), source="auth",
                           correlation_id=session["user_id"])

    def revoke_device(self, user_id: str, device_id: str) -> None:
        self.db.execute("UPDATE sessions SET revoked=1 WHERE user_id=? AND device_id=?", (user_id, device_id))
        self.events.append("DeviceRevoked", "auth", user_id, {"device_id": device_id},
                           actor=user_id, source="auth", correlation_id=user_id)
