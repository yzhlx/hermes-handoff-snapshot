"""Independent migration, checked-window, stale evidence and scaling regressions."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_foundation import authenticated

pytest_plugins = ("test_foundation",)

from hermes_api.knowledge_storage import (
    ChapterRow,
    KnowledgePointRow,
    ProblemKnowledgeLinkRow,
)
from hermes_api.storage import (
    AttemptErrorRow,
    ProblemAttemptRow,
    ProblemRow,
    SessionRow,
    Subject,
    make_engine,
)
from hermes_api.suggestion_service import SuggestionService
from hermes_api.suggestion_storage import SQLSuggestionUnitOfWork, SuggestionRow

NOW = datetime.now(UTC).replace(microsecond=0)


def _session(owner, session_id, *, subject_id=None, resume_note=None, when=None):
    started = when or NOW - timedelta(hours=1)
    return SessionRow(
        id=session_id,
        owner_id=owner,
        goal="QA_TEST 学习记录",
        subject_id=subject_id,
        knowledge_point_id=None,
        status="ended",
        version=2,
        started_at=started,
        ended_at=started + timedelta(minutes=30),
        day_timezone="Asia/Shanghai",
        learning_date=started.date().isoformat(),
        timing_enabled=False,
        method_id=None,
        kind="free",
        previous_session_id=None,
        resume_note=resume_note,
    )


def _learning_scope(db, owner="alice"):
    subject_id, chapter_id, point_id = str(uuid4()), str(uuid4()), str(uuid4())
    db.add(Subject(id=subject_id, owner_id=owner, name="QA_TEST suggestions"))
    db.flush()
    db.add(
        ChapterRow(
            id=chapter_id,
            owner_id=owner,
            subject_id=subject_id,
            name="QA_TEST chapter",
            order_index=0,
            version=1,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    db.add(
        KnowledgePointRow(
            id=point_id,
            owner_id=owner,
            chapter_id=chapter_id,
            subject_id=subject_id,
            name="QA_TEST point",
            notes=None,
            version=1,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    db.flush()
    return subject_id, point_id


def _problem(db, subject_id, session_id, *, title="QA_TEST problem"):
    problem_id = str(uuid4())
    db.add(
        ProblemRow(
            id=problem_id,
            owner_id="alice",
            subject_id=subject_id,
            title=title,
            statement="QA_TEST statement",
            source_note=None,
            correct_answer=None,
            is_representative=False,
            archived_at=None,
            version=1,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    return problem_id


def _attempt(
    db,
    problem_id,
    session_id,
    *,
    when,
    check="checked",
    result="incorrect",
    independence="hinted",
    category="calculation",
):
    attempt_id = str(uuid4())
    verified = NOW if check == "checked" else None
    db.add(
        ProblemAttemptRow(
            id=attempt_id,
            owner_id="alice",
            session_id=session_id,
            problem_id=problem_id,
            independence=independence,
            answer_check=check,
            result=result,
            attempt_text="QA_TEST attempt",
            stuck_note=None,
            occurred_at=when,
            verified_at=verified,
            version=1,
            created_at=when,
            updated_at=when,
        )
    )
    db.flush()
    if category and check == "checked":
        db.add(
            AttemptErrorRow(
                id=str(uuid4()),
                owner_id="alice",
                attempt_id=attempt_id,
                category=category,
                note=None,
            )
        )
    return attempt_id


def _sqlite_snapshot(engine):
    with engine.connect() as conn:
        names = [
            row[0]
            for row in conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                    "AND name != 'alembic_version' ORDER BY name"
                )
            )
        ]
        schema = {}
        counts = {}
        for name in names:
            escaped = name.replace('"', '""')
            schema[name] = {
                "columns": list(conn.exec_driver_sql(f'PRAGMA table_info("{escaped}")')),
                "indexes": [
                    (
                        index[1],
                        index[2],
                        tuple(
                            row[2]
                            for row in conn.exec_driver_sql(f'PRAGMA index_info("{index[1]}")')
                        ),
                    )
                    for index in conn.exec_driver_sql(f'PRAGMA index_list("{escaped}")')
                ],
            }
            counts[name] = conn.exec_driver_sql(f'SELECT count(*) FROM "{escaped}"').scalar_one()
        return names, schema, counts


def test_upgrade_from_filled_0008_preserves_old_schema_rows_and_downgrade_drops_only_suggestions(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "suggestions-migration.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "0008")
    engine = make_engine(url)
    with Session(engine) as db:
        # Seeded with the columns that existed at this revision. Using the
        # current ORM here would insert later additions such as `users.status`,
        # which this schema does not have yet.
        for owner in ("QA_TEST_owner", "QA_TEST_other"):
            db.execute(
                text(
                    "INSERT INTO users (id, username, password_hash, timezone) "
                    "VALUES (:id, :id, 'QA_TEST_hash', 'Asia/Shanghai')"
                ),
                {"id": owner},
            )
        db.flush()
        subject_id = str(uuid4())
        db.add(Subject(id=subject_id, owner_id="QA_TEST_owner", name="QA_TEST old subject"))
        db.flush()
        old_session_id = str(uuid4())
        db.add(
            _session(
                "QA_TEST_owner",
                old_session_id,
                subject_id=subject_id,
                resume_note="QA_TEST preserved position",
            )
        )
        db.commit()
    old_names, old_schema, old_counts = _sqlite_snapshot(engine)

    # This regression verifies only the suggestions migration; later migrations
    # have their own preservation checks and must not change its table contract.
    command.upgrade(config, "0009")
    new_names, new_schema, new_counts = _sqlite_snapshot(engine)
    assert "suggestions" in new_names
    assert set(new_names) - {"suggestions"} == set(old_names)
    assert {name: new_schema[name] for name in old_names} == old_schema
    assert {name: new_counts[name] for name in old_names} == old_counts

    with Session(engine) as db:
        db.add(
            SuggestionRow(
                id=str(uuid4()),
                owner_id="QA_TEST_owner",
                fingerprint="a" * 64,
                kind="review",
                status="available",
                subject_id=None,
                knowledge_point_id=None,
                problem_id=None,
                reason="QA_TEST reason",
                source_refs="[]",
                source_revision="b" * 64,
                rule_version="suggestions-1",
                version=1,
                generated_at=NOW,
            )
        )
        db.commit()
        db.add(
            SuggestionRow(
                id=str(uuid4()),
                owner_id="QA_TEST_owner",
                fingerprint="a" * 64,
                kind="review",
                status="available",
                subject_id=None,
                knowledge_point_id=None,
                problem_id=None,
                reason="QA_TEST duplicate",
                source_refs="[]",
                source_revision="b" * 64,
                rule_version="suggestions-1",
                version=1,
                generated_at=NOW,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert (
            db.scalar(select(SuggestionRow.id).where(SuggestionRow.owner_id == "QA_TEST_owner"))
            is not None
        )
        db.add(
            SuggestionRow(
                id=str(uuid4()),
                owner_id="QA_TEST_other",
                fingerprint="a" * 64,
                kind="review",
                status="available",
                subject_id=None,
                knowledge_point_id=None,
                problem_id=None,
                reason="QA_TEST independent owner",
                source_refs="[]",
                source_revision="b" * 64,
                rule_version="suggestions-1",
                version=1,
                generated_at=NOW,
            )
        )
        db.commit()
        assert (
            db.scalar(select(SuggestionRow.id).where(SuggestionRow.owner_id == "QA_TEST_other"))
            is not None
        )

    command.downgrade(config, "0008")
    rolled_names, rolled_schema, rolled_counts = _sqlite_snapshot(engine)
    assert set(rolled_names) == set(old_names)
    assert rolled_schema == old_schema
    assert rolled_counts == old_counts
    engine.dispose()


def test_sql_repeated_error_uses_latest_twenty_checked_even_with_twenty_three_newer_pending(system):
    app, _ = system
    client = authenticated(app)
    with Session(app.state.engine) as db:
        subject_id, point_id = _learning_scope(db)
        session_id = str(uuid4())
        db.add(_session("alice", session_id, subject_id=subject_id))
        db.flush()
        problem_id = _problem(db, subject_id, session_id)
        db.flush()
        db.add(
            ProblemKnowledgeLinkRow(
                owner_id="alice", problem_id=problem_id, knowledge_point_id=point_id, created_at=NOW
            )
        )
        checked_ids = [
            _attempt(
                db,
                problem_id,
                session_id,
                when=NOW - timedelta(days=30 + i),
                check="checked",
                result="incorrect",
                category="calculation",
            )
            for i in range(3)
        ]
        for i in range(23):
            _attempt(
                db,
                problem_id,
                session_id,
                when=NOW - timedelta(hours=23 - i),
                check="pending",
                result=None,
                category=None,
            )
        db.commit()
    response = client.get("/api/v1/suggestions?kind=repeated_error")
    assert response.status_code == 200, response.text
    repeated = response.json()["data"]["items"]
    assert len(repeated) == 1
    actual_attempt_refs = {
        ref["id"] for ref in repeated[0]["source_refs"] if ref["kind"] == "attempt"
    }
    assert actual_attempt_refs == set(checked_ids)
    assert "计算类错误出现3次" in repeated[0]["reason"]


def test_latest_pending_suppresses_older_due_review_as_unverified(system):
    app, _ = system
    client = authenticated(app)
    with Session(app.state.engine) as db:
        subject_id, _point_id = _learning_scope(db)
        session_id = str(uuid4())
        db.add(_session("alice", session_id, subject_id=subject_id))
        db.flush()
        problem_id = _problem(db, subject_id, session_id, title="QA_TEST latest pending")
        db.flush()
        old_id = _attempt(
            db,
            problem_id,
            session_id,
            when=NOW - timedelta(days=10),
            result="incorrect",
            category="calculation",
        )
        latest_id = _attempt(
            db,
            problem_id,
            session_id,
            when=NOW - timedelta(hours=1),
            check="pending",
            result=None,
            category=None,
        )
        db.commit()
    response = client.get("/api/v1/suggestions?status=all")
    assert response.status_code == 200, response.text
    relevant = [
        item for item in response.json()["data"]["items"] if item["problem_id"] == problem_id
    ]
    assert [item["kind"] for item in relevant] == ["unverified"]
    refs = {ref["id"] for ref in relevant[0]["source_refs"]}
    assert latest_id in refs and old_id not in refs


def test_correction_stales_dismissed_review_without_restoring_same_evidence(system):
    app, _ = system
    client = authenticated(app)
    with Session(app.state.engine) as db:
        subject_id, _point_id = _learning_scope(db)
        session_id = str(uuid4())
        db.add(_session("alice", session_id, subject_id=subject_id))
        db.flush()
        problem_id = _problem(db, subject_id, session_id, title="QA_TEST corrected review")
        db.flush()
        attempt_id = _attempt(
            db,
            problem_id,
            session_id,
            when=NOW - timedelta(days=10),
            result="incorrect",
            independence="independent",
            category="calculation",
        )
        db.commit()
    due = client.get("/api/v1/suggestions?kind=review")
    assert due.status_code == 200 and len(due.json()["data"]["items"]) == 1
    review = due.json()["data"]["items"][0]
    key = str(uuid4())
    dismissed = client.post(
        f"/api/v1/suggestions/{review['id']}/actions",
        json={"operation_id": key, "action": "dismiss"},
        headers={"Idempotency-Key": key, "If-Match": str(review["version"])},
    )
    assert dismissed.status_code == 200 and dismissed.json()["data"]["status"] == "dismissed"
    assert client.get("/api/v1/suggestions?kind=review").json()["data"]["items"] == []

    with Session(app.state.engine) as db:
        attempt = db.get(ProblemAttemptRow, attempt_id)
        attempt.result = "correct"
        attempt.independence = "independent"
        attempt.version += 1
        attempt.verified_at = NOW
        attempt.updated_at = NOW
        db.commit()
    all_items = client.get("/api/v1/suggestions?status=all").json()["data"]["items"]
    old = next(item for item in all_items if item["id"] == review["id"])
    assert old["status"] == "stale"
    assert not any(
        item["kind"] == "review" and item["problem_id"] == problem_id and item["status"] != "stale"
        for item in all_items
    )
    assert client.get("/api/v1/suggestions?kind=review").json()["data"]["items"] == []


def test_suggestion_source_query_count_stays_bounded_from_five_to_twenty_sources(system):
    app, _ = system
    with Session(app.state.engine) as db:
        db.add_all(
            [_session("alice", str(uuid4()), resume_note=f"QA_TEST position {i}") for i in range(5)]
        )
        db.commit()

    def count_list_queries():
        statements = []

        def record(_conn, _cursor, statement, _parameters, _context, _many):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(app.state.engine, "before_cursor_execute", record)
        try:
            with Session(app.state.engine) as db:
                SuggestionService(SQLSuggestionUnitOfWork(db), clock=lambda: NOW).list("alice")
        finally:
            event.remove(app.state.engine, "before_cursor_execute", record)
        return len(statements)

    five_count = count_list_queries()
    with Session(app.state.engine) as db:
        db.add_all(
            [
                _session("alice", str(uuid4()), resume_note=f"QA_TEST position {i}")
                for i in range(5, 20)
            ]
        )
        db.commit()
    twenty_count = count_list_queries()
    assert five_count <= 12
    assert twenty_count <= 12
    assert abs(twenty_count - five_count) <= 1


def test_twenty_one_suggestions_are_reachable_across_cursor_pages(system):
    app, _ = system
    client = authenticated(app)
    with Session(app.state.engine) as db:
        db.add_all(
            [_session("alice", str(uuid4()), resume_note=f"QA_TEST page {i}") for i in range(21)]
        )
        db.commit()
    ids, cursor = [], None
    while True:
        params = {"kind": "continue", "limit": 7}
        if cursor:
            params["cursor"] = cursor
        response = client.get("/api/v1/suggestions", params=params)
        assert response.status_code == 200, response.text
        page = response.json()["data"]
        ids.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert len(ids) == 21
    assert len(set(ids)) == 21
