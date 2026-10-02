"""OpenAI 兼容 provider 的契约测试。

全部用**假 transport**，不打真实网络（AGENTS.md §13.2：自动化测试默认确定性 mock，
真实调用只作可选 smoke test）。

重点覆盖「模型不可信」这条：模型编造证据 id、返回非 JSON、HTTP 报错、
连不上——都必须收敛成契约内输出或 AdvisorModelUnavailable 降级，
而不是让 advisor 变成 500 或把没依据的文本发布出去。
"""
import json

from hermes_api.advisor_ports import AdvisorModelUnavailable
from hermes_api.openai_model import OpenAIModel, extract_json, render_evidence

EVIDENCE = {
    "records": [
        {"id": "attempt-1", "version": 2, "problem_title": "定积分的换元积分法"},
        {"id": "attempt-2", "version": 1, "problem_title": "一阶电路的暂态分析"},
    ]
}


def model_with(reply: str | dict | Exception):
    def transport(payload):  # noqa: ARG001 - 断言 payload 的用例单独取
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, dict):
            return reply
        return {"choices": [{"message": {"content": reply}}]}

    return OpenAIModel("https://example.test/hermes-api/v1", "QA_TEST_key", "gpt-4o-mini",
                       transport=transport)


def test_endpoint_normalisation():
    assert OpenAIModel._endpoint_for("https://x.test/v1") == "https://x.test/v1/chat/completions"
    assert (
        OpenAIModel._endpoint_for("https://x.test/v1/chat/completions")
        == "https://x.test/v1/chat/completions"
    )
    assert OpenAIModel._endpoint_for("https://x.test/v1/") == "https://x.test/v1/chat/completions"


def test_keeps_only_grounded_inferences():
    """模型编造的证据 id 必须被丢弃，合法引用必须保留。"""
    reply = json.dumps({
        "inferences": [
            {"text": "换元后上下限需要一起替换。",
             "source_refs": [{"id": "attempt-1", "version": 2}]},
            {"text": "这条引用了不存在的证据。",
             "source_refs": [{"id": "does-not-exist", "version": 1}]},
            {"text": "这条版本号不对。",
             "source_refs": [{"id": "attempt-2", "version": 99}]},
        ],
        "missing_information": ["还缺少第二次尝试的过程记录。"],
    })
    out = model_with(reply).analyze({"topic": None}, EVIDENCE)

    assert [i["text"] for i in out["inferences"]] == ["换元后上下限需要一起替换。"]
    assert out["inferences"][0]["source_refs"] == [{"id": "attempt-1", "version": 2}]
    assert out["missing_information"] == ["还缺少第二次尝试的过程记录。"]


def test_inference_without_any_valid_ref_is_dropped():
    """契约要求推断必须有依据；无依据的推断不发布。"""
    reply = json.dumps({"inferences": [{"text": "没有引用的断言", "source_refs": []}]})
    out = model_with(reply).analyze({}, EVIDENCE)
    assert out["inferences"] == []


def test_tolerates_code_fence_and_surrounding_prose():
    raw = '好的，分析如下：\n```json\n{"inferences": [], "missing_information": ["缺材料"]}\n```\n以上。'
    out = model_with(raw).analyze({}, EVIDENCE)
    assert out["missing_information"] == ["缺材料"]


def test_non_json_reply_degrades_to_empty_not_crash():
    out = model_with("抱歉，我无法完成。").analyze({}, EVIDENCE)
    assert out == {"inferences": [], "missing_information": []}


def test_http_failure_becomes_unavailable():
    for error in (RuntimeError("boom"), TimeoutError("slow")):
        try:
            model_with(error).analyze({}, EVIDENCE)
        except AdvisorModelUnavailable:
            continue
        raise AssertionError(f"{type(error).__name__} 没有被转成 AdvisorModelUnavailable")


def test_transport_receives_expected_payload():
    seen = {}

    def transport(payload):
        seen.update(payload)
        return {"choices": [{"message": {"content": "{}"}}]}

    model = OpenAIModel("https://x.test/v1", "k", "gpt-4o-mini", transport=transport)
    model.analyze({"topic": "定积分"}, EVIDENCE)

    assert seen["model"] == "gpt-4o-mini"
    assert seen["temperature"] == 0
    assert seen["messages"][0]["role"] == "system"
    body = seen["messages"][1]["content"]
    assert "定积分" in body
    assert "attempt-1" in body and "version=2" in body


def test_missing_credentials_refuse_construction():
    for kwargs in (
        {"base_url": "", "api_key": "k", "model": "m"},
        {"base_url": "https://x.test", "api_key": "", "model": "m"},
        {"base_url": "https://x.test", "api_key": "k", "model": ""},
    ):
        try:
            OpenAIModel(**kwargs)
        except ValueError:
            continue
        raise AssertionError(f"缺少凭据仍构造成功: {kwargs}")


def test_image_capability_is_opt_in():
    """能力声明必须诚实：默认不支持图片，只有显式开启才声明。"""
    plain = OpenAIModel("https://x.test/v1", "k", "m", transport=lambda p: {})
    assert plain.capabilities["modalities"] == ["text"]

    vision = OpenAIModel("https://x.test/v1", "k", "m", supports_image=True,
                         transport=lambda p: {})
    assert vision.capabilities["modalities"] == ["text", "image"]


def test_api_key_never_appears_in_errors():
    secret = "QA_TEST_super_secret_key"

    def transport(payload):  # noqa: ARG001
        raise RuntimeError("upstream said no")

    model = OpenAIModel("https://x.test/v1", secret, "m", transport=transport)
    try:
        model.analyze({}, EVIDENCE)
    except AdvisorModelUnavailable as error:
        assert secret not in str(error)
    else:
        raise AssertionError("应当抛出 AdvisorModelUnavailable")


def test_extract_json_and_render_evidence_helpers():
    assert extract_json("") is None
    assert extract_json("no json here") is None
    assert extract_json('{"a":1}') == {"a": 1}
    assert "没有可用的学习记录" in render_evidence({"records": []})
    assert "attempt-1" in render_evidence(EVIDENCE)
