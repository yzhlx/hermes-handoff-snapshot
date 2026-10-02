"""Authenticated API checks for comparison writes, visibility and version safety."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

pytest_plugins = ("test_foundation",)

from test_foundation import authenticated

from hermes_api.storage import ProblemAttemptRow, ProblemRow, SessionRow


def _source_rows(app):
    now = datetime.now(UTC)
    ids = [str(uuid4()) for _ in range(8)]
    with Session(app.state.engine) as db:
        db.add(
            SessionRow(
                id=ids[4],
                owner_id="alice",
                goal="QA_TEST",
                subject_id=None,
                knowledge_point_id=None,
                status="ended",
                version=1,
                started_at=now,
                ended_at=now,
                day_timezone="UTC",
                learning_date=now.date().isoformat(),
                timing_enabled=False,
                method_id=None,
                kind="free",
                previous_session_id=None,
                resume_note=None,
            )
        )
        db.flush()
        db.add(
            SessionRow(
                id=ids[5],
                owner_id="bob",
                goal="QA_TEST",
                subject_id=None,
                knowledge_point_id=None,
                status="ended",
                version=1,
                started_at=now,
                ended_at=now,
                day_timezone="UTC",
                learning_date=now.date().isoformat(),
                timing_enabled=False,
                method_id=None,
                kind="free",
                previous_session_id=None,
                resume_note=None,
            )
        )
        db.flush()
        for owner, pid in (
            ("alice", ids[0]),
            ("alice", ids[1]),
            ("alice", ids[2]),
            ("bob", ids[3]),
        ):
            db.add(
                ProblemRow(
                    id=pid,
                    owner_id=owner,
                    subject_id=None,
                    title="QA_TEST",
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
        attempt_ids = []
        for problem_id in ids[:3]:
            attempt_id = str(uuid4())
            db.add(
                ProblemAttemptRow(
                    id=attempt_id,
                    owner_id="alice",
                    session_id=ids[4],
                    problem_id=problem_id,
                    independence="hinted",
                    answer_check="pending",
                    result=None,
                    attempt_text="过程",
                    stuck_note=None,
                    occurred_at=now,
                    verified_at=None,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
            )
            attempt_ids.append(attempt_id)
        foreign_attempt_id = str(uuid4())
        db.add(
            ProblemAttemptRow(
                id=foreign_attempt_id,
                owner_id="bob",
                session_id=ids[5],
                problem_id=ids[3],
                independence="hinted",
                answer_check="pending",
                result=None,
                attempt_text="QA_TEST attempt",
                stuck_note=None,
                occurred_at=now,
                verified_at=None,
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()
    return ids[:4], attempt_ids, foreign_attempt_id


def test_comparison_api_auth_replay_conflict_filters_and_source_snapshot(system):
    app, _ = system
    (a, b, other, foreign), attempts, foreign_attempt = _source_rows(app)
    with Session(app.state.engine) as db:
        source_problem = db.scalar(select(ProblemRow).where(ProblemRow.id == a))
        source_attempt = db.scalar(
            select(ProblemAttemptRow).where(ProblemAttemptRow.id == attempts[0])
        )
        problem_state = (
            source_problem.version,
            source_problem.is_representative,
            source_problem.correct_answer,
        )
        attempt_state = (source_attempt.version, source_attempt.answer_check, source_attempt.result)
    client = authenticated(app)
    without_auth = client.post("/api/v1/auth/logout")
    assert without_auth.status_code == 204
    assert client.get("/api/v1/problem-comparisons").status_code == 401
    client = authenticated(app)

    missing_precondition_key = str(uuid4())
    # A valid PATCH request without If-Match must be rejected before mutation.
    create_key = str(uuid4())
    body = {
        "operation_id": create_key,
        "left_problem_id": a,
        "right_problem_id": b,
        "left_attempt_id": None,
        "right_attempt_id": None,
        "conditions": "条件",
        "known_values": None,
        "formulas": None,
        "entry_point": None,
        "diagram": None,
        "boundary": None,
        "assumptions": None,
        "conclusion": "结论",
    }
    created_response = client.post(
        "/api/v1/problem-comparisons", json=body, headers={"Idempotency-Key": create_key}
    )
    assert created_response.status_code == 201
    original = created_response.json()["data"]
    assert original["source_versions"] == {a: 1, b: 1}
    assert (
        client.post(
            "/api/v1/problem-comparisons", json=body, headers={"Idempotency-Key": create_key}
        ).json()["data"]
        == original
    )
    mismatch = {**body, "conclusion": "different"}
    assert (
        client.post(
            "/api/v1/problem-comparisons", json=mismatch, headers={"Idempotency-Key": create_key}
        ).status_code
        == 409
    )
    duplicate_key = str(uuid4())
    assert (
        client.post(
            "/api/v1/problem-comparisons",
            json={**body, "operation_id": duplicate_key, "right_problem_id": a},
            headers={"Idempotency-Key": duplicate_key},
        ).status_code
        == 422
    )
    blank_key = str(uuid4())
    assert (
        client.post(
            "/api/v1/problem-comparisons",
            json={**body, "operation_id": blank_key, "conditions": "   ", "conclusion": "\t"},
            headers={"Idempotency-Key": blank_key},
        ).status_code
        == 422
    )
    long_key = str(uuid4())
    assert (
        client.post(
            "/api/v1/problem-comparisons",
            json={**body, "operation_id": long_key, "conditions": "x" * 2001},
            headers={"Idempotency-Key": long_key},
        ).status_code
        == 422
    )
    missing_key = str(uuid4())
    assert (
        client.post(
            "/api/v1/problem-comparisons", json={**body, "operation_id": missing_key}
        ).status_code
        == 422
    )
    no_csrf = client.headers.pop("X-CSRF-Token")
    csrf_key = str(uuid4())
    assert (
        client.post(
            "/api/v1/problem-comparisons",
            json={**body, "operation_id": csrf_key},
            headers={"Idempotency-Key": csrf_key},
        ).status_code
        == 403
    )
    client.headers["X-CSRF-Token"] = no_csrf

    no_match_key = missing_precondition_key
    assert (
        client.patch(
            f"/api/v1/problem-comparisons/{original['id']}",
            json={"operation_id": no_match_key, "conclusion": "编辑"},
            headers={"Idempotency-Key": no_match_key},
        ).status_code
        == 428
    )
    invalid_if_match_key = str(uuid4())
    assert (
        client.patch(
            f"/api/v1/problem-comparisons/{original['id']}",
            json={"operation_id": invalid_if_match_key, "conclusion": "bad"},
            headers={"Idempotency-Key": invalid_if_match_key, "If-Match": "bad"},
        ).status_code
        == 422
    )
    forbidden_key = str(uuid4())
    assert (
        client.patch(
            f"/api/v1/problem-comparisons/{original['id']}",
            json={"operation_id": forbidden_key, "left_problem_id": other},
            headers={"Idempotency-Key": forbidden_key, "If-Match": "2"},
        ).status_code
        == 422
    )
    patch_key = str(uuid4())
    saved = client.patch(
        f"/api/v1/problem-comparisons/{original['id']}",
        json={"operation_id": patch_key, "conclusion": "更新"},
        headers={"Idempotency-Key": patch_key, "If-Match": '"1"'},
    )
    assert saved.status_code == 200 and saved.json()["data"]["version"] == 2
    stale_key = str(uuid4())
    assert (
        client.patch(
            f"/api/v1/problem-comparisons/{original['id']}",
            json={"operation_id": stale_key, "conclusion": "stale"},
            headers={"Idempotency-Key": stale_key, "If-Match": "1"},
        ).status_code
        == 409
    )
    assert (
        client.get(f"/api/v1/problem-comparisons/{original['id']}").json()["data"]["conclusion"]
        == "更新"
    )

    attempt_key = str(uuid4())
    invalid_attempt = {
        "operation_id": attempt_key,
        "left_problem_id": a,
        "right_problem_id": b,
        "left_attempt_id": attempts[2],
        "right_attempt_id": attempts[1],
        "conditions": "x",
    }
    assert (
        client.post(
            "/api/v1/problem-comparisons",
            json=invalid_attempt,
            headers={"Idempotency-Key": attempt_key},
        ).status_code
        == 422
    )
    valid_attempt_key = str(uuid4())
    valid_attempt_body = {
        "operation_id": valid_attempt_key,
        "left_problem_id": a,
        "right_problem_id": b,
        "left_attempt_id": attempts[0],
        "right_attempt_id": attempts[1],
        "known_values": "给定值",
    }
    valid_attempt = client.post(
        "/api/v1/problem-comparisons",
        json=valid_attempt_body,
        headers={"Idempotency-Key": valid_attempt_key},
    )
    assert valid_attempt.status_code == 201
    valid_data = valid_attempt.json()["data"]
    assert valid_data["source_versions"] == {a: 1, b: 1, attempts[0]: 1, attempts[1]: 1}
    foreign_attempt_key = str(uuid4())
    assert (
        client.post(
            "/api/v1/problem-comparisons",
            json={
                **valid_attempt_body,
                "operation_id": foreign_attempt_key,
                "right_problem_id": foreign,
                "right_attempt_id": foreign_attempt,
            },
            headers={"Idempotency-Key": foreign_attempt_key},
        ).status_code
        == 404
    )
    foreign_attempt_key = str(uuid4())
    assert (
        client.post(
            "/api/v1/problem-comparisons",
            json={
                **valid_attempt_body,
                "operation_id": foreign_attempt_key,
                "right_attempt_id": foreign_attempt,
            },
            headers={"Idempotency-Key": foreign_attempt_key},
        ).status_code
        == 404
    )
    foreign_key = str(uuid4())
    foreign_body = {
        **body,
        "operation_id": foreign_key,
        "right_problem_id": foreign,
        "left_attempt_id": None,
    }
    assert (
        client.post(
            "/api/v1/problem-comparisons",
            json=foreign_body,
            headers={"Idempotency-Key": foreign_key},
        ).status_code
        == 404
    )

    archive_key = str(uuid4())
    archived = client.patch(
        f"/api/v1/problem-comparisons/{original['id']}",
        json={"operation_id": archive_key, "archived": True},
        headers={"Idempotency-Key": archive_key, "If-Match": "2"},
    )
    assert archived.status_code == 200 and archived.json()["data"]["archived"] is True
    active_items = client.get("/api/v1/problem-comparisons").json()["data"]["items"]
    assert original["id"] not in {item["id"] for item in active_items}
    assert valid_data["id"] in {item["id"] for item in active_items}
    archived_items = client.get(
        "/api/v1/problem-comparisons", params={"archived": True, "problem_id": a}
    ).json()["data"]["items"]
    assert original["id"] in {item["id"] for item in archived_items}
    assert (
        client.get("/api/v1/problem-comparisons", params={"cursor": str(uuid4())}).status_code
        == 422
    )
    bob = authenticated(app, "bob")
    assert bob.get(f"/api/v1/problem-comparisons/{original['id']}").status_code == 404
    bob_patch = str(uuid4())
    assert (
        bob.patch(
            f"/api/v1/problem-comparisons/{original['id']}",
            json={"operation_id": bob_patch, "conclusion": "跨用户"},
            headers={"Idempotency-Key": bob_patch, "If-Match": "2"},
        ).status_code
        == 404
    )
    assert bob.get("/api/v1/problem-comparisons", params={"problem_id": a}).status_code == 404
    restore_key = str(uuid4())
    restored = client.patch(
        f"/api/v1/problem-comparisons/{original['id']}",
        json={"operation_id": restore_key, "archived": False},
        headers={"Idempotency-Key": restore_key, "If-Match": "3"},
    )
    assert restored.json()["data"]["archived"] is False

    with Session(app.state.engine) as db:
        before = db.scalar(select(ProblemRow).where(ProblemRow.id == a))
        attempt_before = db.scalar(
            select(ProblemAttemptRow).where(ProblemAttemptRow.id == attempts[0])
        )
        assert (before.version, before.is_representative, before.correct_answer) == problem_state
        assert (
            attempt_before.version,
            attempt_before.answer_check,
            attempt_before.result,
        ) == attempt_state
        before.version = 2
        db.commit()
        refreshed_attempt = db.scalar(
            select(ProblemAttemptRow).where(ProblemAttemptRow.id == attempts[0])
        )
        assert (
            refreshed_attempt.version,
            refreshed_attempt.answer_check,
            refreshed_attempt.result,
        ) == attempt_state
        assert (
            db.scalar(select(ProblemRow).where(ProblemRow.id == a)).is_representative,
            db.scalar(select(ProblemRow).where(ProblemRow.id == a)).correct_answer,
        ) == problem_state[1:]
    assert (
        client.get(f"/api/v1/problem-comparisons/{original['id']}").json()["data"]["source_changed"]
        is True
    )
