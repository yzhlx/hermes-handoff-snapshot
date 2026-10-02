from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

pytest_plugins = ("test_foundation",)

from test_foundation import authenticated

from hermes_api.domain import PolicyError
from hermes_api.main import create_app
from hermes_api.settings import Settings
from hermes_api.storage import SessionReflectionRow, SessionRow
from hermes_api.suggestion_domain import (
    RULE_VERSION,
    build_candidates,
    candidate_fingerprint,
    review_due,
    validate_action,
)
from hermes_api.suggestion_service import SuggestionService
from hermes_api.suggestion_storage import SQLSuggestionUnitOfWork

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)


def source(kind, item_id, version=1, occurred_at=NOW):
    return {
        "kind": kind,
        "id": item_id,
        "version": version,
        "label": "QA_TEST source",
        "occurred_at": occurred_at,
        "session_id": None,
        "problem_id": None,
    }


def test_fingerprint_tracks_source_versions_and_scope_but_not_reason_or_time():
    refs = [source("problem", "p1")]
    first = candidate_fingerprint("review", "s1", None, "p1", None, refs)
    assert first == candidate_fingerprint("review", "s1", None, "p1", None, refs)
    assert first != candidate_fingerprint(
        "review", "s1", None, "p1", None, [source("problem", "p1", version=2)]
    )
    assert first != candidate_fingerprint("review", "s2", None, "p1", None, refs)


def test_review_due_uses_latest_attempt_result_and_utc_age():
    base = {
        "occurred_at": NOW - timedelta(days=7),
        "answer_check": "checked",
        "result": "incorrect",
        "independence": "hinted",
    }
    assert review_due(base, NOW)
    assert not review_due({**base, "occurred_at": NOW - timedelta(days=6, hours=23)}, NOW)
    assert not review_due({**base, "answer_check": "pending", "result": None}, NOW)
    assert not review_due(
        {
            **base,
            "result": "correct",
            "independence": "hinted",
            "occurred_at": NOW - timedelta(days=30),
        },
        NOW,
    )
    assert review_due(
        {
            **base,
            "result": "correct",
            "independence": "independent",
            "occurred_at": NOW - timedelta(days=14),
        },
        NOW,
    )


def test_latest_pending_overrides_an_older_review_and_pending_is_unverified():
    old = {
        "id": "a1",
        "occurred_at": NOW - timedelta(days=30),
        "answer_check": "checked",
        "result": "incorrect",
        "independence": "hinted",
        "error_categories": [],
        "source_ref": source("attempt", "a1"),
        "problem_source_ref": source("problem", "p1"),
    }
    latest = {
        **old,
        "id": "a2",
        "occurred_at": NOW,
        "answer_check": "pending",
        "result": None,
        "source_ref": source("attempt", "a2"),
    }
    candidate = build_candidates(
        {
            "problems": [
                {
                    "id": "p1",
                    "subject_id": "s1",
                    "source_ref": source("problem", "p1"),
                    "attempts": [old, latest],
                }
            ]
        },
        NOW,
    )
    assert [item["kind"] for item in candidate] == ["unverified"]
    old["occurred_at"] = NOW - timedelta(days=8)
    old["source_ref"] = source("attempt", "old", occurred_at=NOW - timedelta(days=8))
    review = build_candidates(
        {
            "problems": [
                {
                    "id": "p1",
                    "subject_id": "s1",
                    "source_ref": source("problem", "p1"),
                    "attempts": [old],
                }
            ]
        },
        NOW,
    )
    assert review[0]["kind"] == "review"
    assert (
        "2026-09-23 UTC" in review[0]["reason"] and "截至2026-10-01已过8天" in review[0]["reason"]
    )


def test_continue_requires_real_resume_position_and_uses_reflection_source():
    facts = {
        "sessions": [
            {
                "id": "ss",
                "status": "ended",
                "version": 2,
                "resume_note": None,
                "subject_id": "s1",
                "source_ref": source("session", "ss", 2),
                "reflection": {"resume_note": "继续复习", "source_ref": source("reflection", "r1")},
            }
        ]
    }
    candidates = build_candidates(facts, NOW)
    assert len(candidates) == 1 and candidates[0]["kind"] == "continue"
    assert {r["kind"] for r in candidates[0]["source_refs"]} == {"session", "reflection"}
    facts["sessions"][0]["reflection"]["resume_note"] = "  "
    assert build_candidates(facts, NOW) == []


def test_repeated_errors_are_scoped_to_checked_recent_twenty_and_active_point():
    attempts = []
    for i in range(21):
        attempts.append(
            {
                "id": f"a{i}",
                "answer_check": "checked",
                "result": "incorrect",
                "error_categories": ["calculation"] if i < 3 else [],
                "source_ref": source("attempt", f"a{i}"),
                "problem_source_ref": source("problem", f"p{i}"),
            }
        )
    facts = {
        "knowledge_points": [
            {
                "id": "kp",
                "subject_id": "s",
                "source_ref": source("knowledge_point", "kp"),
                "attempts": attempts[:20],
            }
        ]
    }
    suggestions = build_candidates(facts, NOW)
    assert len(suggestions) == 1 and suggestions[0]["kind"] == "repeated_error"
    assert "计算类错误出现3次" in suggestions[0]["reason"]
    pending = [
        {
            "id": f"pending{i}",
            "answer_check": "pending",
            "result": None,
            "error_categories": [],
            "source_ref": source("attempt", f"pending{i}"),
            "problem_source_ref": source("problem", f"pending_p{i}"),
        }
        for i in range(25)
    ]
    facts["knowledge_points"][0]["attempts"] = pending + attempts[:20]
    assert len(build_candidates(facts, NOW)) == 1
    # Once the old third matching attempt falls outside the twenty-item window, only two remain.
    facts["knowledge_points"][0]["attempts"] = attempts[1:21]
    assert build_candidates(facts, NOW) == []


def test_snooze_is_fixed_default_or_explicit_one_to_365_days():
    assert validate_action("snooze", None, NOW) == NOW + timedelta(days=7)
    assert validate_action("snooze", NOW + timedelta(days=1), NOW) == NOW + timedelta(days=1)
    for invalid in (
        NOW,
        NOW + timedelta(seconds=1),
        NOW - timedelta(seconds=1),
        NOW + timedelta(days=366),
        datetime.fromisoformat("2026-10-02T00:00:00"),
    ):
        with pytest.raises(PolicyError):
            validate_action("snooze", invalid, NOW)
    assert validate_action("accept", None, NOW) is None
    with pytest.raises(PolicyError):
        validate_action("dismiss", NOW + timedelta(days=1), NOW)


def test_policy_version_is_explicit():
    assert RULE_VERSION == "suggestions-1"


def test_api_persists_ignore_owner_scopes_and_marks_corrected_sources_stale(system):
    app, url = system
    session_id = str(uuid4())
    with Session(app.state.engine) as db:
        db.add(
            SessionRow(
                id=session_id,
                owner_id="alice",
                goal="QA_TEST 继续复习",
                subject_id=None,
                knowledge_point_id=None,
                status="ended",
                version=2,
                started_at=NOW - timedelta(hours=1),
                ended_at=NOW - timedelta(minutes=1),
                day_timezone="Asia/Shanghai",
                learning_date="2026-10-01",
                timing_enabled=False,
                method_id=None,
                kind="free",
                previous_session_id=None,
                resume_note="继续复习",
            )
        )
        db.flush()
        db.add(
            SessionReflectionRow(
                id=str(uuid4()),
                owner_id="alice",
                session_id=session_id,
                summary="QA_TEST reflection",
                recalled_text=None,
                reference_checked=None,
                missing_parts=None,
                stuck_note=None,
                resume_note=None,
                version=1,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        db.commit()

    alice, bob = authenticated(app, "alice"), authenticated(app, "bob")
    assert alice.get("/api/v1/suggestions").status_code == 200
    first_page = alice.get("/api/v1/suggestions").json()["data"]
    assert len(first_page["items"]) == 1
    candidate = first_page["items"][0]
    assert candidate["kind"] == "continue" and candidate["status"] == "available"
    assert bob.get(f"/api/v1/suggestions/{candidate['id']}").status_code == 404
    assert alice.get("/api/v1/suggestions?cursor=not-a-uuid").status_code == 422

    path = f"/api/v1/suggestions/{candidate['id']}/actions"
    absent_key = str(uuid4())
    assert (
        alice.post(
            path,
            json={"operation_id": absent_key, "action": "dismiss"},
            headers={"Idempotency-Key": absent_key},
        ).status_code
        == 428
    )
    csrf_token = alice.headers.pop("X-CSRF-Token")
    denied_key = str(uuid4())
    assert (
        alice.post(
            path,
            json={"operation_id": denied_key, "action": "dismiss"},
            headers={"Idempotency-Key": denied_key, "If-Match": "1"},
        ).status_code
        == 403
    )
    alice.headers["X-CSRF-Token"] = csrf_token

    for bad_time in (
        (datetime.now(UTC) + timedelta(days=2)).replace(tzinfo=None).isoformat(),
        (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        (datetime.now(UTC) + timedelta(days=366)).isoformat(),
    ):
        invalid_key = str(uuid4())
        invalid = alice.post(
            path,
            json={"operation_id": invalid_key, "action": "snooze", "snoozed_until": bad_time},
            headers={"Idempotency-Key": invalid_key, "If-Match": "1"},
        )
        assert invalid.status_code == 422

    snooze_key = str(uuid4())
    explicit_until = datetime.now(UTC) + timedelta(days=2)
    snoozed = alice.post(
        path,
        json={
            "operation_id": snooze_key,
            "action": "snooze",
            "snoozed_until": explicit_until.isoformat(),
        },
        headers={"Idempotency-Key": snooze_key, "If-Match": "1"},
    )
    assert snoozed.status_code == 200 and snoozed.json()["data"]["status"] == "snoozed"
    snoozed_until = datetime.fromisoformat(snoozed.json()["data"]["snoozed_until"])
    expired_clock = snoozed_until + timedelta(seconds=1)
    with Session(app.state.engine) as db:
        service = SuggestionService(SQLSuggestionUnitOfWork(db), clock=lambda: expired_clock)
        page = service.list("alice", status="all")
        current = next(item for item in page["items"] if item["id"] == candidate["id"])
        assert current["status"] == "available" and current["version"] == 3
    stale_key = str(uuid4())
    stale_version = alice.post(
        path,
        json={"operation_id": stale_key, "action": "dismiss"},
        headers={"Idempotency-Key": stale_key, "If-Match": "2"},
    )
    assert (
        stale_version.status_code == 409 and stale_version.json()["error"]["current_version"] == 3
    )

    key = str(uuid4())
    body = {"operation_id": key, "action": "dismiss"}
    headers = {"Idempotency-Key": key, "If-Match": "3"}
    first = alice.post(path, json=body, headers=headers)
    assert first.status_code == 200 and first.json()["data"]["status"] == "dismissed"
    replay = alice.post(path, json=body, headers=headers)
    assert replay.status_code == 200 and replay.json()["data"]["version"] == 4
    assert alice.get("/api/v1/suggestions").json()["data"]["items"] == []
    assert (
        alice.get("/api/v1/suggestions?status=all").json()["data"]["items"][0]["status"]
        == "dismissed"
    )

    # A changed source version invalidates the old judgment and allows fresh evidence to surface.
    with Session(app.state.engine) as db:
        row = db.scalar(
            select(SessionRow).where(SessionRow.owner_id == "alice", SessionRow.id == session_id)
        )
        row.resume_note = "QA_TEST corrected position"
        row.version += 1
        db.commit()
    refreshed = alice.get("/api/v1/suggestions?status=all").json()["data"]["items"]
    by_id = {item["id"]: item for item in refreshed}
    assert by_id[candidate["id"]]["status"] == "stale"
    assert any(
        item["id"] != candidate["id"] and item["status"] == "available" for item in refreshed
    )

    # State survives constructing a new service process over the same temporary database.
    restarted = create_app(Settings(database_url=url, environment="test"))
    restarted_client = authenticated(restarted, "alice")
    restarted_items = restarted_client.get("/api/v1/suggestions?status=all").json()["data"]["items"]
    assert (
        next(item for item in restarted_items if item["id"] == candidate["id"])["status"] == "stale"
    )
