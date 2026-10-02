"""Ports for evidence application services."""

from typing import Protocol


class EvidenceRepository(Protocol):
    def get_knowledge_point_evidence(self, owner_id: str, point_id: str) -> dict: ...

    def create_assessment(self, owner_id: str, values: dict, point_version: int) -> dict: ...


class EvidenceUnitOfWork(Protocol):
    evidence: EvidenceRepository

    def lock_owner(self, owner_id: str) -> None: ...
    def replay(self, owner_id: str, operation: str, key: str, fingerprint: str) -> dict | None: ...
    def remember(
        self, owner_id: str, operation: str, key: str, fingerprint: str, response: dict
    ) -> None: ...
    def commit(self) -> None: ...
