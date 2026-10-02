"""Pure-rule checks for the optional AI advisor output contract (04)."""

import pytest

from hermes_api.advisor_domain import (
    AdvisorPolicyError,
    build_facts,
    build_missing,
    data_version,
    has_forbidden_language,
    knowledge_point_streaks,
    normalize,
    normalize_refs,
    summarize,
    validate_inferences,
    validate_missing,
)


def record(**overrides):
    base = {
        "id": "a1",
        "version": 1,
        "problem_title": "QA_TEST 左题",
        "independence": "independent",
        "answer_check": "checked",
        "result": "correct",
        "error_categories": [],
        "knowledge_point_ids": [],
        "stuck_note": None,
        "occurred_at": "2026-10-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def test_empty_evidence_never_fabricates_progress():
    evidence = {"records": []}
    assert build_facts(evidence) == []
    assert build_missing(evidence) == ["记录还不足，可以先开始学习。"]
    assert summarize([], [], build_missing(evidence)) == "记录还不足，可以先开始学习。"


def test_facts_count_unchecked_separately_and_never_as_correct():
    evidence = {
        "records": [
            record(id="a1", answer_check="pending", result=None, independence="hinted"),
            record(id="a2", result="partial", error_categories=["sign"], independence="hinted"),
            record(id="a3", error_categories=["sign"]),
        ]
    }
    facts = build_facts(evidence)
    text = " ".join(item["text"] for item in facts)
    assert "未核对 1 条" in text
    assert "不计入正确证据" in text
    # Unchecked records may appear only in the not-counted fact, never as correct.
    correct = next(item for item in facts if item["text"].startswith("已核对的记录里"))
    assert "a1" not in correct["source_refs"]
    sign = next(item for item in facts if "符号" in item["text"])
    assert set(sign["source_refs"]) == {"a2", "a3"}
    assert sign["text"].endswith("出现 2 次。")


@pytest.mark.parametrize(
    "phrase",
    [
        "你今天必须优先学习这一科",
        "该知识点已掌握",
        "太棒了，你一定可以",
        # Bypass attempts that a plain substring list would miss:
        "该知识点你已经完全掌握",
        " 你 今天 必须 优先 复习 ",
        "复习欠债：逾期3项",
        "系统替你决定先学哪一科",
        "推荐你优先学习电路",
        "你已经完全学会了",
        "最近连续打卡归零",
    ],
)
def test_forbidden_language_is_detected(phrase):
    assert has_forbidden_language(phrase) is not None


@pytest.mark.parametrize(
    "phrase",
    [
        "还有 3 条记录没有核对，核对之后它们才能成为判断依据。",
        "还没有独立完成且核对正确的记录。",
        "同一个知识点最近连续 3 次独立完成且核对正确。",
        "这道题上一次做完以后还没有对答案。",
    ],
)
def test_honest_phrasing_is_not_blocked(phrase):
    # Honest gaps must never be mistaken for commander language.
    assert has_forbidden_language(phrase) is None


def test_normalize_folds_width_and_drops_separators():
    assert normalize("　已　掌 握．") == "已掌握"


def test_missing_information_passes_the_same_policy_gate():
    # Regression: a command must not be smuggled in through missing_information.
    with pytest.raises(AdvisorPolicyError) as excinfo:
        validate_missing(["你今天必须复习这一科"])
    assert excinfo.value.reason == "forbidden_language"


def test_reference_versions_are_checked_when_supplied():
    allowed = {"a1": 3}
    assert normalize_refs(["a1"], allowed) == ["a1"]
    assert normalize_refs([{"id": "a1", "version": 3}], allowed) == ["a1"]
    with pytest.raises(AdvisorPolicyError) as excinfo:
        normalize_refs([{"id": "a1", "version": 2}], allowed)
    assert excinfo.value.reason == "unknown_reference"


def test_knowledge_point_streaks_break_on_a_non_independent_record():
    records = [
        record(id="a1", occurred_at="2026-10-01T00:03:00+00:00", knowledge_point_ids=["kp1"]),
        record(id="a2", occurred_at="2026-10-01T00:02:00+00:00", knowledge_point_ids=["kp1"]),
        record(
            id="a3",
            occurred_at="2026-10-01T00:01:00+00:00",
            knowledge_point_ids=["kp1"],
            result="partial",
        ),
    ]
    streaks = knowledge_point_streaks(records)
    assert streaks["kp1"]["count"] == 2
    assert [item["id"] for item in streaks["kp1"]["records"]] == ["a1", "a2"]


def test_inferences_require_known_owner_scoped_references():
    allowed = {"a1", "a2"}
    ok = validate_inferences([{"text": "可能集中在条件判断。", "source_refs": ["a1"]}], allowed)
    assert ok == [{"text": "可能集中在条件判断。", "source_refs": ["a1"]}]

    with pytest.raises(AdvisorPolicyError) as excinfo:
        validate_inferences([{"text": "x", "source_refs": ["other"]}], allowed)
    assert excinfo.value.reason == "unknown_reference"

    with pytest.raises(AdvisorPolicyError) as excinfo:
        validate_inferences([{"text": "x", "source_refs": []}], allowed)
    assert excinfo.value.reason == "unknown_reference"


def test_inferences_reject_commander_and_mastery_language():
    with pytest.raises(AdvisorPolicyError) as excinfo:
        validate_inferences(
            [{"text": "你现在必须复习这一课，已经掌握。", "source_refs": ["a1"]}], {"a1"}
        )
    assert excinfo.value.reason == "forbidden_language"


@pytest.mark.parametrize(
    "payload",
    [
        "not-a-list",
        [None],
        [{"text": "", "source_refs": ["a1"]}],
        [{"text": "x", "source_refs": "a1"}],
        [{"text": "x" * 1001, "source_refs": ["a1"]}],
    ],
)
def test_malformed_inferences_are_rejected(payload):
    with pytest.raises(AdvisorPolicyError):
        validate_inferences(payload, {"a1"})


def test_missing_information_is_sanitized_and_deduplicated():
    assert validate_missing(["缺材料", "缺材料", "", 7, "另一个"]) == ["缺材料", "另一个"]
    with pytest.raises(AdvisorPolicyError):
        validate_missing("not-a-list")


def test_data_version_tracks_the_record_snapshot():
    first = data_version({"records": [record(id="a1", version=1)]})
    same = data_version({"records": [record(id="a1", version=1)]})
    bumped = data_version({"records": [record(id="a1", version=2)]})
    assert first == same
    assert first != bumped
    assert len(first) == 64
