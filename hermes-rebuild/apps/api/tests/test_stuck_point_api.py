"""Authenticated API checks for stuck point writes, lifecycle and owner isolation."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

pytest_plugins = ("test_foundation",)

from test_foundation import authenticated

from hermes_api.knowledge_storage import ChapterRow, KnowledgePointRow
from hermes_api.main import create_app
from hermes_api.settings import Settings
from hermes_api.storage import ProblemAttemptRow, ProblemRow, SessionRow, Subject
from hermes_api.stuck_point_storage import StuckPointRow


def _session_row(owner, *, status="ended", subject_id=None, knowledge_point_id=None):
    now = datetime.now(UTC)
    return SessionRow(
        id=str(uuid4()),
        owner_id=owner,
        goal="QA_TEST",
        subject_id=subject_id,
        knowledge_point_id=knowledge_point_id,
        status=status,
        version=1,
        started_at=now,
        ended_at=now if status in ("ended", "cancelled") else None,
        day_timezone="UTC",
        learning_date=now.date().isoformat(),
        timing_enabled=False,
        method_id=None,
        kind="reading",
        previous_session_id=None,
        resume_note=None,
    )


def _fixture(app):
    """One subject, chapter, knowledge point, session and attempt per account."""
    now = datetime.now(UTC)
    ids = {name: str(uuid4()) for name in ("alice", "bob")}
    with Session(app.state.engine) as db:
        for name in ("alice", "bob"):
            subject = Subject(id=ids[name], owner_id=name, name=f"QA_TEST_{name}_subject")
            db.add(subject)
            db.flush()
            chapter = ChapterRow(
                id=str(uuid4()),
                owner_id=name,
                subject_id=subject.id,
                name="QA_TEST_chapter",
                order_index=0,
                version=1,
                created_at=now,
                updated_at=now,
                archived_at=None,
            )
            db.add(chapter)
            db.flush()
            point = KnowledgePointRow(
                id=str(uuid4()),
                owner_id=name,
                chapter_id=chapter.id,
                subject_id=subject.id,
                name="QA_TEST_point",
                notes=None,
                version=1,
                created_at=now,
                updated_at=now,
                archived_at=None,
            )
            db.add(point)
            db.flush()
            session = _session_row(
                name, status="active", subject_id=subject.id, knowledge_point_id=point.id
            )
            db.add(session)
            db.flush()
            problem = ProblemRow(
                id=str(uuid4()),
                owner_id=name,
                subject_id=subject.id,
                title="QA_TEST",
                statement="QA_TEST 题干",
                source_note=None,
                correct_answer="QA_TEST 答案",
                is_representative=False,
                archived_at=None,
                version=1,
                created_at=now,
                updated_at=now,
            )
            db.add(problem)
            db.flush()
            attempt = ProblemAttemptRow(
                id=str(uuid4()),
                owner_id=name,
                session_id=session.id,
                problem_id=problem.id,
                independence="independent",
                answer_check="pending",
                result=None,
                attempt_text="QA_TEST 作答",
                stuck_note=None,
                occurred_at=now,
                verified_at=None,
                version=1,
                created_at=now,
                updated_at=now,
            )
            db.add(attempt)
            db.flush()
            ids[f"{name}_subject"] = subject.id
            ids[f"{name}_point"] = point.id
            ids[f"{name}_session"] = session.id
            ids[f"{name}_attempt"] = attempt.id
        db.commit()
    return ids


def _create(client, session_id, text="QA_TEST 为什么这里 ωs=2π/T？", **extra):
    key = str(uuid4())
    body = {"operation_id": key, "session_id": session_id, "text": text, **extra}
    return (
        client.post("/api/v1/stuck-points", json=body, headers={"Idempotency-Key": key}),
        body,
    )


def test_create_requires_owned_session_and_non_empty_text(system):
    app, _ = system
    ids = _fixture(app)
    client = authenticated(app)

    missing = client.post(
        "/api/v1/stuck-points",
        json={"operation_id": str(uuid4()), "session_id": str(uuid4()), "text": "QA_TEST"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert missing.status_code == 422  # key must equal operation_id

    key = str(uuid4())
    foreign = client.post(
        "/api/v1/stuck-points",
        json={"operation_id": key, "session_id": ids["bob_session"], "text": "QA_TEST"},
        headers={"Idempotency-Key": key},
    )
    assert foreign.status_code == 404

    for bad in ("", "   ", "\n\t "):
        key = str(uuid4())
        empty = client.post(
            "/api/v1/stuck-points",
            json={"operation_id": key, "session_id": ids["alice_session"], "text": bad},
            headers={"Idempotency-Key": key},
        )
        assert empty.status_code == 422, bad

    key = str(uuid4())
    too_long = client.post(
        "/api/v1/stuck-points",
        json={"operation_id": key, "session_id": ids["alice_session"], "text": "x" * 1001},
        headers={"Idempotency-Key": key},
    )
    assert too_long.status_code == 422

    created, body = _create(client, ids["alice_session"])
    assert created.status_code == 201
    data = created.json()["data"]
    assert data["status"] == "open"
    assert data["version"] == 1
    assert data["resolved_at"] is None
    assert data["text"] == body["text"].strip()
    assert data["session_id"] == ids["alice_session"]
    assert data["attempt_id"] is None
    assert data["knowledge_point_id"] is None


def test_create_is_idempotent_and_key_must_match_body(system):
    app, _ = system
    ids = _fixture(app)
    client = authenticated(app)

    key = str(uuid4())
    body = {"operation_id": key, "session_id": ids["alice_session"], "text": "QA_TEST 卡住"}
    first = client.post("/api/v1/stuck-points", json=body, headers={"Idempotency-Key": key})
    second = client.post("/api/v1/stuck-points", json=body, headers={"Idempotency-Key": key})
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["data"]["id"] == second.json()["data"]["id"]

    other = dict(body, text="QA_TEST 换了内容")
    conflict = client.post("/api/v1/stuck-points", json=other, headers={"Idempotency-Key": key})
    assert conflict.status_code == 409

    with Session(app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(StuckPointRow)) == 1


def test_patch_requires_if_match_and_reports_conflict(system):
    app, _ = system
    ids = _fixture(app)
    client = authenticated(app)
    point = _create(client, ids["alice_session"])[0].json()["data"]

    key = str(uuid4())
    body = {"operation_id": key, "text": "QA_TEST 补充描述"}
    without = client.patch(f"/api/v1/stuck-points/{point['id']}", json=body)
    assert without.status_code == 428

    key = str(uuid4())
    stale = client.patch(
        f"/api/v1/stuck-points/{point['id']}",
        json={"operation_id": key, "text": "QA_TEST 过期写入"},
        headers={"Idempotency-Key": key, "If-Match": '"99"'},
    )
    assert stale.status_code == 409
    error = stale.json()["error"]
    assert error["current_version"] == 1
    assert error["current"]["id"] == point["id"]

    key = str(uuid4())
    fresh = client.patch(
        f"/api/v1/stuck-points/{point['id']}",
        json={"operation_id": key, "text": "QA_TEST 补充描述"},
        headers={"Idempotency-Key": key, "If-Match": '"1"'},
    )
    assert fresh.status_code == 200
    assert fresh.json()["data"]["version"] == 2
    assert fresh.json()["data"]["text"] == "QA_TEST 补充描述"


def test_open_resolve_lifecycle_records_and_clears_time(system):
    app, _ = system
    ids = _fixture(app)
    client = authenticated(app)
    point = _create(client, ids["alice_session"])[0].json()["data"]

    key = str(uuid4())
    resolved = client.patch(
        f"/api/v1/stuck-points/{point['id']}",
        json={"operation_id": key, "status": "resolved", "resolution_note": "QA_TEST 换元后清楚"},
        headers={"Idempotency-Key": key, "If-Match": '"1"'},
    )
    assert resolved.status_code == 200
    body = resolved.json()["data"]
    assert body["status"] == "resolved"
    assert body["resolved_at"] is not None
    assert body["resolution_note"] == "QA_TEST 换元后清楚"
    assert body["version"] == 2

    key = str(uuid4())
    reopened = client.patch(
        f"/api/v1/stuck-points/{point['id']}",
        json={"operation_id": key, "status": "open"},
        headers={"Idempotency-Key": key, "If-Match": '"2"'},
    )
    assert reopened.status_code == 200
    assert reopened.json()["data"]["status"] == "open"
    assert reopened.json()["data"]["resolved_at"] is None

    key = str(uuid4())
    unknown = client.patch(
        f"/api/v1/stuck-points/{point['id']}",
        json={"operation_id": key, "status": "archived"},
        headers={"Idempotency-Key": key, "If-Match": '"3"'},
    )
    assert unknown.status_code == 422


def test_stuck_points_are_owner_isolated(system):
    app, _ = system
    ids = _fixture(app)
    alice = authenticated(app, "alice")
    bob = authenticated(app, "bob")
    point = _create(alice, ids["alice_session"])[0].json()["data"]

    assert bob.get(f"/api/v1/stuck-points/{point['id']}").status_code == 404

    key = str(uuid4())
    cross = bob.patch(
        f"/api/v1/stuck-points/{point['id']}",
        json={"operation_id": key, "text": "QA_TEST 越权"},
        headers={"Idempotency-Key": key, "If-Match": '"1"'},
    )
    assert cross.status_code == 404

    listing = bob.get("/api/v1/stuck-points")
    assert listing.status_code == 200
    assert listing.json()["data"]["items"] == []


def test_source_attempt_can_only_be_promoted_once(system):
    app, _ = system
    ids = _fixture(app)
    client = authenticated(app)

    first = _create(client, ids["alice_session"], attempt_id=ids["alice_attempt"])
    assert first[0].status_code == 201
    assert first[0].json()["data"]["attempt_id"] == ids["alice_attempt"]

    duplicate = _create(client, ids["alice_session"], attempt_id=ids["alice_attempt"])
    assert duplicate[0].status_code == 409
    assert duplicate[0].json()["error"]["code"] == "ALREADY_LINKED"

    foreign = _create(client, ids["alice_session"], attempt_id=ids["bob_attempt"])
    assert foreign[0].status_code == 404


def test_list_filters_and_cursor(system):
    app, _ = system
    ids = _fixture(app)
    client = authenticated(app)
    created = []
    for index in range(3):
        point = _create(
            client,
            ids["alice_session"],
            text=f"QA_TEST 卡壳 {index}",
            knowledge_point_id=ids["alice_point"],
        )[0].json()["data"]
        created.append(point)

    key = str(uuid4())
    client.patch(
        f"/api/v1/stuck-points/{created[0]['id']}",
        json={"operation_id": key, "status": "resolved"},
        headers={"Idempotency-Key": key, "If-Match": '"1"'},
    )

    opened = client.get("/api/v1/stuck-points?status=open")
    assert opened.status_code == 200
    assert {item["id"] for item in opened.json()["data"]["items"]} == {
        created[1]["id"],
        created[2]["id"],
    }

    resolved = client.get("/api/v1/stuck-points?status=resolved")
    assert [item["id"] for item in resolved.json()["data"]["items"]] == [created[0]["id"]]

    by_session = client.get(f"/api/v1/stuck-points?session_id={ids['alice_session']}")
    assert len(by_session.json()["data"]["items"]) == 3

    by_point = client.get(f"/api/v1/stuck-points?knowledge_point_id={ids['alice_point']}")
    assert len(by_point.json()["data"]["items"]) == 3

    assert client.get(f"/api/v1/stuck-points?session_id={ids['bob_session']}").status_code == 404
    assert client.get("/api/v1/stuck-points?status=unknown").status_code == 422
    assert client.get("/api/v1/stuck-points?limit=101").status_code == 422

    first_page = client.get("/api/v1/stuck-points?limit=2")
    payload = first_page.json()["data"]
    assert len(payload["items"]) == 2
    assert payload["next_cursor"]

    second_page = client.get(f"/api/v1/stuck-points?limit=2&cursor={payload['next_cursor']}")
    assert second_page.status_code == 200
    assert len(second_page.json()["data"]["items"]) == 1
    assert second_page.json()["data"]["next_cursor"] is None

    assert client.get("/api/v1/stuck-points?cursor=not-a-cursor").status_code == 422

    bob = authenticated(app, "bob")
    assert bob.get(f"/api/v1/stuck-points?cursor={payload['next_cursor']}").status_code == 422


def test_stuck_point_survives_a_fresh_app_on_the_same_database(system):
    app, url = system
    ids = _fixture(app)
    client = authenticated(app)
    point = _create(client, ids["alice_session"])[0].json()["data"]

    key = str(uuid4())
    client.patch(
        f"/api/v1/stuck-points/{point['id']}",
        json={"operation_id": key, "status": "resolved", "resolution_note": "QA_TEST 重启前"},
        headers={"Idempotency-Key": key, "If-Match": '"1"'},
    )

    restarted = create_app(Settings(database_url=url, environment="test"))
    reopened = authenticated(restarted, "alice")
    reloaded = reopened.get(f"/api/v1/stuck-points/{point['id']}")
    assert reloaded.status_code == 200
    body = reloaded.json()["data"]
    assert body["status"] == "resolved"
    assert body["resolution_note"] == "QA_TEST 重启前"
    assert body["resolved_at"] is not None
    assert body["version"] == 2
