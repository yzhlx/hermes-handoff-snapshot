"""Application service that isolates failures between home sections."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .domain import PolicyError
from .home_ports import HomeReader, HomeReadError

HOME_RULE_VERSION = "home-v1"
SECTIONS = ("quote", "subjects", "continue_learning", "suggestions", "methods", "changes", "review")


def _revision(value):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class HomeService:
    def __init__(self, reader: HomeReader, clock=lambda: datetime.now(UTC)):
        self.reader = reader
        self.clock = clock

    def get(self, owner_id: str, timezone: str, section: str | None = None) -> dict:
        if section is not None and section not in SECTIONS:
            raise PolicyError("VALIDATION_ERROR", "Home section is invalid.", 422)
        now = self.clock().astimezone(UTC)
        try:
            today = now.astimezone(ZoneInfo(timezone)).date()
        except (ZoneInfoNotFoundError, ValueError):
            raise PolicyError("VALIDATION_ERROR", "Account timezone is invalid.", 422) from None
        names = (section,) if section else SECTIONS
        sections = {}
        for name in names:
            try:
                data, source_revision = self.reader.read_section(
                    owner_id, timezone, today, name, now
                )
                empty = self._is_empty(name, data)
                sections[name] = {
                    "status": "empty" if empty else "ready",
                    "data": data,
                    "source_revision": source_revision or _revision(data),
                    "error": None,
                }
            except (HomeReadError, PolicyError) as error:
                code, message = self._safe_error(error)
                sections[name] = {
                    "status": "unavailable",
                    "data": None,
                    "source_revision": None,
                    "error": {"code": code, "message": message},
                }
        return {
            "date": today,
            "timezone": timezone,
            "rule_version": HOME_RULE_VERSION,
            "sections": sections,
        }

    @staticmethod
    def _is_empty(name, data):
        if name == "quote":
            return data["daily_quote"]["quote"] is None
        if name == "subjects":
            return not data["items"]
        if name == "continue_learning":
            return data["current"] is None and data["last"] is None
        if name in {"suggestions", "review", "methods"}:
            return not data["items"]
        if name == "changes":
            return not data["items"] and data["effective_learning_days"] == 0
        return False

    @staticmethod
    def _safe_error(error):
        if isinstance(error, HomeReadError):
            return error.code, error.message
        messages = {
            "VALIDATION_ERROR": "此部分的数据暂时无法读取。",
            "RESOURCE_NOT_FOUND": "此部分的数据暂时无法读取。",
            "SERVICE_UNAVAILABLE": "此部分暂时无法读取，请稍后重试。",
        }
        return error.code if error.code in messages else "SECTION_UNAVAILABLE", messages.get(
            error.code, "此部分暂时无法读取，请稍后重试。"
        )

    @staticmethod
    def seven_day_range(today: date):
        return today - timedelta(days=6), today
