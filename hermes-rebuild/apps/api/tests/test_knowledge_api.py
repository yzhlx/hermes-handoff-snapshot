from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from argon2 import PasswordHasher
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_foundation import authenticated, start

from hermes_api.cli import migrate
from hermes_api.knowledge_storage import ChapterRow
from hermes_api.main import create_app
from hermes_api.settings import Settings
from hermes_api.storage import Subject, User


@pytest.fixture
def knowledge_system(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'knowledge.db'}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    migrate()
    app = create_app(Settings(database_url=url, environment="test"))
    alice_subject = str(uuid4())
    alice_other_subject = str(uuid4())
    bob_subject = str(uuid4())
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
        db.add_all(
            [
                Subject(id=alice_subject, owner_id="alice", name="QA_TEST_信号与系统"),
                Subject(id=alice_other_subject, owner_id="alice", name="QA_TEST_英语"),
                Subject(id=bob_subject, owner_id="bob", name="QA_TEST_电路原理"),
            ]
        )
        db.commit()
    return app, url, alice_subject, alice_other_subject, bob_subject


def test_knowledge_crud_links_session_archive_and_owner_scope(knowledge_system):
    app, url, subject_id, other_subject_id, _ = knowledge_system
    client = authenticated(app)

    subjects = client.get("/api/v1/subjects").json()["data"]["items"]
    assert (
        next(item for item in subjects if item["id"] == subject_id)["group_label"] == "上海大学829"
    )
    space = client.get(f"/api/v1/subjects/{subject_id}/space")
    assert space.status_code == 200 and space.json()["data"]["chapters"] == []
    assert space.json()["data"]["recent_sessions"] == []
    assert space.json()["data"]["recent_problems"] == []

    chapter_key = str(uuid4())
    chapter_response = client.post(
        "/api/v1/chapters",
        json={
            "operation_id": chapter_key,
            "subject_id": subject_id,
            "name": "  QA_TEST_傅里叶变换  ",
        },
        headers={"Idempotency-Key": chapter_key},
    )
    assert chapter_response.status_code == 201, chapter_response.text
    chapter = chapter_response.json()["data"]
    assert chapter["name"] == "QA_TEST_傅里叶变换" and chapter["version"] == 1
    assert (
        client.post(
            "/api/v1/chapters",
            json={
                "operation_id": chapter_key,
                "subject_id": subject_id,
                "name": "  QA_TEST_傅里叶变换  ",
            },
            headers={"Idempotency-Key": chapter_key},
        ).json()["data"]
        == chapter
    )
    for invalid_patch in ({}, {"name": None}, {"order_index": None}, {"archived": None}):
        invalid_key = str(uuid4())
        response = client.patch(
            f"/api/v1/chapters/{chapter['id']}",
            json={"operation_id": invalid_key, **invalid_patch},
            headers={"Idempotency-Key": invalid_key, "If-Match": '"1"'},
        )
        assert response.status_code == 422, response.text
    assert client.get(f"/api/v1/chapters/{chapter['id']}").json()["data"]["version"] == 1

    point_key = str(uuid4())
    point_response = client.post(
        "/api/v1/knowledge-points",
        json={
            "operation_id": point_key,
            "chapter_id": chapter["id"],
            "name": "QA_TEST_频域性质",
            "notes": "QA_TEST_说明",
        },
        headers={"Idempotency-Key": point_key},
    )
    assert point_response.status_code == 201, point_response.text
    point = point_response.json()["data"]
    assert point["subject_id"] == subject_id and point["version"] == 1
    for invalid_patch in ({}, {"name": None}, {"archived": None}):
        invalid_key = str(uuid4())
        response = client.patch(
            f"/api/v1/knowledge-points/{point['id']}",
            json={"operation_id": invalid_key, **invalid_patch},
            headers={"Idempotency-Key": invalid_key, "If-Match": '"1"'},
        )
        assert response.status_code == 422, response.text
    assert client.get(f"/api/v1/knowledge-points/{point['id']}").json()["data"]["version"] == 1
    second_point_key = str(uuid4())
    second_point = client.post(
        "/api/v1/knowledge-points",
        json={
            "operation_id": second_point_key,
            "chapter_id": chapter["id"],
            "name": "QA_TEST_卷积定理",
        },
        headers={"Idempotency-Key": second_point_key},
    ).json()["data"]
    first_point_page = client.get(
        f"/api/v1/knowledge-points?chapter_id={chapter['id']}&limit=1"
    ).json()["data"]
    second_point_page = client.get(
        f"/api/v1/knowledge-points?chapter_id={chapter['id']}&limit=1&cursor={first_point_page['next_cursor']}"
    ).json()["data"]
    assert {first_point_page["items"][0]["id"], second_point_page["items"][0]["id"]} == {
        point["id"],
        second_point["id"],
    }

    missing_precondition_key = str(uuid4())
    assert (
        client.patch(
            f"/api/v1/chapters/{chapter['id']}",
            json={
                "operation_id": missing_precondition_key,
                "name": "QA_TEST_无IfMatch",
            },
            headers={"Idempotency-Key": missing_precondition_key},
        ).status_code
        == 428
    )
    stale_key = str(uuid4())
    stale = client.patch(
        f"/api/v1/chapters/{chapter['id']}",
        json={
            "operation_id": stale_key,
            "name": "QA_TEST_旧版本",
        },
        headers={"Idempotency-Key": stale_key, "If-Match": '"9"'},
    )
    assert stale.status_code == 409 and stale.json()["error"]["current_version"] == 1

    bob = authenticated(app, "bob")
    assert bob.get(f"/api/v1/chapters?subject_id={subject_id}").status_code == 404
    assert bob.get(f"/api/v1/knowledge-points?chapter_id={chapter['id']}").status_code == 404
    assert bob.get(f"/api/v1/knowledge-points?chapter_id={chapter['id']}").status_code == 404
    assert bob.get(f"/api/v1/chapters/{chapter['id']}").status_code == 404
    assert bob.get(f"/api/v1/knowledge-points/{point['id']}").status_code == 404

    other_chapter_key = str(uuid4())
    other_chapter = client.post(
        "/api/v1/chapters",
        json={
            "operation_id": other_chapter_key,
            "subject_id": other_subject_id,
            "name": "QA_TEST_外语章节",
        },
        headers={"Idempotency-Key": other_chapter_key},
    ).json()["data"]
    other_point_key = str(uuid4())
    other_point = client.post(
        "/api/v1/knowledge-points",
        json={
            "operation_id": other_point_key,
            "chapter_id": other_chapter["id"],
            "name": "QA_TEST_词汇",
        },
        headers={"Idempotency-Key": other_point_key},
    ).json()["data"]

    started, _ = start(client, subject_id=None, knowledge_point_id=point["id"])
    assert started.status_code == 201, started.text
    session = started.json()["data"]
    assert session["subject_id"] == subject_id and session["knowledge_point_id"] == point["id"]
    end_key = str(uuid4())
    assert (
        client.post(
            f"/api/v1/learning-sessions/{session['id']}/end",
            json={"operation_id": end_key},
            headers={"Idempotency-Key": end_key, "If-Match": '"1"'},
        ).status_code
        == 200
    )
    mismatched_session, _ = start(
        client, subject_id=other_subject_id, knowledge_point_id=point["id"]
    )
    assert mismatched_session.status_code == 422

    problem_key = str(uuid4())
    problem = client.post(
        "/api/v1/problems",
        json={
            "operation_id": problem_key,
            "subject_id": subject_id,
            "statement": "QA_TEST_题目材料",
        },
        headers={"Idempotency-Key": problem_key},
    )
    assert problem.status_code == 201
    problem_id = problem.json()["data"]["id"]
    link_key = str(uuid4())
    linked = client.put(
        f"/api/v1/problems/{problem_id}/knowledge-links",
        json={
            "operation_id": link_key,
            "knowledge_point_ids": [point["id"]],
        },
        headers={"Idempotency-Key": link_key, "If-Match": '"1"'},
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["data"]["problem"]["version"] == 2
    assert linked.json()["data"]["knowledge_point_ids"] == [point["id"]]
    assert client.get(f"/api/v1/problems/{problem_id}").json()["data"]["knowledge_point_ids"] == [
        point["id"]
    ]
    attempt_key = str(uuid4())
    attempt = client.post(
        "/api/v1/problem-attempts",
        json={
            "operation_id": attempt_key,
            "session_id": session["id"],
            "problem_id": problem_id,
            "independence": "independent",
            "answer_check": "checked",
            "result": "correct",
        },
        headers={"Idempotency-Key": attempt_key},
    )
    assert attempt.status_code == 201, attempt.text
    attempt_id = attempt.json()["data"]["id"]
    assessment_key = str(uuid4())
    assessment = client.post(
        "/api/v1/mastery-assessments",
        json={
            "operation_id": assessment_key,
            "knowledge_point_id": point["id"],
            "level": "independent",
            "reason": "QA_TEST_对照自评",
            "evidence_attempt_ids": [attempt_id],
        },
        headers={"Idempotency-Key": assessment_key, "If-Match": '"1"'},
    )
    assert assessment.status_code == 201, assessment.text

    same_key = str(uuid4())

    def submit_same_key(candidate_client):
        return candidate_client.put(
            f"/api/v1/problems/{problem_id}/knowledge-links",
            json={"operation_id": same_key, "knowledge_point_ids": [point["id"]]},
            headers={"Idempotency-Key": same_key, "If-Match": '"2"'},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        same_key_results = list(pool.map(submit_same_key, (client, authenticated(app))))
    assert [response.status_code for response in same_key_results] == [200, 200]
    assert same_key_results[0].json()["data"] == same_key_results[1].json()["data"]
    assert same_key_results[0].json()["data"]["problem"]["version"] == 3

    def submit_distinct(args):
        candidate_client, point_id = args
        key = str(uuid4())
        return candidate_client.put(
            f"/api/v1/problems/{problem_id}/knowledge-links",
            json={"operation_id": key, "knowledge_point_ids": [point_id]},
            headers={"Idempotency-Key": key, "If-Match": '"3"'},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        distinct_results = list(
            pool.map(
                submit_distinct,
                zip(
                    (authenticated(app), authenticated(app)),
                    (point["id"], second_point["id"]),
                    strict=True,
                ),
            )
        )
    assert sorted(response.status_code for response in distinct_results) == [200, 409]
    conflict = next(response for response in distinct_results if response.status_code == 409)
    assert conflict.json()["error"]["current_version"] == 4
    current_problem = client.get(f"/api/v1/problems/{problem_id}").json()["data"]
    assert current_problem["version"] == 4
    assert conflict.json()["error"]["current"] == current_problem

    cross_subject_key = str(uuid4())
    cross_subject_link = client.put(
        f"/api/v1/problems/{problem_id}/knowledge-links",
        json={
            "operation_id": cross_subject_key,
            "knowledge_point_ids": [other_point["id"]],
        },
        headers={"Idempotency-Key": cross_subject_key, "If-Match": '"4"'},
    )
    assert cross_subject_link.status_code == 422
    assert client.get(f"/api/v1/problems/{problem_id}").json()["data"]["version"] == 4

    duplicate_key = str(uuid4())
    duplicate = client.put(
        f"/api/v1/problems/{problem_id}/knowledge-links",
        json={
            "operation_id": duplicate_key,
            "knowledge_point_ids": [point["id"], point["id"]],
        },
        headers={"Idempotency-Key": duplicate_key, "If-Match": '"4"'},
    )
    assert duplicate.status_code == 422

    chapter_archive_key = str(uuid4())
    archived = client.patch(
        f"/api/v1/chapters/{chapter['id']}",
        json={
            "operation_id": chapter_archive_key,
            "archived": True,
        },
        headers={"Idempotency-Key": chapter_archive_key, "If-Match": '"1"'},
    )
    assert archived.status_code == 200 and archived.json()["data"]["version"] == 2
    assert client.get(f"/api/v1/chapters?subject_id={subject_id}").json()["data"]["items"] == []
    assert (
        client.get(f"/api/v1/chapters?subject_id={subject_id}&archived=true").json()["data"][
            "items"
        ][0]["id"]
        == chapter["id"]
    )
    archived_link_key = str(uuid4())
    archived_link = client.put(
        f"/api/v1/problems/{problem_id}/knowledge-links",
        json={"operation_id": archived_link_key, "knowledge_point_ids": [second_point["id"]]},
        headers={"Idempotency-Key": archived_link_key, "If-Match": '"4"'},
    )
    assert archived_link.status_code == 404
    archived_problem = client.get(f"/api/v1/problems/{problem_id}").json()["data"]
    assert archived_problem["version"] == 4
    preserved_links = archived_problem["knowledge_point_ids"]
    assert len(preserved_links) == 1
    replacement_id = second_point["id"] if preserved_links == [point["id"]] else point["id"]
    point_session, _ = start(client, subject_id=subject_id, knowledge_point_id=point["id"])
    assert point_session.status_code == 404
    restore_key = str(uuid4())
    restored = client.patch(
        f"/api/v1/chapters/{chapter['id']}",
        json={
            "operation_id": restore_key,
            "archived": False,
        },
        headers={"Idempotency-Key": restore_key, "If-Match": '"2"'},
    )
    assert restored.status_code == 200
    assert (
        client.get(f"/api/v1/chapters?subject_id={subject_id}").json()["data"]["items"][0]["id"]
        == chapter["id"]
    )
    relink_key = str(uuid4())
    relinked = client.put(
        f"/api/v1/problems/{problem_id}/knowledge-links",
        json={"operation_id": relink_key, "knowledge_point_ids": [replacement_id]},
        headers={"Idempotency-Key": relink_key, "If-Match": '"4"'},
    )
    assert relinked.status_code == 200
    assert relinked.json()["data"]["problem"]["version"] == 5
    empty_links_key = str(uuid4())
    empty_links = client.put(
        f"/api/v1/problems/{problem_id}/knowledge-links",
        json={"operation_id": empty_links_key, "knowledge_point_ids": []},
        headers={"Idempotency-Key": empty_links_key, "If-Match": '"5"'},
    )
    assert empty_links.status_code == 200
    assert empty_links.json()["data"]["problem"]["version"] == 6
    assert empty_links.json()["data"]["knowledge_point_ids"] == []
    stale_evidence = client.get(f"/api/v1/knowledge-points/{point['id']}/evidence").json()["data"]
    assert stale_evidence["assessments"][0]["evidence_status"] == "stale"
    stale_link_key = str(uuid4())
    stale_link = client.put(
        f"/api/v1/problems/{problem_id}/knowledge-links",
        json={"operation_id": stale_link_key, "knowledge_point_ids": []},
        headers={"Idempotency-Key": stale_link_key, "If-Match": '"5"'},
    )
    assert stale_link.status_code == 409
    assert stale_link.json()["error"]["current_version"] == 6
    assert stale_link.json()["error"]["current"]["knowledge_point_ids"] == []

    archive_point_key = str(uuid4())
    archived_point = client.patch(
        f"/api/v1/knowledge-points/{point['id']}",
        json={
            "operation_id": archive_point_key,
            "archived": True,
        },
        headers={"Idempotency-Key": archive_point_key, "If-Match": '"2"'},
    )
    assert archived_point.status_code == 200
    assert all(
        item["id"] != point["id"]
        for item in client.get(f"/api/v1/knowledge-points?chapter_id={chapter['id']}").json()[
            "data"
        ]["items"]
    )
    assert any(
        item["id"] == point["id"]
        for item in client.get(
            f"/api/v1/knowledge-points?chapter_id={chapter['id']}&archived=true"
        ).json()["data"]["items"]
    )
    restore_point_key = str(uuid4())
    restored_point = client.patch(
        f"/api/v1/knowledge-points/{point['id']}",
        json={
            "operation_id": restore_point_key,
            "archived": False,
            "notes": None,
        },
        headers={"Idempotency-Key": restore_point_key, "If-Match": '"3"'},
    )
    assert restored_point.status_code == 200 and restored_point.json()["data"]["notes"] is None

    app2 = create_app(Settings(database_url=url, environment="test"))
    restored_client = authenticated(app2)
    assert (
        restored_client.get(f"/api/v1/knowledge-points/{point['id']}").json()["data"]["name"]
        == "QA_TEST_频域性质"
    )
    assert (
        restored_client.get(f"/api/v1/problems/{problem_id}").json()["data"]["knowledge_point_ids"]
        == []
    )
    assert (
        restored_client.get(f"/api/v1/knowledge-points/{point['id']}/evidence").json()["data"][
            "assessments"
        ][0]["evidence_status"]
        == "stale"
    )


def test_subject_space_signals_chapter_continuation_cursor(knowledge_system):
    app, _url, subject_id, _other_subject_id, _bob_subject_id = knowledge_system
    now = datetime(2026, 9, 30, tzinfo=UTC)
    with Session(app.state.engine) as db:
        db.add_all(
            [
                ChapterRow(
                    id=str(uuid4()),
                    owner_id="alice",
                    subject_id=subject_id,
                    name=f"QA_TEST_章节_{index}",
                    order_index=index,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                for index in range(101)
            ]
        )
        db.commit()
    client = authenticated(app)
    space = client.get(f"/api/v1/subjects/{subject_id}/space").json()["data"]
    assert len(space["chapters"]) == 100
    assert space["chapters_next_cursor"] == space["chapters"][-1]["id"]
    remaining = client.get(
        f"/api/v1/chapters?subject_id={subject_id}&limit=100&cursor={space['chapters_next_cursor']}"
    ).json()["data"]
    assert len(remaining["items"]) == 1
    assert remaining["next_cursor"] is None


def test_0005_preserves_populated_0004_records(tmp_path, monkeypatch):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from hermes_api.storage import make_engine

    url = f"sqlite:///{tmp_path / 'legacy_0004.db'}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "0004")
    engine = make_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, username, password_hash, timezone) VALUES ('legacy', 'QA_TEST_legacy', 'unused', 'Asia/Shanghai')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO subjects (id, owner_id, name) VALUES ('legacy-subject', 'legacy', 'QA_TEST_信号')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO learning_sessions (id, owner_id, subject_id, status, version, started_at, day_timezone, learning_date, timing_enabled, kind) VALUES ('legacy-session', 'legacy', 'legacy-subject', 'ended', 5, '2026-09-30 00:00:00', 'Asia/Shanghai', '2026-09-30', 1, 'problem')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO session_time_segments (id, owner_id, session_id, started_at, ended_at) VALUES ('legacy-segment', 'legacy', 'legacy-session', '2026-09-30 00:00:00', '2026-09-30 00:10:00')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO problems (id, owner_id, subject_id, statement, version, created_at, updated_at) VALUES ('legacy-problem', 'legacy', 'legacy-subject', 'QA_TEST_题目', 4, '2026-09-30 00:00:00', '2026-09-30 00:00:00')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO problem_attempts (id, owner_id, session_id, problem_id, independence, answer_check, result, occurred_at, verified_at, version, created_at, updated_at) VALUES ('legacy-attempt', 'legacy', 'legacy-session', 'legacy-problem', 'independent', 'checked', 'correct', '2026-09-30 00:00:00', '2026-09-30 00:00:00', 3, '2026-09-30 00:00:00', '2026-09-30 00:00:00')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO quote_preferences (owner_id, quote_id, text_snapshot, favorited, disliked, version, updated_at) VALUES ('legacy', 'q01', 'QA_TEST_quote', 1, 0, 2, '2026-09-30 00:00:00')"
            )
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        session = connection.execute(
            text(
                "SELECT id, owner_id, goal, subject_id, status, version, started_at, ended_at, "
                "day_timezone, learning_date, timing_enabled, method_id, kind, previous_session_id, "
                "resume_note, knowledge_point_id FROM learning_sessions WHERE id='legacy-session'"
            )
        ).one()
        assert tuple(session) == (
            "legacy-session",
            "legacy",
            None,
            "legacy-subject",
            "ended",
            5,
            "2026-09-30 00:00:00",
            None,
            "Asia/Shanghai",
            "2026-09-30",
            1,
            None,
            "problem",
            None,
            None,
            None,
        )
        assert connection.execute(
            text(
                "SELECT id, owner_id, session_id, started_at, ended_at "
                "FROM session_time_segments WHERE id='legacy-segment'"
            )
        ).one() == (
            "legacy-segment",
            "legacy",
            "legacy-session",
            "2026-09-30 00:00:00",
            "2026-09-30 00:10:00",
        )
        assert connection.execute(
            text(
                "SELECT id, owner_id, subject_id, title, statement, source_note, correct_answer, "
                "is_representative, archived_at, version, created_at, updated_at "
                "FROM problems WHERE id='legacy-problem'"
            )
        ).one() == (
            "legacy-problem",
            "legacy",
            "legacy-subject",
            None,
            "QA_TEST_题目",
            None,
            None,
            0,
            None,
            4,
            "2026-09-30 00:00:00",
            "2026-09-30 00:00:00",
        )
        assert connection.execute(
            text(
                "SELECT id, owner_id, session_id, problem_id, independence, answer_check, result, "
                "occurred_at, verified_at, version, created_at, updated_at "
                "FROM problem_attempts WHERE id='legacy-attempt'"
            )
        ).one() == (
            "legacy-attempt",
            "legacy",
            "legacy-session",
            "legacy-problem",
            "independent",
            "checked",
            "correct",
            "2026-09-30 00:00:00",
            "2026-09-30 00:00:00",
            3,
            "2026-09-30 00:00:00",
            "2026-09-30 00:00:00",
        )
        assert connection.execute(
            text(
                "SELECT owner_id, quote_id, text_snapshot, favorited, disliked, version, updated_at "
                "FROM quote_preferences WHERE owner_id='legacy'"
            )
        ).one() == ("legacy", "q01", "QA_TEST_quote", 1, 0, 2, "2026-09-30 00:00:00")
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_session_knowledge_scope_integrity_constraints(knowledge_system):
    app, _, subject_id, other_subject_id, _ = knowledge_system
    client = authenticated(app)
    chapter_key = str(uuid4())
    chapter = client.post(
        "/api/v1/chapters",
        json={
            "operation_id": chapter_key,
            "subject_id": subject_id,
            "name": "QA_TEST_完整性章节",
        },
        headers={"Idempotency-Key": chapter_key},
    ).json()["data"]
    point_key = str(uuid4())
    point = client.post(
        "/api/v1/knowledge-points",
        json={
            "operation_id": point_key,
            "chapter_id": chapter["id"],
            "name": "QA_TEST_完整性知识点",
        },
        headers={"Idempotency-Key": point_key},
    ).json()["data"]
    insert_sql = text(
        "INSERT INTO learning_sessions "
        "(id, owner_id, subject_id, knowledge_point_id, status, version, started_at, "
        "day_timezone, learning_date, timing_enabled, kind) "
        "VALUES (:id, 'alice', :subject_id, :point_id, 'ended', 1, "
        "'2026-09-30 00:00:00', 'Asia/Shanghai', '2026-09-30', 0, 'free')"
    )

    with Session(app.state.engine) as db:
        db.execute(insert_sql, {"id": "QA_TEST_null_point", "subject_id": None, "point_id": None})
        db.commit()
    with pytest.raises(IntegrityError), Session(app.state.engine) as db:
        db.execute(
            insert_sql,
            {"id": "QA_TEST_point_no_subject", "subject_id": None, "point_id": point["id"]},
        )
        db.commit()
    with pytest.raises(IntegrityError), Session(app.state.engine) as db:
        db.execute(
            insert_sql,
            {
                "id": "QA_TEST_point_wrong_subject",
                "subject_id": other_subject_id,
                "point_id": point["id"],
            },
        )
        db.commit()
