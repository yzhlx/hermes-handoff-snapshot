import json
import os
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


URL = os.environ.get("LEARNING_OS_URL", "http://127.0.0.1:4173/")


def run():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page_errors = []
        tasks = []
        settings = {
            "base_url": "",
            "protocol": "chat_completions",
            "model": "",
            "timeout_seconds": 30,
            "is_configured": False,
            "key_suffix": None,
        }

        def api_route(route):
            request = route.request
            path = urlparse(request.url).path
            payload = {"items": []}
            status = 200
            if path.endswith("/dashboard"):
                payload = {
                    "tasks": tasks,
                    "current_task": None,
                    "next_tasks": [],
                    "completed_count": 0,
                    "remaining_count": len(tasks),
                    "review": {"items": []},
                }
            elif path.endswith("/tasks") and request.method == "POST":
                task = json.loads(request.post_data or "{}")
                payload = {**task, "id": f"ui-task-{len(tasks)}", "status": "planned"}
                tasks.append(payload)
                status = 201
            elif path.endswith("/tasks"):
                payload = {"items": tasks}
            elif path.endswith("/settings/ai") and request.method == "POST":
                submitted = json.loads(request.post_data or "{}")
                settings.update(
                    {
                        "base_url": submitted.get("base_url", settings["base_url"]),
                        "protocol": submitted.get("protocol", settings["protocol"]),
                        "model": submitted.get("model", settings["model"]),
                        "timeout_seconds": submitted.get(
                            "timeout_seconds", settings["timeout_seconds"]
                        ),
                    }
                )
                payload = settings
            elif path.endswith("/settings/ai"):
                payload = settings
            elif path.endswith("/statistics"):
                payload = {"by_subject": [], "by_chapter": [], "by_error_type": []}
            route.fulfill(
                status=status,
                content_type="application/json; charset=utf-8",
                body=json.dumps(payload),
            )

        page.route("http://127.0.0.1:4174/api/v2/**", api_route)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(URL, wait_until="networkidle")
        assert page.title() == "学习 OS"
        assert page.locator('meta[charset]').get_attribute("charset") == "UTF-8"
        expect(page.get_by_role("link", name="Hermes Learning OS，返回今日")).to_be_visible()
        expect(page.get_by_text("今天的每一步，都会沉淀为长期能力。")).to_be_visible()
        expect(page.get_by_role("navigation", name="主导航")).to_be_visible()
        expect(page.get_by_role("button", name="今日")).to_be_visible()
        expect(page.get_by_role("button", name="错题专栏")).to_be_visible()
        expect(page.get_by_role("heading", name="今天的安排")).to_be_visible()
        expect(page.get_by_text("还没有安排任务")).to_be_visible()
        page.get_by_role("button", name="错题专栏").click()
        expect(page.get_by_role("heading", name="错题专栏")).to_be_visible()
        page.get_by_role("button", name="拍照快速录入").click()
        quick_error_dialog = page.locator("#quickErrorDialog")
        assert quick_error_dialog.evaluate("element => element.open") is True
        quick_error_dialog.get_by_role("button", name="关闭").click()
        assert quick_error_dialog.evaluate("element => element.open") is False
        page.get_by_role("button", name="设置").click()
        expect(page.get_by_label("AI 服务地址")).to_be_visible()
        expect(page.get_by_label("API 密钥")).to_be_visible()
        page.get_by_label("AI 服务地址").fill("https://provider.example/v1")
        page.get_by_label("模型").fill("QA_TEST_MODEL")
        page.get_by_label("超时（秒）").fill("17")
        page.get_by_role("button", name="保存 AI 配置").click()
        expect(page.locator("#notice")).to_have_text("AI 配置已保存。")
        assert not any("currentTarget" in error or "Cannot read" in error for error in page_errors)
        page.get_by_role("button", name="记录状态").click()
        status_dialog = page.locator("#statusDialog")
        assert status_dialog.evaluate("element => element.open") is True
        status_dialog.get_by_role("button", name="关闭").click()
        assert status_dialog.evaluate("element => element.open") is False
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.get_by_role("navigation", name="主导航")).to_be_visible()
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
        for button_name, heading_name in [
            ("今日", "今天的安排"),
            ("周计划", "周计划"),
            ("错题专栏", "错题专栏"),
            ("每日复习", "每日复习"),
            ("AI 对话", "AI 对话"),
            ("学习记录", "学习记录"),
            ("设置", "设置"),
        ]:
            page.get_by_role("button", name=button_name).click()
            expect(page.locator("#pageTitle")).to_have_text(heading_name)
            assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
        page.get_by_role("button", name="周计划").click()
        planner_form = page.locator("#taskForm")
        expect(planner_form.get_by_label("任务标题")).to_be_visible()
        expect(planner_form.get_by_label("安排日期")).to_be_visible()
        expect(planner_form.get_by_label("优先级")).to_be_visible()
        assert page.locator("#taskFormStatus").get_attribute("role") == "status"
        for width, height in [(1440, 900), (1280, 720), (1024, 768), (768, 1024), (390, 844)]:
            page.set_viewport_size({"width": width, "height": height})
            assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
        page.keyboard.press("Tab")
        assert page.evaluate("() => document.activeElement.matches(':focus-visible')")
        assert page_errors == []
        browser.close()


if __name__ == "__main__":
    run()
    print("Learning OS product app checks: OK")
