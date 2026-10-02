"""Cloud Hermes Core — stable error model (Track A owns).

OWNER: Track A (Gateway/Runtime). Error codes are stable strings returned to clients; raw
stack traces are NEVER returned to normal users.
"""
from __future__ import annotations


class HermesError(Exception):
    """Stable, secret-safe error suitable for the API boundary."""

    def __init__(self, code: str, message: str, status: int = 400, *, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}

    def payload(self) -> dict:
        return {"code": self.code, "error": self.message, **self.details}


# code -> default HTTP status. Used by the app layer when status not given.
ERROR_STATUS: dict[str, int] = {
    "HERMES_UNAVAILABLE": 503,
    "AUTH_REQUIRED": 401,
    "AUTH_EXPIRED": 401,
    "AUTH_INVALID": 401,
    "PROVIDER_UNAVAILABLE": 502,
    "PROVIDER_TIMEOUT": 504,
    "PROVIDER_INVALID_RESPONSE": 502,
    "MEMORY_UNAVAILABLE": 503,
    "WRITEBACK_FAILED": 500,
    "RATE_LIMITED": 429,
    "REQUEST_TIMEOUT": 504,
    "INVALID_RESPONSE": 502,
    "LOCAL_EXECUTION_PENDING": 202,
    "VALIDATION_ERROR": 400,
    "CONFLICT": 409,
    "NOT_FOUND": 404,
    "INTERNAL_ERROR": 500,
}


def status_for(code: str, default: int = 400) -> int:
    return ERROR_STATUS.get(code, default)


# Convenience constructors
def hermes_unavailable(msg: str = "Hermes Cloud Core is temporarily unavailable.") -> HermesError:
    return HermesError("HERMES_UNAVAILABLE", msg, status_for("HERMES_UNAVAILABLE"))


def auth_required(msg: str = "Authentication required.") -> HermesError:
    return HermesError("AUTH_REQUIRED", msg, status_for("AUTH_REQUIRED"))


def validation_error(msg: str) -> HermesError:
    return HermesError("VALIDATION_ERROR", msg, status_for("VALIDATION_ERROR"))
