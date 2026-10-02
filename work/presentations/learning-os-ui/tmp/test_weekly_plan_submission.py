import json
import os
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


URL = os.environ.get("LEARNING_OS_TEST_URL", "http://127.0.0.1:4173/")


def run():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page_errors = []
        task_posts = []
        tasks = []

        def api_route(route):
            request = route.request
            path = urlparse(request.url).path
            payload = {"items": []}
            if path.endswith("/dashboard"):
                payload = {"tasks": tasks, "current_task": None, "next_tasks": [], "completed_count": 0, "remaining_count": len(tasks), "review": {"items": []}}
            elif path.endswith("/daily-review"):
                payload = {"items": []}
            elif path.endswith("/tasks") and request.method == "POST":
                task = json.loads(request.post_data)
                task_posts.append(task)
                tasks.append({**task, "id": f"task-{len(tasks)}", "status": "planned"})
                payload = tasks[-1]
            elif path.endswith("/tasks"):
                payload = {"items": tasks}
            route.fulfill(status=201 if request.method == "POST" else 200, content_type="application/json; charset=utf-8", body=json.dumps(payload))

        page.route("http://127.0.0.1:4174/api/v2/**", api_route)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(URL, wait_until="networkidle")
        page.locator('[data-page="plan"]').click()

        form = page.locator("#taskForm")
        form.locator('[name="title"]').fill("QA_TEST_weekly_one")
        form.locator('[name="study_date"]').fill("2026-07-21")
        form.locator('[name="priority"]').select_option("high")
        form.locator('[name="estimated_minutes"]').fill("35")
        form.locator('[name="notes"]').fill("QA_TEST_first_note")
        form.get_by_role("button", name="加入计划").click()

        expect(page.locator("#notice")).to_have_text("任务已加入计划。")
        expect(form.locator('[name="title"]')).to_have_value("")
        expect(page.locator("#taskList")).to_contain_text("QA_TEST_weekly_one")
        assert len(task_posts) == 1
        assert page_errors == []
        browser.close()


if __name__ == "__main__":
    run()
    print("Weekly Plan submission regression: OK")
