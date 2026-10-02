import json
import os
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


URL = os.environ.get("LEARNING_OS_TEST_URL", "http://127.0.0.1:4173/")


def run():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page_errors = []
        records = []
        post_attempts = []

        def api_route(route):
            request = route.request
            path = urlparse(request.url).path
            payload = {"items": []}
            status = 200
            if path.endswith("/dashboard"):
                payload = {
                    "tasks": [],
                    "current_task": None,
                    "next_tasks": [],
                    "completed_count": 0,
                    "remaining_count": 0,
                    "review": {"items": []},
                }
            elif path.endswith("/status"):
                payload = {"items": []}
            elif path.endswith("/error-questions") and request.method == "POST":
                submitted = json.loads(request.post_data or "{}")
                post_attempts.append(submitted)
                if submitted.get("title") == "QA_TEST_error_failure":
                    status = 503
                    payload = {"error": "模拟保存失败", "code": "QA_SAVE_FAILED"}
                else:
                    record = {
                        **submitted,
                        "id": f"error-{len(records)}",
                        "error_types": [],
                        "mastery": "not_mastered",
                    }
                    records.append(record)
                    status = 201
                    payload = record
            elif path.endswith("/error-questions"):
                payload = {"items": records}
            elif path.endswith("/analyze"):
                payload = {
                    "information_sufficient": False,
                    "questions": ["请补充作答过程。"],
                }
            route.fulfill(
                status=status,
                content_type="application/json; charset=utf-8",
                body=json.dumps(payload),
            )

        page.route("http://127.0.0.1:4174/api/v2/**", api_route)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(URL, wait_until="networkidle")
        page.get_by_role("button", name="错题专栏").click()

        form = page.locator("#errorForm")
        form.get_by_label("标题或题号 可选").fill("QA_TEST_error_complete")
        form.get_by_label("学科").fill("高等数学")
        form.get_by_label("章节 可选").fill("卷积")
        form.get_by_label("复习优先级").select_option("high")
        for label_for, label_text in [
            ("errorProblem", "题目证据"),
            ("errorWork", "你的作答"),
            ("errorAnswer", "参考答案"),
            ("errorExplanation", "解析与批注"),
        ]:
            expect(form.locator(f'label[for="{label_for}"]')).to_contain_text(label_text)
        form.locator("#errorProblem").fill("已知 x(t) 与 h(t)，求卷积。")
        form.locator("#errorWork").fill("把积分上下限写反。")
        form.locator("#errorAnswer").fill("按定义分段积分。")
        form.locator("#errorExplanation").fill("检查积分区间。")
        form.get_by_role("button", name="保存错题").click()

        expect(page.locator("#notice")).to_have_text("错题已保存。")
        expect(form.get_by_label("标题或题号 可选")).to_have_value("")
        expect(form.get_by_label("学科")).to_have_value("高等数学")
        expect(page.locator("#errorList")).to_contain_text("QA_TEST_error_complete")
        assert len(records) == 1
        assert len(post_attempts) == 1

        analysis_button = page.get_by_role("button", name="分析学习线索")
        analysis_button.click()
        expect(page.locator(".error-analysis-status")).to_contain_text(
            "需要补充证据：请补充作答过程。"
        )

        form.get_by_label("标题或题号 可选").fill("QA_TEST_error_failure")
        form.get_by_role("button", name="保存错题").click()
        expect(form.get_by_label("标题或题号 可选")).to_have_value(
            "QA_TEST_error_failure"
        )
        expect(page.locator("#errorFormStatus")).to_contain_text("未保存")
        assert len(records) == 1
        assert len(post_attempts) == 2
        assert page_errors == []
        browser.close()


if __name__ == "__main__":
    run()
    print("Wrong-answer submission regression: OK")
