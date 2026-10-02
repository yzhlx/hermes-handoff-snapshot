"""Application service for user declarations and live evidence summaries."""

import hashlib
import json

from .domain import PolicyError
from .evidence_ports import EvidenceUnitOfWork
from .evidence_schemas import CreateMasteryAssessment


class EvidenceService:
    def __init__(self, uow: EvidenceUnitOfWork):
        self.uow = uow

    def get_evidence(self, owner_id: str, point_id: str) -> dict:
        return self.uow.evidence.get_knowledge_point_evidence(owner_id, point_id)

    def create_assessment(
        self, owner_id: str, body: dict, idempotency_key: str, point_version: int | None
    ) -> dict:
        data = CreateMasteryAssessment.model_validate(body).model_dump(mode="json")
        operation_id = data["operation_id"]
        if idempotency_key != operation_id:
            raise PolicyError("VALIDATION_ERROR", "Idempotency-Key must equal operation_id.", 422)
        if point_version is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        fingerprint = hashlib.sha256(
            json.dumps(
                {"body": data, "knowledge_point_version": point_version},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        operation = f"mastery-assessment:create:{data['knowledge_point_id']}"
        self.uow.lock_owner(owner_id)
        cached = self.uow.replay(owner_id, operation, operation_id, fingerprint)
        if cached is not None:
            return cached
        result = self.uow.evidence.create_assessment(owner_id, data, point_version)
        self.uow.remember(owner_id, operation, operation_id, fingerprint, result)
        self.uow.commit()
        return result
