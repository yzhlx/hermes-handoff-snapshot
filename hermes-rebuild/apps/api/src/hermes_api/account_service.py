"""Use cases for account data sovereignty (03 §9).

An export never leaves the owner's own records and never includes credentials or
storage internals. A deletion is a two-step, revocable state change: the first
confirmation creates a pending request and stops new writes; cancelling restores
the account; completing it purges the owner's rows and keeps a tombstone.
"""

import hashlib
import json

from .account_domain import check_confirmation
from .account_schemas import (
    CancelDeletionInput,
    CreateDeletionInput,
    CreateExportInput,
    PurgeDeletionInput,
)
from .domain import PolicyError


class AccountService:
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

    def status(self, owner, username, timezone):
        self.uow.lock_owner(owner)
        counts = self.uow.account.count_records(owner)
        deletion = self.uow.account.pending_deletion(owner) or self.uow.account.latest_deletion(
            owner
        )
        value = {
            "status": self.uow.account.status(owner),
            "username": username,
            "timezone": timezone,
            "record_count": sum(counts.values()),
            "deletion": deletion,
        }
        self.uow.commit()
        return value

    def create_export(self, owner, body, key):
        data = CreateExportInput.model_validate(body).model_dump(mode="json")
        op, fp = self._op(data, key)
        return self._write(
            owner, "account:export", op, fp, lambda: self.uow.account.create_export(owner, data)
        )

    def list_exports(self, owner, limit=20):
        if not 1 <= limit <= 100:
            raise PolicyError("VALIDATION_ERROR", "Limit must be between 1 and 100.", 422)
        self.uow.lock_owner(owner)
        items = self.uow.account.list_exports(owner, limit)
        self.uow.commit()
        return {"items": items, "next_cursor": None}

    def download(self, owner, export_id):
        self.uow.lock_owner(owner)
        row = self.uow.account.download_export(owner, export_id)
        self.uow.commit()
        return {
            "id": row["id"],
            "document": json.loads(row["payload"]),
            "byte_size": row["byte_size"],
            "sha256": row["sha256"],
            "expires_at": row["expires_at"],
        }

    def request_deletion(self, owner, body, key):
        data = CreateDeletionInput.model_validate(body).model_dump(mode="json")
        check_confirmation(data.get("confirmation"))
        op, fp = self._op(data, key)
        return self._write(
            owner,
            "account:deletion",
            op,
            fp,
            lambda: self.uow.account.create_deletion(owner, data),
        )

    def cancel_deletion(self, owner, body, key, version):
        if version is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        data = CancelDeletionInput.model_validate(body).model_dump(mode="json")
        op, fp = self._op(data, key, version)
        return self._write(
            owner,
            "account:deletion:cancel",
            op,
            fp,
            lambda: self.uow.account.cancel_deletion(owner, version),
        )

    def complete_deletion(self, owner, body, key, version):
        if version is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        data = PurgeDeletionInput.model_validate(body).model_dump(mode="json")
        # The phrase is required twice: once to ask, once to actually destroy.
        check_confirmation(data.get("confirmation"))
        op, fp = self._op(data, key, version)
        return self._write(
            owner,
            "account:deletion:purge",
            op,
            fp,
            lambda: self.uow.account.complete_deletion(owner, version),
        )
