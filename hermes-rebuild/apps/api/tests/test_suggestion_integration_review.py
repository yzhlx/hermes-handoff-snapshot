"""Independent API checks for replay, clock and source invalidation semantics."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_foundation import authenticated, start

pytest_plugins = ("test_foundation",)

from hermes_api import suggestion_routes
from hermes_api.storage import Operation, SessionRow
from hermes_api.suggestion_service import SuggestionService

NOW = datetime(2026, 10, 1, 9, tzinfo=UTC)


def _candidate(app, monkeypatch):
    current = [NOW]
    monkeypatch.setattr(
        suggestion_routes,
        "SuggestionService",
        lambda uow: SuggestionService(uow, clock=lambda: current[0]),
    )
    client = authenticated(app)
    created, _ = start(client)
    value = created.json()["data"]
    key = str(uuid4())
    ended = client.post(
        f"/api/v1/learning-sessions/{value['id']}/end",
        json={"operation_id": key},
        headers={"Idempotency-Key": key, "If-Match": "1"},
    )
    assert ended.status_code == 200
    with Session(app.state.engine) as db:
        session = db.get(SessionRow, value["id"])
        session.resume_note = "QA_TEST 回到第三题"
        session.version += 1
        db.commit()
    response = client.get("/api/v1/suggestions")
    assert response.status_code == 200, response.text
    candidate = response.json()["data"]["items"][0]
    return client, candidate, value["id"], current


def _action(client, candidate, action, *, key=None, until=None, version=None):
    key = key or str(uuid4())
    body = {"operation_id": key, "action": action}
    if until is not None:
        body["snoozed_until"] = until
    response = client.post(
        f"/api/v1/suggestions/{candidate['id']}/actions",
        json=body,
        headers={"If-Match": str(version or candidate["version"]), "Idempotency-Key": key},
    )
    return response, key


def test_expired_snooze_changes_version_and_does_not_start_learning(system, monkeypatch):
    app, _ = system
    client, candidate, session_id, clock = _candidate(app, monkeypatch)
    response, _ = _action(client, candidate, "snooze")
    assert response.status_code == 200, response.text
    snoozed = response.json()["data"]
    assert datetime.fromisoformat(snoozed["snoozed_until"]) == NOW + timedelta(days=7)
    assert client.get("/api/v1/suggestions").json()["data"]["items"] == []
    clock[0] += timedelta(days=7)
    available = client.get("/api/v1/suggestions").json()["data"]["items"][0]
    assert available["id"] == candidate["id"] and available["status"] == "available"
    assert available["version"] > snoozed["version"]
    conflict, _ = _action(client, snoozed, "accept")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["current_version"] == available["version"]
    accepted, _ = _action(client, available, "accept")
    assert accepted.status_code == 200
    assert client.get("/api/v1/learning-sessions/current").json()["data"] is None
    with Session(app.state.engine) as db:
        assert db.get(SessionRow, session_id).status == "ended"


def test_expired_explicit_snooze_replay_returns_current_state_without_rejecting_original_date(
    system, monkeypatch
):
    app, _ = system
    client, candidate, _, clock = _candidate(app, monkeypatch)
    until = (NOW + timedelta(days=2)).isoformat()
    original, key = _action(client, candidate, "snooze", until=until)
    assert original.status_code == 200
    with Session(app.state.engine) as db:
        before = len(db.scalars(select(Operation)).all())
    clock[0] += timedelta(days=3)
    replay, _ = _action(client, candidate, "snooze", until=until, key=key)
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"]["status"] == "available"
    assert replay.json()["data"]["version"] > original.json()["data"]["version"]
    with Session(app.state.engine) as db:
        assert len(db.scalars(select(Operation)).all()) == before


def test_replay_revalidates_evidence_and_never_returns_old_actionable_source(system, monkeypatch):
    app, _ = system
    client, candidate, session_id, _ = _candidate(app, monkeypatch)
    dismissed, key = _action(client, candidate, "dismiss")
    assert dismissed.status_code == 200
    with Session(app.state.engine) as db:
        row = db.get(SessionRow, session_id)
        row.resume_note = None
        row.version += 1
        db.commit()
    replay, _ = _action(client, candidate, "dismiss", key=key)
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"]["status"] == "stale"
    assert client.get("/api/v1/suggestions").json()["data"]["items"] == []
    with Session(app.state.engine) as db:
        assert (
            len(list(db.scalars(select(Operation).where(Operation.operation.like("suggestion:%")))))
            == 1
        )


def test_snooze_timestamp_validation_and_csrf_have_no_side_effects(system, monkeypatch):
    app, _ = system
    client, candidate, _, _ = _candidate(app, monkeypatch)
    for until in ("2026-10-02T09:00:00", NOW.isoformat(), (NOW + timedelta(days=366)).isoformat()):
        response, _ = _action(client, candidate, "snooze", until=until)
        assert response.status_code == 422, response.text
    key = str(uuid4())
    invalid = client.post(
        f"/api/v1/suggestions/{candidate['id']}/actions",
        json={"operation_id": key, "action": "dismiss"},
        headers={
            "Idempotency-Key": key,
            "If-Match": str(candidate["version"]),
            "X-CSRF-Token": "QA_TEST_wrong",
        },
    )
    assert invalid.status_code == 403
    assert (
        client.get(f"/api/v1/suggestions/{candidate['id']}").json()["data"]["version"]
        == candidate["version"]
    )
