"""Use cases for factual record pages and daily summaries."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .domain import PolicyError
from .records_domain import RULE_VERSION, counts, effective, revision
from .records_ports import RecordsUnitOfWork


class RecordsService:
    uow: RecordsUnitOfWork

    def __init__(self, uow: RecordsUnitOfWork, clock=lambda: datetime.now(UTC)):
        self.uow, self.clock = uow, clock

    def _collect(self, owner, start, end, subject_id=None):
        facts = self.uow.records.collect(owner, start.isoformat(), end.isoformat(), subject_id)
        attempt_by_session = {}
        refs = []
        for s in facts["sessions"]:
            refs.append({"kind": "session", "id": s.id, "version": s.version})
        for reflection in facts["reflections"].values():
            refs.append({"kind": "reflection", "id": reflection.id, "version": reflection.version})
        for attempt in facts["attempts"]:
            attempt_by_session.setdefault(attempt.session_id, []).append(attempt)
            refs.append({"kind": "attempt", "id": attempt.id, "version": attempt.version})
        selected_attempt_ids = {attempt.id for attempt in facts["attempts"]}
        for attempt in facts.get("history_attempts", []):
            if attempt.id not in selected_attempt_ids:
                refs.append({"kind": "attempt", "id": attempt.id, "version": attempt.version})
        for point_ids in facts.get("history_points", {}).values():
            for point_id in point_ids:
                point = facts.get("knowledge_points", {}).get(point_id)
                if point:
                    refs.append(
                        {"kind": "knowledge_point", "id": point.id, "version": point.version}
                    )
        records = []
        for s in facts["sessions"]:
            reflection = facts["reflections"].get(s.id)
            attempts = attempt_by_session.get(s.id, [])
            n, pending, checked, independent = counts(attempts)
            is_effective = effective(reflection, attempts)
            source_refs = [
                {
                    "kind": "session",
                    "id": s.id,
                    "version": s.version,
                    "label": (s.goal or "学习记录")[:120],
                    "occurred_at": s.started_at,
                    "session_id": s.id,
                }
            ]
            if reflection:
                source_refs.append(
                    {
                        "kind": "reflection",
                        "id": reflection.id,
                        "version": reflection.version,
                        "label": "学习反馈",
                        "occurred_at": reflection.updated_at,
                        "session_id": s.id,
                    }
                )
            for a in attempts:
                problem = facts["problems"].get(a.problem_id)
                if problem:
                    refs.append({"kind": "problem", "id": problem.id, "version": problem.version})
                    source_refs.append(
                        {
                            "kind": "problem",
                            "id": problem.id,
                            "version": problem.version,
                            "label": (problem.title or problem.statement or "题目")[:120],
                            "occurred_at": problem.updated_at,
                            "session_id": s.id,
                            "problem_id": problem.id,
                        }
                    )
                for point_id in facts.get("problem_points", {}).get(a.problem_id, []):
                    point = facts.get("knowledge_points", {}).get(point_id)
                    if point:
                        refs.append(
                            {"kind": "knowledge_point", "id": point.id, "version": point.version}
                        )
                        source_refs.append(
                            {
                                "kind": "knowledge_point",
                                "id": point.id,
                                "version": point.version,
                                "label": point.name,
                                "occurred_at": point.updated_at,
                                "session_id": s.id,
                                "problem_id": a.problem_id,
                            }
                        )
                source_refs.append(
                    {
                        "kind": "attempt",
                        "id": a.id,
                        "version": a.version,
                        "label": (
                            (problem.title or problem.statement or "题目")[:120]
                            if problem
                            else "题目练习"
                        ),
                        "occurred_at": a.occurred_at,
                        "session_id": s.id,
                        "problem_id": a.problem_id,
                    }
                )
            records.append(
                {
                    "id": s.id,
                    "version": s.version,
                    "goal": s.goal,
                    "subject_id": s.subject_id,
                    "subject_name": facts["subjects"].get(s.subject_id),
                    "status": s.status,
                    "learning_date": s.learning_date,
                    "day_timezone": s.day_timezone,
                    "started_at": s.started_at,
                    "ended_at": s.ended_at,
                    "resume_note": s.resume_note,
                    "summary": reflection.summary if reflection else None,
                    "recalled_text": reflection.recalled_text if reflection else None,
                    "missing_parts": reflection.missing_parts if reflection else None,
                    "stuck_note": reflection.stuck_note if reflection else None,
                    "attempt_count": n,
                    "pending_count": pending,
                    "checked_count": checked,
                    "independent_correct_count": independent,
                    "effective": is_effective,
                    "source_refs": source_refs,
                    "_attempts": attempts,
                    "_reflection": reflection,
                }
            )
        ref_key = sorted(refs, key=lambda x: (x["kind"], x["id"], x["version"]))
        return facts, records, revision(ref_key)

    def list_records(
        self, owner, timezone, from_date=None, to_date=None, subject_id=None, limit=50, cursor=None
    ):
        try:
            today = self.clock().astimezone(ZoneInfo(timezone)).date()
        except (ZoneInfoNotFoundError, ValueError):
            raise PolicyError("VALIDATION_ERROR", "Account timezone is invalid.", 422) from None
        end = to_date or today
        start = from_date or end - timedelta(days=6)
        if start > end or (end - start).days >= 366:
            raise PolicyError("VALIDATION_ERROR", "Date range must cover at most 366 days.", 422)
        _, records, src_revision = self._collect(owner, start, end, subject_id)
        totals = {
            "session_count": len(records),
            "effective_record_count": sum(r["effective"] for r in records),
            "pending_count": sum(r["pending_count"] for r in records),
            "checked_count": sum(r["checked_count"] for r in records),
            "independent_correct_count": sum(r["independent_correct_count"] for r in records),
        }
        if cursor:
            ids = [r["id"] for r in records]
            if cursor not in ids:
                raise PolicyError("VALIDATION_ERROR", "Records cursor is invalid.", 422)
            records = records[ids.index(cursor) + 1 :]
        selected = records[:limit]
        has_more = len(records) > limit
        for row in selected:
            row.pop("_attempts")
            row.pop("_reflection")
        return {
            "items": selected,
            "next_cursor": selected[-1]["id"] if has_more else None,
            "from_date": start,
            "to_date": end,
            "timezone": timezone,
            "rule_version": RULE_VERSION,
            "source_revision": src_revision,
            "totals": totals,
        }

    def day_summary(self, owner, timezone, day=None):
        try:
            target = day or self.clock().astimezone(ZoneInfo(timezone)).date()
        except (ZoneInfoNotFoundError, ValueError):
            raise PolicyError("VALIDATION_ERROR", "Account timezone is invalid.", 422) from None
        facts, rows, src_revision = self._collect(owner, target, target)
        attempts = [a for r in rows for a in r["_attempts"]]
        all_refs = [ref for row in rows if row["effective"] for ref in row["source_refs"]]
        learned, stuck, categories, review = [], [], {}, []
        attempts_by_problem = {}
        attempts_by_point = {}
        day_attempt_refs = {
            ref["id"]: ref for row in rows for ref in row["source_refs"] if ref["kind"] == "attempt"
        }
        for attempt in facts.get("history_attempts", []):
            problem = facts["problems"].get(attempt.problem_id)
            aref = day_attempt_refs.get(attempt.id) or {
                "kind": "attempt",
                "id": attempt.id,
                "version": attempt.version,
                "label": (
                    (problem.title or problem.statement or "题目")[:120] if problem else "题目练习"
                ),
                "occurred_at": attempt.occurred_at,
                "session_id": attempt.session_id,
                "problem_id": attempt.problem_id,
            }
            attempts_by_problem.setdefault(attempt.problem_id, []).append((attempt, aref))
            for point_id in facts.get("history_points", {}).get(attempt.problem_id, []):
                attempts_by_point.setdefault(point_id, []).append((attempt, aref))
        for row in rows:
            ref = row["source_refs"]
            reflection = row["_reflection"]
            if reflection:
                for key in ("summary", "recalled_text"):
                    value = (getattr(reflection, key) or "").strip()
                    if value:
                        learned.append({"text": value, "source_refs": ref[:2]})
                value = (reflection.stuck_note or reflection.missing_parts or "").strip()
                if value:
                    stuck.append({"text": value, "source_refs": ref[:2]})
            for a in row["_attempts"]:
                aref = next((x for x in ref if x["kind"] == "attempt" and x["id"] == a.id), ref[:1])
                if a.stuck_note and a.stuck_note.strip():
                    stuck.append({"text": a.stuck_note.strip(), "source_refs": [aref]})
                if a.answer_check == "checked":
                    for cat in facts["errors"].get(a.id, []):
                        categories.setdefault(cat, []).append(aref)
        latest_today = {}
        for row in rows:
            for attempt in row["_attempts"]:
                current = latest_today.get(attempt.problem_id)
                if current is None or (attempt.occurred_at, attempt.id) > (
                    current.occurred_at,
                    current.id,
                ):
                    latest_today[attempt.problem_id] = attempt
        for problem_id, attempt in latest_today.items():
            if attempt.answer_check == "checked" and attempt.result in (
                "incorrect",
                "partial",
                "correct",
            ):
                problem = facts["problems"].get(problem_id)
                title = (problem.title or problem.statement or "题目") if problem else "题目练习"
                aref = day_attempt_refs.get(attempt.id)
                if aref:
                    if attempt.result in ("incorrect", "partial"):
                        text = f"可在7天后回顾：{title[:100]}"
                    elif attempt.independence == "independent":
                        text = f"可在14天后再练习：{title[:100]}"
                    else:
                        continue
                    review.append({"text": text, "source_refs": [aref]})
        changes = self._change_projection(
            facts, attempts_by_problem, attempts_by_point, day_attempt_refs
        )
        _, pending, checked, independent = counts(attempts)
        return {
            "date": target,
            "timezone": timezone,
            "rule_version": RULE_VERSION,
            "source_revision": src_revision,
            "session_count": len(rows),
            "effective_record_count": sum(r["effective"] for r in rows),
            "pending_count": pending,
            "checked_count": checked,
            "independent_correct_count": independent,
            "learned": learned,
            "changes": changes,
            "stuck_points": stuck,
            "error_categories": [
                {"category": k, "count": len(v), "source_refs": v}
                for k, v in sorted(categories.items())
            ],
            "review_candidates": review,
            "source_refs": all_refs,
        }

    def _change_projection(self, facts, attempts_by_problem, attempts_by_point, range_attempt_refs):
        """Project learning changes whose qualifying evidence falls in the requested range."""
        changes = []
        for problem_id, sequence in attempts_by_problem.items():
            sequence.sort(
                key=lambda pair: (
                    pair[0].occurred_at.replace(tzinfo=UTC)
                    if pair[0].occurred_at.tzinfo is None
                    else pair[0].occurred_at,
                    pair[0].id,
                )
            )
            earlier_errors = []
            for attempt, aref in sequence:
                if attempt.answer_check != "checked":
                    continue
                if attempt.result in ("incorrect", "partial"):
                    earlier_errors.append(aref)
                elif (
                    attempt.result == "correct"
                    and attempt.independence == "independent"
                    and earlier_errors
                ):
                    # Historical corrections clear the pending earlier error, but cannot
                    # be presented as a change in this projection unless the correction
                    # itself belongs to the target date/range.
                    if attempt.id in range_attempt_refs:
                        problem = facts["problems"].get(problem_id)
                        title = (
                            (problem.title or problem.statement or "该题") if problem else "该题"
                        )
                        changes.append(
                            {
                                "text": f"在{title[:80]}上，先前的错误后出现了一次独立正确作答。",
                                "source_refs": [earlier_errors[-1], aref],
                            }
                        )
                    earlier_errors = []
        for point_id, sequence in attempts_by_point.items():
            sequence.sort(
                key=lambda pair: (
                    pair[0].occurred_at.replace(tzinfo=UTC)
                    if pair[0].occurred_at.tzinfo is None
                    else pair[0].occurred_at,
                    pair[0].id,
                )
            )
            checked_sequence = [pair for pair in sequence if pair[0].answer_check == "checked"]
            recent = checked_sequence[-3:]
            if (
                len(recent) == 3
                and any(attempt.id in range_attempt_refs for attempt, _ in recent)
                and all(
                    attempt.result == "correct" and attempt.independence == "independent"
                    for attempt, _ in recent
                )
            ):
                point = facts.get("knowledge_points", {}).get(point_id)
                if point:
                    point_ref = {
                        "kind": "knowledge_point",
                        "id": point.id,
                        "version": point.version,
                        "label": point.name,
                        "occurred_at": point.updated_at,
                    }
                    changes.append(
                        {
                            "text": f"{point.name}最近三个已核对练习均为独立正确作答。",
                            "source_refs": [point_ref, *(ref for _, ref in recent)],
                        }
                    )
        return changes

    def changes_range(self, owner, timezone, from_date, to_date):
        """Return seven-day change evidence using one bounded source-fact collection."""
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise PolicyError("VALIDATION_ERROR", "Account timezone is invalid.", 422) from None
        if from_date > to_date or (to_date - from_date).days >= 366:
            raise PolicyError("VALIDATION_ERROR", "Date range must cover at most 366 days.", 422)
        facts, rows, src_revision = self._collect(owner, from_date, to_date)
        range_attempt_refs = {}
        for row in rows:
            for attempt in row["_attempts"]:
                ref = next(
                    item
                    for item in row["source_refs"]
                    if item["kind"] == "attempt" and item["id"] == attempt.id
                )
                range_attempt_refs[attempt.id] = ref
        attempts_by_problem = {}
        attempts_by_point = {}
        for attempt in facts.get("history_attempts", []):
            problem = facts["problems"].get(attempt.problem_id)
            ref = range_attempt_refs.get(attempt.id) or {
                "kind": "attempt",
                "id": attempt.id,
                "version": attempt.version,
                "label": (
                    (problem.title or problem.statement or "题目")[:120] if problem else "题目练习"
                ),
                "occurred_at": attempt.occurred_at,
                "session_id": attempt.session_id,
                "problem_id": attempt.problem_id,
            }
            attempts_by_problem.setdefault(attempt.problem_id, []).append((attempt, ref))
            for point_id in facts.get("history_points", {}).get(attempt.problem_id, []):
                attempts_by_point.setdefault(point_id, []).append((attempt, ref))
        changes = self._change_projection(
            facts, attempts_by_problem, attempts_by_point, range_attempt_refs
        )
        return {
            "from_date": from_date,
            "to_date": to_date,
            "items": changes,
            "effective_learning_days": len(
                {row["learning_date"] for row in rows if row["effective"]}
            ),
            "rule_version": RULE_VERSION,
            "source_revision": src_revision,
        }

    def record_projection(self, owner, timezone, day, record_id):
        """Read one record from a full-day projection without page-size truncation."""
        _facts, records, src_revision = self._collect(owner, day, day)
        record = next((item for item in records if item["id"] == record_id), None)
        if record is None:
            return None, src_revision
        record.pop("_attempts")
        record.pop("_reflection")
        return record, src_revision
