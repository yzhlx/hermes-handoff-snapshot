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
        save_payloads = []
        connection_mode = {"fails": False}
        settings = {
            "base_url": "https://provider.example/v1",
            "protocol": "chat_completions",
            "model": "QA_TEST_MODEL",
            "timeout_seconds": 30,
            "is_configured": True,
            "key_suffix": "1234",
        }

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
            elif path.endswith("/settings/ai/test"):
                if connection_mode["fails"]:
                    status = 503
                    payload = {
                        "error": "模拟 Provider 不可用",
                        "code": "AI_PROVIDER_UNAVAILABLE",
                    }
                else:
                    payload = {"reply": "DO_NOT_EXPOSE_TEST_REPLY"}
            elif path.endswith("/settings/ai") and request.method == "POST":
                submitted = json.loads(request.post_data or "{}")
                save_payloads.append(submitted)
                settings.update(
                    {
                        "base_url": submitted["base_url"],
                        "protocol": submitted["protocol"],
                        "model": submitted["model"],
                        "timeout_seconds": submitted["timeout_seconds"],
                    }
                )
                payload = settings
            elif path.endswith("/settings/ai"):
                payload = settings
            route.fulfill(
                status=status,
                content_type="application/json; charset=utf-8",
                body=json.dumps(payload),
            )

        page.route("http://127.0.0.1:4174/api/v2/**", api_route)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(URL, wait_until="networkidle")
        page.get_by_role("button", name="设置").click()

        form = page.locator("#aiSettingsForm")
        expect(page.locator("#aiConfigStatus")).to_have_text("密钥已配置（末四位 1234）")
        expect(form.locator('label[for="aiApiKey"]')).to_contain_text("输入或更换密钥")
        expect(form.locator("#aiApiKey")).to_have_value("")
        assert "DO_NOT_EXPOSE_TEST_REPLY" not in page.content()

        form.get_by_label("模型").fill("QA_TEST_UPDATED_MODEL")
        form.get_by_role("button", name="保存 AI 配置").click()
        expect(page.locator("#notice")).to_have_text("AI 配置已保存。")
        assert len(save_payloads) == 1
        assert "api_key" not in save_payloads[0]
        assert save_payloads[0]["model"] == "QA_TEST_UPDATED_MODEL"

        test_button = page.get_by_role("button", name="测试 AI 连接")
        test_button.click()
        expect(page.locator("#connectionTestStatus")).to_have_text(
            "连接测试成功。当前 Provider 可以响应最小请求。"
        )
        assert "DO_NOT_EXPOSE_TEST_REPLY" not in page.content()

        connection_mode["fails"] = True
        test_button.click()
        expect(page.locator("#connectionTestStatus")).to_contain_text("连接测试未通过")
        expect(test_button).to_be_enabled()
        assert page_errors == []
        browser.close()


if __name__ == "__main__":
    run()
    print("AI settings UI regression: OK")
