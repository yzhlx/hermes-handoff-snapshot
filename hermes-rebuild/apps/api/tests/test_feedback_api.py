from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_foundation import authenticated, start

from hermes_api.cli import migrate
from hermes_api.main import create_app
from hermes_api.settings import Settings
from hermes_api.storage import AttemptRevisionRow, ProblemAttemptRow, Subject, User


@pytest.fixture
def feedback_system(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'feedback.db'}"
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


def test_reflection_attempt_correction_persistence_and_idempotency(feedback_system):
    app, url = feedback_system
    client = authenticated(app)
    started, _ = start(client)
    session = started.json()["data"]
    end_key = str(uuid4())
    ended = client.post(
        f"/api/v1/learning-sessions/{session['id']}/end",
        json={"operation_id": end_key},
        headers={"Idempotency-Key": end_key, "If-Match": '"1"'},
    )
    assert ended.status_code == 200

    reflect_key = str(uuid4())
    reflection_body = {
        "operation_id": reflect_key,
        "session_id": session["id"],
        "recalled_text": "QA_TEST_说明了采样条件",
        "stuck_note": "QA_TEST_δ 符号的来源",
        "resume_note": "QA_TEST_回到第三题",
    }
    reflected = client.post(
        "/api/v1/session-reflections",
        json=reflection_body,
        headers={"Idempotency-Key": reflect_key},
    )
    assert reflected.status_code == 201, reflected.text
    replayed = client.post(
        "/api/v1/session-reflections",
        json=reflection_body,
        headers={"Idempotency-Key": reflect_key},
    )
    assert replayed.json()["data"] == reflected.json()["data"]
    assert (
        client.get(f"/api/v1/session-reflections/{session['id']}").json()["data"]["resume_note"]
        == "QA_TEST_回到第三题"
    )
    assert (
        client.get(f"/api/v1/learning-sessions/{session['id']}").json()["data"]["resume_note"]
        == "QA_TEST_回到第三题"
    )
    reflection_update_key = str(uuid4())
    reflection_update = client.patch(
        f"/api/v1/session-reflections/{session['id']}",
        json={"operation_id": reflection_update_key, "resume_note": "QA_TEST_回到第四题"},
        headers={"Idempotency-Key": reflection_update_key, "If-Match": '"1"'},
    )
    assert reflection_update.status_code == 200
    assert reflection_update.json()["data"]["version"] == 2
    assert (
        client.get(f"/api/v1/learning-sessions/{session['id']}").json()["data"]["resume_note"]
        == "QA_TEST_回到第四题"
    )

    problem_key = str(uuid4())
    problem = client.post(
        "/api/v1/problems",
        json={
            "operation_id": problem_key,
            "title": "QA_TEST_采样定理",
            "statement": "QA_TEST_证明采样条件",
        },
        headers={"Idempotency-Key": problem_key},
    )
    assert problem.status_code == 201, problem.text
    problem_id = problem.json()["data"]["id"]
    update_problem_key = str(uuid4())
    updated_problem = client.patch(
        f"/api/v1/problems/{problem_id}",
        json={
            "operation_id": update_problem_key,
            "title": "QA_TEST_更新标题",
            "is_representative": True,
        },
        headers={"Idempotency-Key": update_problem_key, "If-Match": '"1"'},
    )
    assert updated_problem.status_code == 200
    assert updated_problem.json()["data"]["version"] == 2
    assert updated_problem.json()["data"]["statement"] == "QA_TEST_证明采样条件"
    assert updated_problem.json()["data"]["is_representative"] is True
    for invalid_patch in ({}, {"archived": None}, {"is_representative": None}):
        invalid_key = str(uuid4())
        response = client.patch(
            f"/api/v1/problems/{problem_id}",
            json={"operation_id": invalid_key, **invalid_patch},
            headers={"Idempotency-Key": invalid_key, "If-Match": '"2"'},
        )
        assert response.status_code == 422, response.text
    unchanged_problem = client.get(f"/api/v1/problems/{problem_id}").json()["data"]
    assert unchanged_problem["version"] == 2
    assert unchanged_problem["archived"] is False
    assert unchanged_problem["is_representative"] is True
    second_problem_key = str(uuid4())
    second_problem = client.post(
        "/api/v1/problems",
        json={"operation_id": second_problem_key, "statement": "QA_TEST_第二题"},
        headers={"Idempotency-Key": second_problem_key},
    )
    assert second_problem.status_code == 201
    first_page = client.get("/api/v1/problems?limit=1").json()["data"]
    assert len(first_page["items"]) == 1 and first_page["next_cursor"]
    second_page = client.get(f"/api/v1/problems?limit=1&cursor={first_page['next_cursor']}").json()[
        "data"
    ]
    assert len(second_page["items"]) == 1
    assert first_page["items"][0]["id"] != second_page["items"][0]["id"]
    attempt_key = str(uuid4())
    attempt_body = {
        "operation_id": attempt_key,
        "session_id": session["id"],
        "problem_id": problem_id,
        "independence": "independent",
        "answer_check": "pending",
        "error_categories": [],
    }
    pending = client.post(
        "/api/v1/problem-attempts", json=attempt_body, headers={"Idempotency-Key": attempt_key}
    )
    assert pending.status_code == 201, pending.text
    assert pending.json()["data"]["result"] is None
    assert pending.json()["data"]["verified_at"] is None
    assert pending.json()["data"]["evidence_eligibility"]["eligible"] is False
    replayed_attempt = client.post(
        "/api/v1/problem-attempts", json=attempt_body, headers={"Idempotency-Key": attempt_key}
    )
    assert replayed_attempt.json()["data"] == pending.json()["data"]

    attempt_id = pending.json()["data"]["id"]
    corrected_key = str(uuid4())
    checked = client.patch(
        f"/api/v1/problem-attempts/{attempt_id}",
        json={"operation_id": corrected_key, "answer_check": "checked", "result": "correct"},
        headers={"Idempotency-Key": corrected_key, "If-Match": '"1"'},
    )
    assert checked.status_code == 200, checked.text
    assert checked.json()["data"]["version"] == 2
    assert checked.json()["data"]["evidence_eligibility"]["eligible"] is True
    stale_key = str(uuid4())
    stale = client.patch(
        f"/api/v1/problem-attempts/{attempt_id}",
        json={"operation_id": stale_key, "result": "incorrect"},
        headers={"Idempotency-Key": stale_key, "If-Match": '"1"'},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["current_version"] == 2
    assert stale.json()["error"]["current"]["result"] == "correct"

    note_key = str(uuid4())
    note_attempt_body = {
        "operation_id": note_key,
        "session_id": session["id"],
        "problem_id": problem_id,
        "independence": "hinted",
        "answer_check": "checked",
        "result": "incorrect",
        "error_categories": ["other"],
        "other_error_note": "QA_TEST_符号忘了",
    }
    note_attempt = client.post(
        "/api/v1/problem-attempts", json=note_attempt_body, headers={"Idempotency-Key": note_key}
    )
    assert note_attempt.status_code == 201
    note_id = note_attempt.json()["data"]["id"]
    verified_at = note_attempt.json()["data"]["verified_at"]
    revise_text_key = str(uuid4())
    revised_text = client.patch(
        f"/api/v1/problem-attempts/{note_id}",
        json={
            "operation_id": revise_text_key,
            "answer_check": "checked",
            "result": "incorrect",
            "attempt_text": "QA_TEST_补充了思路，但核对结果没有变化",
        },
        headers={"Idempotency-Key": revise_text_key, "If-Match": '"1"'},
    )
    assert revised_text.status_code == 200, revised_text.text
    assert revised_text.json()["data"]["version"] == 2
    assert revised_text.json()["data"]["verified_at"] == verified_at
    revise_note_key = str(uuid4())
    revised_note = client.patch(
        f"/api/v1/problem-attempts/{note_id}",
        json={"operation_id": revise_note_key, "other_error_note": "QA_TEST_方向弄反"},
        headers={"Idempotency-Key": revise_note_key, "If-Match": '"2"'},
    )
    assert revised_note.status_code == 200, revised_note.text
    assert revised_note.json()["data"]["other_error_note"] == "QA_TEST_方向弄反"
    assert revised_note.json()["data"]["verified_at"] == verified_at
    clear_note_key = str(uuid4())
    cleared_note = client.patch(
        f"/api/v1/problem-attempts/{note_id}",
        json={"operation_id": clear_note_key, "other_error_note": None},
        headers={"Idempotency-Key": clear_note_key, "If-Match": '"3"'},
    )
    assert cleared_note.status_code == 200
    assert cleared_note.json()["data"]["other_error_note"] is None

    archive_key = str(uuid4())
    archived = client.patch(
        f"/api/v1/problems/{problem_id}",
        json={"operation_id": archive_key, "archived": True},
        headers={"Idempotency-Key": archive_key, "If-Match": '"2"'},
    )
    assert archived.status_code == 200 and archived.json()["data"]["archived"] is True
    assert all(
        item["id"] != problem_id for item in client.get("/api/v1/problems").json()["data"]["items"]
    )
    archived_items = client.get("/api/v1/problems?archived=true").json()["data"]["items"]
    assert any(item["id"] == problem_id for item in archived_items)
    bob_client = authenticated(app, "bob")
    assert all(
        item["id"] != problem_id
        for item in bob_client.get("/api/v1/problems?archived=true").json()["data"]["items"]
    )
    restore_key = str(uuid4())
    restored_problem = client.patch(
        f"/api/v1/problems/{problem_id}",
        json={"operation_id": restore_key, "archived": False},
        headers={"Idempotency-Key": restore_key, "If-Match": '"3"'},
    )
    assert restored_problem.status_code == 200
    assert any(
        item["id"] == problem_id for item in client.get("/api/v1/problems").json()["data"]["items"]
    )
    assert all(
        item["id"] != problem_id
        for item in client.get("/api/v1/problems?archived=true").json()["data"]["items"]
    )

    app2 = create_app(Settings(database_url=url, environment="test"))
    restored = authenticated(app2)
    detail = restored.get(f"/api/v1/problems/{problem_id}").json()["data"]
    assert detail["attempts"][0]["result"] == "correct"
    with Session(app2.state.engine) as db:
        row = db.scalar(select(ProblemAttemptRow).where(ProblemAttemptRow.id == attempt_id))
        assert row.answer_check == "checked" and row.version == 2
        revisions = db.scalars(
            select(AttemptRevisionRow).where(AttemptRevisionRow.attempt_id == attempt_id)
        ).all()
        assert len(revisions) == 1 and '"answer_check": "pending"' in revisions[0].snapshot


def test_feedback_rejects_unchecked_claims_and_cross_owner_relations(feedback_system):
    app, _ = feedback_system
    alice, bob = authenticated(app), authenticated(app, "bob")
    key = str(uuid4())
    invalid = alice.post(
        "/api/v1/problem-attempts",
        json={
            "operation_id": key,
            "session_id": str(uuid4()),
            "problem_id": str(uuid4()),
            "independence": "independent",
            "answer_check": "pending",
            "result": "correct",
        },
        headers={"Idempotency-Key": key},
    )
    assert invalid.status_code == 422
    assert "data" not in invalid.json()
    owner_key = str(uuid4())
    own_problem = bob.post(
        "/api/v1/problems",
        json={"operation_id": owner_key, "statement": "QA_TEST_bob question"},
        headers={"Idempotency-Key": owner_key},
    )
    own_session, _ = start(alice)
    attempt_key = str(uuid4())
    cross = alice.post(
        "/api/v1/problem-attempts",
        json={
            "operation_id": attempt_key,
            "session_id": own_session.json()["data"]["id"],
            "problem_id": own_problem.json()["data"]["id"],
            "independence": "unable",
            "answer_check": "pending",
        },
        headers={"Idempotency-Key": attempt_key},
    )
    assert cross.status_code == 404


def test_0003_preserves_populated_0002_session_and_timer_segment(tmp_path, monkeypatch):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from hermes_api.storage import make_engine

    url = f"sqlite:///{tmp_path / 'legacy_0002.db'}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "0002")
    engine = make_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, username, password_hash, timezone) VALUES ('legacy', 'QA_TEST_legacy', 'unused', 'Asia/Shanghai')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO learning_sessions (id, owner_id, goal, subject_id, status, version, started_at, ended_at, day_timezone, learning_date, timing_enabled, method_id) VALUES ('legacy-session', 'legacy', 'QA_TEST_old', NULL, 'active', 3, '2026-09-29 02:00:00', NULL, 'Asia/Shanghai', '2026-09-29', 1, 'active-recall')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO session_time_segments (id, owner_id, session_id, started_at, ended_at) VALUES ('legacy-segment', 'legacy', 'legacy-session', '2026-09-29 02:00:00', NULL)"
            )
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT id, status, version, learning_date, timing_enabled, method_id, kind, previous_session_id FROM learning_sessions WHERE id='legacy-session'"
            )
        ).one()
        assert tuple(row) == (
            "legacy-session",
            "active",
            3,
            "2026-09-29",
            1,
            "active-recall",
            "free",
            None,
        )
        segment = connection.execute(
            text(
                "SELECT id, owner_id, session_id FROM session_time_segments WHERE id='legacy-segment'"
            )
        ).one()
        assert tuple(segment) == ("legacy-segment", "legacy", "legacy-session")
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_concurrent_attempt_replay_writes_once(feedback_system):
    app, _ = feedback_system
    client_a = authenticated(app)
    client_b = authenticated(app)
    problem_key = str(uuid4())
    problem = client_a.post(
        "/api/v1/problems",
        json={"operation_id": problem_key, "statement": "QA_TEST_并发同题"},
        headers={"Idempotency-Key": problem_key},
    ).json()["data"]
    session = start(client_a)[0].json()["data"]
    attempt_key = str(uuid4())
    body = {
        "operation_id": attempt_key,
        "session_id": session["id"],
        "problem_id": problem["id"],
        "independence": "unable",
        "answer_check": "pending",
        "error_categories": [],
    }

    def submit(client):
        return client.post(
            "/api/v1/problem-attempts", json=body, headers={"Idempotency-Key": attempt_key}
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        one, two = list(pool.map(submit, (client_a, client_b)))
    assert one.status_code == two.status_code == 201
    assert one.json()["data"]["id"] == two.json()["data"]["id"]
    with Session(app.state.engine) as db:
        rows = db.scalars(
            select(ProblemAttemptRow).where(ProblemAttemptRow.problem_id == problem["id"])
        ).all()
        assert len(rows) == 1
