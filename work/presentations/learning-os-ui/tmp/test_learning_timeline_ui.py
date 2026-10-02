import json
import os
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


URL = os.environ.get("LEARNING_OS_TEST_URL", "http://127.0.0.1:4173/")


def run():
    timeline_tasks = [
        {
            "id": "timeline-completed",
            "title": "QA_TEST_已完成的主动回忆",
            "status": "completed",
            "priority": "medium",
            "estimated_minutes": 15,
            "start_time": "08:30",
        },
        {
            "id": "timeline-current",
            "title": "QA_TEST_当前卷积概念回忆",
            "status": "active",
            "priority": "high",
            "estimated_minutes": 35,
            "start_time": None,
        },
        {
            "id": "timeline-planned",
            "title": "QA_TEST_一个很长的未来学习任务标题，用于验证时间轴在窄窗口中不会压坏布局或产生横向溢出",
            "status": "planned",
            "priority": "low",
            "estimated_minutes": 45,
            "start_time": None,
        },
    ]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page_errors = []

        def api_route(route):
            path = urlparse(route.request.url).path
            payload = {"items": []}
            if path.endswith("/dashboard"):
                payload = {
                    "tasks": timeline_tasks,
                    "current_task": timeline_tasks[1],
                    "next_tasks": [timeline_tasks[2]],
                    "completed_count": 1,
                    "remaining_count": 2,
                    "review": {"items": []},
                }
            elif path.endswith("/status"):
                payload = {"items": []}
            route.fulfill(
                status=200,
                content_type="application/json; charset=utf-8",
                body=json.dumps(payload),
            )

        page.route("http://127.0.0.1:4174/api/v2/**", api_route)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(URL, wait_until="networkidle")

        timeline = page.locator("#todayTimeline")
        expect(timeline).to_contain_text("08:30")
        expect(timeline).to_contain_text("待安排")
        expect(timeline).not_to_contain_text("稍后")
        expect(timeline).not_to_contain_text("现在")
        current = timeline.locator('[data-state="current"]')
        assert current.get_attribute("aria-current") == "step"
        expect(current).to_contain_text("当前任务")

        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
        expect(timeline).to_contain_text("QA_TEST_一个很长的未来学习任务标题")
        assert page_errors == []
        browser.close()


if __name__ == "__main__":
    run()
    print("Learning timeline UI regression: OK")
