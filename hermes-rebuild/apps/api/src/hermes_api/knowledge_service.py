"""Use cases for chapter, knowledge-point and problem-link writes."""

import hashlib
import json
from uuid import uuid4

from .domain import PolicyError
from .knowledge_ports import KnowledgeUnitOfWork


class KnowledgeService:
    def __init__(self, uow: KnowledgeUnitOfWork):
        self.uow = uow

    def write(self, owner, action, body, key, version=None, resource_id=None):
        operation_id = body.get("operation_id")
        if not key or key != str(operation_id) or len(key) > 128:
            raise PolicyError("VALIDATION_ERROR", "Idempotency-Key must equal operation_id.", 422)
        payload = {**body, "operation_id": str(operation_id)}
        fingerprint = hashlib.sha256(
            json.dumps({"body": payload, "version": version}, sort_keys=True).encode()
        ).hexdigest()
        operation = f"knowledge:{action}:{resource_id or ''}"
        self.uow.lock_owner(owner)
        if replay := self.uow.replay(owner, operation, key, fingerprint):
            return replay
        if action == "create_chapter":
            values = {**payload, "id": str(uuid4()), "subject_id": str(body["subject_id"])}
            result = self.uow.knowledge.create_chapter(owner, values)
        elif action == "patch_chapter":
            result = self.uow.knowledge.update_chapter(owner, resource_id, body, version)
        elif action == "create_point":
            values = {**payload, "id": str(uuid4()), "chapter_id": str(body["chapter_id"])}
            result = self.uow.knowledge.create_point(owner, values)
        elif action == "patch_point":
            result = self.uow.knowledge.update_point(owner, resource_id, body, version)
        elif action == "link_problem":
            result = self.uow.knowledge.link_problem(
                owner, resource_id, [str(value) for value in body["knowledge_point_ids"]], version
            )
        else:
            raise AssertionError(f"Unknown knowledge operation: {action}")
        self.uow.remember(owner, operation, key, fingerprint, result)
        self.uow.commit()
        return result
