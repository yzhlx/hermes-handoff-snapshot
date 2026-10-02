from hermes_api.evidence_domain import (
    ERROR_CATEGORIES,
    RULE_VERSION,
    EvidenceRuleError,
    assessment_status,
    derive_counts,
    source_revision,
    validate_assessment,
)


def _attempt(
    attempt_id,
    *,
    checked="checked",
    result="correct",
    independence="independent",
    version=1,
    categories=(),
):
    return {
        "id": attempt_id,
        "version": version,
        "problem_id": f"problem-{attempt_id}",
        "problem_version": 1,
        "independence": independence,
        "answer_check": checked,
        "result": result,
        "occurred_at": f"2026-09-30T10:00:0{attempt_id[-1]}+00:00",
        "error_categories": list(categories),
    }


def test_empty_sources_have_null_rate_and_ten_zero_categories():
    value = derive_counts([])
    assert value["attempt_count"] == value["checked_count"] == 0
    assert value["checked_correct_rate"] is None
    assert value["recent_checked_streak"]["count"] == 0
    assert value["recent_checked_streak"]["pending_count"] == 0
    assert len(value["error_categories"]) == 10
    assert {row["category"] for row in value["error_categories"]} == set(ERROR_CATEGORIES)


def test_counts_only_checked_for_correct_rate_deduplicates_category_attempts_and_reports_pending():
    pending = _attempt("attempt-1", checked="pending", result=None, categories=("sign",))
    incorrect = _attempt("attempt-2", result="incorrect", categories=("sign", "sign", "reading"))
    correct = _attempt("attempt-3", categories=("sign",))
    value = derive_counts([pending, incorrect, correct])
    assert value["attempt_count"] == 3
    assert value["pending_count"] == 1
    assert value["checked_count"] == 2
    assert value["checked_correct_count"] == 1
    assert value["checked_correct_rate"] == 0.5
    assert value["independent_correct_count"] == 1
    assert value["recent_checked_streak"]["label"] == "最近 1 个已核对记录"
    assert value["recent_checked_streak"]["pending_count"] == 1
    sign = next(row for row in value["error_categories"] if row["category"] == "sign")
    assert sign["attempt_count"] == 2
    assert len(sign["source_refs"]) == 2


def test_hint_or_incorrect_checked_result_breaks_recent_checked_sequence():
    newest = _attempt("attempt-3")
    hinted = _attempt("attempt-2", independence="hinted")
    older = _attempt("attempt-1")
    value = derive_counts([older, hinted, newest])
    assert value["recent_checked_streak"]["count"] == 1
    assert value["independent_correct_count"] == 2


def test_levels_allow_no_evidence_but_qualifying_levels_reject_false_evidence():
    validate_assessment("variant_stable", None, [])
    wrong = _attempt("attempt-1", result="partial")
    try:
        validate_assessment("independent", None, [wrong])
    except EvidenceRuleError:
        pass
    else:
        raise AssertionError("independent claims must require independent correct evidence")
    correct = _attempt("attempt-1")
    try:
        validate_assessment("variant_stable", "  ", [correct])
    except EvidenceRuleError:
        pass
    else:
        raise AssertionError("linked variant-stable evidence requires a user variant note")


def test_snapshot_status_changes_when_source_versions_or_current_link_changes():
    link = {
        "level": "independent",
        "attempt_version": 1,
        "problem_version": 2,
        "current_attempt_version": 1,
        "current_problem_version": 2,
        "currently_linked": True,
        "current_answer_check": "checked",
        "current_independence": "independent",
        "current_result": "correct",
    }
    assert assessment_status([link]) == "current"
    changed = {**link, "current_attempt_version": 2}
    assert assessment_status([changed]) == "stale"
    unlinked = {**link, "currently_linked": False}
    assert assessment_status([unlinked]) == "stale"


def test_source_revision_is_deterministic_and_changes_with_version():
    refs = [{"attempt_id": "a", "attempt_version": 1, "problem_id": "p", "problem_version": 1}]
    assert source_revision(refs) == source_revision(refs)
    assert source_revision(refs) != source_revision([{**refs[0], "attempt_version": 2}])
    assert RULE_VERSION == "mastery-evidence-v1"
