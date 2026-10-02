"""Use cases for first-class learning stuck points.

A stuck point is owned by one account, tied to the session it was noticed in,
and moves through an independent ``open -> resolved`` lifecycle. Resolving a
stuck point records *whether* the learner got past it; it never claims mastery
and never writes to problems, attempts or mastery state.
"""

import hashlib
import json

from .domain import PolicyError
from .stuck_point_domain import check_status, clean_note, clean_text
from .stuck_point_schemas import CreateStuckPointInput, PatchStuckPointInput


class StuckPointService:
    def __init__(self, uow):
        self.uow = uow

    @staticmethod
    def _op(data, key, version=None):
        operation_id = str(data.get("operation_id", ""))
        if not operation_id or len(operation_id) > 128 or operation_id != key:
            raise PolicyError("VALIDATION_ERROR", "Idempotency-Key must equal operation_id.", 422)
        fingerprint = hashlib.sha256(
            json.dumps({"body": data, "version": version}, sort_keys=True).encode()
        ).hexdigest()
        return operation_id, fingerprint

    def _write(self, owner, operation, key, fingerprint, callback):
        self.uow.lock_owner(owner)
        cached = self.uow.replay(owner, operation, key, fingerprint)
        if cached is not None:
            return cached
        result = callback()
        result = json.loads(json.dumps(result, default=lambda value: value.isoformat()))
        self.uow.remember(owner, operation, key, fingerprint, result)
        self.uow.commit()
        return result

    def create(self, owner, body, key):
        data = CreateStuckPointInput.model_validate(body).model_dump(mode="json")
        op, fp = self._op(data, key)
        data["text"] = clean_text(data["text"])
        data["session_id"] = str(data["session_id"])
        data["knowledge_point_id"] = (
            str(data["knowledge_point_id"]) if data.get("knowledge_point_id") else None
        )
        data["attempt_id"] = str(data["attempt_id"]) if data.get("attempt_id") else None
        return self._write(
            owner,
            "stuck_point:create",
            op,
            fp,
            lambda: self.uow.stuck_points.create(owner, data),
        )

    def get(self, owner, stuck_point_id):
        self.uow.lock_owner(owner)
        value = self.uow.stuck_points.get(owner, stuck_point_id)
        self.uow.commit()
        return value

    def list(
        self,
        owner,
        *,
        session_id=None,
        knowledge_point_id=None,
        status=None,
        limit=50,
        cursor=None,
    ):
        if not 1 <= limit <= 100:
            raise PolicyError("VALIDATION_ERROR", "Limit must be between 1 and 100.", 422)
        if status is not None:
            check_status(status)
        self.uow.lock_owner(owner)
        rows = self.uow.stuck_points.list(
            owner,
            {
                "session_id": session_id,
                "knowledge_point_id": knowledge_point_id,
                "status": status,
            },
            limit + 1,
            cursor,
        )
        self.uow.commit()
        items = rows[:limit]
        next_cursor = None
        if len(rows) > limit and items:
            import datetime as _datetime

            last = items[-1]
            created = _datetime.datetime.fromisoformat(last["created_at"]).replace(tzinfo=None)
            # URL-safe opaque cursor: naive UTC timestamp + id (no '+' offset).
            next_cursor = f"{created.isoformat()}|{last['id']}"
        return {"items": items, "next_cursor": next_cursor}

    def patch(self, owner, stuck_point_id, body, key, version):
        if version is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        data = PatchStuckPointInput.model_validate(body).model_dump(mode="json", exclude_unset=True)
        op, fp = self._op(data, key, version)
        changes = {}
        if "text" in data:
            changes["text"] = clean_text(data["text"])
        if "status" in data:
            changes["status"] = check_status(data["status"])
        if "resolution_note" in data:
            changes["resolution_note"] = clean_note(data["resolution_note"])
        return self._write(
            owner,
            f"stuck_point:update:{stuck_point_id}",
            op,
            fp,
            lambda: self.uow.stuck_points.patch(owner, stuck_point_id, changes, version),
        )
