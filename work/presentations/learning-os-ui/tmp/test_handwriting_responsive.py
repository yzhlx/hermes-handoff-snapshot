import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


URL = os.environ.get(
    "LEARNING_OS_URL",
    "http://127.0.0.1:4173/learning-os-ui-prototype.html",
)
VIEWPORTS = [(1440, 900), (768, 1024), (375, 667)]
EVIDENCE_ID = "99999999-9999-4999-8999-999999999999"
PENDING_EVIDENCE_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
FAILED_EVIDENCE_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"


def run():
    screenshot_dir = Path(__file__).with_name("handwriting-verify")
    screenshot_dir.mkdir(exist_ok=True)
    failures = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for width, height in VIEWPORTS:
            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=2 if width <= 768 else 1,
                has_touch=width <= 768,
            )
            page = context.new_page()
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.route(
                f"http://127.0.0.1:4174/api/v1/evidence/{EVIDENCE_ID}",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "event_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                            "evidence_id": EVIDENCE_ID,
                            "status": "recorded",
                            "artifact_integrity": "verified",
                            "assessment": {
                                "assessment_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                                "summary": "结论正确，继续补充时域与收敛域的对应关系。",
                                "correct_points": ["说明了 ROC 是收敛域"],
                                "missing_points": ["补充左右边信号的区别"],
                                "incorrect_points": [],
                                "formula_feedback": ["X(s)=1/(s+3) 的极点判断正确"],
                                "f_state": "F3",
                                "recommended_action": "稍后再答一次",
                                "uncertain": [],
                            },
                            "failure": None,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
            page.route(
                f"http://127.0.0.1:4174/api/v1/evidence/{PENDING_EVIDENCE_ID}",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "event_id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
                            "evidence_id": PENDING_EVIDENCE_ID,
                            "status": "assessing",
                            "artifact_integrity": "verified",
                            "assessment": None,
                            "failure": None,
                        }
                    ),
                ),
            )
            page.route(
                f"http://127.0.0.1:4174/api/v1/evidence/{FAILED_EVIDENCE_ID}",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "event_id": "ffffffff-ffff-4fff-8fff-ffffffffffff",
                            "evidence_id": FAILED_EVIDENCE_ID,
                            "status": "failed",
                            "artifact_integrity": "verified",
                            "assessment": None,
                            "failure": {
                                "category": "upstream_error",
                                "retryable": True,
                            },
                        }
                    ),
                ),
            )
            page.goto(URL, wait_until="networkidle")
            page.locator('[data-action="recall"]').first.click()
            expect(page.locator("#handwritingCanvas")).to_be_visible()

            before_png = page.locator("#handwritingCanvas").evaluate(
                "canvas => canvas.toDataURL('image/png')"
            )
            page.locator("#handwritingCanvas").evaluate(
                """
                canvas => {
                  const rect = canvas.getBoundingClientRect();
                  const point = (type, x, y) => canvas.dispatchEvent(new PointerEvent(type, {
                    bubbles: true,
                    cancelable: true,
                    pointerId: 91,
                    pointerType: 'pen',
                    isPrimary: true,
                    button: type === 'pointerup' ? -1 : 0,
                    buttons: type === 'pointerup' ? 0 : 1,
                    clientX: rect.left + x,
                    clientY: rect.top + y,
                    pressure: type === 'pointerup' ? 0 : .6,
                  }));
                  point('pointerdown', 70, 80);
                  point('pointermove', 120, 110);
                  point('pointerup', 170, 140);
                }
                """
            )
            after_png = page.locator("#handwritingCanvas").evaluate(
                "canvas => canvas.toDataURL('image/png')"
            )
            if before_png == after_png:
                failures.append(f"{width}x{height}: canvas stayed blank after drawing")

            layout = page.evaluate(
                """
                () => {
                  const viewport = { width: innerWidth, height: innerHeight };
                  const modal = document.querySelector('.modal').getBoundingClientRect();
                  const canvas = document.querySelector('#handwritingCanvas').getBoundingClientRect();
                  const submit = document.querySelector('#submitAnswer').getBoundingClientRect();
                  const zoom = document.querySelector('#zoomLevel').getBoundingClientRect();
                  const pan = document.querySelector('#panTool').getBoundingClientRect();
                  const recognize = document.querySelector('#recognizeAnswer').getBoundingClientRect();
                  const toolbarControls = [...document.querySelectorAll('.answer-toolbar button')]
                    .filter(item => item.offsetParent !== null)
                    .map(item => {
                      const box = item.getBoundingClientRect();
                      return {
                        id: item.id,
                        left: box.left,
                        right: box.right,
                        top: box.top,
                        bottom: box.bottom,
                        clientWidth: item.clientWidth,
                        clientHeight: item.clientHeight,
                        scrollWidth: item.scrollWidth,
                        scrollHeight: item.scrollHeight,
                      };
                    });
                  const toolbar = document.querySelector('.answer-toolbar').getBoundingClientRect();
                  const compactTools = ['drawTool', 'eraserTool', 'panTool', 'resetView'].map(id => {
                    const item = document.getElementById(id);
                    return {
                      id,
                      fontSize: getComputedStyle(item).fontSize,
                      icon: getComputedStyle(item, '::after').content,
                    };
                  });
                  const inputTabs = [...document.querySelectorAll('.segmented button')].map(item => ({
                    id: item.id,
                    whiteSpace: getComputedStyle(item).whiteSpace,
                  }));
                  return {
                    viewport,
                    documentWidth: document.documentElement.scrollWidth,
                    modal: { left: modal.left, right: modal.right, top: modal.top, bottom: modal.bottom },
                    canvas: { width: canvas.width, height: canvas.height },
                    submit: { left: submit.left, right: submit.right },
                    controls: {
                      zoom: { left: zoom.left, right: zoom.right },
                      pan: { left: pan.left, right: pan.right },
                      recognize: { left: recognize.left, right: recognize.right },
                    },
                    toolbarControls,
                    toolbar: { height: toolbar.height },
                    compactTools,
                    inputTabs,
                  };
                }
                """
            )
            if layout["documentWidth"] > width + 1:
                failures.append(f"{width}x{height}: document overflows horizontally")
            if layout["modal"]["left"] < -1 or layout["modal"]["right"] > width + 1:
                failures.append(f"{width}x{height}: modal is outside viewport")
            if layout["canvas"]["width"] < 300 or layout["canvas"]["height"] < 300:
                failures.append(f"{width}x{height}: canvas is too small: {layout['canvas']}")
            if layout["canvas"]["height"] < height * 0.6:
                failures.append(
                    f"{width}x{height}: canvas uses less than 60% of viewport height"
                )
            if layout["submit"]["left"] < -1 or layout["submit"]["right"] > width + 1:
                failures.append(f"{width}x{height}: submit button is clipped")
            for control, bounds in layout["controls"].items():
                if bounds["left"] < -1 or bounds["right"] > width + 1:
                    failures.append(
                        f"{width}x{height}: {control} control is clipped: {bounds}"
                    )
            for bounds in layout["toolbarControls"]:
                if (
                    bounds["left"] < -1
                    or bounds["right"] > width + 1
                    or bounds["top"] < -1
                    or bounds["bottom"] > height + 1
                ):
                    failures.append(
                        f"{width}x{height}: toolbar control is clipped: {bounds}"
                    )
                if (
                    bounds["scrollWidth"] > bounds["clientWidth"] + 1
                    or bounds["scrollHeight"] > bounds["clientHeight"] + 1
                ):
                    failures.append(
                        f"{width}x{height}: toolbar label overflows: {bounds['id']}"
                    )
            toolbar_limit = 70 if width >= 768 else 150
            if layout["toolbar"]["height"] > toolbar_limit:
                failures.append(
                    f"{width}x{height}: toolbar is too tall: {layout['toolbar']['height']:.1f}px"
                )
            if width <= 920:
                for tool in layout["compactTools"]:
                    if tool["fontSize"] != "0px" or tool["icon"] in {"none", '""'}:
                        failures.append(
                            f"{width}x{height}: {tool['id']} is not in compact icon mode"
                        )
                for tab in layout["inputTabs"]:
                    if tab["whiteSpace"] != "nowrap":
                        failures.append(
                            f"{width}x{height}: {tab['id']} wraps vertically"
                        )

            page.evaluate(
                "evidenceId => localStorage.setItem('learning-os-active-evidence-id', evidenceId)",
                EVIDENCE_ID,
            )
            page.locator("#closeModal").click()
            page.locator('[data-action="recall"]').first.click()
            expect(page.locator("#assessmentSummary")).to_contain_text("结论正确")
            drawer_layout = page.evaluate(
                """
                () => {
                  const canvas = document.querySelector('#handwritingCanvas').getBoundingClientRect();
                  const drawer = document.querySelector('#assessmentDrawer').getBoundingClientRect();
                  const summary = document.querySelector('#assessmentSummary').getBoundingClientRect();
                  const sections = [...document.querySelectorAll('#assessmentDrawer .assessment-section')]
                    .map(item => item.getBoundingClientRect());
                  const actions = document.querySelector('#assessmentDrawer .drawer-actions').getBoundingClientRect();
                  return {
                    documentWidth: document.documentElement.scrollWidth,
                    canvas: { left: canvas.left, right: canvas.right, top: canvas.top, bottom: canvas.bottom },
                    drawer: { left: drawer.left, right: drawer.right, top: drawer.top, bottom: drawer.bottom },
                    summary: { top: summary.top, bottom: summary.bottom },
                    sections: sections.map(box => ({ top: box.top, bottom: box.bottom })),
                    actions: { top: actions.top, bottom: actions.bottom },
                  };
                }
                """
            )
            if drawer_layout["documentWidth"] > width + 1:
                failures.append(f"{width}x{height}: drawer causes horizontal overflow")
            if width > 920:
                visible_canvas_width = drawer_layout["drawer"]["left"] - drawer_layout["canvas"]["left"]
                if visible_canvas_width < 300:
                    failures.append(
                        f"{width}x{height}: drawer leaves only {visible_canvas_width:.1f}px of canvas"
                    )
            elif drawer_layout["drawer"]["top"] < drawer_layout["canvas"]["bottom"] - 1:
                failures.append(f"{width}x{height}: mobile drawer overlaps the writing canvas")
            ordered_blocks = [drawer_layout["summary"], *drawer_layout["sections"], drawer_layout["actions"]]
            for previous, current in zip(ordered_blocks, ordered_blocks[1:]):
                if current["top"] < previous["bottom"] - 1:
                    failures.append(f"{width}x{height}: assessment content overlaps")

            page.screenshot(
                path=screenshot_dir / f"handwriting-{width}x{height}.png",
                full_page=False,
            )
            page.locator("#assessmentDrawer").screenshot(
                path=screenshot_dir / f"assessment-{width}x{height}.png"
            )

            for evidence_id, state, expected in (
                (PENDING_EVIDENCE_ID, "assessing", "正在生成 Assessment"),
                (FAILED_EVIDENCE_ID, "failed", "upstream_error"),
            ):
                page.evaluate(
                    "evidenceId => localStorage.setItem('learning-os-active-evidence-id', evidenceId)",
                    evidence_id,
                )
                page.locator("#closeModal").click()
                page.locator('[data-action="recall"]').first.click()
                expect(page.locator("#assessmentSummary")).to_contain_text(expected)
                if state == "assessing":
                    expect(page.locator("#assessmentStateChange")).to_have_text("F2 → —")
                    expect(page.locator("#assessmentCorrect")).to_have_text("等待评估")
                    expect(page.locator("#assessmentId")).to_have_text("—")
                else:
                    expect(page.locator("#assessmentCorrect")).to_have_text("未生成")
                    expect(page.locator("#assessmentId")).to_have_text("—")
                    expect(page.locator("#retryAssessment")).to_be_visible()
                page.locator("#assessmentDrawer").screenshot(
                    path=screenshot_dir / f"assessment-{state}-{width}x{height}.png"
                )
            failures.extend(f"{width}x{height}: {error}" for error in page_errors)
            context.close()
        browser.close()

    if failures:
        raise AssertionError("\n".join(failures))


if __name__ == "__main__":
    run()
    print("responsive handwriting checks: OK")
