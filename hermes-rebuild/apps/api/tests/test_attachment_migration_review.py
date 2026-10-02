"""Regression coverage for upgrading a populated 0006 database through 0007."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy.exc import IntegrityError

from hermes_api import (  # noqa: F401
    attachment_storage,
    evidence_storage,
    knowledge_storage,
    quotes_storage,
)
from hermes_api.storage import Base, make_engine


def _config(tmp_path, monkeypatch, name):
    url = f"sqlite:///{tmp_path / name}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    return url, Config(str(Path(__file__).parents[1] / "alembic.ini"))


def _populate_0006(engine):
    stamp = "2026-09-30 08:12:13"
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO users (id, username, password_hash, timezone) "
                "VALUES ('legacy', 'QA_TEST_legacy', 'unused', 'Asia/Shanghai')"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO subjects (id, owner_id, name) "
                "VALUES ('subject', 'legacy', 'QA_TEST_subject')"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO chapters (id, owner_id, subject_id, name, order_index, version, created_at, updated_at) "
                "VALUES ('chapter', 'legacy', 'subject', 'QA_TEST_chapter', 4, 6, :stamp, :stamp)"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO knowledge_points (id, owner_id, chapter_id, subject_id, name, notes, version, created_at, updated_at) "
                "VALUES ('point', 'legacy', 'chapter', 'subject', 'QA_TEST_point', 'QA_TEST_notes', 8, :stamp, :stamp)"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO learning_sessions (id, owner_id, subject_id, status, version, started_at, "
                "ended_at, day_timezone, learning_date, timing_enabled, kind, knowledge_point_id) "
                "VALUES ('session', 'legacy', 'subject', 'ended', 7, :stamp, :stamp, 'Asia/Shanghai', "
                "'2026-09-30', 1, 'problem', 'point')"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO session_time_segments (id, owner_id, session_id, started_at, ended_at) "
                "VALUES ('segment', 'legacy', 'session', :stamp, :stamp)"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO problems (id, owner_id, subject_id, title, statement, source_note, "
                "correct_answer, is_representative, archived_at, version, created_at, updated_at) "
                "VALUES ('problem', 'legacy', 'subject', 'QA_TEST_title', 'QA_TEST_statement', "
                "'QA_TEST_source', 'QA_TEST_answer', 1, NULL, 9, :stamp, :stamp)"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO problem_attempts (id, owner_id, session_id, problem_id, independence, "
                "answer_check, result, attempt_text, stuck_note, occurred_at, verified_at, version, "
                "created_at, updated_at) VALUES ('attempt', 'legacy', 'session', 'problem', "
                "'independent', 'checked', 'correct', 'QA_TEST_attempt', 'QA_TEST_stuck', :stamp, "
                ":stamp, 4, :stamp, :stamp)"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO session_reflections (id, owner_id, session_id, summary, recalled_text, "
                "reference_checked, missing_parts, stuck_note, resume_note, version, created_at, updated_at) "
                "VALUES ('reflection', 'legacy', 'session', 'QA_TEST_summary', 'QA_TEST_recall', 1, "
                "'QA_TEST_missing', 'QA_TEST_stuck', 'QA_TEST_resume', 3, :stamp, :stamp)"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO problem_knowledge_links (owner_id, problem_id, knowledge_point_id, created_at) "
                "VALUES ('legacy', 'problem', 'point', :stamp)"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO mastery_assessments (id, owner_id, knowledge_point_id, level, reason, "
                "variant_note, version, knowledge_point_version, created_at) VALUES ('assessment', "
                "'legacy', 'point', 'independent', 'QA_TEST_reason', 'QA_TEST_variant', 1, 8, :stamp)"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO mastery_evidence_links (owner_id, assessment_id, attempt_id, problem_id, "
                "attempt_version, problem_version, attempt_snapshot, problem_snapshot) VALUES ('legacy', "
                "'assessment', 'attempt', 'problem', 4, 9, 'attempt snapshot v4', 'problem snapshot v9')"
            )
        )


def _snapshot(conn):
    """The legacy rows, keyed by column.

    Comparing column by column keeps this test's intent - a later migration must
    not change or drop any value that already existed - while allowing an
    additive migration to introduce columns that are simply NULL for these rows.
    A ``SELECT *`` tuple comparison would instead fail on the column count alone.
    """
    tables = {
        "users": "id='legacy'",
        "subjects": "id='subject'",
        "learning_sessions": "id='session'",
        "session_time_segments": "id='segment'",
        "problems": "id='problem'",
        "problem_attempts": "id='attempt'",
        "session_reflections": "id='reflection'",
        "chapters": "id='chapter'",
        "knowledge_points": "id='point'",
        "problem_knowledge_links": "problem_id='problem'",
        "mastery_assessments": "id='assessment'",
        "mastery_evidence_links": "attempt_id='attempt'",
    }
    return {
        table: dict(conn.execute(sa.text(f"SELECT * FROM {table} WHERE {where}")).one()._mapping)
        for table, where in tables.items()
    }


def _assert_rows_preserved(before, after):
    for table, before_values in before.items():
        assert table in after, f"{table} lost its row during the upgrade"
        for column, value in before_values.items():
            assert column in after[table], f"{table}.{column} disappeared during the upgrade"
            assert after[table][column] == value, f"{table}.{column} changed during the upgrade"


def _populate_0007_attachment_rows(engine):
    stamp = "2026-09-30 08:12:13"
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO attachments (id, owner_id, storage_key, original_name, declared_mime, "
                "detected_mime, byte_size, declared_size, sha256, page_count, status, version, "
                "created_at, updated_at, expires_at) VALUES ('file', 'legacy', 'opaque-qa-key', "
                "'QA_TEST_file.png', 'image/png', 'image/png', 32, 32, "
                "'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 1, 'ready', 2, "
                ":stamp, :stamp, :stamp)"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO attachment_jobs (id, owner_id, attachment_id, kind, status, "
                "input_version, page, attempt_count, available_at, locked_at, completed_at, "
                "error_code, result_json, created_at) VALUES ('preview-job', 'legacy', 'file', "
                "'preview', 'queued', 2, 1, 0, :stamp, NULL, NULL, NULL, NULL, :stamp)"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO problem_attachment_links (link_id, owner_id, problem_id, "
                "attachment_id, role, page_start, page_end, created_at) VALUES ('file-link', "
                "'legacy', 'problem', 'file', 'question', NULL, NULL, :stamp)"
            ),
            {"stamp": stamp},
        )


def _attachment_snapshot(conn):
    attachment = tuple(conn.execute(sa.text("SELECT * FROM attachments WHERE id='file'")).one())
    job = tuple(
        conn.execute(
            sa.text(
                "SELECT id, owner_id, attachment_id, kind, status, input_version, page, "
                "attempt_count, available_at, locked_at, completed_at, error_code, result_json, "
                "created_at FROM attachment_jobs WHERE id='preview-job'"
            )
        ).one()
    )
    link = tuple(
        conn.execute(
            sa.text("SELECT * FROM problem_attachment_links WHERE link_id='file-link'")
        ).one()
    )
    return {"attachments": attachment, "attachment_jobs": job, "problem_attachment_links": link}


def test_populated_0006_upgrade_preserves_rows_and_metadata(tmp_path, monkeypatch):
    url, config = _config(tmp_path, monkeypatch, "filled-0006.db")
    command.upgrade(config, "0006")
    engine = make_engine(url)
    _populate_0006(engine)
    with engine.connect() as conn:
        before = _snapshot(conn)

    command.upgrade(config, "head")
    with engine.connect() as conn:
        _assert_rows_preserved(before, _snapshot(conn))
        assert conn.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        problem_sql = conn.execute(
            sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='problems'")
        ).scalar_one()
        assert "ck_problem_has_text" not in problem_sql

        # Every schema difference from the current model is expected to be the one
        # deliberately removed database check for the new attachment-backed flow.
        context = MigrationContext.configure(conn, opts={"compare_server_default": False})
        diffs = compare_metadata(context, Base.metadata)
        unexpected = [
            diff
            for diff in diffs
            if not (
                isinstance(diff, tuple)
                and diff[0] == "add_constraint"
                and getattr(diff[1], "name", None) == "ck_problem_has_text"
            )
        ]
        assert unexpected == []
        # SQLite's stock Alembic comparator ignores CHECK constraints, so we
        # also verified the exact known check difference directly above.


def test_downgrade_restores_text_guard_and_preserves_text_problem(tmp_path, monkeypatch):
    url, config = _config(tmp_path, monkeypatch, "downgrade-0007.db")
    command.upgrade(config, "0006")
    engine = make_engine(url)
    _populate_0006(engine)
    command.upgrade(config, "0007")
    command.downgrade(config, "0006")
    with engine.connect() as conn:
        assert conn.execute(
            sa.text("SELECT statement, version FROM problems WHERE id='problem'")
        ).one() == ("QA_TEST_statement", 9)
        problem_sql = conn.execute(
            sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='problems'")
        ).scalar_one()
        assert "ck_problem_has_text" in problem_sql

    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO problems (id, owner_id, statement, version, created_at, updated_at) "
                "VALUES ('textless', 'legacy', NULL, 1, '2026-09-30', '2026-09-30')"
            )
        )


def test_downgrade_refuses_to_drop_question_needed_by_textless_problem(tmp_path, monkeypatch):
    url, config = _config(tmp_path, monkeypatch, "downgrade-guard-0007.db")
    command.upgrade(config, "0006")
    engine = make_engine(url)
    _populate_0006(engine)
    command.upgrade(config, "0007")
    stamp = "2026-09-30 08:12:13"
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO problems (id, owner_id, subject_id, statement, version, created_at, updated_at) "
                "VALUES ('textless', 'legacy', 'subject', NULL, 1, :stamp, :stamp)"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO attachments (id, owner_id, storage_key, original_name, declared_mime, "
                "detected_mime, byte_size, declared_size, sha256, page_count, status, version, created_at, updated_at, expires_at) "
                "VALUES ('attachment', 'legacy', 'private/test-key', 'QA_TEST.png', 'image/png', 'image/png', "
                "12, 12, 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 1, 'ready', 1, :stamp, :stamp, :stamp)"
            ),
            {"stamp": stamp},
        )
        conn.execute(
            sa.text(
                "INSERT INTO problem_attachment_links (link_id, owner_id, problem_id, attachment_id, role, created_at) "
                "VALUES ('link', 'legacy', 'textless', 'attachment', 'question', :stamp)"
            ),
            {"stamp": stamp},
        )

    with pytest.raises(RuntimeError, match="textless question depends"):
        command.downgrade(config, "0006")
    with engine.connect() as conn:
        assert (
            conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == "0007"
        )
        assert (
            conn.execute(
                sa.text("SELECT count(*) FROM problem_attachment_links WHERE link_id='link'")
            ).scalar_one()
            == 1
        )
        problem_sql = conn.execute(
            sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='problems'")
        ).scalar_one()
        assert "ck_problem_has_text" not in problem_sql


def test_populated_0007_attachment_rows_survive_0008_upgrade_and_safe_downgrade(
    tmp_path, monkeypatch
):
    url, config = _config(tmp_path, monkeypatch, "populated-0007-0008.db")
    command.upgrade(config, "0006")
    engine = make_engine(url)
    _populate_0006(engine)
    command.upgrade(config, "0007")
    _populate_0007_attachment_rows(engine)
    with engine.connect() as conn:
        before = _attachment_snapshot(conn)

    command.upgrade(config, "0008")
    with engine.connect() as conn:
        assert _attachment_snapshot(conn) == before
        job_columns = {
            column["name"]: column for column in sa.inspect(conn).get_columns("attachment_jobs")
        }
        assert "lease_token" in job_columns and job_columns["lease_token"]["nullable"] is True
        assert (
            conn.execute(
                sa.text("SELECT lease_token FROM attachment_jobs WHERE id='preview-job'")
            ).scalar_one()
            is None
        )
        assert (
            conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == "0008"
        )
        assert conn.exec_driver_sql("PRAGMA foreign_key_check").all() == []

    # ORM metadata describes the current head, not the historical 0008 schema.
    # Verify the head too, then return to 0008 to exercise the lease-only rollback.
    command.upgrade(config, "head")
    with engine.connect() as conn:
        context = MigrationContext.configure(conn, opts={"compare_server_default": False})
        assert compare_metadata(context, Base.metadata) == []
        assert _attachment_snapshot(conn) == before
    command.downgrade(config, "0008")
    # A queued job carries no active lease, so rolling back the nullable token is safe.
    command.downgrade(config, "0007")
    with engine.connect() as conn:
        assert _attachment_snapshot(conn) == before
        job_columns = {column["name"] for column in sa.inspect(conn).get_columns("attachment_jobs")}
        assert "lease_token" not in job_columns
        assert (
            conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == "0007"
        )
        assert conn.exec_driver_sql("PRAGMA foreign_key_check").all() == []
