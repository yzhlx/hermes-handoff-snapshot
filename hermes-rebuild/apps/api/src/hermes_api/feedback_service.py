"""Application use cases for reflection and problem feedback writes."""

import hashlib
import json

from .domain import PolicyError
from .feedback import (
    CreateAttempt,
    CreateProblem,
    CreateReflection,
    LinkProblemAttachment,
    UnlinkProblemAttachment,
    UpdateAttempt,
    UpdateReflection,
)
from .feedback_ports import FeedbackUnitOfWork


class FeedbackService:
    def __init__(self, uow: FeedbackUnitOfWork):
        self.uow = uow

    @staticmethod
    def _operation(body, key, action, version=None):
        operation_id = str(body.get("operation_id", ""))
        if not operation_id or len(operation_id) > 128 or key != operation_id:
            raise PolicyError("VALIDATION_ERROR", "Idempotency-Key must equal operation_id.", 422)
        fingerprint = hashlib.sha256(
            json.dumps({"body": body, "version": version}, sort_keys=True).encode()
        ).hexdigest()
        return f"feedback:{action}", operation_id, fingerprint

    def _write(self, owner, action, body, key, callback, version=None):
        operation, op_key, fingerprint = self._operation(body, key, action, version)
        self.uow.lock_owner(owner)
        replay = self.uow.replay(owner, operation, op_key, fingerprint)
        if replay is not None:
            return replay
        result = callback()
        self.uow.remember(owner, operation, op_key, fingerprint, result)
        self.uow.commit()
        return result

    def create_reflection(self, owner, body, key):
        data = CreateReflection.model_validate(body).model_dump(mode="json", exclude_unset=True)
        return self._write(
            owner,
            "reflection:create",
            data,
            key,
            lambda: self.uow.feedback.create_reflection(owner, data),
        )

    def create_problem(self, owner, body, key):
        data = CreateProblem.model_validate(body).model_dump(mode="json")
        return self._write(
            owner,
            "problem:create",
            data,
            key,
            lambda: self.uow.feedback.create_problem(owner, data),
        )

    def update_reflection(self, owner, session_id, body, key, version):
        data = UpdateReflection.model_validate(body).model_dump(mode="json", exclude_unset=True)
        self._require_operation(data, key)
        if version is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        values = {k: v for k, v in data.items() if k != "operation_id"}
        if not values:
            raise PolicyError("VALIDATION_ERROR", "At least one reflection field is required.", 422)
        return self._write(
            owner,
            f"reflection:update:{session_id}",
            data,
            key,
            lambda: self.uow.feedback.update_reflection(owner, session_id, values, version),
            version,
        )

    def update_problem(self, owner, problem_id, body, key, version):
        data = dict(body)
        self._require_operation(data, key)
        if version is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        values = {k: v for k, v in data.items() if k != "operation_id"}
        return self._write(
            owner,
            f"problem:update:{problem_id}",
            data,
            key,
            lambda: self.uow.feedback.update_problem(owner, problem_id, values, version),
            version,
        )

    def link_attachment(self, owner, problem_id, body, key, version):
        data = LinkProblemAttachment.model_validate(body).model_dump(mode="json")
        self._require_operation(data, key)
        if version is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        values = {k: v for k, v in data.items() if k != "operation_id"}
        return self._write(
            owner,
            f"problem:attachment-link:create:{problem_id}",
            data,
            key,
            lambda: self.uow.feedback.link_attachment(owner, problem_id, values, version),
            version,
        )

    def unlink_attachment(self, owner, problem_id, link_id, body, key, version):
        data = UnlinkProblemAttachment.model_validate(body).model_dump(mode="json")
        self._require_operation(data, key)
        if version is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        return self._write(
            owner,
            f"problem:attachment-link:delete:{problem_id}:{link_id}",
            data,
            key,
            lambda: self.uow.feedback.unlink_attachment(owner, problem_id, link_id, version),
            version,
        )

    def create_attempt(self, owner, body, key):
        data = CreateAttempt.model_validate(body).model_dump(mode="json")
        if data.get("other_error_note") and "other" not in data.get("error_categories", []):
            raise PolicyError(
                "VALIDATION_ERROR", "An other-error note needs the other category.", 422
            )
        return self._write(
            owner,
            "attempt:create",
            data,
            key,
            lambda: self.uow.feedback.create_attempt(owner, data),
        )

    def update_attempt(self, owner, attempt_id, body, key, version):
        data = UpdateAttempt.model_validate(body).model_dump(mode="json", exclude_unset=True)
        self._require_operation(data, key)
        if version is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        values = {k: v for k, v in data.items() if k != "operation_id"}
        return self._write(
            owner,
            f"attempt:update:{attempt_id}",
            data,
            key,
            lambda: self.uow.feedback.update_attempt(owner, attempt_id, values, version),
            version,
        )

    @staticmethod
    def _require_operation(body, key):
        if not body.get("operation_id") or str(body["operation_id"]) != key:
            raise PolicyError("VALIDATION_ERROR", "Idempotency-Key must equal operation_id.", 422)
