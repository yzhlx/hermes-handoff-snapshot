from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from hermes_api.domain import PolicyError
from hermes_api.home_ports import HomeReadError
from hermes_api.home_routes import create_home_router
from hermes_api.home_service import HomeService
from hermes_api.home_storage import SQLHomeReader
from hermes_api.storage import SessionRow

pytest_plugins = ("test_foundation",)


NOW = datetime(2026, 10, 1, 16, tzinfo=UTC)


class Reader:
    def __init__(self):
        self.calls = []
        self.failures = {}

    def read_section(self, owner_id, timezone, today, section, now):
        self.calls.append(section)
        failure = self.failures.get(section)
        if failure:
            raise failure
        data = {
            "quote": {"daily_quote": {"quote": None}},
            "subjects": {"items": []},
            "continue_learning": {"current": None, "last": None},
            "suggestions": {"items": [], "has_more": False},
            "methods": {"items": []},
            "changes": {
                "items": [],
                "effective_learning_days": 0,
            },
            "review": {"items": [], "has_more": False},
        }[section]
        return data, f"revision-{section}"


def test_home_date_uses_one_fixed_server_clock_in_account_timezone():
    reader = Reader()
    result = HomeService(reader, clock=lambda: NOW).get("owner", "Asia/Shanghai")
    assert result["date"] == date(2026, 10, 2)
    assert result["timezone"] == "Asia/Shanghai"
    assert len(reader.calls) == 7


def test_known_section_failure_is_isolated_and_single_section_request_retries_it():
    reader = Reader()
    reader.failures["subjects"] = HomeReadError("secret db detail")
    service = HomeService(reader, clock=lambda: NOW)
    full = service.get("owner", "UTC")
    assert full["sections"]["subjects"]["status"] == "unavailable"
    assert full["sections"]["subjects"]["error"] == {
        "code": "STORAGE_UNAVAILABLE",
        "message": "此部分暂时无法读取，请稍后重试。",
    }
    assert full["sections"]["quote"]["status"] == "empty"
    assert reader.calls.count("subjects") == 1

    reader.failures.clear()
    retried = service.get("owner", "UTC", section="subjects")
    assert set(retried["sections"]) == {"subjects"}
    assert retried["sections"]["subjects"]["status"] == "empty"
    assert reader.calls.count("subjects") == 2


def test_policy_error_is_section_local_but_unknown_errors_propagate():
    reader = Reader()
    reader.failures["review"] = PolicyError("SERVICE_UNAVAILABLE", "private detail", 503)
    result = HomeService(reader, clock=lambda: NOW).get("owner", "UTC")
    assert result["sections"]["review"]["status"] == "unavailable"
    assert result["sections"]["review"]["error"]["message"] == "此部分暂时无法读取，请稍后重试。"
    reader.failures["review"] = RuntimeError("must propagate")
    with pytest.raises(RuntimeError, match="must propagate"):
        HomeService(reader, clock=lambda: NOW).get("owner", "UTC", section="review")


def test_section_names_are_validated_before_reading():
    reader = Reader()
    with pytest.raises(PolicyError) as error:
        HomeService(reader, clock=lambda: NOW).get("owner", "UTC", section="nope")
    assert error.value.status == 422
    assert reader.calls == []


def _session(owner, session_id, status, started_at, *, goal=None, resume_note=None):
    return SessionRow(
        id=session_id,
        owner_id=owner,
        goal=goal,
        subject_id=None,
        status=status,
        version=1,
        started_at=started_at,
        ended_at=started_at if status in {"ended", "cancelled"} else None,
        day_timezone="UTC",
        learning_date="2026-10-01",
        timing_enabled=False,
        method_id=None,
        kind="free",
        previous_session_id=None,
        resume_note=resume_note,
    )


def test_sql_home_prefers_running_session_and_finds_valid_ended_record_past_newer_empty_rows(
    system,
):
    app, _url = system
    with Session(app.state.engine) as db:
        db.add(_session("alice", "QA_TEST_running", "paused", NOW))
        db.add(
            _session(
                "alice",
                "QA_TEST_valid_old",
                "ended",
                NOW - timedelta(days=20),
                goal="QA_TEST_goal",
                resume_note="继续积分中的边界情况",
            )
        )
        db.add_all(
            [
                _session(
                    "alice",
                    f"QA_TEST_empty_{index}",
                    "ended",
                    NOW + timedelta(seconds=index + 1),
                    goal="只有目标没有学习内容",
                )
                for index in range(105)
            ]
        )
        db.commit()

    data, _revision = SQLHomeReader(app.state.engine).read_section(
        "alice", "UTC", date(2026, 10, 1), "continue_learning", NOW
    )
    assert data["current"]["id"] == "QA_TEST_running"
    assert data["current"]["status"] == "paused"
    assert data["last"]["id"] == "QA_TEST_valid_old"
    assert data["last"]["resume_note"] == "继续积分中的边界情况"


def test_sql_home_excludes_empty_and_cancelled_sessions_from_continue(system):
    app, _url = system
    with Session(app.state.engine) as db:
        db.add(
            _session(
                "alice",
                "QA_TEST_empty_ended",
                "ended",
                NOW,
                goal="只有目标没有学习内容",
            )
        )
        db.add(
            _session(
                "alice",
                "QA_TEST_cancelled",
                "cancelled",
                NOW + timedelta(seconds=1),
                resume_note="取消记录不能作为继续入口",
            )
        )
        db.commit()

    data, _revision = SQLHomeReader(app.state.engine).read_section(
        "alice", "UTC", date(2026, 10, 1), "continue_learning", NOW
    )
    assert data == {"current": None, "last": None}


def test_router_validates_section_and_omits_unrequested_sections(system):
    app, _url = system
    api = FastAPI()

    def identity():
        return SimpleNamespace(id="alice", timezone="UTC"), None

    @api.middleware("http")
    async def request_id(request, call_next):
        request.state.request_id = "QA_TEST_request"
        return await call_next(request)

    api.include_router(create_home_router(app.state.engine, identity))
    client = TestClient(api)
    response = client.get("/api/v1/home?section=methods")
    assert response.status_code == 200
    body = response.json()["data"]
    assert set(body["sections"]) == {"methods"}
    assert body["sections"]["methods"]["status"] == "ready"
    assert len(body["sections"]["methods"]["data"]["items"]) == 3
    assert client.get("/api/v1/home?section=not-a-section").status_code == 422


def test_suggestion_sections_filter_at_source_before_pagination(system, monkeypatch):
    from hermes_api import home_storage

    calls = []

    class Suggestions:
        def __init__(self, _uow, clock):
            assert clock() == NOW

        def list(self, owner, *, kind, status, limit):
            calls.append((kind, status, limit))
            items = [
                {
                    "id": f"QA_TEST_{kind}_{index}",
                    "kind": kind,
                    "generated_at": NOW + timedelta(seconds=index),
                    "source_revision": f"revision-{kind}-{index}",
                }
                for index in range(4)
            ]
            return {"items": items, "next_cursor": f"cursor-{kind}"}

    monkeypatch.setattr(home_storage, "SuggestionService", Suggestions)
    app, _url = system
    reader = SQLHomeReader(app.state.engine)
    suggestions, _ = reader.read_section("alice", "UTC", date(2026, 10, 1), "suggestions", NOW)
    assert calls == [
        ("unverified", "available", 4),
        ("repeated_error", "available", 4),
    ]
    assert len(suggestions["items"]) == 3
    assert suggestions["has_more"] is True
    calls.clear()
    review, _ = reader.read_section("alice", "UTC", date(2026, 10, 1), "review", NOW)
    assert calls == [("review", "available", 4)]
    assert {item["kind"] for item in review["items"]} == {"review"}
