from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_foundation import authenticated

from hermes_api.cli import migrate
from hermes_api.evidence_storage import MasteryAssessmentRow, MasteryEvidenceLinkRow
from hermes_api.knowledge_storage import ChapterRow, KnowledgePointRow, ProblemKnowledgeLinkRow
from hermes_api.main import create_app
from hermes_api.settings import Settings
from hermes_api.storage import (
    AttemptErrorRow,
    Operation,
    ProblemAttemptRow,
    ProblemRow,
    SessionRow,
    Subject,
    User,
)


@pytest.fixture
def evidence_system(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'evidence.db'}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    migrate()
    app = create_app(Settings(database_url=url, environment="test"))
    point_ids: dict[str, str] = {}
    attempt_ids: dict[str, dict[str, str]] = {}
    with Session(app.state.engine) as db:
        for owner in ("alice", "bob"):
            db.add(
                User(
                    id=owner,
                    username=owner,
                    password_hash=PasswordHasher().hash("QA_TEST_password"),
                    timezone="Asia/Shanghai",
                )
            )
        db.flush()
        for owner in ("alice", "bob"):
            subject_id = str(uuid4())
            chapter_id = str(uuid4())
            point_id = str(uuid4())
            second_point_id = str(uuid4()) if owner == "alice" else None
            empty_point_id = str(uuid4()) if owner == "alice" else None
            problem_id = str(uuid4())
            session_id = str(uuid4())
            db.add(Subject(id=subject_id, owner_id=owner, name=f"QA_TEST_{owner}_subject"))
            db.flush()
            now = datetime(2026, 9, 30, 4, tzinfo=UTC)
            db.add(
                ChapterRow(
                    id=chapter_id,
                    owner_id=owner,
                    subject_id=subject_id,
                    name="QA_TEST_章节",
                    order_index=0,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                KnowledgePointRow(
                    id=point_id,
                    owner_id=owner,
                    chapter_id=chapter_id,
                    subject_id=subject_id,
                    name="QA_TEST_知识点",
                    notes=None,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
            )
            if second_point_id:
                db.add(
                    KnowledgePointRow(
                        id=second_point_id,
                        owner_id=owner,
                        chapter_id=chapter_id,
                        subject_id=subject_id,
                        name="QA_TEST_同题第二知识点",
                        notes=None,
                        version=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
            if empty_point_id:
                db.add(
                    KnowledgePointRow(
                        id=empty_point_id,
                        owner_id=owner,
                        chapter_id=chapter_id,
                        subject_id=subject_id,
                        name="QA_TEST_无作答知识点",
                        notes=None,
                        version=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
            db.add(
                ProblemRow(
                    id=problem_id,
                    owner_id=owner,
                    subject_id=subject_id,
                    title="QA_TEST_题目",
                    statement="QA_TEST_题干",
                    source_note=None,
                    correct_answer=None,
                    is_representative=False,
                    archived_at=None,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                SessionRow(
                    id=session_id,
                    owner_id=owner,
                    goal="QA_TEST_学习",
                    subject_id=subject_id,
                    status="ended",
                    version=2,
                    started_at=now - timedelta(minutes=5),
                    ended_at=now,
                    day_timezone="Asia/Shanghai",
                    learning_date="2026-09-30",
                    timing_enabled=False,
                    method_id=None,
                    kind="problem",
                    previous_session_id=None,
                    resume_note=None,
                    knowledge_point_id=point_id,
                )
            )
            db.flush()
            db.add(
                ProblemKnowledgeLinkRow(
                    owner_id=owner,
                    problem_id=problem_id,
                    knowledge_point_id=point_id,
                    created_at=now,
                )
            )
            if second_point_id:
                db.add(
                    ProblemKnowledgeLinkRow(
                        owner_id=owner,
                        problem_id=problem_id,
                        knowledge_point_id=second_point_id,
                        created_at=now,
                    )
                )
            attempts = {}
            for suffix, check, independence, result, categories in (
                ("1", "checked", "independent", "correct", ["sign", "reading"]),
                ("2", "checked", "hinted", "partial", ["sign"]),
                ("3", "pending", "independent", None, []),
            ):
                attempt_id = str(uuid4())
                occurred = now - timedelta(seconds=int(suffix))
                db.add(
                    ProblemAttemptRow(
                        id=attempt_id,
                        owner_id=owner,
                        session_id=session_id,
                        problem_id=problem_id,
                        independence=independence,
                        answer_check=check,
                        result=result,
                        attempt_text=f"QA_TEST_attempt_{suffix}",
                        stuck_note=None,
                        occurred_at=occurred,
                        verified_at=now if check == "checked" else None,
                        version=1,
                        created_at=occurred,
                        updated_at=occurred,
                    )
                )
                db.flush()
                for category in categories:
                    db.add(
                        AttemptErrorRow(
                            id=str(uuid4()),
                            owner_id=owner,
                            attempt_id=attempt_id,
                            category=category,
                            note=None,
                        )
                    )
                attempts[suffix] = attempt_id
            point_ids[owner] = point_id
            if second_point_id:
                point_ids["alice_second"] = second_point_id
            if empty_point_id:
                point_ids["alice_empty"] = empty_point_id
            attempt_ids[owner] = attempts
        db.commit()
    return app, url, point_ids, attempt_ids


def _post_assessment(client, point_id, key, version, **overrides):
    body = {
        "operation_id": key,
        "knowledge_point_id": point_id,
        "level": "unfamiliar",
        "reason": "QA_TEST_自评理由",
        "variant_note": None,
        "evidence_attempt_ids": [],
        **overrides,
    }
    return client.post(
        "/api/v1/mastery-assessments",
        json=body,
        headers={"Idempotency-Key": key, "If-Match": f'"{version}"'},
    ), body


def test_empty_evidence_and_all_five_levels_are_user_declarations(evidence_system):
    app, _url, points, _attempts = evidence_system
    client = authenticated(app)
    point_id = points["alice"]
    empty = client.get(f"/api/v1/knowledge-points/{point_id}/evidence")
    assert empty.status_code == 200
    assert empty.json()["data"]["counts"] == {
        "attempt_count": 3,
        "pending_count": 1,
        "checked_count": 2,
        "checked_correct_count": 1,
        "checked_correct_rate": 0.5,
        "independent_correct_count": 1,
    }
    assert empty.json()["data"]["recent_checked_streak"]["count"] == 1
    assert empty.json()["data"]["recent_checked_streak"]["pending_count"] == 1
    sign = next(
        item for item in empty.json()["data"]["error_categories"] if item["category"] == "sign"
    )
    assert sign["attempt_count"] == 2
    assert len(sign["source_refs"]) == 2

    levels = ["unfamiliar", "encountered", "typical", "independent", "variant_stable"]
    version = 1
    for level in levels:
        key = str(uuid4())
        response, _body = _post_assessment(client, point_id, key, version, level=level)
        assert response.status_code == 201, response.text
        data = response.json()["data"]
        assert data["knowledge_point_version"] == version + 1
        assert data["assessment"]["version"] == 1
        assert data["assessment"]["level"] == level
        assert data["assessment"]["evidence_status"] == "unsupported"
        assert data["assessment"]["evidence_message"] == "自评，暂无已核证据"
        version += 1
    history = client.get(f"/api/v1/knowledge-points/{point_id}/evidence").json()["data"][
        "assessments"
    ]
    assert [item["level"] for item in history] == list(reversed(levels))
    assert all(item["version"] == 1 for item in history)


def test_assessment_requires_if_match_and_replays_exactly_without_second_version(evidence_system):
    app, _url, points, _attempts = evidence_system
    client = authenticated(app)
    point_id = points["alice"]
    key = str(uuid4())
    body = {
        "operation_id": key,
        "knowledge_point_id": point_id,
        "level": "encountered",
        "evidence_attempt_ids": [],
    }
    assert (
        client.post(
            "/api/v1/mastery-assessments", json=body, headers={"Idempotency-Key": key}
        ).status_code
        == 428
    )
    first, _ = _post_assessment(client, point_id, key, 1, level="encountered")
    replay, _ = _post_assessment(client, point_id, key, 1, level="encountered")
    assert first.status_code == 201 and replay.status_code == 201
    assert replay.json()["data"] == first.json()["data"]
    conflict, _ = _post_assessment(client, point_id, key, 1, level="typical")
    assert conflict.status_code == 409
    stale_key = str(uuid4())
    stale, _ = _post_assessment(client, point_id, stale_key, 1)
    assert stale.status_code == 409
    assert stale.json()["error"]["current_version"] == 2
    current_point = client.get(f"/api/v1/knowledge-points/{point_id}").json()["data"]
    assert stale.json()["error"]["current"] == current_point
    with Session(app.state.engine) as db:
        assert len(db.scalars(select(MasteryAssessmentRow)).all()) == 1
        assert db.get(KnowledgePointRow, point_id).version == 2
        assert len(db.scalars(select(Operation)).all()) == 1


@pytest.mark.parametrize("version_header", ["0", "-1", '"0"', '"-1"'])
def test_nonpositive_if_match_is_rejected_without_side_effects(evidence_system, version_header):
    app, _url, points, _attempts = evidence_system
    client = authenticated(app)
    key = str(uuid4())
    body = {
        "operation_id": key,
        "knowledge_point_id": points["alice"],
        "level": "encountered",
        "evidence_attempt_ids": [],
    }
    response = client.post(
        "/api/v1/mastery-assessments",
        json=body,
        headers={"Idempotency-Key": key, "If-Match": version_header},
    )
    assert response.status_code == 422
    with Session(app.state.engine) as db:
        assert db.get(KnowledgePointRow, points["alice"]).version == 1
        assert db.scalars(select(MasteryAssessmentRow)).all() == []


def test_one_attempt_linked_to_two_points_is_counted_once_per_point_scope(evidence_system):
    _app, _url, points, _attempts = evidence_system
    client = authenticated(_app)
    first = client.get(f"/api/v1/knowledge-points/{points['alice']}/evidence").json()["data"]
    second = client.get(f"/api/v1/knowledge-points/{points['alice_second']}/evidence").json()[
        "data"
    ]
    assert first["counts"]["attempt_count"] == 3
    assert second["counts"]["attempt_count"] == 3
    assert len(first["source_refs"]) == len(second["source_refs"]) == 3


def test_empty_knowledge_point_has_zero_counts_null_ratio_and_no_claim(evidence_system):
    app, _url, points, _attempts = evidence_system
    client = authenticated(app)
    data = client.get(f"/api/v1/knowledge-points/{points['alice_empty']}/evidence").json()["data"]
    assert data["counts"] == {
        "attempt_count": 0,
        "pending_count": 0,
        "checked_count": 0,
        "checked_correct_count": 0,
        "checked_correct_rate": None,
        "independent_correct_count": 0,
    }
    assert data["source_refs"] == []
    assert data["assessments"] == []
    assert data["recent_checked_streak"]["count"] == 0


def test_linked_evidence_needs_current_link_checked_qualification_and_variant_note(evidence_system):
    _app, _url, points, attempts = evidence_system
    client = authenticated(_app)
    point_id = points["alice"]

    pending, _ = _post_assessment(
        client, point_id, str(uuid4()), 1, evidence_attempt_ids=[attempts["alice"]["3"]]
    )
    assert pending.status_code == 422
    cross_owner, _ = _post_assessment(
        client,
        point_id,
        str(uuid4()),
        1,
        evidence_attempt_ids=[attempts["bob"]["1"]],
    )
    assert cross_owner.status_code == 404
    unlinked, _ = _post_assessment(
        client,
        point_id,
        str(uuid4()),
        1,
        evidence_attempt_ids=[str(uuid4())],
    )
    assert unlinked.status_code == 404

    not_correct, _ = _post_assessment(
        client,
        point_id,
        str(uuid4()),
        1,
        level="independent",
        evidence_attempt_ids=[attempts["alice"]["2"]],
    )
    assert not_correct.status_code == 422
    variant_missing_note, _ = _post_assessment(
        client,
        point_id,
        str(uuid4()),
        1,
        level="variant_stable",
        evidence_attempt_ids=[attempts["alice"]["1"]],
    )
    assert variant_missing_note.status_code == 422

    valid, _ = _post_assessment(
        client,
        point_id,
        str(uuid4()),
        1,
        level="variant_stable",
        variant_note="QA_TEST_换了数字后仍独立完成",
        evidence_attempt_ids=[attempts["alice"]["1"]],
    )
    assert valid.status_code == 201, valid.text
    assessment = valid.json()["data"]["assessment"]
    assert assessment["evidence_status"] == "current"
    with Session(_app.state.engine) as db:
        source = db.get(ProblemAttemptRow, attempts["alice"]["1"])
    assert assessment["source_refs"] == [
        {
            "attempt_id": attempts["alice"]["1"],
            "attempt_version": 1,
            "problem_id": source.problem_id,
            "problem_version": 1,
        }
    ]


def test_sources_become_stale_without_rewriting_self_assessment_and_restart_persists(
    evidence_system,
):
    app, url, points, attempts = evidence_system
    client = authenticated(app)
    point_id = points["alice"]
    response, _ = _post_assessment(
        client,
        point_id,
        str(uuid4()),
        1,
        level="independent",
        evidence_attempt_ids=[attempts["alice"]["1"]],
    )
    assert response.status_code == 201
    with Session(app.state.engine) as db:
        attempt = db.get(ProblemAttemptRow, attempts["alice"]["1"])
        attempt.version += 1
        db.commit()
    evidence = client.get(f"/api/v1/knowledge-points/{point_id}/evidence").json()["data"]
    assert evidence["assessments"][0]["evidence_status"] == "stale"
    assert evidence["assessments"][0]["level"] == "independent"
    assert evidence["assessments"][0]["evidence_message"] == "关联来源已变化，原自评仍保留"
    app2 = create_app(Settings(database_url=url, environment="test"))
    restored = authenticated(app2)
    saved = restored.get(f"/api/v1/knowledge-points/{point_id}/evidence").json()["data"]
    assert saved["assessments"][0]["evidence_status"] == "stale"
    assert saved["assessments"][0]["level"] == "independent"
    with Session(app2.state.engine) as db:
        assert len(db.scalars(select(MasteryEvidenceLinkRow)).all()) == 1


def test_problem_edit_and_unlink_stale_assessment_sources(evidence_system):
    app, _url, points, attempts = evidence_system
    client = authenticated(app)
    point_id = points["alice"]
    attempt_id = attempts["alice"]["1"]
    with Session(app.state.engine) as db:
        problem_id = db.get(ProblemAttemptRow, attempt_id).problem_id

    created, _ = _post_assessment(
        client, point_id, str(uuid4()), 1, level="independent", evidence_attempt_ids=[attempt_id]
    )
    assert created.status_code == 201
    with Session(app.state.engine) as db:
        problem = db.get(ProblemRow, problem_id)
        problem.version += 1
        db.commit()
    detail = client.get(f"/api/v1/knowledge-points/{point_id}/evidence").json()["data"]
    assert detail["assessments"][0]["evidence_status"] == "stale"

    # A fresh assessment captures the new problem version; removing the current association
    # must stale it even if the source rows themselves have not changed.
    assessment, _ = _post_assessment(
        client, point_id, str(uuid4()), 2, level="independent", evidence_attempt_ids=[attempt_id]
    )
    assert assessment.status_code == 201
    with Session(app.state.engine) as db:
        link = db.get(ProblemKnowledgeLinkRow, ("alice", problem_id, point_id))
        db.delete(link)
        db.commit()
    detail = client.get(f"/api/v1/knowledge-points/{point_id}/evidence").json()["data"]
    assert detail["assessments"][0]["evidence_status"] == "stale"


def test_owner_isolation_and_concurrent_same_operation_creates_once(evidence_system):
    app, _url, points, _attempts = evidence_system
    alice, bob = authenticated(app), authenticated(app, "bob")
    point_id = points["alice"]
    assert bob.get(f"/api/v1/knowledge-points/{point_id}/evidence").status_code == 404
    key = str(uuid4())

    def submit(client):
        return _post_assessment(client, point_id, key, 1)[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(submit, (alice, authenticated(app))))
    assert first.status_code == second.status_code == 201
    assert first.json()["data"] == second.json()["data"]
    with Session(app.state.engine) as db:
        assert len(db.scalars(select(MasteryAssessmentRow)).all()) == 1
        assert len(db.scalars(select(MasteryEvidenceLinkRow)).all()) == 0


def test_concurrent_distinct_assessments_share_if_match_version_gate(evidence_system):
    app, _url, points, _attempts = evidence_system
    point_id = points["alice"]
    clients = [authenticated(app), authenticated(app)]

    def submit(args):
        client, level = args
        return _post_assessment(client, point_id, str(uuid4()), 1, level=level)[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        one, two = list(pool.map(submit, zip(clients, ("encountered", "typical"), strict=True)))
    assert sorted([one.status_code, two.status_code]) == [201, 409]
    conflict = one if one.status_code == 409 else two
    assert conflict.json()["error"]["current_version"] == 2
    with Session(app.state.engine) as db:
        assert len(db.scalars(select(MasteryAssessmentRow)).all()) == 1
