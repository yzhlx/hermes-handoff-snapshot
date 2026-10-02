"""Authenticated API checks for the optional AI advisor (FR-043—046)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

pytest_plugins = ("test_foundation",)

from test_foundation import authenticated

from hermes_api.advisor_mock import DeterministicAdvisorModel
from hermes_api.knowledge_storage import ChapterRow, KnowledgePointRow, ProblemKnowledgeLinkRow
from hermes_api.storage import (
    AttemptErrorRow,
    ProblemAttemptRow,
    ProblemRow,
    SessionRow,
    Subject,
)


def _seed(app):
    """Alice owns a subject, one knowledge point, three records of the same
    repeated error and three consecutive independent-correct records."""

    now = datetime.now(UTC)
    session_id = str(uuid4())
    subject_id = str(uuid4())
    chapter_id = str(uuid4())
    point_id = str(uuid4())
    problem_ids = [str(uuid4()) for _ in range(3)]
    attempt_ids = [str(uuid4()) for _ in range(7)]
    with Session(app.state.engine) as db:
        db.add(Subject(id=subject_id, owner_id="alice", name="QA_TEST 信号与系统"))
        db.flush()
        db.add(
            ChapterRow(
                id=chapter_id,
                owner_id="alice",
                subject_id=subject_id,
                name="QA_TEST 采样",
                order_index=0,
                version=1,
                created_at=now,
                updated_at=now,
                archived_at=None,
            )
        )
        db.flush()
        db.add(
            KnowledgePointRow(
                id=point_id,
                owner_id="alice",
                chapter_id=chapter_id,
                subject_id=subject_id,
                name="QA_TEST 频谱搬移",
                notes=None,
                version=1,
                created_at=now,
                updated_at=now,
                archived_at=None,
            )
        )
        db.flush()
        for problem_id in problem_ids:
            db.add(
                ProblemRow(
                    id=problem_id,
                    owner_id="alice",
                    subject_id=subject_id,
                    title="QA_TEST 采样题",
                    statement="题干",
                    source_note=None,
                    correct_answer="答案",
                    is_representative=False,
                    archived_at=None,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
            )
        db.flush()
        for problem_id in problem_ids:
            db.add(
                ProblemKnowledgeLinkRow(
                    owner_id="alice",
                    problem_id=problem_id,
                    knowledge_point_id=point_id,
                    created_at=now,
                )
            )
        db.add(
            SessionRow(
                id=session_id,
                owner_id="alice",
                goal="QA_TEST",
                subject_id=subject_id,
                knowledge_point_id=None,
                status="ended",
                version=1,
                started_at=now,
                ended_at=now,
                day_timezone="Asia/Shanghai",
                learning_date=now.date().isoformat(),
                timing_enabled=False,
                method_id=None,
                kind="problem",
                previous_session_id=None,
                resume_note=None,
            )
        )
        db.flush()
        # Oldest -> newest. Three repeats of one error, then three consecutive
        # independent-correct records, then one unverified record.
        plan = [
            (attempt_ids[0], problem_ids[0], "hinted", "checked", "partial", ["sign"], 0),
            (attempt_ids[1], problem_ids[1], "hinted", "checked", "incorrect", ["sign"], 1),
            (attempt_ids[2], problem_ids[2], "hinted", "checked", "incorrect", ["sign"], 2),
            (attempt_ids[3], problem_ids[0], "independent", "checked", "correct", [], 3),
            (attempt_ids[4], problem_ids[1], "independent", "checked", "correct", [], 4),
            (attempt_ids[5], problem_ids[2], "independent", "checked", "correct", [], 5),
            (attempt_ids[6], problem_ids[0], "hinted", "pending", None, [], 6),
        ]
        for attempt_id, problem_id, independence, check, result, _categories, offset in plan:
            occurred = now + timedelta(minutes=offset)
            db.add(
                ProblemAttemptRow(
                    id=attempt_id,
                    owner_id="alice",
                    session_id=session_id,
                    problem_id=problem_id,
                    independence=independence,
                    answer_check=check,
                    result=result,
                    attempt_text="过程",
                    stuck_note="QA_TEST 为什么这里要换方向？"
                    if attempt_id == attempt_ids[0]
                    else None,
                    occurred_at=occurred,
                    verified_at=occurred if check == "checked" else None,
                    version=1,
                    created_at=occurred,
                    updated_at=occurred,
                )
            )
        db.flush()
        for attempt_id, _pid, _ind, _check, _res, categories, _offset in plan:
            for category in categories:
                db.add(
                    AttemptErrorRow(
                        id=str(uuid4()),
                        owner_id="alice",
                        attempt_id=attempt_id,
                        category=category,
                        note=None,
                    )
                )
        db.commit()
    return session_id, subject_id, point_id, problem_ids, attempt_ids


def _analyze(client, **overrides):
    operation_id = str(uuid4())
    body = {"operation_id": operation_id, **overrides}
    return client.post(
        "/api/v1/advisor/analyses", json=body, headers={"Idempotency-Key": operation_id}
    ), body


def test_advisor_without_records_stays_honest_and_skips_the_model(system):
    app, _ = system
    model = DeterministicAdvisorModel()
    app.state.advisor_model = model
    client = authenticated(app)

    response, _ = _analyze(client, topic="QA_TEST 帮我看看")
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "insufficient"
    assert data["facts"] == []
    assert data["inferences"] == []
    assert data["missing_information"] == ["记录还不足，可以先开始学习。"]
    assert data["evidence_count"] == 0
    assert data["privacy"]["external"] is False
    assert data["provider"] == "local-deterministic"
    # No records: the adapter is never called, so no fabricated progress.
    assert model.calls == 0


def test_advisor_ready_run_cites_records_and_is_idempotent(system):
    app, _ = system
    app.state.advisor_model = DeterministicAdvisorModel()
    client = authenticated(app)
    _session, subject_id, point_id, _problems, attempt_ids = _seed(app)

    response, body = _analyze(client, subject_id=subject_id, topic="QA_TEST 分析采样")
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "ready"
    assert data["evidence_count"] == 7
    assert data["model_id"] == "mock-advisor-1"
    assert data["privacy"]["external"] is False

    facts = data["facts"]
    assert any("未核对 1 条" in item["text"] for item in facts)
    assert any("不计入正确证据" in item["text"] for item in facts)
    sign = next(item for item in facts if "符号" in item["text"])
    assert set(sign["source_refs"]) == set(attempt_ids[:3])

    # The pending record is never counted as correct evidence.
    correct_fact = next(item for item in facts if "核对正确" in item["text"])
    assert attempt_ids[6] not in correct_fact["source_refs"]

    allowed = set(attempt_ids)
    assert data["inferences"], "grounded inferences are expected"
    for inference in data["inferences"]:
        assert inference["source_refs"]
        assert set(inference["source_refs"]) <= allowed
    # 04 §2 thresholds: three repeats produce a repetition note; three
    # consecutive independent-correct records on one point produce a change note.
    assert any("出现过 3 次" in item["text"] for item in data["inferences"])
    assert any("连续 3 次独立完成" in item["text"] for item in data["inferences"])

    # Knowledge-point scoping selects the same evidence for that subject.
    scoped, _ = _analyze(client, knowledge_point_id=point_id)
    assert scoped.status_code == 201
    assert scoped.json()["data"]["evidence_count"] == 7

    # Replay with the same key returns the stored run instead of a new one.
    replay = client.post(
        "/api/v1/advisor/analyses", json=body, headers={"Idempotency-Key": body["operation_id"]}
    )
    assert replay.status_code == 201
    assert replay.json()["data"] == data

    # Reusing the key with a different body is a conflict.
    changed = {**body, "topic": "changed"}
    conflict = client.post(
        "/api/v1/advisor/analyses", json=changed, headers={"Idempotency-Key": body["operation_id"]}
    )
    assert conflict.status_code == 409

    listed = client.get("/api/v1/advisor/analyses").json()["data"]
    assert any(item["id"] == data["id"] for item in listed["items"])
    assert client.get(f"/api/v1/advisor/analyses/{data['id']}").json()["data"] == data

    # The analysis never rewrites the underlying learning facts.
    with Session(app.state.engine) as db:
        versions = sorted(
            db.scalars(
                select(ProblemAttemptRow.version).where(ProblemAttemptRow.owner_id == "alice")
            )
        )
    assert versions == [1] * 7


def test_advisor_is_owner_scoped(system):
    app, _ = system
    app.state.advisor_model = DeterministicAdvisorModel()
    alice, bob = authenticated(app), authenticated(app, "bob")
    _session, subject_id, point_id, _problems, _attempts = _seed(app)

    # The Idempotency-Key must equal operation_id.
    mismatched = alice.post(
        "/api/v1/advisor/analyses",
        json={"operation_id": str(uuid4()), "subject_id": subject_id},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert mismatched.status_code == 422

    created, _ = _analyze(alice, subject_id=subject_id)
    assert created.status_code == 201
    run_id = created.json()["data"]["id"]
    assert bob.get(f"/api/v1/advisor/analyses/{run_id}").status_code == 404
    assert bob.get("/api/v1/advisor/analyses").json()["data"]["items"] == []
    # Bob can never reach Alice's records through his own analysis.
    bob_run, _ = _analyze(bob, topic="QA_TEST 看看别人")
    assert bob_run.json()["data"]["status"] == "insufficient"
    assert bob_run.json()["data"]["evidence_count"] == 0
    # A subject or knowledge point owned by someone else is not selectable.
    assert _analyze(bob, subject_id=subject_id)[0].status_code == 404
    assert _analyze(bob, knowledge_point_id=point_id)[0].status_code == 404


def test_advisor_degrades_when_the_model_is_unavailable(system):
    app, _ = system
    client = authenticated(app)
    _session, subject_id, _point, _problems, _attempts = _seed(app)

    for mode, expected in (
        ("unavailable", "model_unavailable"),
        ("error", "model_error"),
    ):
        app.state.advisor_model = DeterministicAdvisorModel(mode)
        response, _ = _analyze(client, subject_id=subject_id)
        assert response.status_code == 201, mode
        data = response.json()["data"]
        assert data["status"] == "degraded", mode
        assert data["inferences"] == []
        assert data["degradation_reason"] == expected
        # Deterministic record facts survive, so the surface is still useful.
        assert data["facts"] and data["evidence_count"] == 7
    # And the rest of the product is unaffected (FR-043).
    assert client.get("/api/v1/problems").status_code == 200
    assert client.get("/api/v1/advisor/analyses").status_code == 200


def test_advisor_blocks_unsafe_model_output(system):
    app, _ = system
    client = authenticated(app)
    _session, subject_id, _point, _problems, _attempts = _seed(app)

    for mode, expected in (
        ("forbidden", "forbidden_language"),
        ("unknown_ref", "unknown_reference"),
        ("stale_ref", "unknown_reference"),
        ("malformed", "malformed_output"),
    ):
        app.state.advisor_model = DeterministicAdvisorModel(mode)
        response, _ = _analyze(client, subject_id=subject_id)
        assert response.status_code == 201, mode
        data = response.json()["data"]
        assert data["status"] == "blocked", mode
        assert data["degradation_reason"] == expected
        # No unsafe text is ever published; deterministic facts remain.
        assert data["inferences"] == []
        assert data["facts"]


def test_advisor_cancel_is_idempotent(system):
    app, _ = system
    app.state.advisor_model = DeterministicAdvisorModel()
    client = authenticated(app)
    _session, subject_id, _point, _problems, _attempts = _seed(app)
    created, _ = _analyze(client, subject_id=subject_id)
    run_id = created.json()["data"]["id"]

    key = str(uuid4())
    body = {"operation_id": key}
    first = client.post(
        f"/api/v1/advisor/analyses/{run_id}/cancel", json=body, headers={"Idempotency-Key": key}
    )
    assert first.status_code == 200
    assert first.json()["data"]["status"] == "cancelled"
    replay = client.post(
        f"/api/v1/advisor/analyses/{run_id}/cancel", json=body, headers={"Idempotency-Key": key}
    )
    assert replay.json()["data"] == first.json()["data"]

    missing = str(uuid4())
    not_found = client.post(
        f"/api/v1/advisor/analyses/{missing}/cancel",
        json={"operation_id": missing},
        headers={"Idempotency-Key": missing},
    )
    assert not_found.status_code == 404


def test_advisor_list_pagination_is_stable_and_owner_scoped(system):
    app, _ = system
    app.state.advisor_model = DeterministicAdvisorModel()
    alice, bob = authenticated(app), authenticated(app, "bob")
    _session, subject_id, _point, _problems, _attempts = _seed(app)
    run_ids = []
    for index in range(3):
        created, _ = _analyze(alice, subject_id=subject_id, topic=f"QA_TEST {index}")
        run_ids.append(created.json()["data"]["id"])

    first = alice.get("/api/v1/advisor/analyses", params={"limit": 1}).json()["data"]
    assert len(first["items"]) == 1
    assert first["next_cursor"]
    second_response = alice.get(
        "/api/v1/advisor/analyses", params={"limit": 1, "cursor": first["next_cursor"]}
    )
    assert second_response.status_code == 200, second_response.text
    second = second_response.json()["data"]
    assert len(second["items"]) == 1
    assert second["items"][0]["id"] != first["items"][0]["id"]
    third_response = alice.get(
        "/api/v1/advisor/analyses", params={"limit": 1, "cursor": second["next_cursor"]}
    )
    assert third_response.status_code == 200, third_response.text
    third = third_response.json()["data"]
    collected = [first["items"][0]["id"], second["items"][0]["id"], third["items"][0]["id"]]
    assert sorted(collected) == sorted(run_ids)
    assert third["next_cursor"] is None

    assert alice.get("/api/v1/advisor/analyses", params={"limit": 101}).status_code == 422
    assert (
        alice.get("/api/v1/advisor/analyses", params={"cursor": "not-a-cursor"}).status_code == 422
    )
    # Bob cannot continue from Alice's cursor.
    assert (
        bob.get("/api/v1/advisor/analyses", params={"cursor": first["next_cursor"]}).status_code
        == 422
    )


def test_advisor_survives_a_service_restart(system):
    from hermes_api.main import create_app
    from hermes_api.settings import Settings

    app, url = system
    app.state.advisor_model = DeterministicAdvisorModel()
    client = authenticated(app)
    _session, subject_id, _point, _problems, _attempts = _seed(app)
    created, _ = _analyze(client, subject_id=subject_id)
    run_id = created.json()["data"]["id"]

    restarted = create_app(Settings(database_url=url, environment="test"))
    assert restarted.state.advisor_model.model_id == "mock-advisor-1"
    resumed = authenticated(restarted)
    assert (
        resumed.get(f"/api/v1/advisor/analyses/{run_id}").json()["data"] == created.json()["data"]
    )
