"""Comparison persistence, source snapshots, keyset paging and migration regressions."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

pytest_plugins = ("test_foundation",)

from hermes_api.comparison_service import ComparisonService
from hermes_api.comparison_storage import ProblemComparisonRow, SQLComparisonUnitOfWork
from hermes_api.domain import PolicyError
from hermes_api.storage import (
    ProblemAttemptRow,
    ProblemRow,
    SessionReflectionRow,
    SessionRow,
    Subject,
)


def _problem(db, owner="alice", subject_id=None):
    item_id = str(uuid4())
    now = datetime.now(UTC)
    db.add(
        ProblemRow(
            id=item_id,
            owner_id=owner,
            subject_id=subject_id,
            title="QA_TEST",
            statement="QA_TEST题",
            source_note=None,
            correct_answer="2",
            is_representative=False,
            archived_at=None,
            version=1,
            created_at=now,
            updated_at=now,
        )
    )
    db.flush()
    return item_id


def _create(service, left, right, **overrides):
    key = str(uuid4())
    data = {
        "operation_id": key,
        "left_problem_id": left,
        "right_problem_id": right,
        "conditions": "条件",
        **overrides,
    }
    return service.create("alice", data, key)


def test_create_validation_owner_distinct_and_source_change(system):
    app, _ = system
    with Session(app.state.engine) as db:
        left, right = _problem(db), _problem(db)
        db.commit()
        service = ComparisonService(SQLComparisonUnitOfWork(db))
        item = _create(service, left, right, formulas="a²+b²")
        assert item["source_versions"] == {left: 1, right: 1}
        row = db.scalar(select(ProblemRow).where(ProblemRow.id == left))
        row.version = 2
        db.commit()
        assert service.get("alice", item["id"])["source_changed"] is True
        with pytest.raises(PolicyError) as same:
            _create(service, left, left)
        assert same.value.status == 422
        with pytest.raises(PolicyError) as other:
            _create(service, left, str(uuid4()))
        assert other.value.status == 404


def test_idempotency_version_patch_archive_and_pagination(system):
    app, _ = system
    with Session(app.state.engine) as db:
        ids = [_problem(db) for _ in range(4)]
        db.commit()
        service = ComparisonService(SQLComparisonUnitOfWork(db))
        first_key = str(uuid4())
        body = {
            "operation_id": first_key,
            "left_problem_id": ids[0],
            "right_problem_id": ids[1],
            "conclusion": "QA_TEST结论",
        }
        one = service.create("alice", body, first_key)
        assert service.create("alice", body, first_key) == one
        changed = {**body, "conclusion": "different"}
        with pytest.raises(PolicyError) as idem:
            service.create("alice", changed, first_key)
        assert idem.value.status == 409
        two = _create(service, ids[2], ids[3])
        all_rows = service.list("alice", limit=1)
        assert len(all_rows["items"]) == 1 and all_rows["next_cursor"]
        next_rows = service.list("alice", limit=10, cursor=all_rows["next_cursor"])
        assert len(next_rows["items"]) == 1
        key = str(uuid4())
        updated = service.patch(
            "alice", one["id"], {"operation_id": key, "conclusion": "已改"}, key, 1
        )
        assert updated["version"] == 2 and updated["source_versions"] == one["source_versions"]
        replayed = service.patch(
            "alice", one["id"], {"operation_id": key, "conclusion": "已改"}, key, 1
        )
        assert replayed == updated
        stale_key = str(uuid4())
        with pytest.raises(PolicyError) as stale:
            service.patch(
                "alice",
                one["id"],
                {"operation_id": stale_key, "conclusion": "冲突"},
                stale_key,
                1,
            )
        assert stale.value.status == 409
        with pytest.raises(PolicyError) as missing:
            service.patch(
                "alice",
                one["id"],
                {"operation_id": str(uuid4()), "archived": True},
                str(uuid4()),
                None,
            )
        assert missing.value.status == 428
        archive_key = str(uuid4())
        archived = service.patch(
            "alice", one["id"], {"operation_id": archive_key, "archived": True}, archive_key, 2
        )
        assert archived["archived"] is True
        assert len(service.list("alice", archived=True)["items"]) == 1
        assert two["archived"] is False


def test_attempt_binding_and_merged_text_validation(system):
    app, _ = system
    with Session(app.state.engine) as db:
        now = datetime.now(UTC)
        subject = str(uuid4())
        db.add(Subject(id=subject, owner_id="alice", name="QA_TEST subject"))
        db.flush()
        session_id = str(uuid4())
        db.add(
            SessionRow(
                id=session_id,
                owner_id="alice",
                goal="QA_TEST",
                subject_id=subject,
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
        left, right, unrelated = (_problem(db, subject_id=subject) for _ in range(3))
        db.flush()
        attempts = []
        for problem_id in (left, right, unrelated):
            attempt_id = str(uuid4())
            db.add(
                ProblemAttemptRow(
                    id=attempt_id,
                    owner_id="alice",
                    session_id=session_id,
                    problem_id=problem_id,
                    independence="hinted",
                    answer_check="pending",
                    result=None,
                    attempt_text="QA_TEST answer",
                    stuck_note=None,
                    occurred_at=now,
                    verified_at=None,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
            )
            attempts.append(attempt_id)
        db.commit()
        service = ComparisonService(SQLComparisonUnitOfWork(db))
        key = str(uuid4())
        item = service.create(
            "alice",
            {
                "operation_id": key,
                "left_problem_id": left,
                "right_problem_id": right,
                "left_attempt_id": attempts[0],
                "right_attempt_id": attempts[1],
                "assumptions": "假设",
            },
            key,
        )
        assert item["source_versions"] == {left: 1, right: 1, attempts[0]: 1, attempts[1]: 1}
        mismatched = str(uuid4())
        with pytest.raises(PolicyError) as mismatch:
            service.create(
                "alice",
                {
                    "operation_id": mismatched,
                    "left_problem_id": left,
                    "right_problem_id": right,
                    "left_attempt_id": attempts[2],
                    "conditions": "条件",
                },
                mismatched,
            )
        assert mismatch.value.status == 422
        blank = str(uuid4())
        with pytest.raises(PolicyError) as empty:
            service.patch(
                "alice",
                item["id"],
                {"operation_id": blank, "conditions": "  ", "assumptions": " "},
                blank,
                1,
            )
        assert empty.value.status == 422


def test_filtered_keyset_pages_apply_limit_after_owner_and_subject_filters(system):
    app, _ = system
    with Session(app.state.engine) as db:
        now = datetime.now(UTC)
        subject = str(uuid4())
        db.add(Subject(id=subject, owner_id="alice", name="QA_TEST pagination"))
        db.flush()
        left, right = _problem(db, subject_id=subject), _problem(db, subject_id=subject)
        db.flush()
        for index in range(103):
            db.add(
                ProblemComparisonRow(
                    id=str(uuid4()),
                    owner_id="alice",
                    version=1,
                    left_problem_id=left,
                    right_problem_id=right,
                    left_attempt_id=None,
                    right_attempt_id=None,
                    conditions=f"row {index}",
                    known_values=None,
                    formulas=None,
                    entry_point=None,
                    diagram=None,
                    boundary=None,
                    assumptions=None,
                    conclusion=None,
                    archived_at=None,
                    created_at=now,
                    updated_at=now,
                    source_versions=f'{{"{left}":1,"{right}":1}}',
                )
            )
        db.commit()
        service = ComparisonService(SQLComparisonUnitOfWork(db))
        first = service.list("alice", subject_id=subject, limit=100)
        assert len(first["items"]) == 100 and first["next_cursor"]
        second = service.list("alice", subject_id=subject, limit=100, cursor=first["next_cursor"])
        assert len(second["items"]) == 3 and second["next_cursor"] is None
        with pytest.raises(PolicyError) as forged_problem:
            service.list("alice", problem_id=str(uuid4()))
        assert forged_problem.value.status == 404


def test_database_enforces_owner_scoped_problem_foreign_keys_and_distinct_pair(system):
    app, _ = system
    with Session(app.state.engine) as db:
        own, other_own, foreign = _problem(db), _problem(db), _problem(db, owner="bob")
        db.commit()
        now = datetime.now(UTC)

        def comparison(left, right):
            return ProblemComparisonRow(
                id=str(uuid4()),
                owner_id="alice",
                version=1,
                left_problem_id=left,
                right_problem_id=right,
                left_attempt_id=None,
                right_attempt_id=None,
                conditions="QA_TEST",
                known_values=None,
                formulas=None,
                entry_point=None,
                diagram=None,
                boundary=None,
                assumptions=None,
                conclusion=None,
                archived_at=None,
                created_at=now,
                updated_at=now,
                source_versions="{}",
            )

        db.add(comparison(own, foreign))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.add(comparison(own, own))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.add(comparison(own, other_own))
        db.commit()


def test_migration_0009_to_0010_preserves_prior_rows_and_empty_downgrade(
    system, tmp_path, monkeypatch
):
    # The normal system fixture has migrated to head; migration behavior is isolated here.
    from hermes_api.storage import make_engine

    path = tmp_path / "comparison-migration.db"
    url = f"sqlite:///{path}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "0009")
    engine = make_engine(url)
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    session_id, second_session_id = str(uuid4()), str(uuid4())
    problem_id, attempt_id, reflection_id = str(uuid4()), str(uuid4()), str(uuid4())
    with Session(engine) as db:
        # Seeded with the columns that existed at this revision. Using the
        # current ORM here would insert later additions such as `users.status`,
        # which this schema does not have yet.
        db.execute(
            text(
                "INSERT INTO users (id, username, password_hash, timezone) "
                "VALUES ('QA_TEST_owner', 'QA_TEST_owner', 'QA_TEST_hash', 'UTC')"
            )
        )
        db.flush()
        db.add_all(
            [
                SessionRow(
                    id=session_id,
                    owner_id="QA_TEST_owner",
                    goal="QA_TEST old session",
                    subject_id=None,
                    knowledge_point_id=None,
                    status="ended",
                    version=2,
                    started_at=now,
                    ended_at=now,
                    day_timezone="UTC",
                    learning_date="2026-10-01",
                    timing_enabled=False,
                    method_id=None,
                    kind="free",
                    previous_session_id=None,
                    resume_note="preserved",
                ),
                SessionRow(
                    id=second_session_id,
                    owner_id="QA_TEST_owner",
                    goal="QA_TEST followup",
                    subject_id=None,
                    knowledge_point_id=None,
                    status="ended",
                    version=1,
                    started_at=now,
                    ended_at=now,
                    day_timezone="UTC",
                    learning_date="2026-10-01",
                    timing_enabled=False,
                    method_id=None,
                    kind="free",
                    previous_session_id=session_id,
                    resume_note=None,
                ),
            ]
        )
        db.flush()
        db.add(
            ProblemRow(
                id=problem_id,
                owner_id="QA_TEST_owner",
                subject_id=None,
                title="QA_TEST old problem",
                statement="old statement",
                source_note=None,
                correct_answer="old answer",
                is_representative=True,
                archived_at=None,
                version=3,
                created_at=now,
                updated_at=now,
            )
        )
        db.flush()
        db.add(
            ProblemAttemptRow(
                id=attempt_id,
                owner_id="QA_TEST_owner",
                session_id=session_id,
                problem_id=problem_id,
                independence="hinted",
                answer_check="checked",
                result="partial",
                attempt_text="old attempt",
                stuck_note="old stuck",
                occurred_at=now,
                verified_at=now,
                version=4,
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            SessionReflectionRow(
                id=reflection_id,
                owner_id="QA_TEST_owner",
                session_id=session_id,
                summary="QA_TEST reflection",
                recalled_text=None,
                reference_checked=True,
                missing_parts=None,
                stuck_note=None,
                resume_note="keep place",
                version=2,
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()

    def old_data_snapshot():
        tables = (
            "users",
            "learning_sessions",
            "session_reflections",
            "problems",
            "problem_attempts",
        )
        snapshot = {}
        with engine.connect() as conn:
            for table in tables:
                schema = conn.exec_driver_sql(f'PRAGMA table_info("{table}")').all()
                rows = conn.exec_driver_sql(f'SELECT * FROM "{table}" ORDER BY rowid').all()
                snapshot[table] = {"schema": schema, "data": rows}
        encoded = json.dumps(snapshot, ensure_ascii=False, default=str, sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()

    old_hash = old_data_snapshot()
    # Scoped to this test's own migration: the snapshot hashes the schema as
    # well as the rows, so upgrading to head would also fold in later,
    # unrelated migrations and stop asserting anything about 0009 -> 0010.
    command.upgrade(config, "0010")
    with engine.connect() as conn:
        assert old_data_snapshot() == old_hash
        assert conn.execute(text("SELECT count(*) FROM problem_comparisons")).scalar_one() == 0
        assert conn.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    command.downgrade(config, "0009")
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT username FROM users WHERE id='QA_TEST_owner'")).scalar_one()
            == "QA_TEST_owner"
        )
