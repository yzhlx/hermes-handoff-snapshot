"""Application boundary for the optional AI advisor.

The advisor reads a bounded, owner-scoped evidence bundle and returns
structured, citation-checked output. Model access goes through
:class:`AdvisorModel` so a real provider can replace the deterministic mock
without touching use cases.
"""

from typing import Protocol


class AdvisorModelUnavailable(RuntimeError):
    """The configured model could not produce output (timeout, budget, config)."""


class AdvisorModel(Protocol):
    """A narrowly declared model adapter.

    Capabilities must be declared, never presumed from an "OpenAI-compatible"
    label. Tool scope is read-only and empty in the base implementation.
    """

    model_id: str
    prompt_version: str
    externally_hosted: bool
    capabilities: dict

    def analyze(self, request: dict, evidence: dict) -> dict: ...


class AdvisorRepository(Protocol):
    def collect_evidence(
        self, owner_id: str, subject_id: str | None, knowledge_point_id: str | None
    ) -> dict: ...

    def create_run(self, owner_id: str, data: dict) -> dict: ...

    def get_run(self, owner_id: str, run_id: str) -> dict: ...

    def list_runs(self, owner_id: str, limit: int, cursor: str | None) -> list[dict]: ...

    def cancel_run(self, owner_id: str, run_id: str) -> dict: ...


class AdvisorUnitOfWork(Protocol):
    advisor: AdvisorRepository

    def lock_owner(self, owner_id: str) -> None: ...
    def replay(self, owner_id: str, operation: str, key: str, fingerprint: str): ...
    def remember(
        self, owner_id: str, operation: str, key: str, fingerprint: str, response: dict
    ) -> None: ...
    def commit(self) -> None: ...
