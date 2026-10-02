from uuid import uuid4

from argon2 import PasswordHasher
from sqlalchemy import update
from sqlalchemy.orm import Session
from test_foundation import authenticated, start

from hermes_api.main import create_app
from hermes_api.settings import Settings
from hermes_api.storage import Base, SessionRow, User


def test_records_and_day_summary_http_contract(tmp_path):
    url = f"sqlite:///{tmp_path / 'records-isolated.db'}"
    app = create_app(Settings(database_url=url, environment="test"))
    Base.metadata.create_all(app.state.engine)
    with Session(app.state.engine) as db:
        db.add(
            User(
                id="qa-records",
                username="qa-records",
                password_hash=PasswordHasher().hash("QA_TEST_password"),
                timezone="Asia/Shanghai",
            )
        )
        db.commit()
    client = authenticated(app, "qa-records")
    started, _ = start(client)
    session = started.json()["data"]
    # Freeze the test session's account-local day after creation so this test never depends
    # on the host clock or the day it happens to run.
    with Session(app.state.engine) as db:
        db.execute(
            update(SessionRow)
            .where(SessionRow.owner_id == "qa-records", SessionRow.id == session["id"])
            .values(learning_date="2026-10-01", day_timezone="Asia/Shanghai")
        )
        db.commit()
    end_key = str(uuid4())
    ended = client.post(
        f"/api/v1/learning-sessions/{session['id']}/end",
        json={"operation_id": end_key},
        headers={"Idempotency-Key": end_key, "If-Match": '"1"'},
    )
    assert ended.status_code == 200
    reflection_key = str(uuid4())
    reflected = client.post(
        "/api/v1/session-reflections",
        json={
            "operation_id": reflection_key,
            "session_id": session["id"],
            "summary": "QA_TEST_整理了采样条件",
            "stuck_note": "QA_TEST_符号约定仍需核对",
        },
        headers={"Idempotency-Key": reflection_key},
    )
    assert reflected.status_code == 201
    problem_key = str(uuid4())
    problem = client.post(
        "/api/v1/problems",
        json={
            "operation_id": problem_key,
            "title": "QA_TEST_练习题",
            "statement": "QA_TEST_计算一个例子",
        },
        headers={"Idempotency-Key": problem_key},
    )
    assert problem.status_code == 201
    attempt_key = str(uuid4())
    attempt = client.post(
        "/api/v1/problem-attempts",
        json={
            "operation_id": attempt_key,
            "session_id": session["id"],
            "problem_id": problem.json()["data"]["id"],
            "independence": "independent",
            "answer_check": "pending",
            "stuck_note": "QA_TEST_不确定边界条件",
        },
        headers={"Idempotency-Key": attempt_key},
    )
    assert attempt.status_code == 201
    records = client.get("/api/v1/records?from=2026-10-01&to=2026-10-01")
    summary = client.get("/api/v1/day-summary?date=2026-10-01")
    assert records.status_code == summary.status_code == 200
    page = records.json()["data"]
    day = summary.json()["data"]
    assert page["from_date"] == page["to_date"] == "2026-10-01"
    assert page["timezone"] == day["timezone"] == "Asia/Shanghai"
    assert page["totals"]["session_count"] == 1
    assert page["totals"]["effective_record_count"] == 1
    assert page["items"][0]["summary"] == "QA_TEST_整理了采样条件"
    assert page["items"][0]["attempt_count"] == 1
    assert page["items"][0]["pending_count"] == 1
    assert day["date"] == "2026-10-01" and len(day["source_refs"]) == 4
    assert day["learned"][0]["text"] == "QA_TEST_整理了采样条件"
    assert day["stuck_points"][0]["text"] == "QA_TEST_符号约定仍需核对"
    assert day["stuck_points"][1]["text"] == "QA_TEST_不确定边界条件"
    assert client.get("/api/v1/records?limit=101").status_code == 422
    assert client.get("/api/v1/records?from=2025-09-30&to=2026-10-01").status_code == 422
