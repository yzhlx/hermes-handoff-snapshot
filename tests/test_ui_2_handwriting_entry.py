"""Formal product-page regression coverage for the UI 2.0 handwriting workspace."""

import importlib.util
import threading
import unittest
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
STATIC_MODULE = ROOT / "outputs" / "learning-os-static.py"


def load_static_module():
    spec = importlib.util.spec_from_file_location("learning_os_static", STATIC_MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def draw_pen_stroke(page, points, pointer_id=71):
    page.locator("#handwritingCanvas").evaluate(
        """
        (canvas, data) => {
          const rect = canvas.getBoundingClientRect();
          const fire = (type, point) => canvas.dispatchEvent(new PointerEvent(type, {
            bubbles: true,
            cancelable: true,
            pointerId: data.pointerId,
            pointerType: 'pen',
            isPrimary: true,
            button: type === 'pointerup' ? -1 : 0,
            buttons: type === 'pointerup' ? 0 : 1,
            clientX: rect.left + point.x,
            clientY: rect.top + point.y,
            pressure: type === 'pointerup' ? 0 : point.pressure,
          }));
          fire('pointerdown', data.points[0]);
          data.points.slice(1, -1).forEach(point => fire('pointermove', point));
          fire('pointerup', data.points[data.points.length - 1]);
        }
        """,
        {"points": points, "pointerId": pointer_id},
    )


class Ui2HandwritingEntryTests(unittest.TestCase):
    """The product root, not the legacy prototype, owns this regression."""

    @classmethod
    def setUpClass(cls):
        cls.static = load_static_module()
        cls.server = cls.static.create_server("127.0.0.1", 0, ROOT / "outputs")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_workspace_script_is_a_cache_safe_static_asset(self):
        with urllib.request.urlopen(
            f"{self.url}learning-os-handwriting-workspace.js", timeout=5
        ) as response:
            source = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertIn("javascript", response.headers["Content-Type"])
            self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")
        self.assertIn("__learningOSHandwriting", source)

    def test_product_entry_supports_ink_tools_and_workspace_lifecycle(self):
        page_errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.route(
                "**/api/v2/**",
                lambda route: route.fulfill(
                    json={"items": [], "tasks": [], "next_tasks": [], "review": {"items": []}}
                ),
            )
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            try:
                page.goto(self.url, wait_until="domcontentloaded")
                self.assertNotIn("learning-os-ui-prototype.html", page.url)

                entry = page.get_by_role("button", name="手写画布", exact=True)
                expect(entry).to_be_visible()
                entry.click()
                expect(page.locator("#handwritingCanvas")).to_be_visible()
                expect(page.locator("#drawTool")).to_be_visible()
                expect(page.locator("#recognizeAnswer")).to_be_visible()
                self.assertTrue(page.evaluate("() => Boolean(window.__learningOSHandwriting)"))

                page.locator("#strokeSize").evaluate(
                    "input => { input.value = '6'; input.dispatchEvent(new Event('input', {bubbles: true})); }"
                )
                draw_pen_stroke(
                    page,
                    [
                        {"x": 100, "y": 120, "pressure": 0.6},
                        {"x": 155, "y": 150, "pressure": 0.7},
                        {"x": 210, "y": 180, "pressure": 0.5},
                    ],
                )
                after_draw = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
                first_stroke = after_draw["pages"][0]["strokes"][0]
                self.assertEqual(first_stroke["color"], "#172127")
                self.assertEqual(first_stroke["baseWidth"], 6)

                page.locator("#eraserTool").click()
                draw_pen_stroke(
                    page,
                    [
                        {"x": 155, "y": 150, "pressure": 0.5},
                        {"x": 160, "y": 155, "pressure": 0.5},
                    ],
                    pointer_id=72,
                )
                after_erase = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
                self.assertNotEqual(after_erase["pages"][0]["strokes"], after_draw["pages"][0]["strokes"])
                page.locator("#undoStroke").click()
                self.assertEqual(
                    page.evaluate("window.__learningOSHandwriting.debugSnapshot()")["pages"][0]["strokes"],
                    after_draw["pages"][0]["strokes"],
                )
                page.locator("#redoStroke").click()
                self.assertEqual(
                    page.evaluate("window.__learningOSHandwriting.debugSnapshot()")["pages"][0]["strokes"],
                    after_erase["pages"][0]["strokes"],
                )

                page.locator("#moreCanvasActions").click()
                page.locator("#clearPage").click()
                expect(page.locator("#clearConfirm")).to_be_visible()
                page.locator("#confirmClear").click()
                self.assertEqual(
                    page.evaluate("window.__learningOSHandwriting.debugSnapshot()")["pages"][0]["strokes"], []
                )

                page.locator("#drawTool").click()
                draw_pen_stroke(
                    page,
                    [
                        {"x": 80, "y": 100, "pressure": 0.5},
                        {"x": 130, "y": 130, "pressure": 0.5},
                    ],
                    pointer_id=73,
                )
                page.locator("#closeModal").click()
                page.get_by_role("button", name="周计划", exact=True).click()
                entry.click()
                before_reentry = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
                draw_pen_stroke(
                    page,
                    [
                        {"x": 230, "y": 160, "pressure": 0.6},
                        {"x": 280, "y": 190, "pressure": 0.6},
                    ],
                    pointer_id=74,
                )
                after_reentry = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
                self.assertEqual(
                    len(after_reentry["pages"][0]["strokes"]),
                    len(before_reentry["pages"][0]["strokes"]) + 1,
                    "re-entering the workspace must not duplicate Pointer listeners",
                )

                page.reload(wait_until="domcontentloaded")
                page.get_by_role("button", name="手写画布", exact=True).click()
                restored = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
                self.assertGreaterEqual(len(restored["pages"][0]["strokes"]), 2)
                self.assertEqual(page_errors, [])
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
