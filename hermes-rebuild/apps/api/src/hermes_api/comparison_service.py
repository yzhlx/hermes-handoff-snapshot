"""Use cases for persisted problem comparisons."""

import hashlib
import json

from .comparison_domain import FIELDS, validate_texts
from .comparison_schemas import CreateComparisonInput, PatchComparisonInput
from .domain import PolicyError


class ComparisonService:
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
        data = CreateComparisonInput.model_validate(body).model_dump(mode="json")
        op, fp = self._op(data, key)
        data.update(validate_texts(data, require_content=True))
        data["left_problem_id"] = str(data["left_problem_id"])
        data["right_problem_id"] = str(data["right_problem_id"])
        data["left_attempt_id"] = str(data["left_attempt_id"]) if data["left_attempt_id"] else None
        data["right_attempt_id"] = (
            str(data["right_attempt_id"]) if data["right_attempt_id"] else None
        )
        return self._write(
            owner, "comparison:create", op, fp, lambda: self.uow.comparisons.create(owner, data)
        )

    def get(self, owner, cid):
        self.uow.lock_owner(owner)
        value = self.uow.comparisons.get(owner, cid)
        self.uow.commit()
        return value

    def list(
        self, owner, *, problem_id=None, subject_id=None, archived=None, limit=50, cursor=None
    ):
        if not 1 <= limit <= 100:
            raise PolicyError("VALIDATION_ERROR", "Limit must be between 1 and 100.", 422)
        self.uow.lock_owner(owner)
        rows = self.uow.comparisons.list(
            owner,
            {"problem_id": problem_id, "subject_id": subject_id, "archived": archived},
            limit + 1,
            cursor,
        )
        self.uow.commit()
        items = rows[:limit]
        return {"items": items, "next_cursor": items[-1]["id"] if len(rows) > limit else None}

    def patch(self, owner, cid, body, key, version):
        if version is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        data = PatchComparisonInput.model_validate(body).model_dump(mode="json", exclude_unset=True)
        op, fp = self._op(data, key, version)
        changes = {field: data[field] for field in FIELDS if field in data}
        changes.update(validate_texts(changes, require_content=False))
        if "archived" in data:
            changes["archived"] = data["archived"]

        def update_comparison():
            merged = self.uow.comparisons.get(owner, cid)
            merged.update(changes)
            if not any((merged.get(field) or "").strip() for field in FIELDS):
                raise PolicyError(
                    "VALIDATION_ERROR", "At least one comparison field must contain text.", 422
                )
            return self.uow.comparisons.patch(owner, cid, changes, version)

        return self._write(
            owner,
            f"comparison:update:{cid}",
            op,
            fp,
            update_comparison,
        )
