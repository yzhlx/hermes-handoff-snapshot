"""Versioned, public learning-method content and situation mappings."""

from dataclasses import dataclass


def subject_group_label(name: str) -> str:
    if "信号" in name or "电路" in name:
        return "上海大学829"
    return "公共课"


@dataclass(frozen=True, slots=True)
class LearningMethod:
    id: str
    title: str
    summary: str
    problem: str
    situations: tuple[str, ...]
    steps: tuple[str, ...]
    pitfalls: tuple[str, ...]
    content_version: int = 1


@dataclass(frozen=True, slots=True)
class LearningSituation:
    id: str
    label: str
    method_ids: tuple[str, ...]
    reason: str
    allow_free_learning: bool = False


METHODS: tuple[LearningMethod, ...] = (
    LearningMethod(
        id="active-recall",
        title="主动回忆",
        summary="合上资料，先从脑中把它取出来。",
        problem="重新阅读容易带来熟悉感，却不能说明离开资料后还能否想起。",
        situations=("刚学完一节", "刚看完网课", "复习知识点", "检查自己是否记住"),
        steps=(
            "合上资料。",
            "给自己提出一个具体问题。",
            "尝试完整回答。",
            "打开资料核对遗漏。",
            "挑一处遗漏处理，之后可自愿再回来。",
        ),
        pitfalls=("把重新看一遍当成已经记住。", "想不起来时急着看答案，跳过了自己的尝试。"),
    ),
    LearningMethod(
        id="practice-feedback",
        title="实际执行与反馈",
        summary="看懂之后，自己完整尝试一次，再对照差异。",
        problem="看懂他人的解法不等于能独立找到入口、推进过程并发现卡点。",
        situations=("需要解题的内容", "不知道从哪里下手", "看答案会但自己不会"),
        steps=(
            "先不看答案，留下自己的尝试。",
            "尽量完整做下去，并标出卡住的位置。",
            "查看答案或参考材料。",
            "比较自己的过程与参考过程。",
            "记录具体差异和卡点。",
        ),
        pitfalls=(
            "只看解答并产生熟悉感。",
            "没尝试就把结果记成独立完成。",
            "把计算失误和入口缺失混为一谈。",
        ),
    ),
    LearningMethod(
        id="spaced-review",
        title="间隔复习",
        summary="隔一段时间重新提取，让遗忘成为可发现的线索。",
        problem="内容学过后容易淡忘；连续重看可能掩盖当前真正能回忆的部分。",
        situations=("已经学过", "容易忘", "公式或概念", "错题", "需要长期保持的内容"),
        steps=(
            "自己选择要回顾的材料。",
            "合上材料，先尝试回忆或作答。",
            "打开材料核查。",
            "记下遗漏或卡点。",
            "之后想回来时再自愿选择时间。",
        ),
        pitfalls=(
            "把建议当成必须完成的任务。",
            "把看答案当成已经掌握。",
            "因暂时想不起来就假装从未学过。",
        ),
    ),
    LearningMethod(
        id="worked-example-compare",
        title="双例对比",
        summary="把两道相似题并排，找出真正改变解法的差异。",
        problem="外观相似的题可能因条件或边界不同而需要不同入口。",
        situations=("相似题做法不同", "公式容易混", "一道会一道不会"),
        steps=(
            "选两道自己想比较的题。",
            "先看条件和已知量。",
            "比较公式、解题入口与图形。",
            "再看边界和隐含假设。",
            "只记录对这两题真正相关的差异。",
        ),
        pitfalls=("没核对材料就断言两题相似。", "强行填满所有比较维度。", "跳过比较直接继续刷题。"),
    ),
    LearningMethod(
        id="feynman-check",
        title="费曼式检查",
        summary="用自己的话说清楚是什么、为什么、何时使用。",
        problem="听课时的熟悉感可能掩盖对原理、使用条件或知识区别的含混。",
        situations=("刚听完课感觉听懂", "检查是否真的理解", "概念之间容易混"),
        steps=(
            "离开教材原话，用自己的表达说明它是什么。",
            "解释为什么成立。",
            "说出什么时候使用。",
            "与相似知识作一个区别。",
            "把说不清的地方记为待澄清问题。",
        ),
        pitfalls=(
            "照搬老师或教材的原句。",
            "用术语替代解释。",
            "把一次表达流畅误当成已掌握。",
            "认为必须录音或写长文。",
        ),
    ),
)


SITUATIONS: tuple[LearningSituation, ...] = (
    LearningSituation(
        "just-finished-class",
        "刚听完课，感觉听懂",
        ("active-recall", "feynman-check"),
        "检查能否离开原话复述。",
    ),
    LearningSituation(
        "no-entry-point",
        "一看题不知道下手",
        ("practice-feedback",),
        "先留下自己的尝试，定位入口缺失。",
    ),
    LearningSituation(
        "answer-looks-clear",
        "看答案会，自己不会",
        ("practice-feedback", "active-recall"),
        "区分看懂与独立完成。",
    ),
    LearningSituation(
        "similar-problems",
        "两道题很像但做法不同",
        ("worked-example-compare",),
        "比较条件与解题入口。",
    ),
    LearningSituation(
        "confusable-formulas",
        "公式很多容易混",
        ("active-recall", "worked-example-compare"),
        "比较公式的适用条件和差异。",
    ),
    LearningSituation(
        "forgotten-content",
        "以前学过现在忘了",
        ("spaced-review", "active-recall"),
        "重新提取，而不是假装从未学过。",
    ),
    LearningSituation(
        "repeated-mistake",
        "同类问题反复错",
        ("practice-feedback", "worked-example-compare"),
        "回看真实尝试过程和题目差异。",
    ),
    LearningSituation(
        "low-energy",
        "状态差，只想先开始一下",
        ("active-recall",),
        "可以只尝试回忆一次，不设达标量。",
        allow_free_learning=True,
    ),
    LearningSituation(
        "know-what-to-do",
        "知道要干什么",
        (),
        "直接自由学习，不额外插入方法。",
        allow_free_learning=True,
    ),
)


def list_methods() -> tuple[LearningMethod, ...]:
    """Return the immutable public method catalog in stable display order."""
    return METHODS


def get_method(method_id: str) -> LearningMethod | None:
    return next((method for method in METHODS if method.id == method_id), None)


def list_situations() -> tuple[LearningSituation, ...]:
    return SITUATIONS


def get_situation(situation_id: str) -> LearningSituation | None:
    return next((situation for situation in SITUATIONS if situation.id == situation_id), None)
