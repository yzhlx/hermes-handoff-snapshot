import json
import os
from datetime import date
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


URL = os.environ.get("LEARNING_OS_TEST_URL", "http://127.0.0.1:4173/")


def run():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page_errors = []
        saved_statuses = []

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
            elif path.endswith("/statistics"):
                payload = {
                    "by_subject": [{"subject": "高等数学", "count": 3}],
                    "by_chapter": [{"chapter": "卷积", "count": 2}],
                    "by_error_type": [{"name": "计算错误", "count": 1}],
                }
            elif path.endswith("/status") and request.method == "POST":
                saved = json.loads(request.post_data or "{}")
                saved_statuses.append(saved)
                payload = saved
                status = 201
            elif path.endswith("/status"):
                payload = {"items": []}
            route.fulfill(
                status=status,
                content_type="application/json; charset=utf-8",
                body=json.dumps(payload),
            )

        page.route("http://127.0.0.1:4174/api/v2/**", api_route)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(URL, wait_until="networkidle")

        page.get_by_role("button", name="学习记录").click()
        expect(page.locator("#subjectStats")).to_contain_text("高等数学")
        expect(page.locator("#chapterStats")).to_contain_text("卷积")
        expect(page.locator("#typeStats")).to_contain_text("计算错误")
        assert page.locator(".statistic-row").count() == 3
        assert page.locator(".statistic-row").nth(0).get_attribute("aria-label") == "高等数学，3 条记录"

        page.get_by_role("button", name="记录状态").click()
        dialog = page.locator("#statusDialog")
        assert dialog.evaluate("element => element.open") is True
        dialog.get_by_label("心情").select_option("4")
        dialog.get_by_label("精力").select_option("3")
        dialog.get_by_label("压力").select_option("2")
        expect(dialog.locator('label[for="statusNotes"]')).to_contain_text("备注")
        dialog.locator("#statusNotes").fill("QA_TEST_低难度回忆")
        dialog.get_by_role("button", name="保存状态").click()
        expect(page.locator("#notice")).to_have_text("状态已记录。")
        assert dialog.evaluate("element => element.open") is False
        assert len(saved_statuses) == 1
        saved = saved_statuses[0]
        assert saved["mood"] == 4
        assert saved["energy"] == 3
        assert saved["stress"] == 2
        assert saved["fatigued"] is False
        assert saved["willing_to_continue"] is True
        assert saved["notes"] == "QA_TEST_低难度回忆"
        assert date.fromisoformat(saved["recorded_on"])
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
        assert page_errors == []
        browser.close()


if __name__ == "__main__":
    run()
    print("Learning state and statistics UI regression: OK")
