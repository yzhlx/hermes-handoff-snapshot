import pytest
from pydantic import ValidationError

from hermes_api.feedback import AttemptFeedback, ErrorCategory, Independence, ReflectionFeedback


@pytest.mark.parametrize("independence", list(Independence))
@pytest.mark.parametrize("result", [None, "correct", "partial", "incorrect"])
def test_unchecked_never_claims_result(independence, result):
    values = {"independence": independence, "answer_check": "pending", "result": result}
    if result is None:
        assert not AttemptFeedback(**values).independently_correct
    else:
        with pytest.raises(ValidationError):
            AttemptFeedback(**values)


@pytest.mark.parametrize("independence", list(Independence))
@pytest.mark.parametrize("result", ["correct", "partial", "incorrect"])
def test_only_checked_independent_correct_is_evidence(independence, result):
    value = AttemptFeedback(independence=independence, answer_check="checked", result=result)
    assert value.independently_correct == (independence == "independent" and result == "correct")


def test_checked_requires_result_and_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        AttemptFeedback(independence="independent", answer_check="checked")
    with pytest.raises(ValidationError):
        AttemptFeedback(independence="independent", answer_check="pending", mastery="stable")


@pytest.mark.parametrize("category", list(ErrorCategory))
def test_ten_categories_and_unique_counts(category):
    values = {"independence": "hinted", "answer_check": "checked", "result": "incorrect"}
    assert AttemptFeedback(**values, error_categories=[category]).error_categories == [category]
    with pytest.raises(ValidationError):
        AttemptFeedback(**values, error_categories=[category, category])


def test_pending_error_draft_is_not_confirmed_correctness():
    value = AttemptFeedback(
        independence="unable", answer_check="pending", error_categories=["concept"]
    )
    assert value.result is None and not value.independently_correct


def test_correct_result_does_not_fabricate_errors():
    with pytest.raises(ValidationError):
        AttemptFeedback(
            independence="independent",
            answer_check="checked",
            result="correct",
            error_categories=["concept"],
        )


def test_other_note_and_unicode_are_preserved():
    values = {"independence": "hinted", "answer_check": "checked", "result": "partial"}
    with pytest.raises(ValidationError):
        AttemptFeedback(**values, other_error_note="QA_TEST_未分类")
    value = AttemptFeedback(
        **values,
        error_categories=["other"],
        other_error_note="QA_TEST_方向",
        stuck_note="QA_TEST_ω 与正负方向不一致",
    )
    assert value.stuck_note == "QA_TEST_ω 与正负方向不一致"


def test_optional_reflection_distinguishes_actual_content_from_timer_or_future_plan():
    assert not ReflectionFeedback().has_learning_evidence
    assert not ReflectionFeedback(resume_note="QA_TEST_明天第三题").has_learning_evidence
    assert not ReflectionFeedback(summary="  ", reference_checked=True).has_learning_evidence
    assert ReflectionFeedback(summary="QA_TEST_尝试推导采样公式").has_learning_evidence
    assert ReflectionFeedback(recalled_text="QA_TEST_能复述采样条件").has_learning_evidence
