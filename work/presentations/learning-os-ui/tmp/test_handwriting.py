import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


URL = os.environ.get(
    "LEARNING_OS_URL",
    "http://127.0.0.1:4173/learning-os-ui-prototype.html",
)


def draw_stroke(page, points):
    page.locator("#handwritingCanvas").evaluate(
        """
        (canvas, points) => {
          const rect = canvas.getBoundingClientRect();
          const fire = (type, point) => canvas.dispatchEvent(new PointerEvent(type, {
            bubbles: true,
            cancelable: true,
            pointerId: 7,
            pointerType: 'pen',
            isPrimary: true,
            button: type === 'pointerup' ? -1 : 0,
            buttons: type === 'pointerup' ? 0 : 1,
            clientX: rect.left + point.x,
            clientY: rect.top + point.y,
            pressure: point.pressure,
          }));
          fire('pointerdown', points[0]);
          points.slice(1, -1).forEach(point => fire('pointermove', point));
          fire('pointerup', points[points.length - 1]);
        }
        """,
        points,
    )


def erase_stroke(page, points):
    page.locator("#eraserTool").click()
    draw_stroke(page, points)


def dispatch_pointer(
    page,
    event_type,
    *,
    pointer_type,
    x,
    y,
    width=1,
    height=1,
    pointer_id=19,
):
    page.locator("#handwritingCanvas").evaluate(
        """
        (canvas, data) => {
          const rect = canvas.getBoundingClientRect();
          canvas.dispatchEvent(new PointerEvent(data.eventType, {
            bubbles: true,
            cancelable: true,
            pointerId: data.pointerId,
            pointerType: data.pointerType,
            isPrimary: true,
            button: data.eventType === 'pointerup' ? -1 : 0,
            buttons: data.eventType === 'pointerup' ? 0 : 1,
            clientX: rect.left + data.x,
            clientY: rect.top + data.y,
            width: data.width,
            height: data.height,
            pressure: data.eventType === 'pointerup' ? 0 : 0.5,
          }));
        }
        """,
        {
            "eventType": event_type,
            "pointerType": pointer_type,
            "pointerId": pointer_id,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        },
    )


def open_workspace(page):
    page.goto(URL, wait_until="networkidle")
    page.locator('[data-action="recall"]').first.click()
    expect(page.locator("#handwritingCanvas")).to_be_visible()


def open_canvas_menu(page):
    page.locator("#moreCanvasActions").click()
    expect(page.locator("#canvasMenu")).to_be_visible()


def clear_current_page(page):
    open_canvas_menu(page)
    page.locator("#clearPage").click()
    page.locator("#confirmClear").click()


def run():
    output_dir = Path(__file__).with_name("downloads")
    output_dir.mkdir(exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1024, "height": 768},
            accept_downloads=True,
            has_touch=True,
        )
        errors = []
        submitted_evidence = []
        recognition_requests = []
        poll_count = {"value": 0}
        page.on("pageerror", lambda error: errors.append(str(error)))

        def handle_recognition(route):
            recognition_requests.append(json.loads(route.request.post_data))
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "request_id": "resp_test",
                        "model": "gpt-5.6-luna",
                        "confidence": None,
                        "date": None,
                        "sections": [
                            {"title": "信号", "transcript": "ROC 为收敛域。"}
                        ],
                        "critical_formulas": [
                            {
                                "latex": "X(s)=1/(s+3)",
                                "meaning": "拉普拉斯变换",
                            }
                        ],
                        "diagram_notes": ["门函数图"],
                        "uncertain": ["积分下限需确认"],
                    },
                    ensure_ascii=False,
                ),
            )

        page.route(
            "http://127.0.0.1:4174/api/v1/handwriting/recognize",
            handle_recognition,
        )

        def handle_evidence_submit(route):
            request = route.request
            submitted_evidence.append(json.loads(request.post_data))
            route.fulfill(
                status=201,
                content_type="application/json",
                body=json.dumps(
                    {
                        "event_id": "11111111-1111-4111-8111-111111111111",
                        "evidence_id": "22222222-2222-4222-8222-222222222222",
                        "status": "assessing",
                        "artifact_integrity": "verified",
                    }
                ),
            )

        def handle_evidence_detail(route):
            poll_count["value"] += 1
            assessing = poll_count["value"] == 1
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "event_id": "11111111-1111-4111-8111-111111111111",
                        "evidence_id": "22222222-2222-4222-8222-222222222222",
                        "status": "assessing" if assessing else "recorded",
                        "artifact_integrity": "verified",
                        "assessment": None if assessing else {
                            "assessment_id": "33333333-3333-4333-8333-333333333333",
                            "summary": "核心结论正确",
                            "correct_points": ["写出了 ROC 边界"],
                            "missing_points": ["未讨论双边信号"],
                            "incorrect_points": [],
                            "formula_feedback": ["X(s) 正确"],
                            "f_state": "F3",
                            "recommended_action": "补充后再答一次",
                            "uncertain": [],
                        },
                        "failure": None,
                    },
                    ensure_ascii=False,
                ),
            )

        page.route(
            "http://127.0.0.1:4174/api/v1/evidence",
            handle_evidence_submit,
        )
        page.route(
            "http://127.0.0.1:4174/api/v1/evidence/22222222-2222-4222-8222-222222222222",
            handle_evidence_detail,
        )
        open_workspace(page)

        expect(page.locator("#drawTool")).to_have_attribute("aria-pressed", "true")
        expect(page.locator("#pageIndicator")).to_have_text("1 / 1")
        assert page.locator(".answer-footer #exportPng").count() == 0
        assert page.locator(".answer-footer #exportJson").count() == 0
        open_canvas_menu(page)
        expect(page.locator("#clearPage")).to_be_visible()
        expect(page.locator("#exportPng")).to_be_visible()
        expect(page.locator("#exportJson")).to_be_visible()
        page.locator("#moreCanvasActions").click()

        page.locator("#zoomIn").click()
        expect(page.locator("#zoomLevel")).to_have_text("125%")
        zoomed = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert zoomed["view"]["zoom"] == 1.25

        dispatch_pointer(
            page,
            "pointerdown",
            pointer_type="touch",
            x=220,
            y=180,
            width=10,
            height=10,
            pointer_id=20,
        )
        dispatch_pointer(
            page,
            "pointermove",
            pointer_type="touch",
            x=250,
            y=210,
            width=10,
            height=10,
            pointer_id=20,
        )
        dispatch_pointer(
            page,
            "pointerup",
            pointer_type="touch",
            x=250,
            y=210,
            width=10,
            height=10,
            pointer_id=20,
        )
        touch_panned = page.evaluate(
            "window.__learningOSHandwriting.debugSnapshot()"
        )
        assert touch_panned["view"] != zoomed["view"]

        page.locator("#resetView").click()
        dispatch_pointer(
            page,
            "pointerdown",
            pointer_type="touch",
            x=150,
            y=180,
            width=10,
            height=10,
            pointer_id=21,
        )
        dispatch_pointer(
            page,
            "pointerdown",
            pointer_type="touch",
            x=270,
            y=180,
            width=10,
            height=10,
            pointer_id=22,
        )
        dispatch_pointer(
            page,
            "pointermove",
            pointer_type="touch",
            x=330,
            y=180,
            width=10,
            height=10,
            pointer_id=22,
        )
        pinched = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert pinched["view"]["zoom"] > 1
        dispatch_pointer(
            page,
            "pointerup",
            pointer_type="touch",
            x=150,
            y=180,
            width=10,
            height=10,
            pointer_id=21,
        )
        dispatch_pointer(
            page,
            "pointerup",
            pointer_type="touch",
            x=330,
            y=180,
            width=10,
            height=10,
            pointer_id=22,
        )

        page.locator("#resetView").click()
        page.locator("#zoomIn").click()
        dispatch_pointer(
            page,
            "pointerdown",
            pointer_type="touch",
            x=200,
            y=180,
            width=10,
            height=10,
            pointer_id=30,
        )
        dispatch_pointer(
            page,
            "pointerdown",
            pointer_type="pen",
            x=100,
            y=100,
            pointer_id=31,
        )
        pen_down_view = page.evaluate(
            "window.__learningOSHandwriting.debugSnapshot().view"
        )
        dispatch_pointer(
            page,
            "pointermove",
            pointer_type="touch",
            x=260,
            y=230,
            width=10,
            height=10,
            pointer_id=30,
        )
        during_pen_view = page.evaluate(
            "window.__learningOSHandwriting.debugSnapshot().view"
        )
        assert during_pen_view == pen_down_view
        dispatch_pointer(
            page,
            "pointerup",
            pointer_type="pen",
            x=130,
            y=120,
            pointer_id=31,
        )
        dispatch_pointer(
            page,
            "pointerup",
            pointer_type="touch",
            x=260,
            y=230,
            width=10,
            height=10,
            pointer_id=30,
        )
        clear_current_page(page)

        page.locator("#resetView").click()
        page.locator("#zoomIn").click()
        zoomed = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")

        canvas_width = page.locator("#handwritingCanvas").evaluate(
            "canvas => canvas.getBoundingClientRect().width"
        )
        draw_stroke(
            page,
            [
                {"x": 200, "y": 150, "pressure": 0.5},
                {"x": 240, "y": 170, "pressure": 0.5},
            ],
        )
        zoom_draw = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        first_zoom_point = zoom_draw["pages"][0]["strokes"][0]["points"][0]
        expected_x = (
            (200 - zoomed["view"]["panX"])
            / zoomed["view"]["zoom"]
        )
        assert abs(first_zoom_point["x"] - expected_x) < 0.2

        clear_current_page(page)
        page.locator("#resetView").click()
        expect(page.locator("#zoomLevel")).to_have_text("100%")

        before_touch = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        dispatch_pointer(
            page,
            "pointerdown",
            pointer_type="touch",
            x=100,
            y=100,
            width=70,
            height=70,
        )
        dispatch_pointer(
            page,
            "pointermove",
            pointer_type="touch",
            x=160,
            y=160,
            width=70,
            height=70,
        )
        dispatch_pointer(
            page,
            "pointerup",
            pointer_type="touch",
            x=160,
            y=160,
            width=70,
            height=70,
        )
        after_touch = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert after_touch["pages"] == before_touch["pages"]
        assert after_touch["view"] == before_touch["view"]

        draw_stroke(
            page,
            [
                {"x": 90, "y": 90, "pressure": 0.2},
                {"x": 125, "y": 112, "pressure": 0.55},
                {"x": 165, "y": 135, "pressure": 0.9},
            ],
        )
        snapshot = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert len(snapshot["pages"][0]["strokes"]) == 1
        pressures = [point["pressure"] for point in snapshot["pages"][0]["strokes"][0]["points"]]
        assert min(pressures) < max(pressures), pressures

        page.locator("#undoStroke").click()
        snapshot = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert len(snapshot["pages"][0]["strokes"]) == 0
        expect(page.locator("#redoStroke")).to_be_enabled()

        page.locator("#redoStroke").click()
        snapshot = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert len(snapshot["pages"][0]["strokes"]) == 1

        clear_current_page(page)
        draw_stroke(
            page,
            [
                {"x": 90 + index * 18, "y": 110, "pressure": 0.55}
                for index in range(10)
            ],
        )
        before_erase = page.evaluate(
            "window.__learningOSHandwriting.debugSnapshot()"
        )
        erase_stroke(
            page,
            [
                {"x": 160, "y": 100, "pressure": 0.5},
                {"x": 160, "y": 120, "pressure": 0.5},
            ],
        )
        erased = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert len(erased["pages"][0]["strokes"]) == 2
        assert all(
            stroke["tool"] == "draw"
            for stroke in erased["pages"][0]["strokes"]
        )

        page.locator("#undoStroke").click()
        restored_erase = page.evaluate(
            "window.__learningOSHandwriting.debugSnapshot()"
        )
        assert (
            restored_erase["pages"][0]["strokes"]
            == before_erase["pages"][0]["strokes"]
        )

        page.locator("#redoStroke").click()
        redone_erase = page.evaluate(
            "window.__learningOSHandwriting.debugSnapshot()"
        )
        assert redone_erase["pages"][0]["strokes"] == erased["pages"][0]["strokes"]
        page.locator("#undoStroke").click()
        page.locator("#drawTool").click()

        clear_current_page(page)
        draw_stroke(
            page,
            [
                {"x": 90, "y": 110, "pressure": 0.55},
                {"x": 250, "y": 110, "pressure": 0.55},
            ],
        )
        sparse_before = page.evaluate(
            "window.__learningOSHandwriting.debugSnapshot()"
        )
        erase_stroke(
            page,
            [
                {"x": 170, "y": 100, "pressure": 0.5},
                {"x": 170, "y": 120, "pressure": 0.5},
            ],
        )
        sparse_erased = page.evaluate(
            "window.__learningOSHandwriting.debugSnapshot()"
        )
        assert len(sparse_erased["pages"][0]["strokes"]) == 2
        page.locator("#undoStroke").click()
        sparse_restored = page.evaluate(
            "window.__learningOSHandwriting.debugSnapshot()"
        )
        assert (
            sparse_restored["pages"][0]["strokes"]
            == sparse_before["pages"][0]["strokes"]
        )
        erase_stroke(
            page,
            [
                {"x": 170, "y": 60, "pressure": 0.5},
                {"x": 170, "y": 160, "pressure": 0.5},
            ],
        )
        path_erased = page.evaluate(
            "window.__learningOSHandwriting.debugSnapshot()"
        )
        assert len(path_erased["pages"][0]["strokes"]) == 2
        page.locator("#undoStroke").click()
        page.locator("#drawTool").click()

        png_before_resize = page.evaluate(
            "renderPageDataUrl(currentPage(), 800, 600)"
        )
        page.set_viewport_size({"width": 760, "height": 768})
        page.wait_for_timeout(100)
        png_after_resize = page.evaluate(
            "renderPageDataUrl(currentPage(), 800, 600)"
        )
        assert png_after_resize == png_before_resize

        page.locator("#zoomIn").click()
        page.locator("#zoomIn").click()
        page.locator("#panTool").click()
        dispatch_pointer(
            page,
            "pointerdown",
            pointer_type="mouse",
            x=300,
            y=180,
            pointer_id=40,
        )
        dispatch_pointer(
            page,
            "pointermove",
            pointer_type="mouse",
            x=40,
            y=60,
            pointer_id=40,
        )
        dispatch_pointer(
            page,
            "pointerup",
            pointer_type="mouse",
            x=40,
            y=60,
            pointer_id=40,
        )
        page.set_viewport_size({"width": 520, "height": 768})
        page.wait_for_timeout(100)
        resized_view = page.evaluate(
            """
            () => {
              const rect = document.querySelector('#handwritingCanvas').getBoundingClientRect();
              const snapshot = window.__learningOSHandwriting.debugSnapshot();
              return {
                rect: { width: rect.width, height: rect.height },
                view: snapshot.view,
                bounds: snapshot.pages[snapshot.currentPage].bounds,
              };
            }
            """
        )
        assert resized_view["view"]["panX"] >= min(
            0,
            resized_view["rect"]["width"]
            - resized_view["bounds"]["maxX"] * resized_view["view"]["zoom"]
            - 140,
        )
        assert resized_view["view"]["panY"] >= min(
            0,
            resized_view["rect"]["height"]
            - resized_view["bounds"]["maxY"] * resized_view["view"]["zoom"]
            - 140,
        )
        page.set_viewport_size({"width": 1024, "height": 768})
        page.wait_for_timeout(100)
        page.locator("#resetView").click()
        page.locator("#drawTool").click()

        page.locator("#addPage").click()
        expect(page.locator("#pageIndicator")).to_have_text("2 / 2")
        draw_stroke(
            page,
            [
                {"x": 210, "y": 80, "pressure": 0.4},
                {"x": 215, "y": 130, "pressure": 0.7},
                {"x": 220, "y": 185, "pressure": 0.5},
            ],
        )
        snapshot = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert [len(item["strokes"]) for item in snapshot["pages"]] == [1, 1]

        with page.expect_download() as json_download_info:
            open_canvas_menu(page)
            page.locator("#exportJson").click()
        json_download = json_download_info.value
        json_path = output_dir / json_download.suggested_filename
        json_download.save_as(json_path)
        exported = json.loads(json_path.read_text(encoding="utf-8"))
        assert exported["schemaVersion"] == 2
        assert exported["coordinateSpace"] == "world-css-px"
        assert len(exported["pages"]) == 2
        assert exported["pages"][0]["strokes"][0]["points"][0]["pressure"] > 0

        with page.expect_download() as png_download_info:
            open_canvas_menu(page)
            page.locator("#exportPng").click()
        png_download = png_download_info.value
        png_path = output_dir / png_download.suggested_filename
        png_download.save_as(png_path)
        assert png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

        page.reload(wait_until="networkidle")
        page.locator('[data-action="recall"]').first.click()
        restored = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert [len(item["strokes"]) for item in restored["pages"]] == [1, 1]
        expect(page.locator("#pageIndicator")).to_have_text("1 / 2")

        page.evaluate(
            """
            () => {
              window.__nativeFetch = window.fetch;
              window.fetch = () => new Promise(resolve => {
                window.__resolveStaleRecognition = () => resolve({
                  ok: true,
                  json: async () => ({
                    request_id: 'resp_stale',
                    model: 'gpt-5.6-luna',
                    confidence: null,
                    sections: [{ title: '旧结果', transcript: '不应落地' }],
                    critical_formulas: [],
                    diagram_notes: [],
                    uncertain: [],
                  }),
                });
              });
            }
            """
        )
        page.locator("#recognizeAnswer").click()
        draw_stroke(
            page,
            [
                {"x": 230, "y": 155, "pressure": 0.5},
                {"x": 245, "y": 165, "pressure": 0.5},
            ],
        )
        page.evaluate(
            """
            () => {
              window.__resolveStaleRecognition();
              window.fetch = window.__nativeFetch;
            }
            """
        )
        expect(page.locator("#recognitionStatus")).to_contain_text("笔迹已变化")
        assert "不应落地" not in page.locator("#recognizedText").input_value()

        page.locator("#recognizeAnswer").click()
        expect(page.locator("#recognitionPanel")).to_be_visible()
        expect(page.locator("#recognitionStatus")).to_contain_text("识别完成")
        assert "ROC 为收敛域" in page.locator("#recognizedText").input_value()
        expect(page.locator("#recognizedText")).to_be_editable()
        expect(page.locator("#recognitionModel")).to_have_text("gpt-5.6-luna")
        expect(page.locator("#recognitionFormulas")).to_contain_text("X(s)=1/(s+3)")
        expect(page.locator("#recognitionUncertain")).to_contain_text("积分下限需确认")
        expect(page.locator("#transcriptConfirmed")).not_to_be_checked()
        recognition_payload = recognition_requests[-1]
        assert "png_data_url" not in recognition_payload
        assert len(recognition_payload["chunks"]) >= 2
        assert [item["index"] for item in recognition_payload["chunks"][:2]] == [0, 0]
        assert all(
            item["png_data_url"].startswith("data:image/png;base64,")
            for item in recognition_payload["chunks"]
        )

        page.evaluate(
            """
            () => {
              window.__nativeFetch = window.fetch;
              window.fetch = async () => ({
                ok: false,
                json: async () => ({ error: 'Vision service timed out; try again later' }),
              });
            }
            """
        )
        page.locator("#recognizeAnswer").click()
        expect(page.locator("#recognitionStatus")).to_contain_text(
            "\u8bc6\u522b\u670d\u52a1\u54cd\u5e94\u8d85\u65f6"
        )
        expect(page.locator("#recognitionServiceState")).to_contain_text(
            "\u670d\u52a1\u8d85\u65f6"
        )
        page.evaluate("() => { window.fetch = window.__nativeFetch; }")

        page.locator("#transcriptConfirmed").check()
        draw_stroke(
            page,
            [
                {"x": 260, "y": 180, "pressure": 0.5},
                {"x": 280, "y": 195, "pressure": 0.5},
            ],
        )
        expect(page.locator("#transcriptConfirmed")).not_to_be_checked()

        clear_current_page(page)
        page.locator("#nextPage").click()
        clear_current_page(page)
        recognition_count = len(recognition_requests)
        page.locator("#recognizeAnswer").click()
        expect(page.locator("#recognitionStatus")).to_contain_text("请先手写")
        assert len(recognition_requests) == recognition_count
        page.locator("#submitAnswer").click()
        expect(page.locator("#answerError")).to_be_visible()
        expect(page.locator("#modalBackdrop")).to_have_class("modal-backdrop open")

        draw_stroke(
            page,
            [
                {"x": 120, "y": 100, "pressure": 0.35},
                {"x": 155, "y": 120, "pressure": 0.6},
                {"x": 190, "y": 145, "pressure": 0.8},
            ],
        )
        page.locator("#recognizedText").fill("ROC 表示拉普拉斯变换的收敛域。")
        page.locator("#transcriptConfirmed").check()
        page.locator("#submitAnswer").click()
        expect(page.locator("#modalBackdrop")).to_have_class("modal-backdrop open")
        expect(page.locator("#submissionStatus")).to_contain_text("评估")
        expect(page.locator("#assessmentDrawer")).to_be_visible()
        expect(page.locator("#assessmentSummary")).to_have_text("核心结论正确", timeout=7000)
        expect(page.locator("#assessmentStateChange")).to_contain_text("F2 → F3")
        expect(page.locator("#assessmentCorrect")).to_contain_text("写出了 ROC 边界")
        expect(page.locator("#assessmentMissing")).to_contain_text("未讨论双边信号")
        expect(page.locator("#handwritingCanvas")).to_be_visible()
        assert len(submitted_evidence) == 1
        evidence = submitted_evidence[0]
        assert evidence["transcript_confirmed"] is True
        assert evidence["transcript"].startswith("ROC")
        assert evidence["handwriting"]["schemaVersion"] == 2
        assert evidence["images"][0]["png_data_url"].startswith("data:image/png;base64,")
        assert page.evaluate("localStorage.getItem('learning-os-last-evidence-demo')") is None

        recorded_snapshot = page.evaluate(
            "window.__learningOSHandwriting.debugSnapshot()"
        )
        page.once("dialog", lambda dialog: dialog.dismiss())
        page.locator("#answerAgain").click()
        assert page.evaluate(
            "window.__learningOSHandwriting.debugSnapshot()"
        )["pages"] == recorded_snapshot["pages"]
        expect(page.locator("#assessmentDrawer")).to_be_visible()
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#answerAgain").click()
        restarted = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
        assert all(not item["strokes"] for item in restarted["pages"])
        expect(page.locator("#assessmentDrawer")).to_be_hidden()

        failed_id = "44444444-4444-4444-8444-444444444444"
        retry_calls = {"value": 0}
        failed_polls = {"value": 0}

        def handle_failed_detail(route):
            failed_polls["value"] += 1
            recorded = retry_calls["value"] > 0
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "event_id": "55555555-5555-4555-8555-555555555555",
                        "evidence_id": failed_id,
                        "status": "recorded" if recorded else "failed",
                        "artifact_integrity": "verified",
                        "assessment": {
                            "assessment_id": "66666666-6666-4666-8666-666666666666",
                            "summary": "重试后评估成功",
                            "correct_points": ["结论有效"],
                            "missing_points": [],
                            "incorrect_points": [],
                            "formula_feedback": [],
                            "f_state": "F3",
                            "recommended_action": "继续复习",
                            "uncertain": [],
                        } if recorded else None,
                        "failure": None if recorded else {
                            "category": "upstream_error",
                            "retryable": True,
                        },
                    },
                    ensure_ascii=False,
                ),
            )

        def handle_retry(route):
            retry_calls["value"] += 1
            route.fulfill(
                status=202,
                content_type="application/json",
                body=json.dumps({"evidence_id": failed_id, "status": "assessing"}),
            )

        page.route(
            f"http://127.0.0.1:4174/api/v1/evidence/{failed_id}",
            handle_failed_detail,
        )
        page.route(
            f"http://127.0.0.1:4174/api/v1/evidence/{failed_id}/assessment/retry",
            handle_retry,
        )
        page.evaluate(
            "evidenceId => localStorage.setItem('learning-os-active-evidence-id', evidenceId)",
            failed_id,
        )
        page.reload(wait_until="networkidle")
        page.locator('[data-action="recall"]').first.click()
        expect(page.locator("#assessmentDrawer")).to_be_visible()
        expect(page.locator("#assessmentSummary")).to_contain_text("upstream_error")
        expect(page.locator("#retryAssessment")).to_be_visible()
        page.locator("#retryAssessment").click()
        expect(page.locator("#assessmentSummary")).to_have_text(
            "重试后评估成功", timeout=7000
        )
        assert retry_calls["value"] == 1

        pending_id = "77777777-7777-4777-8777-777777777777"
        pending_polls = {"value": 0}

        def handle_pending_detail(route):
            pending_polls["value"] += 1
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "event_id": "88888888-8888-4888-8888-888888888888",
                        "evidence_id": pending_id,
                        "status": "assessing",
                        "artifact_integrity": "verified",
                        "assessment": None,
                        "failure": None,
                    }
                ),
            )

        page.route(
            f"http://127.0.0.1:4174/api/v1/evidence/{pending_id}",
            handle_pending_detail,
        )
        page.evaluate(
            "evidenceId => localStorage.setItem('learning-os-active-evidence-id', evidenceId)",
            pending_id,
        )
        page.reload(wait_until="networkidle")
        page.locator('[data-action="recall"]').first.click()
        expect(page.locator("#assessmentDrawer")).to_be_visible()
        expect(page.locator("#assessmentStatusText")).to_have_text(
            "正在评估当前作答"
        )
        assert pending_polls["value"] == 1
        page.locator("#closeModal").click()
        page.wait_for_timeout(2300)
        assert pending_polls["value"] == 1

        page.evaluate("localStorage.removeItem('learning-os-active-evidence-id')")
        page.reload(wait_until="networkidle")
        page.locator('[data-action="recall"]').first.click()
        page.locator("#inputTabText").click()
        page.locator("#answer").fill("ROC 是拉普拉斯变换的收敛域。")
        page.locator("#submitAnswer").click()
        expect(page.locator("#assessmentSummary")).to_have_text(
            "核心结论正确", timeout=7000
        )
        typed_evidence = submitted_evidence[-1]
        assert typed_evidence["typed_answer"].startswith("ROC")
        assert typed_evidence["transcript"] is None
        assert typed_evidence["transcript_confirmed"] is False

        assert errors == [], errors
        browser.close()


if __name__ == "__main__":
    run()
    print("handwriting Playwright checks: OK")
