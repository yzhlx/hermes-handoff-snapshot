"""Read-only boundary for factual learning records."""

from typing import Protocol

from .records_domain import RecordFacts


class RecordsRepository(Protocol):
    def collect(
        self, owner_id: str, from_date: str, to_date: str, subject_id: str | None
    ) -> RecordFacts: ...


class RecordsUnitOfWork(Protocol):
    records: RecordsRepository
