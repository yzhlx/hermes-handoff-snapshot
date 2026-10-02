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
        chats = []
        messages_by_chat = {}

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
            elif path.endswith("/chats") and request.method == "POST":
                submitted = json.loads(request.post_data or "{}")
                chat = {
                    "id": f"chat-{len(chats)}",
                    "title": submitted["title"],
                    "updated_at": "2026-07-22T09:00:00",
                }
                chats.append(chat)
                messages_by_chat[chat["id"]] = []
                status = 201
                payload = chat
            elif path.endswith("/chats"):
                payload = {"items": chats}
            elif path.endswith("/messages") and request.method == "POST":
                chat_id = path.split("/")[-2]
                submitted = json.loads(request.post_data or "{}")
                messages_by_chat.setdefault(chat_id, []).append(
                    {"role": "user", "content": submitted["content"]}
                )
                if submitted["content"] == "QA_TEST_AI_FAILURE":
                    status = 503
                    payload = {
                        "error": "模拟 Provider 不可用",
                        "code": "AI_PROVIDER_UNAVAILABLE",
                    }
                else:
                    messages_by_chat[chat_id].append(
                        {
                            "role": "assistant",
                            "content": "**学习批注**\n\n- 从定义开始\n- 先做一次低难度回忆\n\n```text\n先写出卷积定义\n```",
                        }
                    )
                    status = 201
                    payload = messages_by_chat[chat_id][-1]
            elif path.endswith("/messages"):
                chat_id = path.split("/")[-2]
                payload = {"items": messages_by_chat.get(chat_id, [])}
            route.fulfill(
                status=status,
                content_type="application/json; charset=utf-8",
                body=json.dumps(payload),
            )

        page.route("http://127.0.0.1:4174/api/v2/**", api_route)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(URL, wait_until="networkidle")
        page.get_by_role("navigation", name="主导航").get_by_role(
            "button", name="AI 对话", exact=True
        ).click()
        expect(page.get_by_role("heading", name="学习导师")).to_be_visible()
        expect(page.get_by_text("今天我们先解决最重要的一件事。")).to_be_visible()

        page.once("dialog", lambda dialog: dialog.accept("QA_TEST_AI_CHAT"))
        page.get_by_role("button", name="新建对话").click()
        expect(page.locator("#chatStatus")).to_have_text("等待你的问题")

        form = page.locator("#chatForm")
        form.get_by_label("向 Hermes 说明你正在学习什么").fill("卷积下一步怎么复习？")
        form.get_by_role("button", name="发送").click()
        expect(page.locator("#messages")).to_contain_text("学习批注")
        assert page.locator(".message-content ul").count() == 1
        assert page.locator(".message-content pre").count() == 1
        expect(form.get_by_label("向 Hermes 说明你正在学习什么")).to_have_value("")

        form.get_by_label("向 Hermes 说明你正在学习什么").fill("QA_TEST_AI_FAILURE")
        form.get_by_role("button", name="发送").click()
        expect(page.locator("#chatStatus")).to_have_text("回复未生成；你的问题已保留")
        expect(form.get_by_label("向 Hermes 说明你正在学习什么")).to_have_value(
            "QA_TEST_AI_FAILURE"
        )
        expect(page.locator("#messages")).to_contain_text("QA_TEST_AI_FAILURE")
        assert len(chats) == 1
        assert page_errors == []
        browser.close()


if __name__ == "__main__":
    run()
    print("Hermes AI UI regression: OK")
