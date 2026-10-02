import os

from playwright.sync_api import sync_playwright


URL = os.environ.get(
    "LEARNING_OS_URL",
    "http://127.0.0.1:4173/learning-os-ui-prototype.html",
)


def dispatch_pen(page, event_type, x, y, pointer_id=71):
    page.locator("#handwritingCanvas").evaluate(
        """
        (canvas, data) => {
          const rect = canvas.getBoundingClientRect();
          canvas.dispatchEvent(new PointerEvent(data.type, {
            bubbles: true,
            cancelable: true,
            pointerId: data.pointerId,
            pointerType: 'pen',
            isPrimary: true,
            button: data.type === 'pointerup' ? -1 : 0,
            buttons: data.type === 'pointerup' ? 0 : 1,
            clientX: rect.left + data.x,
            clientY: rect.top + data.y,
            pressure: data.type === 'pointerup' ? 0 : .6,
          }));
        }
        """,
        {"type": event_type, "pointerId": pointer_id, "x": x, "y": y},
    )


def open_recall(page):
    page.goto(URL, wait_until="networkidle")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="networkidle")
    page.locator('[data-action="recall"]').first.click()


def run():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1024, "height": 768})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        open_recall(page)

        initial = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert initial["schemaVersion"] == 2
        assert initial["coordinateSpace"] == "world-css-px"
        initial_bounds = initial["pages"][0]["bounds"]
        canvas_width = page.locator("#handwritingCanvas").evaluate(
            "canvas => canvas.getBoundingClientRect().width"
        )

        dispatch_pen(page, "pointerdown", canvas_width - 20, 120)
        during = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert during["pages"][0]["bounds"] == initial_bounds
        dispatch_pen(page, "pointerup", canvas_width - 5, 140)
        after = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert after["pages"][0]["bounds"]["maxX"] == initial_bounds["maxX"] + 400
        assert after["pages"][0]["strokes"][0]["points"][0]["x"] > 1
        assert len(after["pages"][0]["undoStack"]) == 1, after["pages"][0]
        assert errors == [], errors

        page.locator("#undoStroke").click()
        undone = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert undone["pages"][0]["bounds"] == initial_bounds
        page.locator("#redoStroke").click()
        redone = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert redone["pages"][0]["bounds"] == after["pages"][0]["bounds"]

        assert page.locator("#fitContent").count() == 1
        page.locator("#fitContent").click()
        fitted = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert .5 <= fitted["view"]["zoom"] <= 3

        full_before = page.evaluate(
            "window.__learningOSHandwriting.renderFullContentDataUrl()"
        )
        view_before = page.evaluate(
            "window.__learningOSHandwriting.renderCurrentViewDataUrl()"
        )
        page.set_viewport_size({"width": 760, "height": 768})
        page.wait_for_timeout(100)
        full_after = page.evaluate(
            "window.__learningOSHandwriting.renderFullContentDataUrl()"
        )
        view_after = page.evaluate(
            "window.__learningOSHandwriting.renderCurrentViewDataUrl()"
        )
        assert full_after == full_before
        assert view_after != view_before
        chunks = page.evaluate(
            "window.__learningOSHandwriting.planCurrentRecognitionChunks()"
        )
        assert chunks
        assert [chunk["index"] for chunk in chunks] == list(range(len(chunks)))
        assert all(
            chunk["png_data_url"].startswith("data:image/png;base64,")
            for chunk in chunks
        )
        small_chunks = page.evaluate(
            """
            () => window.LearningOSCanvasModel.planRecognitionChunks(
              { minX: 0, minY: 0, maxX: 353, maxY: 262 },
              { maxWidth: 1600, maxHeight: 1600, overlap: 120, maxChunks: 12 }
            )
            """
        )
        assert len(small_chunks) == 1
        # Provider limits are caps, not target dimensions: narrow content must
        # keep its native resolution instead of being enlarged to 1600px.
        assert small_chunks[0]["outputWidth"] == 353
        assert small_chunks[0]["outputHeight"] == 262
        page.set_viewport_size({"width": 1024, "height": 768})
        page.wait_for_timeout(100)

        page.evaluate(
            """
            () => localStorage.setItem('learning-os-handwriting-draft-v1', JSON.stringify({
              schemaVersion: 1,
              pages: [{
                id: 'legacy-page',
                strokes: [{
                  id: 'legacy-stroke',
                  tool: 'draw',
                  color: '#172127',
                  baseWidth: 3,
                  points: [{ x: .25, y: .5, pressure: .7, t: 12 }],
                }],
              }],
            }))
            """
        )
        page.reload(wait_until="networkidle")
        page.locator('[data-action="recall"]').first.click()
        migrated = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert migrated["schemaVersion"] == 2
        assert migrated["pages"][0]["strokes"][0]["points"][0]["x"] == 300
        stored = page.evaluate(
            "JSON.parse(localStorage.getItem('learning-os-handwriting-draft-v1'))"
        )
        assert stored["schemaVersion"] == 2
        assert errors == [], errors
        browser.close()


if __name__ == "__main__":
    run()
    print("world canvas Playwright checks: OK")
