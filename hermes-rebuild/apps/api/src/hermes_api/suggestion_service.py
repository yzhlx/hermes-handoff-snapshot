"""Use cases for fresh, deterministic suggestions and idempotent user actions."""

import hashlib
import json
from datetime import UTC, datetime

from .domain import PolicyError
from .suggestion_domain import RULE_VERSION, validate_action
from .suggestion_ports import SuggestionUnitOfWork


class SuggestionService:
    def __init__(self, uow: SuggestionUnitOfWork, clock=lambda: datetime.now(UTC)):
        self.uow, self.clock = uow, clock

    def list(
        self, owner_id, *, kind=None, subject_id=None, status="available", limit=20, cursor=None
    ):
        if not 1 <= limit <= 100:
            raise PolicyError("VALIDATION_ERROR", "Limit must be between 1 and 100.", 422)
        if status not in {"available", "accepted", "snoozed", "dismissed", "stale", "all"}:
            raise PolicyError("VALIDATION_ERROR", "Invalid suggestion status.", 422)
        if kind not in {None, "continue", "unverified", "review", "repeated_error"}:
            raise PolicyError("VALIDATION_ERROR", "Invalid suggestion kind.", 422)
        now = self.clock().astimezone(UTC)
        self.uow.lock_owner(owner_id)
        rows = self.uow.suggestions.list_suggestions(
            owner_id,
            {"kind": kind, "subject_id": subject_id, "status": status, "now": now},
            limit + 1,
            cursor,
        )
        self.uow.commit()
        page = rows[:limit]
        return {
            "items": page,
            "next_cursor": page[-1]["id"] if len(rows) > limit else None,
            "rule_version": RULE_VERSION,
        }

    def get(self, owner_id, suggestion_id):
        now = self.clock().astimezone(UTC)
        self.uow.lock_owner(owner_id)
        result = self.uow.suggestions.get_suggestion(owner_id, suggestion_id, now)
        self.uow.commit()
        return result

    def act(self, owner_id, suggestion_id, body, idempotency_key, version):
        if (
            not idempotency_key
            or idempotency_key != body["operation_id"]
            or len(idempotency_key) > 128
        ):
            raise PolicyError("VALIDATION_ERROR", "Idempotency-Key must equal operation_id.", 422)
        now = self.clock().astimezone(UTC)
        fingerprint = hashlib.sha256(
            json.dumps({"body": body, "version": version}, sort_keys=True, default=str).encode()
        ).hexdigest()
        operation = f"suggestion:{suggestion_id}:{body['action']}"
        self.uow.lock_owner(owner_id)
        # Recompute the source set before replaying a key so an old success can never
        # claim that an item is still actionable after its evidence changed.
        self.uow.suggestions.candidates(owner_id, now)
        cached = self.uow.replay(owner_id, operation, idempotency_key, fingerprint)
        if cached is not None:
            current = self.uow.suggestions.get_suggestion(owner_id, suggestion_id, now)
            self.uow.commit()
            return current
        until = validate_action(body["action"], body.get("snoozed_until"), now)
        result = self.uow.suggestions.act(
            owner_id, suggestion_id, body["action"], until, version, now
        )
        self.uow.remember(owner_id, operation, idempotency_key, fingerprint, result)
        self.uow.commit()
        return result
