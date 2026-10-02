/* Extracted Canvas controller from the preserved handwriting reference; isolated for UI 2.0. */
(() => {
    const backdrop = document.getElementById('modalBackdrop');
    const canvas = document.getElementById('handwritingCanvas');
    const canvasEmpty = document.getElementById('canvasEmpty');
    const answerError = document.getElementById('answerError');
    const clearConfirm = document.getElementById('clearConfirm');
    const inputTabHandwrite = document.getElementById('inputTabHandwrite');
    const inputTabText = document.getElementById('inputTabText');
    const handwritingPanel = document.getElementById('handwritingPanel');
    const textAnswerPanel = document.getElementById('textAnswerPanel');
    const answer = document.getElementById('answer');
    const recognizedText = document.getElementById('recognizedText');
    const transcriptConfirmed = document.getElementById('transcriptConfirmed');
    const draftStorageKey = 'learning-os-handwriting-draft-v1';
    const CanvasModel = window.LearningOSCanvasModel;

    const makePage = () => CanvasModel.createPage({ width: 900, height: 700 });
    const handwritingState = {
      pages: [makePage()],
      currentPage: 0,
      tool: 'draw',
      inputMode: 'handwrite',
      baseWidth: 3.5,
      activeStroke: null,
      pointerId: null,
      gestureBefore: null,
      lastErasePoint: null,
      contentVersion: 0,
      view: { zoom: 1, panX: 0, panY: 0 },
      touches: new Map(),
      touchGesture: null,
      panGesture: null,
      penPointerId: null,
      lastPenAt: 0
    };

    const PEN_GUARD_MS = 800;
    const PALM_SIZE_PX = 35;

    function currentPage() {
      return handwritingState.pages[handwritingState.currentPage];
    }

    function drawPaper(ctx, bounds) {
      const width = bounds.maxX - bounds.minX;
      const height = bounds.maxY - bounds.minY;
      ctx.save();
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(bounds.minX, bounds.minY, width, height);
      ctx.strokeStyle = '#edf1ef';
      ctx.lineWidth = 1;
      const firstRule = bounds.minY + 54;
      for (let y = firstRule; y < bounds.maxY; y += 42) {
        ctx.beginPath();
        ctx.moveTo(bounds.minX, y + .5);
        ctx.lineTo(bounds.maxX, y + .5);
        ctx.stroke();
      }
      ctx.strokeStyle = '#f4d8d3';
      ctx.beginPath();
      ctx.moveTo(bounds.minX + Math.min(58, width * .09), bounds.minY);
      ctx.lineTo(bounds.minX + Math.min(58, width * .09), bounds.maxY);
      ctx.stroke();
      ctx.restore();
    }

    function drawStroke(ctx, stroke) {
      const points = stroke.points;
      if (!points.length) return;
      ctx.save();
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.strokeStyle = stroke.color || '#172127';
      ctx.fillStyle = ctx.strokeStyle;
      if (points.length === 1) {
        const point = points[0];
        const pressure = point.pressure || .5;
        const radius = stroke.baseWidth * .55 * (.55 + pressure);
        ctx.beginPath();
        ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
        return;
      }
      for (let index = 1; index < points.length; index += 1) {
        const start = points[index - 1];
        const end = points[index];
        const pressure = ((start.pressure || .5) + (end.pressure || .5)) / 2;
        ctx.lineWidth = stroke.baseWidth * (.55 + pressure);
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.stroke();
      }
      ctx.restore();
    }

    function renderPageToCanvas(targetCanvas, page, cssWidth, cssHeight, deviceScale = 1) {
      const context = targetCanvas.getContext('2d');
      const width = Math.max(1, cssWidth);
      const height = Math.max(1, cssHeight);
      targetCanvas.width = Math.round(width * deviceScale);
      targetCanvas.height = Math.round(height * deviceScale);
      context.setTransform(deviceScale, 0, 0, deviceScale, 0, 0);
      const worldWidth = Math.max(1, page.bounds.maxX - page.bounds.minX);
      const worldHeight = Math.max(1, page.bounds.maxY - page.bounds.minY);
      context.scale(width / worldWidth, height / worldHeight);
      context.translate(-page.bounds.minX, -page.bounds.minY);
      drawPaper(context, page.bounds);
      page.strokes.forEach(stroke => drawStroke(context, stroke));
      if (targetCanvas === canvas && handwritingState.activeStroke) {
        drawStroke(context, handwritingState.activeStroke);
      }
    }

    function renderCanvas() {
      const rect = canvas.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const deviceScale = Math.min(devicePixelRatio || 1, 2);
      const context = canvas.getContext('2d');
      canvas.width = Math.round(rect.width * deviceScale);
      canvas.height = Math.round(rect.height * deviceScale);
      context.setTransform(deviceScale, 0, 0, deviceScale, 0, 0);
      context.clearRect(0, 0, rect.width, rect.height);
      context.fillStyle = '#e8ece9';
      context.fillRect(0, 0, rect.width, rect.height);
      context.save();
      context.translate(handwritingState.view.panX, handwritingState.view.panY);
      context.scale(handwritingState.view.zoom, handwritingState.view.zoom);
      drawPaper(context, currentPage().bounds);
      currentPage().strokes.forEach(stroke => drawStroke(context, stroke));
      if (handwritingState.activeStroke) {
        drawStroke(context, handwritingState.activeStroke);
      }
      context.restore();
      canvasEmpty.classList.toggle('hidden', currentPage().strokes.length > 0 || Boolean(handwritingState.activeStroke));
    }

    function clampView() {
      const rect = canvas.getBoundingClientRect();
      const view = handwritingState.view;
      const bounds = currentPage().bounds;
      const margin = 140;
      const minPanX = rect.width - bounds.maxX * view.zoom - margin;
      const maxPanX = -bounds.minX * view.zoom + margin;
      const minPanY = rect.height - bounds.maxY * view.zoom - margin;
      const maxPanY = -bounds.minY * view.zoom + margin;
      view.panX = Math.min(maxPanX, Math.max(minPanX, view.panX));
      view.panY = Math.min(maxPanY, Math.max(minPanY, view.panY));
    }

    function updateViewControls() {
      document.getElementById('zoomLevel').textContent = `${Math.round(handwritingState.view.zoom * 100)}%`;
      document.getElementById('zoomOut').disabled = handwritingState.view.zoom <= .5;
      document.getElementById('zoomIn').disabled = handwritingState.view.zoom >= 3;
    }

    function setZoom(nextZoom, focalX, focalY) {
      const view = handwritingState.view;
      const zoom = Math.min(3, Math.max(.5, nextZoom));
      const ratio = zoom / view.zoom;
      view.panX = focalX - (focalX - view.panX) * ratio;
      view.panY = focalY - (focalY - view.panY) * ratio;
      view.zoom = zoom;
      clampView();
      updateViewControls();
      renderCanvas();
    }

    function resetView() {
      handwritingState.view = { zoom: 1, panX: 0, panY: 0 };
      updateViewControls();
      renderCanvas();
    }

    function updateControls() {
      const page = currentPage();
      document.getElementById('pageIndicator').textContent = `${handwritingState.currentPage + 1} / ${handwritingState.pages.length}`;
      document.getElementById('previousPage').disabled = handwritingState.currentPage === 0;
      document.getElementById('nextPage').disabled = handwritingState.currentPage === handwritingState.pages.length - 1;
      document.getElementById('deletePage').disabled = handwritingState.pages.length === 1;
      document.getElementById('undoStroke').disabled = page.undoStack.length === 0;
      document.getElementById('redoStroke').disabled = page.redoStack.length === 0;
      canvasEmpty.classList.toggle('hidden', page.strokes.length > 0);
    }

    function saveDraft() {
      const draft = {
        schemaVersion: 2,
        coordinateSpace: 'world-css-px',
        savedAt: new Date().toISOString(),
        pages: handwritingState.pages.map(page => ({
          id: page.id,
          bounds: page.bounds,
          strokes: page.strokes
        }))
      };
      localStorage.setItem(draftStorageKey, JSON.stringify(draft));
      document.getElementById('savedState').textContent = `本机暂存 · ${new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`;
    }

    function loadDraft() {
      try {
        const draft = JSON.parse(localStorage.getItem(draftStorageKey) || 'null');
        if (!draft || !Array.isArray(draft.pages) || !draft.pages.length) return;
        const migrated = CanvasModel.migrateDraft(draft, { width: 1200, height: 1800 });
        handwritingState.pages = migrated.pages;
        handwritingState.currentPage = 0;
        if (draft.savedAt) {
          const savedAt = new Date(draft.savedAt);
          document.getElementById('savedState').textContent = `已恢复暂存 · ${savedAt.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`;
        }
        if (draft.schemaVersion !== 2) saveDraft();
      } catch (_) {
        localStorage.removeItem(draftStorageKey);
      }
    }

    function pointFromEvent(event) {
      const rect = canvas.getBoundingClientRect();
      const view = handwritingState.view;
      const pressure = event.pressure > 0 ? event.pressure : .5;
      return {
        x: (event.clientX - rect.left - view.panX) / view.zoom,
        y: (event.clientY - rect.top - view.panY) / view.zoom,
        pressure: Number(pressure.toFixed(3)),
        t: Math.round(performance.now())
      };
    }

    function commitHistory(page, before, after) {
      if (JSON.stringify(before) === JSON.stringify(after)) return;
      page.undoStack.push({ before, after: JSON.parse(JSON.stringify(after)) });
      page.redoStack = [];
      markHandwritingChanged();
    }

    function invalidateTranscriptConfirmation() {
      if (!transcriptConfirmed.checked) return;
      transcriptConfirmed.checked = false;
      const status = document.getElementById('recognitionStatus');
      if (status) status.textContent = '笔迹已变化，请重新识别或核对转写。';
    }

    function markHandwritingChanged() {
      handwritingState.contentVersion += 1;
      invalidateTranscriptConfirmation();
    }

    function densifyPoints(points, radiusX, radiusY) {
      if (points.length < 2) return points;
      const dense = [points[0]];
      for (let index = 1; index < points.length; index += 1) {
        const start = points[index - 1];
        const end = points[index];
        const span = Math.hypot(
          (end.x - start.x) / radiusX,
          (end.y - start.y) / radiusY
        );
        const steps = Math.max(1, Math.ceil(span * 2));
        for (let step = 1; step <= steps; step += 1) {
          const ratio = step / steps;
          dense.push({
            x: start.x + (end.x - start.x) * ratio,
            y: start.y + (end.y - start.y) * ratio,
            pressure: start.pressure + (end.pressure - start.pressure) * ratio,
            t: Math.round(start.t + (end.t - start.t) * ratio)
          });
        }
      }
      return dense;
    }

    function eraseAt(point, radiusPx = 18) {
      const rect = canvas.getBoundingClientRect();
      const radiusX = radiusPx / handwritingState.view.zoom;
      const radiusY = radiusPx / handwritingState.view.zoom;
      currentPage().strokes = currentPage().strokes.flatMap(stroke => {
        const candidates = densifyPoints(stroke.points, radiusX, radiusY);
        const hits = candidates.map(candidate => Math.hypot(
          (candidate.x - point.x) / radiusX,
          (candidate.y - point.y) / radiusY
        ) <= 1);
        if (!hits.some(Boolean)) return [stroke];
        const fragments = [];
        let fragment = [];
        candidates.forEach((candidate, index) => {
          if (hits[index]) {
            if (fragment.length) fragments.push(fragment);
            fragment = [];
          } else {
            fragment.push(candidate);
          }
        });
        if (fragment.length) fragments.push(fragment);
        return fragments.map(points => ({
          ...stroke,
          id: globalThis.crypto?.randomUUID?.() || `stroke-${Date.now()}-${Math.random().toString(16).slice(2)}`,
          tool: 'draw',
          points
        }));
      });
    }

    function eraseAlongPath(start, end, radiusPx = 18) {
      const rect = canvas.getBoundingClientRect();
      const radiusX = radiusPx / handwritingState.view.zoom;
      const radiusY = radiusPx / handwritingState.view.zoom;
      const span = Math.hypot(
        (end.x - start.x) / radiusX,
        (end.y - start.y) / radiusY
      );
      const steps = Math.max(1, Math.ceil(span * 2));
      for (let step = 1; step <= steps; step += 1) {
        const ratio = step / steps;
        eraseAt({
          x: start.x + (end.x - start.x) * ratio,
          y: start.y + (end.y - start.y) * ratio
        }, radiusPx);
      }
    }

    function startStroke(event) {
      if (handwritingState.inputMode !== 'handwrite' || (event.pointerType === 'mouse' && event.button !== 0)) return;
      event.preventDefault();
      handwritingState.pointerId = event.pointerId;
      handwritingState.gestureBefore = CanvasModel.snapshotPage(currentPage());
      if (handwritingState.tool === 'eraser') {
        handwritingState.lastErasePoint = pointFromEvent(event);
        eraseAt(handwritingState.lastErasePoint);
        try { canvas.setPointerCapture(event.pointerId); } catch (_) {}
        answerError.classList.remove('visible');
        renderCanvas();
        return;
      }
      handwritingState.activeStroke = {
        id: globalThis.crypto?.randomUUID?.() || `stroke-${Date.now()}`,
        tool: handwritingState.tool,
        color: '#172127',
        baseWidth: handwritingState.baseWidth,
        points: [pointFromEvent(event)]
      };
      try { canvas.setPointerCapture(event.pointerId); } catch (_) {}
      answerError.classList.remove('visible');
      renderCanvas();
    }

    function continueStroke(event) {
      if (event.pointerId !== handwritingState.pointerId) return;
      event.preventDefault();
      const coalesced = typeof event.getCoalescedEvents === 'function'
        ? event.getCoalescedEvents()
        : [];
      const events = coalesced.length ? coalesced : [event];
      if (handwritingState.tool === 'eraser') {
        events.forEach(item => {
          const point = pointFromEvent(item);
          eraseAlongPath(handwritingState.lastErasePoint || point, point);
          handwritingState.lastErasePoint = point;
        });
      } else if (handwritingState.activeStroke) {
        events.forEach(item => handwritingState.activeStroke.points.push(pointFromEvent(item)));
      }
      renderCanvas();
    }

    function finishStroke(event) {
      if (event.pointerId !== handwritingState.pointerId) return;
      event.preventDefault();
      if (handwritingState.tool === 'eraser') {
        const point = pointFromEvent(event);
        eraseAlongPath(handwritingState.lastErasePoint || point, point);
      } else if (handwritingState.activeStroke) {
        handwritingState.activeStroke.points.push(pointFromEvent(event));
        currentPage().strokes.push(handwritingState.activeStroke);
        const grown = CanvasModel.growForStroke(currentPage(), handwritingState.activeStroke);
        currentPage().bounds = grown.bounds;
      }
      commitHistory(
        currentPage(),
        handwritingState.gestureBefore,
        CanvasModel.snapshotPage(currentPage())
      );
      handwritingState.activeStroke = null;
      handwritingState.pointerId = null;
      handwritingState.gestureBefore = null;
      handwritingState.lastErasePoint = null;
      saveDraft();
      updateControls();
      renderCanvas();
    }

    function canvasPointPx(event) {
      const rect = canvas.getBoundingClientRect();
      return { x: event.clientX - rect.left, y: event.clientY - rect.top };
    }

    function isLikelyPalm(event) {
      return event.pointerType === 'touch'
        && (event.width >= PALM_SIZE_PX || event.height >= PALM_SIZE_PX);
    }

    function touchAllowed(event) {
      return !isLikelyPalm(event)
        && handwritingState.penPointerId === null
        && Date.now() - handwritingState.lastPenAt >= PEN_GUARD_MS;
    }

    function rebaseTouchGesture() {
      const entries = [...handwritingState.touches.entries()];
      const view = { ...handwritingState.view };
      if (entries.length === 1) {
        handwritingState.touchGesture = {
          type: 'pan',
          pointerId: entries[0][0],
          start: { ...entries[0][1] },
          view
        };
      } else if (entries.length >= 2) {
        const [first, second] = entries;
        const midpoint = {
          x: (first[1].x + second[1].x) / 2,
          y: (first[1].y + second[1].y) / 2
        };
        handwritingState.touchGesture = {
          type: 'pinch',
          ids: [first[0], second[0]],
          midpoint,
          distance: Math.max(1, Math.hypot(second[1].x - first[1].x, second[1].y - first[1].y)),
          view
        };
      } else {
        handwritingState.touchGesture = null;
      }
    }

    function startTouch(event) {
      if (!touchAllowed(event)) return;
      event.preventDefault();
      handwritingState.touches.set(event.pointerId, canvasPointPx(event));
      try { canvas.setPointerCapture(event.pointerId); } catch (_) {}
      rebaseTouchGesture();
    }

    function continueTouch(event) {
      if (!handwritingState.touches.has(event.pointerId)) return;
      if (handwritingState.penPointerId !== null
          || Date.now() - handwritingState.lastPenAt < PEN_GUARD_MS
          || isLikelyPalm(event)) {
        handwritingState.touches.delete(event.pointerId);
        rebaseTouchGesture();
        return;
      }
      event.preventDefault();
      handwritingState.touches.set(event.pointerId, canvasPointPx(event));
      const gesture = handwritingState.touchGesture;
      if (!gesture) return;
      if (gesture.type === 'pan' && gesture.pointerId === event.pointerId) {
        const point = handwritingState.touches.get(event.pointerId);
        handwritingState.view.panX = gesture.view.panX + point.x - gesture.start.x;
        handwritingState.view.panY = gesture.view.panY + point.y - gesture.start.y;
      } else if (gesture.type === 'pinch') {
        const first = handwritingState.touches.get(gesture.ids[0]);
        const second = handwritingState.touches.get(gesture.ids[1]);
        if (!first || !second) return;
        const midpoint = {
          x: (first.x + second.x) / 2,
          y: (first.y + second.y) / 2
        };
        const distance = Math.max(1, Math.hypot(second.x - first.x, second.y - first.y));
        const zoom = Math.min(3, Math.max(.5, gesture.view.zoom * distance / gesture.distance));
        const logicalX = (gesture.midpoint.x - gesture.view.panX) / gesture.view.zoom;
        const logicalY = (gesture.midpoint.y - gesture.view.panY) / gesture.view.zoom;
        handwritingState.view.zoom = zoom;
        handwritingState.view.panX = midpoint.x - logicalX * zoom;
        handwritingState.view.panY = midpoint.y - logicalY * zoom;
      }
      clampView();
      updateViewControls();
      renderCanvas();
    }

    function finishTouch(event) {
      if (!handwritingState.touches.has(event.pointerId)) return;
      event.preventDefault();
      handwritingState.touches.delete(event.pointerId);
      rebaseTouchGesture();
    }

    function startPan(event) {
      if (event.pointerType === 'mouse' && event.button !== 0) return;
      event.preventDefault();
      handwritingState.panGesture = {
        pointerId: event.pointerId,
        start: canvasPointPx(event),
        view: { ...handwritingState.view }
      };
      try { canvas.setPointerCapture(event.pointerId); } catch (_) {}
    }

    function continuePan(event) {
      const gesture = handwritingState.panGesture;
      if (!gesture || gesture.pointerId !== event.pointerId) return;
      event.preventDefault();
      const point = canvasPointPx(event);
      handwritingState.view.panX = gesture.view.panX + point.x - gesture.start.x;
      handwritingState.view.panY = gesture.view.panY + point.y - gesture.start.y;
      clampView();
      renderCanvas();
    }

    function finishPan(event) {
      if (!handwritingState.panGesture || handwritingState.panGesture.pointerId !== event.pointerId) return;
      event.preventDefault();
      handwritingState.panGesture = null;
    }

    function handlePointerDown(event) {
      if (event.pointerType === 'touch') {
        startTouch(event);
        return;
      }
      if (event.pointerType === 'pen') {
        handwritingState.touches.clear();
        handwritingState.touchGesture = null;
        handwritingState.penPointerId = event.pointerId;
        handwritingState.lastPenAt = Date.now();
      }
      if (handwritingState.tool === 'pan') startPan(event);
      else startStroke(event);
    }

    function handlePointerMove(event) {
      if (event.pointerType === 'touch') {
        continueTouch(event);
        return;
      }
      if (event.pointerType === 'pen') handwritingState.lastPenAt = Date.now();
      if (handwritingState.panGesture) continuePan(event);
      else continueStroke(event);
    }

    function handlePointerEnd(event) {
      if (event.pointerType === 'touch') {
        finishTouch(event);
        return;
      }
      if (event.pointerType === 'pen') handwritingState.lastPenAt = Date.now();
      if (handwritingState.panGesture) finishPan(event);
      else finishStroke(event);
      if (handwritingState.penPointerId === event.pointerId) {
        handwritingState.penPointerId = null;
      }
    }

    canvas.addEventListener('pointerdown', handlePointerDown);
    canvas.addEventListener('pointermove', handlePointerMove);
    canvas.addEventListener('pointerup', handlePointerEnd);
    canvas.addEventListener('pointercancel', handlePointerEnd);
    canvas.addEventListener('wheel', event => {
      event.preventDefault();
      const point = canvasPointPx(event);
      setZoom(handwritingState.view.zoom * (event.deltaY < 0 ? 1.1 : 1 / 1.1), point.x, point.y);
    }, { passive: false });

    function setTool(tool) {
      handwritingState.tool = tool;
      document.getElementById('drawTool').setAttribute('aria-pressed', String(tool === 'draw'));
      document.getElementById('eraserTool').setAttribute('aria-pressed', String(tool === 'eraser'));
      document.getElementById('panTool').setAttribute('aria-pressed', String(tool === 'pan'));
      canvas.classList.toggle('eraser-active', tool === 'eraser');
      canvas.classList.toggle('pan-active', tool === 'pan');
    }

    function setInputMode(mode) {
      handwritingState.inputMode = mode;
      const isHandwrite = mode === 'handwrite';
      inputTabHandwrite.classList.toggle('active', isHandwrite);
      inputTabText.classList.toggle('active', !isHandwrite);
      inputTabHandwrite.setAttribute('aria-pressed', String(isHandwrite));
      inputTabText.setAttribute('aria-pressed', String(!isHandwrite));
      handwritingPanel.hidden = !isHandwrite;
      textAnswerPanel.classList.toggle('active', !isHandwrite);
      if (isHandwrite) requestAnimationFrame(renderCanvas);
      else answer.focus();
    }

    document.getElementById('drawTool').addEventListener('click', () => setTool('draw'));
    document.getElementById('eraserTool').addEventListener('click', () => setTool('eraser'));
    document.getElementById('panTool').addEventListener('click', () => setTool('pan'));
    document.getElementById('zoomOut').addEventListener('click', () => {
      const rect = canvas.getBoundingClientRect();
      setZoom(handwritingState.view.zoom - .25, rect.width / 2, rect.height / 2);
    });
    document.getElementById('zoomIn').addEventListener('click', () => {
      const rect = canvas.getBoundingClientRect();
      setZoom(handwritingState.view.zoom + .25, rect.width / 2, rect.height / 2);
    });
    document.getElementById('resetView').addEventListener('click', resetView);
    document.getElementById('fitContent').addEventListener('click', () => {
      const rect = canvas.getBoundingClientRect();
      handwritingState.view = CanvasModel.fitContentView(
        currentPage(),
        { width: rect.width, height: rect.height },
        80
      );
      updateViewControls();
      renderCanvas();
    });
    document.getElementById('moreCanvasActions').addEventListener('click', () => {
      const menu = document.getElementById('canvasMenu');
      menu.hidden = !menu.hidden;
    });
    document.getElementById('strokeSize').addEventListener('input', event => { handwritingState.baseWidth = Number(event.target.value); });
    inputTabHandwrite.addEventListener('click', () => setInputMode('handwrite'));
    inputTabText.addEventListener('click', () => setInputMode('text'));

    document.getElementById('undoStroke').addEventListener('click', () => {
      const page = currentPage();
      if (!page.undoStack.length) return;
      const operation = page.undoStack.pop();
      CanvasModel.restorePageSnapshot(page, operation.before);
      page.redoStack.push(operation);
      markHandwritingChanged();
      saveDraft();
      updateControls();
      renderCanvas();
    });
    document.getElementById('redoStroke').addEventListener('click', () => {
      const page = currentPage();
      if (!page.redoStack.length) return;
      const operation = page.redoStack.pop();
      CanvasModel.restorePageSnapshot(page, operation.after);
      page.undoStack.push(operation);
      markHandwritingChanged();
      saveDraft();
      updateControls();
      renderCanvas();
    });
    document.getElementById('clearPage').addEventListener('click', () => {
      document.getElementById('canvasMenu').hidden = true;
      if (!currentPage().strokes.length) return;
      clearConfirm.classList.add('show');
    });
    document.getElementById('cancelClear').addEventListener('click', () => clearConfirm.classList.remove('show'));
    document.getElementById('confirmClear').addEventListener('click', () => {
      const page = currentPage();
      const before = CanvasModel.snapshotPage(page);
      page.strokes = [];
      page.bounds = CanvasModel.createPage({ width: 900, height: 700 }).bounds;
      commitHistory(page, before, CanvasModel.snapshotPage(page));
      clearConfirm.classList.remove('show');
      saveDraft();
      updateControls();
      renderCanvas();
    });

    function goToPage(index) {
      const nextPage = Math.min(handwritingState.pages.length - 1, Math.max(0, index));
      if (nextPage !== handwritingState.currentPage) invalidateTranscriptConfirmation();
      handwritingState.currentPage = nextPage;
      clearConfirm.classList.remove('show');
      updateControls();
      renderCanvas();
    }
    document.getElementById('previousPage').addEventListener('click', () => goToPage(handwritingState.currentPage - 1));
    document.getElementById('nextPage').addEventListener('click', () => goToPage(handwritingState.currentPage + 1));
    document.getElementById('addPage').addEventListener('click', () => {
      handwritingState.pages.push(makePage());
      markHandwritingChanged();
      goToPage(handwritingState.pages.length - 1);
      saveDraft();
    });
    document.getElementById('deletePage').addEventListener('click', () => {
      if (handwritingState.pages.length === 1) return;
      handwritingState.pages.splice(handwritingState.currentPage, 1);
      markHandwritingChanged();
      goToPage(Math.min(handwritingState.currentPage, handwritingState.pages.length - 1));
      saveDraft();
    });

    function exportPayload() {
      return {
        schemaVersion: 2,
        artifactType: 'learning-os-handwriting',
        createdAt: new Date().toISOString(),
        aggregate: { type: 'knowledge-point', id: 'laplace-roc' },
        coordinateSpace: 'world-css-px',
        pages: handwritingState.pages.map(page => ({
          id: page.id,
          bounds: page.bounds,
          strokes: page.strokes
        }))
      };
    }

    function renderPageDataUrl(page, width = 1600, height = 1200) {
      const exportCanvas = document.createElement('canvas');
      renderPageToCanvas(exportCanvas, page, width, height, 1);
      return exportCanvas.toDataURL('image/png');
    }

    function renderWorldRegion(page, region, outputWidth, outputHeight) {
      const exportCanvas = document.createElement('canvas');
      exportCanvas.width = Math.max(1, Math.ceil(outputWidth));
      exportCanvas.height = Math.max(1, Math.ceil(outputHeight));
      const context = exportCanvas.getContext('2d');
      const scaleX = exportCanvas.width / Math.max(1, region.maxX - region.minX);
      const scaleY = exportCanvas.height / Math.max(1, region.maxY - region.minY);
      context.scale(scaleX, scaleY);
      context.translate(-region.minX, -region.minY);
      drawPaper(context, page.bounds);
      page.strokes.forEach(stroke => drawStroke(context, stroke));
      return exportCanvas;
    }

    function renderFullContentDataUrl(page = currentPage(), padding = 80) {
      const region = CanvasModel.contentBounds(page, padding);
      const worldWidth = Math.max(1, region.maxX - region.minX);
      const worldHeight = Math.max(1, region.maxY - region.minY);
      const outputWidth = Math.min(1600, Math.max(1, Math.ceil(worldWidth)));
      const outputHeight = Math.max(1, Math.ceil(worldHeight * outputWidth / worldWidth));
      return renderWorldRegion(page, region, outputWidth, outputHeight).toDataURL('image/png');
    }

    function renderCurrentViewDataUrl(page = currentPage()) {
      const rect = canvas.getBoundingClientRect();
      const view = handwritingState.view;
      const region = {
        minX: -view.panX / view.zoom,
        minY: -view.panY / view.zoom,
        maxX: (rect.width - view.panX) / view.zoom,
        maxY: (rect.height - view.panY) / view.zoom
      };
      return renderWorldRegion(page, region, rect.width, rect.height).toDataURL('image/png');
    }

    function planCurrentRecognitionChunks(page = currentPage()) {
      const bounds = CanvasModel.contentBounds(page, 80);
      return CanvasModel.planRecognitionChunks(bounds, {
        maxWidth: 1600,
        maxHeight: 1600,
        overlap: 120,
        maxChunks: 12
      }).map(chunk => ({
        page_id: page.id,
        index: chunk.index,
        minY: chunk.minY,
        maxY: chunk.maxY,
        png_data_url: renderWorldRegion(
          page,
          chunk,
          chunk.outputWidth,
          chunk.outputHeight
        ).toDataURL('image/png')
      }));
    }

    function downloadHref(href, filename, shouldRevoke = false) {
      const link = document.createElement('a');
      link.href = href;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      if (shouldRevoke) setTimeout(() => URL.revokeObjectURL(href), 1000);
    }

    document.getElementById('exportJson').addEventListener('click', () => {
      const blob = new Blob([JSON.stringify(exportPayload(), null, 2)], { type: 'application/json' });
      downloadHref(URL.createObjectURL(blob), 'learning-os-handwriting.json', true);
      document.getElementById('canvasMenu').hidden = true;
    });
    document.getElementById('exportPng').addEventListener('click', () => {
      downloadHref(renderFullContentDataUrl(currentPage()), `learning-os-handwriting-page-${handwritingState.currentPage + 1}.png`);
      document.getElementById('canvasMenu').hidden = true;
    });
    document.getElementById('exportViewPng').addEventListener('click', () => {
      downloadHref(renderCurrentViewDataUrl(currentPage()), `learning-os-handwriting-view-${handwritingState.currentPage + 1}.png`);
      document.getElementById('canvasMenu').hidden = true;
    });

    const RECOGNITION_URL = 'http://127.0.0.1:4174/api/v1/handwriting/recognize';

    function replaceList(containerId, items, formatItem) {
      const container = document.getElementById(containerId);
      container.replaceChildren();
      const values = Array.isArray(items) ? items : [];
      if (!values.length) {
        const empty = document.createElement('li');
        empty.textContent = '无';
        container.append(empty);
        return;
      }
      values.forEach(item => {
        const row = document.createElement('li');
        row.textContent = formatItem(item);
        container.append(row);
      });
    }

    function renderRecognitionDetails(result) {
      document.getElementById('recognitionRequestId').textContent = result.request_id || '—';
      document.getElementById('recognitionModel').textContent = result.model || '—';
      document.getElementById('recognitionConfidence').textContent = '—';
      const uncertain = Array.isArray(result.uncertain) ? result.uncertain : [];
      document.getElementById('recognitionUncertainCount').textContent = String(uncertain.length);
      replaceList(
        'recognitionFormulas',
        result.critical_formulas,
        item => `${item?.latex || '—'}${item?.meaning ? ` · ${item.meaning}` : ''}`
      );
      replaceList('recognitionDiagrams', result.diagram_notes, item => String(item));
      replaceList('recognitionUncertain', uncertain, item => String(item));
      document.getElementById('recognitionResult').classList.add('visible');
    }

    function recognitionFailureState(detail) {
      const message = String(detail || '');
      if (/timed out|HTTP 504/i.test(message)) {
        return {
          status: '\u8bc6\u522b\u670d\u52a1\u54cd\u5e94\u8d85\u65f6\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
          service: '\u670d\u52a1\u8d85\u65f6'
        };
      }
      if (/upstream HTTP|HTTP 502|HTTP 403|service unavailable/i.test(message)) {
        return {
          status: '\u8bc6\u522b\u670d\u52a1\u6682\u4e0d\u53ef\u7528\uff0c\u8bf7\u68c0\u67e5\u6a21\u578b\u670d\u52a1\u914d\u7f6e\u540e\u91cd\u8bd5\u3002',
          service: '\u670d\u52a1\u4e0d\u53ef\u7528'
        };
      }
      if (message && !/failed to fetch|networkerror|load failed/i.test(message)) {
        return { status: message, service: '\u8bc6\u522b\u5931\u8d25' };
      }
      return {
        status: '\u65e0\u6cd5\u8fde\u63a5\u8bc6\u522b\u670d\u52a1\uff0c\u8bf7\u68c0\u67e5\u7f51\u7edc\u6216 VPN \u540e\u91cd\u8bd5\u3002',
        service: '\u7f51\u7edc\u8fde\u63a5\u5f02\u5e38'
      };
    }

    function setRecognitionState(state, detail = '') {
      const button = document.getElementById('recognizeAnswer');
      const status = document.getElementById('recognitionStatus');
      const service = document.getElementById('recognitionServiceState');
      document.getElementById('recognitionPanel').hidden = false;
      document.getElementById('recognitionResult').classList.add('visible');
      if (state === 'running') {
        button.disabled = true;
        button.textContent = '识别中…';
        status.textContent = '正在识别当前页手写内容。';
        service.textContent = '识别中';
      } else if (state === 'success') {
        status.textContent = '识别完成，请核对后确认。';
        service.textContent = detail || '识别完成';
      } else if (state === 'empty') {
        status.textContent = detail || '请先手写作答。';
        service.textContent = '等待笔迹';
      } else {
        status.textContent = detail || '识别失败，请稍后重试。';
        service.textContent = '连接异常';
      }
    }

    const renderRecognitionState = setRecognitionState;
    setRecognitionState = (state, detail = '') => {
      renderRecognitionState(state, detail);
      if (state !== 'error') return;
      const failure = recognitionFailureState(detail);
      document.getElementById('recognitionStatus').textContent = failure.status;
      document.getElementById('recognitionServiceState').textContent = failure.service;
    };

    async function recognizeCurrentAnswer() {
      const button = document.getElementById('recognizeAnswer');
      const pagesWithInk = handwritingState.pages.filter(page =>
        page.strokes.some(stroke => stroke.tool === 'draw')
      );
      if (!pagesWithInk.length) {
        setRecognitionState('empty', '请先手写作答，再进行 AI 识别。');
        return;
      }
      const requestVersion = handwritingState.contentVersion;
      const requestPageIds = handwritingState.pages.map(page => page.id).join('|');
      const chunks = pagesWithInk.flatMap(page => planCurrentRecognitionChunks(page));
      setRecognitionState('running');
      try {
        const response = await fetch(RECOGNITION_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            chunks,
            stroke_json: exportPayload()
          })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || '识别失败');
        if (requestVersion !== handwritingState.contentVersion
            || requestPageIds !== handwritingState.pages.map(page => page.id).join('|')) {
          throw new Error('笔迹已变化，本次识别结果已丢弃。');
        }
        const sections = Array.isArray(result.sections) ? result.sections : [];
        recognizedText.value = sections
          .map(section => `${section.title ? `## ${section.title}\n` : ''}${section.transcript || ''}`)
          .join('\n\n');
        renderRecognitionDetails(result);
        transcriptConfirmed.checked = false;
        setRecognitionState('success', result.model);
        recognizedText.focus();
      } catch (error) {
        setRecognitionState('error', error.message);
      } finally {
        button.disabled = false;
        button.textContent = '识别当前作答';
      }
    }

    document.getElementById('recognizeAnswer').addEventListener('click', recognizeCurrentAnswer);
    recognizedText.addEventListener('input', invalidateTranscriptConfirmation);

    function showToast(message) {
      const toast = document.getElementById('toast');
      toast.textContent = message;
      toast.classList.add('show');
      setTimeout(() => { toast.classList.remove('show'); toast.textContent = '已提交到待评估队列'; }, 2600);
    }

    function openRecall() {
      backdrop.classList.add('open');
      document.body.style.overflow = 'hidden';
      answerError.classList.remove('visible');
      requestAnimationFrame(() => {
        renderCanvas();
        canvas.focus();
        const activeEvidenceId = localStorage.getItem('learning-os-active-evidence-id');
        if (activeEvidenceId) {
          if (submissionState.evidenceId !== activeEvidenceId) {
            submissionState.evidenceId = activeEvidenceId;
            submissionState.pollStartedAt = 0;
          }
          showAssessmentDrawer();
          setSubmissionState(SubmissionState.ASSESSING, '正在恢复后台评估状态。');
          pollEvidence(activeEvidenceId);
        }
      });
    }

    function closeRecall() {
      backdrop.classList.remove('open');
      document.body.style.overflow = '';
      clearConfirm.classList.remove('show');
      clearTimeout(submissionState.pollTimer);
      submissionState.pollTimer = null;
    }

    document.querySelectorAll('[data-action="recall"]').forEach(btn => btn.addEventListener('click', openRecall));
    document.getElementById('closeModal').addEventListener('click', closeRecall);
    backdrop.addEventListener('click', event => { if (event.target === backdrop) closeRecall(); });
    document.addEventListener('keydown', event => {
      if (!backdrop.classList.contains('open')) return;
      if (event.key === 'Escape') closeRecall();
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
        event.preventDefault();
        document.getElementById(event.shiftKey ? 'redoStroke' : 'undoStroke').click();
      }
    });

    const EVIDENCE_URL = 'http://127.0.0.1:4174/api/v1/evidence';
    const SubmissionState = Object.freeze({
      DRAFT: 'draft',
      SAVING: 'saving',
      ASSESSING: 'assessing',
      RECORDED: 'recorded',
      FAILED: 'failed'
    });
    const submissionState = {
      value: SubmissionState.DRAFT,
      submissionId: null,
      evidenceId: localStorage.getItem('learning-os-active-evidence-id'),
      pollTimer: null,
      pollStartedAt: 0
    };

    function setSubmissionState(state, message) {
      submissionState.value = state;
      document.getElementById('submissionStatus').textContent = message;
      const button = document.getElementById('submitAnswer');
      button.disabled = state === SubmissionState.SAVING;
      button.textContent = state === SubmissionState.SAVING ? '正在保存…' : '提交为 Evidence';
    }

    function showAssessmentDrawer() {
      document.getElementById('recognitionPanel').hidden = true;
      document.getElementById('assessmentDrawer').hidden = false;
      document.getElementById('assessmentEvidenceId').textContent = submissionState.evidenceId || '—';
    }

    function resetAssessmentDetails(label) {
      document.getElementById('assessmentId').textContent = '—';
      replaceList('assessmentCorrect', [label], item => String(item));
      replaceList('assessmentMissing', [label], item => String(item));
      replaceList('assessmentFormulas', [label], item => String(item));
    }

    function renderAssessment(detail) {
      clearTimeout(submissionState.pollTimer);
      submissionState.pollTimer = null;
      showAssessmentDrawer();
      const assessment = detail.assessment || {};
      document.getElementById('assessmentStatusText').textContent = 'Assessment 已记录';
      document.getElementById('assessmentSummary').textContent = assessment.summary || '评估完成';
      document.getElementById('assessmentStateChange').textContent = `F2 → ${assessment.f_state || '—'}`;
      document.getElementById('assessmentId').textContent = assessment.assessment_id || '—';
      replaceList('assessmentCorrect', assessment.correct_points, item => String(item));
      replaceList('assessmentMissing', assessment.missing_points, item => String(item));
      replaceList('assessmentFormulas', assessment.formula_feedback, item => String(item));
      document.getElementById('retryAssessment').hidden = true;
      setSubmissionState(SubmissionState.RECORDED, 'Assessment 已返回，Learning State 已从事件重新投影。');
    }

    function renderAssessmentFailure(detail) {
      clearTimeout(submissionState.pollTimer);
      submissionState.pollTimer = null;
      showAssessmentDrawer();
      const category = detail.failure?.category || 'unknown';
      document.getElementById('assessmentStatusText').textContent = '评估失败';
      document.getElementById('assessmentSummary').textContent = `Evidence 已安全保存；评估失败类别：${category}`;
      document.getElementById('assessmentStateChange').textContent = 'F2 → 未变化';
      resetAssessmentDetails('未生成');
      document.getElementById('retryAssessment').hidden = detail.failure?.retryable === false;
      setSubmissionState(SubmissionState.FAILED, 'Evidence 已保存，Assessment 可重试。');
    }

    async function pollEvidence(evidenceId) {
      if (!evidenceId || submissionState.evidenceId !== evidenceId) return;
      if (!submissionState.pollStartedAt) submissionState.pollStartedAt = Date.now();
      try {
        const response = await fetch(`${EVIDENCE_URL}/${encodeURIComponent(evidenceId)}`);
        const detail = await response.json();
        if (!response.ok) throw new Error(detail.error || '无法读取 Evidence');
        if (detail.status === 'recorded') {
          renderAssessment(detail);
          return;
        }
        if (detail.status === 'failed') {
          renderAssessmentFailure(detail);
          return;
        }
        showAssessmentDrawer();
        document.getElementById('assessmentStatusText').textContent = '正在评估当前作答';
        document.getElementById('assessmentSummary').textContent = 'Evidence 已持久化，正在生成 Assessment。';
        document.getElementById('assessmentStateChange').textContent = 'F2 → —';
        resetAssessmentDetails('等待评估');
        document.getElementById('retryAssessment').hidden = true;
        setSubmissionState(SubmissionState.ASSESSING, 'Evidence 已保存，后台正在评估。');
      } catch (error) {
        setSubmissionState(SubmissionState.FAILED, `读取评估状态失败：${error.message}`);
      }
      if (Date.now() - submissionState.pollStartedAt < 5 * 60 * 1000) {
        clearTimeout(submissionState.pollTimer);
        submissionState.pollTimer = setTimeout(() => pollEvidence(evidenceId), 2000);
      }
    }

    async function submitEvidence() {
      const hasHandwriting = handwritingState.pages.some(page => page.strokes.some(stroke => stroke.tool === 'draw'));
      const hasTypedAnswer = Boolean(answer.value.trim());
      const hasTranscript = Boolean(recognizedText.value.trim());
      if (!hasHandwriting && !hasTypedAnswer && !hasTranscript) {
        answerError.textContent = '请先手写或输入作答内容。';
        answerError.classList.add('visible');
        return;
      }
      if (hasTranscript && !transcriptConfirmed.checked) {
        answerError.textContent = '请先核对识别文本并确认。';
        answerError.classList.add('visible');
        recognizedText.focus();
        return;
      }
      answerError.classList.remove('visible');
      submissionState.submissionId = submissionState.submissionId
        || globalThis.crypto?.randomUUID?.()
        || `submission-${Date.now()}`;
      const images = handwritingState.pages.flatMap(page => planCurrentRecognitionChunks(page));
      const payload = {
        submission_id: submissionState.submissionId,
        aggregate: { type: 'knowledge-point', id: 'laplace-roc' },
        question: '解释拉普拉斯变换的 ROC，并说明它与信号时域特性的关系。',
        transcript: hasTranscript ? recognizedText.value.trim() : null,
        transcript_confirmed: hasTranscript && transcriptConfirmed.checked,
        handwriting: exportPayload(),
        typed_answer: hasTypedAnswer ? answer.value.trim() : null,
        images
      };
      setSubmissionState(SubmissionState.SAVING, '正在持久化原始笔迹和 Evidence…');
      try {
        const response = await fetch(EVIDENCE_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Evidence 保存失败');
        submissionState.evidenceId = result.evidence_id;
        submissionState.pollStartedAt = 0;
        localStorage.setItem('learning-os-active-evidence-id', result.evidence_id);
        document.getElementById('assessmentEvidenceId').textContent = result.evidence_id;
        showAssessmentDrawer();
        setSubmissionState(SubmissionState.ASSESSING, 'Evidence 已保存，后台正在评估。');
        showToast('Evidence 已持久化，正在评估');
        await pollEvidence(result.evidence_id);
      } catch (error) {
        setSubmissionState(SubmissionState.FAILED, `保存失败：${error.message}`);
        answerError.textContent = 'Evidence 保存失败，原始笔迹仍在本机草稿中。';
        answerError.classList.add('visible');
      }
    }

    document.getElementById('submitAnswer').addEventListener('click', submitEvidence);
    document.getElementById('closeAssessment').addEventListener('click', () => {
      document.getElementById('assessmentDrawer').hidden = true;
    });
    document.getElementById('answerAgain').addEventListener('click', () => {
      if (!window.confirm('开始新的作答？当前 Evidence 会保留，画布草稿将被清空。')) return;
      clearTimeout(submissionState.pollTimer);
      submissionState.pollTimer = null;
      document.getElementById('assessmentDrawer').hidden = true;
      document.getElementById('recognitionPanel').hidden = true;
      handwritingState.pages = [makePage()];
      handwritingState.currentPage = 0;
      handwritingState.view = { zoom: 1, panX: 0, panY: 0 };
      handwritingState.contentVersion += 1;
      answer.value = '';
      recognizedText.value = '';
      transcriptConfirmed.checked = false;
      document.getElementById('recognitionResult').classList.remove('visible');
      submissionState.value = SubmissionState.DRAFT;
      submissionState.submissionId = null;
      submissionState.evidenceId = null;
      submissionState.pollStartedAt = 0;
      localStorage.removeItem('learning-os-active-evidence-id');
      saveDraft();
      updateControls();
      updateViewControls();
      renderCanvas();
      setSubmissionState(SubmissionState.DRAFT, '继续作答；新的提交会生成新的 Evidence。');
    });
    document.getElementById('retryAssessment').addEventListener('click', async () => {
      if (!submissionState.evidenceId) return;
      const response = await fetch(
        `${EVIDENCE_URL}/${encodeURIComponent(submissionState.evidenceId)}/assessment/retry`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }
      );
      const result = await response.json();
      if (!response.ok) {
        setSubmissionState(SubmissionState.FAILED, result.error || '评估重试失败');
        return;
      }
      submissionState.pollStartedAt = 0;
      setSubmissionState(SubmissionState.ASSESSING, '已重新进入评估队列。');
      pollEvidence(submissionState.evidenceId);
    });

    const resizeObserver = new ResizeObserver(() => {
      if (backdrop.classList.contains('open')) {
        clampView();
        renderCanvas();
      }
    });
    resizeObserver.observe(document.getElementById('canvasWrap'));
    loadDraft();
    updateControls();
    updateViewControls();
    window.__learningOSHandwriting = {
      debugSnapshot: () => JSON.parse(JSON.stringify({
        schemaVersion: 2,
        coordinateSpace: 'world-css-px',
        currentPage: handwritingState.currentPage,
        tool: handwritingState.tool,
        pages: handwritingState.pages,
        view: handwritingState.view
      })),
      createExportBundle: exportPayload,
      renderFullContentDataUrl: () => renderFullContentDataUrl(currentPage()),
      renderCurrentViewDataUrl: () => renderCurrentViewDataUrl(currentPage()),
      planCurrentRecognitionChunks: () => planCurrentRecognitionChunks(currentPage()),
      render: renderCanvas
    };
    // Kept for the existing deterministic canvas-image regression contract.
    window.currentPage = currentPage;
    window.renderPageDataUrl = renderPageDataUrl;


})();
