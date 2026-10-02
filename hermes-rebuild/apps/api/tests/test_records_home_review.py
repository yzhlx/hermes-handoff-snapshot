from datetime import UTC, date, datetime
from types import SimpleNamespace

from hermes_api.records_service import RecordsService


def _facts(sessions, attempts, history, problem):
    return {
        "sessions": sessions,
        "reflections": {},
        "attempts": attempts,
        "subjects": {},
        "problems": {problem.id: problem},
        "errors": {},
        "history_attempts": history,
        "problem_points": {},
        "history_points": {},
        "knowledge_points": {},
    }


def _session(session_id, day, now):
    return SimpleNamespace(
        id=session_id,
        version=1,
        goal=None,
        subject_id=None,
        status="ended",
        learning_date=day.isoformat(),
        day_timezone="UTC",
        started_at=now,
        ended_at=now,
        resume_note=None,
        knowledge_point_id=None,
    )


def _attempt(attempt_id, session_id, at, result, check="checked", independence="hinted"):
    return SimpleNamespace(
        id=attempt_id,
        session_id=session_id,
        problem_id="problem-1",
        version=1,
        answer_check=check,
        independence=independence,
        result=result,
        occurred_at=at,
        stuck_note=None,
    )


def test_old_correction_clears_old_error_without_becoming_a_later_day_change():
    now = datetime(2026, 10, 3, 10, tzinfo=UTC)
    old_error = _attempt("old-error", "s1", datetime(2026, 10, 1, 8, tzinfo=UTC), "incorrect")
    historical_correct = _attempt(
        "old-correct",
        "s2",
        datetime(2026, 10, 2, 8, tzinfo=UTC),
        "correct",
        independence="independent",
    )
    today_pending = _attempt("pending-today", "s3", now, None, check="pending")

    class Repo:
        def collect(self, owner, start, end, subject):
            return _facts(
                [_session("s3", date(2026, 10, 3), now)],
                [today_pending],
                [old_error, historical_correct, today_pending],
                SimpleNamespace(
                    id="problem-1", version=1, title="QA_TEST题目", statement=None, updated_at=now
                ),
            )

    result = RecordsService(SimpleNamespace(records=Repo()), clock=lambda: now).day_summary(
        "owner-1", "UTC", date(2026, 10, 3)
    )
    assert result["changes"] == []


def test_home_seven_day_projection_collects_once_and_counts_distinct_effective_days():
    now = datetime(2026, 10, 3, 10, tzinfo=UTC)
    sessions = [
        _session("s1", date(2026, 9, 28), now),
        _session("s2", date(2026, 9, 28), now),
        _session("s3", date(2026, 10, 1), now),
        _session("s4", date(2026, 10, 2), now),
    ]
    reflection = SimpleNamespace(
        id="reflection-1",
        session_id="s1",
        version=1,
        summary="真实反馈",
        recalled_text=None,
        missing_parts=None,
        stuck_note=None,
        updated_at=now,
    )
    from hermes_api.records_domain import RecordFacts

    class Repo:
        calls = 0

        def collect(self, owner, start, end, subject):
            self.calls += 1
            return RecordFacts(
                sessions=sessions,
                reflections={"s1": reflection},
                attempts=[],
                subjects={},
                problems={},
                errors={},
                history_attempts=[],
                problem_points={},
                history_points={},
                knowledge_points={},
            )

    repo = Repo()
    service = RecordsService(SimpleNamespace(records=repo), clock=lambda: now)
    result = service.changes_range("owner-1", "UTC", date(2026, 9, 27), date(2026, 10, 3))
    assert repo.calls == 1
    assert result["from_date"] == date(2026, 9, 27)
    assert result["to_date"] == date(2026, 10, 3)
    assert result["effective_learning_days"] == 1
    assert result["items"] == []
