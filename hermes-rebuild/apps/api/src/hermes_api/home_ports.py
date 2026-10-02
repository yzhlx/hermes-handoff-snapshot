"""Read-side port for the composed home view."""

from datetime import date, datetime
from typing import Protocol


class HomeReadError(Exception):
    """Safe application-level failure raised for an unavailable section store."""

    code = "STORAGE_UNAVAILABLE"
    message = "此部分暂时无法读取，请稍后重试。"


class HomeReader(Protocol):
    def read_section(
        self, owner_id: str, timezone: str, today: date, section: str, now: datetime
    ) -> tuple[dict, str | None]: ...
