from datetime import UTC, datetime
from types import SimpleNamespace

from hermes_api.records_domain import counts, effective
from hermes_api.records_service import RecordsService


def test_timer_goal_and_resume_alone_are_not_effective_but_attempt_is():
    assert not effective(None, [])
    assert not effective(
        SimpleNamespace(
            summary=" ",
            recalled_text=None,
            missing_parts=None,
            stuck_note=None,
            resume_note="later",
        ),
        [],
    )
    assert effective(None, [SimpleNamespace()])


def test_only_checked_independent_correct_contributes_independent_correct_count():
    attempts = [
        SimpleNamespace(answer_check="pending", result=None, independence="independent"),
        SimpleNamespace(answer_check="checked", result="correct", independence="hinted"),
        SimpleNamespace(answer_check="checked", result="correct", independence="independent"),
    ]
    assert counts(attempts) == (3, 1, 2, 1)


def test_empty_day_is_honest_and_account_today_uses_timezone():
    class Repo:
        def collect(self, owner, start, end, subject):
            return {
                "sessions": [],
                "reflections": {},
                "attempts": [],
                "subjects": {},
                "problems": {},
                "errors": {},
                "range_start": None,
                "range_end": None,
            }

    service = RecordsService(
        SimpleNamespace(records=Repo()), clock=lambda: datetime(2026, 10, 1, 16, tzinfo=UTC)
    )
    summary = service.day_summary("alice", "Asia/Shanghai")
    assert summary["date"].isoformat() == "2026-10-02"
    assert summary["session_count"] == summary["effective_record_count"] == 0
    assert not summary["learned"] and not summary["changes"] and not summary["source_refs"]
    page = service.list_records("alice", "Asia/Shanghai")
    assert page["from_date"].isoformat() == "2026-09-26"
    assert page["to_date"].isoformat() == "2026-10-02"


def test_source_revision_tracks_fact_version_changes():
    class Repo:
        version = 1

        def collect(self, owner, start, end, subject):
            session = SimpleNamespace(
                id="session-1",
                version=self.version,
                goal="QA_TEST",
                subject_id=None,
                status="ended",
                learning_date=start,
                day_timezone="UTC",
                started_at=datetime(2026, 10, 1, tzinfo=UTC),
                ended_at=None,
                resume_note=None,
            )
            return {
                "sessions": [session],
                "reflections": {},
                "attempts": [],
                "subjects": {},
                "problems": {},
                "errors": {},
            }

    repo = Repo()
    service = RecordsService(
        SimpleNamespace(records=repo), clock=lambda: datetime(2026, 10, 1, tzinfo=UTC)
    )
    fixed_day = datetime(2026, 10, 1, tzinfo=UTC).date()
    first = service.day_summary("alice", "UTC", fixed_day)
    repo.version = 2
    second = service.day_summary("alice", "UTC", fixed_day)
    assert first["source_revision"] != second["source_revision"]
    assert first["effective_record_count"] == 0  # Session goal alone is not learning evidence.


def test_day_summary_reports_cross_day_error_followed_by_independent_correct():
    now = datetime(2026, 10, 2, 9, tzinfo=UTC)
    earlier = SimpleNamespace(
        id="attempt-old",
        session_id="session-old",
        problem_id="problem-1",
        version=1,
        answer_check="checked",
        independence="hinted",
        result="incorrect",
        occurred_at=datetime(2026, 10, 1, 9, tzinfo=UTC),
        stuck_note=None,
    )
    current = SimpleNamespace(
        id="attempt-today",
        session_id="session-today",
        problem_id="problem-1",
        version=1,
        answer_check="checked",
        independence="independent",
        result="correct",
        occurred_at=now,
        stuck_note=None,
    )
    session = SimpleNamespace(
        id="session-today",
        version=1,
        goal="QA_TEST",
        subject_id=None,
        status="ended",
        learning_date="2026-10-02",
        day_timezone="UTC",
        started_at=now,
        ended_at=now,
        resume_note=None,
        knowledge_point_id=None,
    )
    problem = SimpleNamespace(
        id="problem-1", version=1, title="QA_TEST_题目", statement=None, updated_at=now
    )

    class Repo:
        def collect(self, owner, start, end, subject):
            return {
                "sessions": [session],
                "reflections": {},
                "attempts": [current],
                "history_attempts": [earlier, current],
                "subjects": {},
                "problems": {problem.id: problem},
                "errors": {},
                "problem_points": {},
                "history_points": {},
                "knowledge_points": {},
            }

    service = RecordsService(SimpleNamespace(records=Repo()), clock=lambda: now)
    result = service.day_summary("alice", "UTC", now.date())
    assert len(result["changes"]) == 1
    assert [ref["id"] for ref in result["changes"][0]["source_refs"]] == [
        "attempt-old",
        "attempt-today",
    ]


def test_day_summary_reports_three_recent_independent_correct_on_same_point():
    now = datetime(2026, 10, 2, 9, tzinfo=UTC)
    attempts = [
        SimpleNamespace(
            id=f"attempt-{i}",
            session_id=f"session-{i}",
            problem_id=f"problem-{i}",
            version=1,
            answer_check="checked",
            independence="independent",
            result="correct",
            occurred_at=datetime(2026, 10, 2, 7 + i, tzinfo=UTC),
            stuck_note=None,
        )
        for i in range(3)
    ]
    session = SimpleNamespace(
        id="session-2",
        version=1,
        goal="QA_TEST",
        subject_id=None,
        status="ended",
        learning_date="2026-10-02",
        day_timezone="UTC",
        started_at=now,
        ended_at=now,
        resume_note=None,
        knowledge_point_id=None,
    )
    problems = {
        f"problem-{i}": SimpleNamespace(
            id=f"problem-{i}",
            version=1,
            title=f"QA_TEST_problem_{i}",
            statement=None,
            updated_at=now,
        )
        for i in range(3)
    }

    class Repo:
        def collect(self, owner, start, end, subject):
            return {
                "sessions": [session],
                "reflections": {},
                "attempts": [attempts[-1]],
                "history_attempts": attempts,
                "subjects": {},
                "problems": problems,
                "errors": {},
                "problem_points": {"problem-2": ["point-1"]},
                "history_points": {f"problem-{i}": ["point-1"] for i in range(3)},
                "knowledge_points": {
                    "point-1": SimpleNamespace(
                        id="point-1", version=2, name="QA_TEST_知识点", updated_at=now
                    )
                },
            }

    result = RecordsService(SimpleNamespace(records=Repo()), clock=lambda: now).day_summary(
        "alice", "UTC", now.date()
    )
    point_change = next(
        item for item in result["changes"] if item["source_refs"][0]["kind"] == "knowledge_point"
    )
    assert len(point_change["source_refs"]) == 4
