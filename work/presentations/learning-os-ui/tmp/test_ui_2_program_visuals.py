"""Deterministic, non-persistent UI 2.0 visual and responsive evidence capture."""

import json
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


URL = os.environ.get("LEARNING_OS_TEST_URL", "http://127.0.0.1:4173/")
SOURCE_ROOT = Path(__file__).resolve().parents[4]
SCREENSHOT_DIR = (
    SOURCE_ROOT / "artifacts" / "ui-2.0-program" / "screenshots" / "milestone-10"
)

TASKS = [
    {
        "id": "ui2-complete",
        "title": "QA_TEST_昨日错题二次作答",
        "status": "completed",
        "priority": "medium",
        "estimated_minutes": 45,
        "start_time": "08:30",
    },
    {
        "id": "ui2-current",
        "title": "QA_TEST_卷积主动回忆",
        "status": "active",
        "priority": "high",
        "estimated_minutes": 35,
        "start_time": "10:00",
    },
    {
        "id": "ui2-planned",
        "title": "QA_TEST_信号与系统计算题整理",
        "status": "planned",
        "priority": "medium",
        "estimated_minutes": 40,
        "start_time": None,
    },
]


def dashboard_payload():
    return {
        "tasks": TASKS,
        "current_task": TASKS[1],
        "next_tasks": [TASKS[2]],
        "completed_count": 1,
        "remaining_count": 2,
        "review": {"items": [{"id": "ui2-review"}]},
    }


def run() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    page_errors = []
    chats = [
        {
            "id": "ui2-chat",
            "title": "QA_TEST_卷积复盘",
            "updated_at": "2026-07-22T09:00:00",
        }
    ]
    messages_by_chat = {
        "ui2-chat": [
            {"role": "user", "content": "卷积下一步该怎么复习？"},
            {
                "role": "assistant",
                "content": "**学习批注**\n\n- 先复述卷积定义\n- 再做一次 10 分钟低难度回忆",
            },
        ]
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        def api_route(route):
            request = route.request
            path = urlparse(request.url).path
            payload = {"items": []}

            if path.endswith("/dashboard"):
                payload = dashboard_payload()
            elif path.endswith("/tasks"):
                payload = {"items": TASKS}
            elif path.endswith("/status"):
                payload = {
                    "items": [
                        {
                            "mood": 4,
                            "energy": 3,
                            "stress": 2,
                            "advice": {"message": "QA_TEST_先完成当前回忆，再决定是否增加新输入。"},
                        }
                    ]
                }
            elif path.endswith("/error-questions"):
                payload = {
                    "items": [
                        {
                            "id": "ui2-error",
                            "title": "QA_TEST_卷积积分区间",
                            "subject": "高等数学",
                            "chapter": "卷积",
                            "priority": "high",
                            "problem_text": "已知 x(t) 与 h(t)，求卷积。",
                            "work_text": "积分上下限写反。",
                            "correct_answer": "按定义分段积分。",
                            "explanation": "先判断非零区间，再写积分范围。",
                            "error_types": ["概念混淆"],
                        }
                    ]
                }
            elif path.endswith("/daily-review"):
                payload = {
                    "items": [
                        {
                            "id": "ui2-review",
                            "title": "QA_TEST_卷积定义复盘",
                            "subject": "高等数学",
                            "chapter": "信号与系统",
                            "problem_text": "写出连续时间卷积的定义。",
                            "work_text": "仅写出了符号，没有说明积分区间。",
                            "correct_answer": "x(t) * h(t) = ∫ x(τ)h(t-τ)dτ。",
                            "explanation": "先说清变量，再开始计算。",
                            "review_count": 1,
                        }
                    ]
                }
            elif path.endswith("/chats"):
                payload = {"items": chats}
            elif path.endswith("/messages"):
                chat_id = path.split("/")[-2]
                payload = {"items": messages_by_chat.get(chat_id, [])}
            elif path.endswith("/statistics"):
                payload = {
                    "by_subject": [{"subject": "高等数学", "count": 3}],
                    "by_chapter": [{"chapter": "卷积", "count": 2}],
                    "by_error_type": [{"name": "概念混淆", "count": 1}],
                }
            elif path.endswith("/settings/ai"):
                payload = {
                    "base_url": "https://provider.example/v1",
                    "protocol": "chat_completions",
                    "model": "QA_TEST_MODEL",
                    "timeout_seconds": 30,
                    "is_configured": True,
                    "key_suffix": "1234",
                }

            route.fulfill(
                status=200,
                content_type="application/json; charset=utf-8",
                body=json.dumps(payload),
            )

        page.route("http://127.0.0.1:4174/api/v2/**", api_route)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(URL, wait_until="networkidle")
        expect(
            page.get_by_role("heading", name="QA_TEST_卷积主动回忆")
        ).to_be_visible()
        candidate_title = page.locator("#nextTasks .list-item strong")
        assert candidate_title.count() == 1
        candidate_box = candidate_title.bounding_box()
        next_tasks_box = page.locator("#nextTasks").bounding_box()
        assert candidate_box is not None
        assert next_tasks_box is not None
        assert candidate_box["width"] >= next_tasks_box["width"] * 0.5

        for width, height in [
            (1440, 900),
            (1280, 720),
            (1024, 768),
            (768, 1024),
            (390, 844),
        ]:
            page.set_viewport_size({"width": width, "height": height})
            assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
            if width == 390:
                assert page.evaluate(
                    """() => {
                        const navigation = document.querySelector('.main-nav');
                        const sidebar = document.querySelector('.sidebar');
                        return navigation.getBoundingClientRect().right <= window.innerWidth
                            && sidebar.scrollWidth <= sidebar.clientWidth;
                    }"""
                )
            page.screenshot(path=str(SCREENSHOT_DIR / f"home-{width}x{height}.png"))

        page.emulate_media(reduced_motion="reduce")
        assert page.evaluate(
            "() => getComputedStyle(document.querySelector('.page.active')).animationDuration"
        ) in {"0.01ms", "1e-05s"}
        page.emulate_media(reduced_motion="no-preference")
        page.keyboard.press("Tab")
        assert page.evaluate("() => document.activeElement.matches(':focus-visible')")

        page.set_viewport_size({"width": 1440, "height": 900})
        nav = page.get_by_role("navigation", name="主导航")
        views = [
            ("周计划", "周计划", "plan"),
            ("错题专栏", "错题专栏", "wrong-answers"),
            ("每日复习", "每日复习", "daily-review"),
            ("AI 对话", "AI 对话", "hermes-ai"),
            ("学习记录", "学习记录", "learning-records"),
            ("设置", "设置", "settings"),
        ]

        for button_name, heading_name, filename in views:
            button = nav.get_by_role("button", name=button_name, exact=True)
            assert button.count() == 1
            button.click()
            expect(page.locator("#pageTitle")).to_have_text(heading_name)

            if filename == "plan":
                expect(page.locator("#taskList")).to_contain_text("QA_TEST_卷积主动回忆")
            elif filename == "wrong-answers":
                expect(page.locator("#errorList")).to_contain_text("QA_TEST_卷积积分区间")
            elif filename == "daily-review":
                expect(page.locator("#reviewList")).to_contain_text("QA_TEST_卷积定义复盘")
            elif filename == "hermes-ai":
                chat = page.locator("#chatList .chat-history-item")
                expect(chat).to_have_count(1)
                expect(chat).to_contain_text("QA_TEST_卷积复盘")
                chat.click()
                expect(page.locator("#messages")).to_contain_text("学习批注")
            elif filename == "learning-records":
                expect(page.locator("#subjectStats")).to_contain_text("高等数学")
            elif filename == "settings":
                expect(page.locator("#aiConfigStatus")).to_contain_text("末四位 1234")

            assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
            page.screenshot(path=str(SCREENSHOT_DIR / f"{filename}-1440x900.png"), full_page=True)

        for button_name, heading_name, filename in [
            ("周计划", "周计划", "plan"),
            ("错题专栏", "错题专栏", "wrong-answers"),
            ("AI 对话", "AI 对话", "hermes-ai"),
            ("设置", "设置", "settings"),
        ]:
            page.set_viewport_size({"width": 390, "height": 844})
            button = nav.get_by_role("button", name=button_name, exact=True)
            assert button.count() == 1
            button.click()
            expect(page.locator("#pageTitle")).to_have_text(heading_name)
            assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
            page.screenshot(path=str(SCREENSHOT_DIR / f"{filename}-390x844.png"), full_page=True)

        assert page_errors == []
        browser.close()


if __name__ == "__main__":
    run()
    print(f"UI 2.0 visual evidence: {SCREENSHOT_DIR}")
