import ast
import json
from pathlib import Path
from uuid import uuid4

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from hermes_api.application import AdvisorService
from hermes_api.cli import migrate
from hermes_api.domain import PolicyError
from hermes_api.main import create_app
from hermes_api.model import MockModel
from hermes_api.settings import Settings
from hermes_api.storage import Base, Subject, User

ORIGIN = "http://127.0.0.1:5173"


@pytest.fixture
def system(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'isolated.db'}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    migrate()
    app = create_app(Settings(database_url=url, environment="test"))
    with Session(app.state.engine) as db:
        for name in ("alice", "bob"):
            db.add(
                User(
                    id=name,
                    username=name,
                    password_hash=PasswordHasher().hash("QA_TEST_password"),
                    timezone="Asia/Shanghai",
                )
            )
        db.flush()
        db.add(Subject(id=str(uuid4()), owner_id="bob", name="QA_TEST_bob_subject"))
        db.commit()
    return app, url


def authenticated(app, name="alice"):
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": name, "password": "QA_TEST_password"},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": response.json()["data"]["csrf_token"]})
    assert "HttpOnly" in response.headers["set-cookie"]
    return client


def start(client, **extra):
    key = str(uuid4())
    body = {"operation_id": key, "goal": "QA_TEST_中文学习", **extra}
    return client.post(
        "/api/v1/learning-sessions", json=body, headers={"Idempotency-Key": key}
    ), body


def test_auth_csrf_and_logout(system):
    app, _ = system
    client = TestClient(app)
    assert client.get("/api/v1/auth/session").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "wrong"},
            headers={"Origin": ORIGIN},
        ).status_code
        == 401
    )
    client = authenticated(app)
    assert client.get("/api/v1/auth/session").json()["data"]["user"]["timezone"] == "Asia/Shanghai"
    client.headers.pop("X-CSRF-Token")
    assert start(client)[0].status_code == 403
    client.headers["X-CSRF-Token"] = client.get("/api/v1/auth/session").json()["data"]["csrf_token"]
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/session").status_code == 401


def test_persistence_idempotency_and_version(system):
    app, url = system
    client = authenticated(app)
    assert client.get("/api/v1/learning-sessions/current").json()["data"] is None
    result, body = start(client)
    assert result.status_code == 201
    value = result.json()["data"]
    assert value["version"] == 1 and value["status"] == "active"
    assert (
        client.post(
            "/api/v1/learning-sessions",
            json=body,
            headers={"Idempotency-Key": body["operation_id"]},
        ).json()["data"]
        == value
    )
    changed = {**body, "goal": "changed"}
    assert (
        client.post(
            "/api/v1/learning-sessions",
            json=changed,
            headers={"Idempotency-Key": body["operation_id"]},
        ).status_code
        == 409
    )
    assert start(client)[0].status_code == 409
    restarted = create_app(Settings(database_url=url, environment="test"))
    resumed = authenticated(restarted)
    assert resumed.get("/api/v1/learning-sessions/current").json()["data"] == value
    key = str(uuid4())
    path = f"/api/v1/learning-sessions/{value['id']}/end"
    command = {"operation_id": key}
    headers = {"Idempotency-Key": key}
    assert resumed.post(path, json=command, headers=headers).status_code == 428
    assert resumed.post(path, json=command, headers={**headers, "If-Match": "9"}).status_code == 409
    ended = resumed.post(path, json=command, headers={**headers, "If-Match": "1"})
    assert ended.status_code == 200
    assert ended.json()["data"]["ended_at"] and ended.json()["data"]["version"] == 2
    assert (
        resumed.post(path, json=command, headers={**headers, "If-Match": "1"}).json()["data"]
        == ended.json()["data"]
    )
    assert resumed.get("/api/v1/learning-sessions/current").json()["data"] is None


def session_action(client, session_id, action, version, key=None):
    key = key or str(uuid4())
    headers = {"Idempotency-Key": key, "If-Match": f'"{version}"'}
    return client.post(
        f"/api/v1/learning-sessions/{session_id}/{action}",
        json={"operation_id": key},
        headers=headers,
    )


def test_learning_session_pause_resume_cancel_and_history(system):
    app, url = system
    alice, bob = authenticated(app), authenticated(app, "bob")
    created, _ = start(alice)
    session = created.json()["data"]
    session_id = session["id"]

    paused = session_action(alice, session_id, "pause", 1)
    assert paused.status_code == 200
    assert paused.json()["data"]["status"] == "paused"
    assert paused.json()["data"]["version"] == 2
    assert alice.get("/api/v1/learning-sessions/current").json()["data"] == paused.json()["data"]
    assert start(alice)[0].status_code == 409

    assert session_action(alice, session_id, "resume", 1).status_code == 409
    resumed = session_action(alice, session_id, "resume", 2)
    assert resumed.status_code == 200
    assert resumed.json()["data"]["status"] == "active"
    assert resumed.json()["data"]["version"] == 3
    cancelled = session_action(alice, session_id, "cancel", 3)
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "cancelled"
    assert cancelled.json()["data"]["ended_at"]
    assert alice.get("/api/v1/learning-sessions/current").json()["data"] is None

    detail = alice.get(f"/api/v1/learning-sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["data"] == cancelled.json()["data"]
    history = alice.get("/api/v1/learning-sessions?limit=20").json()["data"]
    assert history == {"items": [cancelled.json()["data"]], "next_cursor": None}
    assert bob.get(f"/api/v1/learning-sessions/{session_id}").status_code == 404
    assert bob.get("/api/v1/learning-sessions").json()["data"]["items"] == []
    assert alice.get("/api/v1/learning-sessions?limit=101").status_code == 422

    restarted = create_app(Settings(database_url=url, environment="test"))
    restored = authenticated(restarted)
    assert (
        restored.get(f"/api/v1/learning-sessions/{session_id}").json()["data"]
        == detail.json()["data"]
    )


def test_session_action_idempotency_and_illegal_transitions(system):
    app, _ = system
    client = authenticated(app)
    result, _ = start(client)
    session_id = result.json()["data"]["id"]
    key = str(uuid4())
    first = session_action(client, session_id, "pause", 1, key)
    replay = session_action(client, session_id, "pause", 1, key)
    assert first.status_code == replay.status_code == 200
    assert first.json()["data"] == replay.json()["data"]
    assert session_action(client, session_id, "resume", 2).status_code == 200
    assert session_action(client, session_id, "pause", 3).status_code == 200
    assert session_action(client, session_id, "cancel", 4).status_code == 200
    assert session_action(client, session_id, "resume", 5).status_code == 409
    assert session_action(client, session_id, "cancel", 5).status_code == 409
    missing_precondition_key = str(uuid4())
    assert (
        client.post(
            f"/api/v1/learning-sessions/{session_id}/resume",
            json={"operation_id": missing_precondition_key},
            headers={"Idempotency-Key": missing_precondition_key},
        ).status_code
        == 428
    )


def test_session_timer_segments_close_on_pause_and_terminal_action(system):
    from sqlalchemy import func, select

    from hermes_api.storage import SessionTimeSegmentRow

    app, _ = system
    client = authenticated(app)
    created, _body = start(client, timing_enabled=True, method_id="active-recall")
    assert created.status_code == 201
    value = created.json()["data"]
    assert value["timing_enabled"] is True
    assert value["method_id"] == "active-recall"
    assert len(value["time_segments"]) == 1
    assert value["time_segments"][0]["ended_at"] is None

    session_id = value["id"]
    paused = session_action(client, session_id, "pause", 1)
    assert paused.status_code == 200
    first_segment = paused.json()["data"]["time_segments"][0]
    assert first_segment["ended_at"] is not None
    assert paused.json()["data"]["effective_duration_seconds"] >= 0
    with Session(app.state.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(SessionTimeSegmentRow)
                .where(SessionTimeSegmentRow.session_id == session_id)
            )
            == 1
        )

    resumed = session_action(client, session_id, "resume", 2)
    assert resumed.status_code == 200
    assert len(resumed.json()["data"]["time_segments"]) == 2
    cancelled = session_action(client, session_id, "cancel", 3)
    assert cancelled.status_code == 200
    assert len(cancelled.json()["data"]["time_segments"]) == 2
    assert all(segment["ended_at"] for segment in cancelled.json()["data"]["time_segments"])
    assert cancelled.json()["data"]["effective_duration_seconds"] == sum(
        segment["duration_seconds"] for segment in cancelled.json()["data"]["time_segments"]
    )

    no_timer, _ = start(client, timing_enabled=False)
    assert no_timer.status_code == 201
    assert no_timer.json()["data"]["time_segments"] == []
    assert no_timer.json()["data"]["effective_duration_seconds"] == 0
    assert session_action(client, no_timer.json()["data"]["id"], "cancel", 1).status_code == 200
    assert start(client, method_id="unknown-method")[0].status_code == 422


def test_timer_duration_uses_only_active_segments_and_replays_are_noops(system, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import func, select

    from hermes_api import application, domain, storage
    from hermes_api.storage import SessionTimeSegmentRow

    app, _ = system
    client = authenticated(app)
    clock = {"now": datetime(2026, 9, 30, 8, 0, tzinfo=UTC)}
    frozen_now = lambda: clock["now"]
    monkeypatch.setattr(domain, "utc_now", frozen_now)
    monkeypatch.setattr(application, "utc_now", frozen_now)
    monkeypatch.setattr(storage, "utc_now", frozen_now)

    created, create_body = start(client, timing_enabled=True)
    assert created.status_code == 201
    session_id = created.json()["data"]["id"]
    create_key = create_body["operation_id"]
    create_replay = client.post(
        "/api/v1/learning-sessions",
        json=create_body,
        headers={"Idempotency-Key": create_key},
    )
    assert create_replay.json()["data"] == created.json()["data"]

    clock["now"] += timedelta(seconds=60)
    pause_key = str(uuid4())
    paused = session_action(client, session_id, "pause", 1, pause_key)
    assert paused.json()["data"]["effective_duration_seconds"] == 60
    assert len(paused.json()["data"]["time_segments"]) == 1
    assert (
        session_action(client, session_id, "pause", 1, pause_key).json()["data"]
        == paused.json()["data"]
    )

    with Session(app.state.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(SessionTimeSegmentRow)
                .where(SessionTimeSegmentRow.session_id == session_id)
            )
            == 1
        )

    clock["now"] += timedelta(hours=1)
    assert (
        client.get(f"/api/v1/learning-sessions/{session_id}").json()["data"][
            "effective_duration_seconds"
        ]
        == 60
    )
    resume_key = str(uuid4())
    resumed = session_action(client, session_id, "resume", 2, resume_key)
    assert len(resumed.json()["data"]["time_segments"]) == 2
    assert (
        session_action(client, session_id, "resume", 2, resume_key).json()["data"]
        == resumed.json()["data"]
    )

    clock["now"] += timedelta(seconds=30)
    end_key = str(uuid4())
    ended = session_action(client, session_id, "end", 3, end_key)
    ended_data = ended.json()["data"]
    assert ended_data["status"] == "ended"
    assert ended_data["effective_duration_seconds"] == 90
    assert [segment["duration_seconds"] for segment in ended_data["time_segments"]] == [60, 30]
    assert session_action(client, session_id, "end", 3, end_key).json()["data"] == ended_data
    with Session(app.state.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(SessionTimeSegmentRow)
                .where(SessionTimeSegmentRow.session_id == session_id)
            )
            == 2
        )


def test_database_rejects_duplicate_open_and_cross_owner_timer_segments(system):
    from datetime import UTC, datetime

    from sqlalchemy.exc import IntegrityError

    from hermes_api.storage import SessionTimeSegmentRow

    app, _ = system
    client = authenticated(app)
    created, _ = start(client, timing_enabled=True)
    value = created.json()["data"]
    session_id = value["id"]
    with Session(app.state.engine) as db:
        db.add(
            SessionTimeSegmentRow(
                id=str(uuid4()),
                owner_id="alice",
                session_id=session_id,
                started_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        db.add(
            SessionTimeSegmentRow(
                id=str(uuid4()),
                owner_id="bob",
                session_id=session_id,
                started_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_history_cursor_returns_bounded_pages(system):
    app, _ = system
    client = authenticated(app)
    first, _ = start(client)
    first_id = first.json()["data"]["id"]
    assert session_action(client, first_id, "cancel", 1).status_code == 200
    second, _ = start(client)
    second_id = second.json()["data"]["id"]

    page_one = client.get("/api/v1/learning-sessions?limit=1").json()["data"]
    assert [item["id"] for item in page_one["items"]] == [second_id]
    assert page_one["next_cursor"] == second_id
    page_two = client.get(
        f"/api/v1/learning-sessions?limit=1&cursor={page_one['next_cursor']}"
    ).json()["data"]
    assert [item["id"] for item in page_two["items"]] == [first_id]
    assert page_two["next_cursor"] is None
    assert client.get(f"/api/v1/learning-sessions?cursor={uuid4()}").status_code == 422


def test_timing_migration_preserves_existing_sessions(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from hermes_api.storage import make_engine

    url = f"sqlite:///{tmp_path / 'upgrade_existing.db'}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "0001")
    engine = make_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, username, password_hash, timezone) "
                "VALUES ('legacy', 'QA_TEST_legacy', 'unused', 'Asia/Shanghai')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO learning_sessions "
                "(id, owner_id, goal, subject_id, status, version, started_at, ended_at, "
                "day_timezone, learning_date) VALUES "
                "('legacy-session', 'legacy', NULL, NULL, 'paused', 7, "
                "'2026-09-29 02:00:00', NULL, 'Asia/Shanghai', '2026-09-29')"
            )
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT id, status, version, learning_date, timing_enabled, method_id "
                "FROM learning_sessions WHERE id='legacy-session'"
            )
        ).one()
        assert tuple(row) == (
            "legacy-session",
            "paused",
            7,
            "2026-09-29",
            0,
            None,
        )
        assert connection.execute(text("SELECT count(*) FROM session_time_segments")).scalar() == 0


def test_ownership_validation_and_health(system):
    app, _ = system
    alice, bob = authenticated(app), authenticated(app, "bob")
    subject = bob.get("/api/v1/subjects").json()["data"]["items"][0]["id"]
    assert alice.get("/api/v1/subjects").json()["data"]["items"] == []
    assert start(alice, subject_id=subject)[0].status_code == 404
    result, _ = start(bob, subject_id=subject)
    assert result.status_code == 201
    key = str(uuid4())
    path = f"/api/v1/learning-sessions/{result.json()['data']['id']}/end"
    assert (
        alice.post(
            path, json={"operation_id": key}, headers={"Idempotency-Key": key, "If-Match": "1"}
        ).status_code
        == 404
    )
    assert start(alice, goal="a" * 2001)[0].status_code == 422
    assert alice.get("/api/v1/health/ready").status_code == 200
    Base.metadata.drop_all(app.state.engine)
    assert alice.get("/api/v1/health/ready").status_code == 503
    assert alice.get("/api/v1/health/live").status_code == 200


def test_production_and_architecture():
    with pytest.raises(ValueError):
        Settings(environment="production")
    root = Path(__file__).parents[1] / "src/hermes_api"
    for module in ("domain.py", "application.py", "ports.py"):
        tree = ast.parse((root / module).read_text())
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        assert not any(
            name.startswith(("fastapi", "sqlalchemy", "hermes_api.storage")) for name in imports
        )


def test_agent_evidence_and_budget():
    evidence = [{"id": "a", "version": 1, "text": "Practiced one question"}]
    assert AdvisorService(MockModel()).advise(evidence)["facts"][0]["source_version"] == 1
    assert not MockModel.capabilities["image"]
    with pytest.raises(PolicyError):
        AdvisorService(MockModel()).advise(evidence, budget=1)

    class UntrustedModel:
        def advise(self, evidence, budget):
            return {
                "facts": [{"source_id": "unknown", "source_version": 1, "text": "invented"}],
                "inferences": [],
                "missing_information": [],
            }

    with pytest.raises(PolicyError, match="unknown evidence"):
        AdvisorService(UntrustedModel()).advise(evidence)
    assert json.dumps(AdvisorService(MockModel()).advise([]))


@pytest.mark.parametrize(
    "output",
    [
        None,
        "bad",
        {},
        {"facts": "bad", "inferences": [], "missing_information": []},
        {"facts": [None], "inferences": [], "missing_information": []},
    ],
)
def test_agent_malformed_output(output):
    class BrokenModel:
        def advise(self, evidence, budget):
            return output

    with pytest.raises(PolicyError):
        AdvisorService(BrokenModel()).advise([])


def test_migration_recovery(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    from hermes_api.storage import make_engine

    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    migrate()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.downgrade(config, "base")
    engine = make_engine(url)
    assert inspect(engine).get_table_names() == ["alembic_version"]
    migrate()
    assert "learning_sessions" in inspect(engine).get_table_names()


def test_expired_session_and_origin(system):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from hermes_api.storage import LoginSession

    app, _ = system
    client = authenticated(app)
    assert start(client)[0].status_code == 201
    client.headers["Origin"] = "https://untrusted.example"
    assert client.post("/api/v1/auth/logout").status_code == 403
    with Session(app.state.engine) as db:
        db.execute(update(LoginSession).values(expires_at=datetime.now(UTC) - timedelta(days=1)))
        db.commit()
    assert client.get("/api/v1/auth/session").status_code == 401


def test_bootstrap_five_subjects_and_no_overwrite(tmp_path, monkeypatch):
    from sqlalchemy import select

    from hermes_api.cli import bootstrap
    from hermes_api.storage import make_engine

    url = f"sqlite:///{tmp_path / 'bootstrap.db'}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    migrate()
    bootstrap("QA_TEST_bootstrap", "QA_TEST_long_password")
    with Session(make_engine(url)) as db:
        assert set(db.scalars(select(Subject.name))) == {
            "信号与系统",
            "电路基础",
            "高等数学",
            "英语",
            "政治",
        }
        assert db.scalar(select(User.password_hash)).startswith("$argon2")
    with pytest.raises(ValueError, match="already exists"):
        bootstrap("QA_TEST_bootstrap", "QA_TEST_long_password")


def test_inference_references_are_checked():
    class InvalidInference:
        def advise(self, evidence, budget):
            return {
                "facts": [],
                "inferences": [{"text": "guess", "source_refs": [{"id": "other", "version": 1}]}],
                "missing_information": [],
            }

    with pytest.raises(PolicyError, match="unknown evidence"):
        AdvisorService(InvalidInference()).advise([{"id": "known", "version": 1, "text": "source"}])


def test_concurrent_replay_creates_one_session(system):
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import func, select

    from hermes_api.storage import SessionRow

    app, _ = system
    first, second = authenticated(app), authenticated(app)
    key = str(uuid4())
    body = {"operation_id": key, "goal": "QA_TEST_concurrent"}

    def submit(client):
        return client.post("/api/v1/learning-sessions", json=body, headers={"Idempotency-Key": key})

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, [first, second]))
    assert [result.status_code for result in responses] == [201, 201]
    assert responses[0].json()["data"] == responses[1].json()["data"]
    with Session(app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(SessionRow)) == 1


@pytest.mark.parametrize("invalid", ["duplicate", "status", "version", "owner", "subject_owner"])
def test_database_rejects_invalid_direct_writes(system, invalid):
    from sqlalchemy import select, text
    from sqlalchemy.exc import IntegrityError

    from hermes_api.storage import SessionRow

    app, _ = system
    response, _ = start(authenticated(app))
    assert response.status_code == 201
    with Session(app.state.engine) as db:
        assert db.scalar(text("PRAGMA foreign_keys")) == 1
        source = db.get(SessionRow, response.json()["data"]["id"])
        values = {
            column.name: getattr(source, column.name) for column in SessionRow.__table__.columns
        }
        values.update(id=str(uuid4()), status="ended")
        if invalid == "duplicate":
            values["status"] = "paused"
        elif invalid == "status":
            values["status"] = "impossible"
        elif invalid == "version":
            values["version"] = 0
        elif invalid == "owner":
            values["owner_id"] = "missing-user"
        else:
            values["subject_id"] = db.scalar(select(Subject.id).where(Subject.owner_id == "bob"))
        db.add(SessionRow(**values))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_orm_matches_migration_schema(system):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    app, _ = system
    with app.state.engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
