(function attachCanvasModel(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.LearningOSCanvasModel = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function createCanvasModel() {
  'use strict';

  const SCHEMA_VERSION = 2;
  const INITIAL_HEIGHT_FACTOR = 1.5;
  const BOTTOM_THRESHOLD = 160;
  const SIDE_THRESHOLD = 120;
  const VERTICAL_GROWTH = 600;
  const HORIZONTAL_GROWTH = 400;
  const MIN_ZOOM = .5;
  const MAX_ZOOM = 3;

  const clone = value => JSON.parse(JSON.stringify(value));

  function createId(prefix) {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
    return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function createPage({ width, height, id } = {}) {
    const pageWidth = Math.max(1, Number(width) || 1200);
    const viewportHeight = Math.max(1, Number(height) || 1200);
    return {
      id: id || createId('page'),
      bounds: {
        minX: 0,
        minY: 0,
        maxX: pageWidth,
        maxY: viewportHeight * INITIAL_HEIGHT_FACTOR,
      },
      strokes: [],
      undoStack: [],
      redoStack: [],
    };
  }

  function normalizeV2Page(page, initialSize) {
    const fallback = createPage({
      width: initialSize.width,
      height: initialSize.height,
      id: page?.id,
    });
    return {
      id: typeof page?.id === 'string' ? page.id : fallback.id,
      bounds: page?.bounds ? clone(page.bounds) : fallback.bounds,
      strokes: Array.isArray(page?.strokes) ? clone(page.strokes) : [],
      undoStack: [],
      redoStack: [],
    };
  }

  function migrateDraft(draft, initialSize = { width: 1200, height: 1800 }) {
    const source = draft && typeof draft === 'object' ? draft : {};
    const pages = Array.isArray(source.pages) ? source.pages : [];
    if (source.schemaVersion === SCHEMA_VERSION) {
      return {
        schemaVersion: SCHEMA_VERSION,
        coordinateSpace: 'world-css-px',
        savedAt: source.savedAt || null,
        pages: pages.map(page => normalizeV2Page(page, initialSize)),
      };
    }

    const width = Math.max(1, Number(initialSize.width) || 1200);
    const height = Math.max(1, Number(initialSize.height) || 1800);
    return {
      schemaVersion: SCHEMA_VERSION,
      coordinateSpace: 'world-css-px',
      savedAt: source.savedAt || null,
      pages: pages.map(page => {
        const next = createPage({ width, height: height / INITIAL_HEIGHT_FACTOR, id: page?.id });
        next.bounds.maxY = height;
        next.strokes = (Array.isArray(page?.strokes) ? page.strokes : []).map(item => ({
          ...clone(item),
          points: (Array.isArray(item.points) ? item.points : []).map(point => ({
            ...clone(point),
            x: Number(point.x) * width,
            y: Number(point.y) * height,
          })),
        }));
        return next;
      }),
    };
  }

  function strokeBounds(stroke) {
    const points = Array.isArray(stroke?.points) ? stroke.points : [];
    if (!points.length) return null;
    const halfWidth = Math.max(0, Number(stroke.baseWidth) || 0) / 2;
    const xs = points.map(point => Number(point.x));
    const ys = points.map(point => Number(point.y));
    return {
      minX: Math.min(...xs) - halfWidth,
      minY: Math.min(...ys) - halfWidth,
      maxX: Math.max(...xs) + halfWidth,
      maxY: Math.max(...ys) + halfWidth,
    };
  }

  function contentBounds(page, padding = 0) {
    const bounds = (Array.isArray(page?.strokes) ? page.strokes : [])
      .filter(stroke => stroke.tool === 'draw')
      .map(strokeBounds)
      .filter(Boolean);
    if (!bounds.length) return clone(page.bounds);
    const inset = Math.max(0, Number(padding) || 0);
    return {
      minX: Math.min(...bounds.map(item => item.minX)) - inset,
      minY: Math.min(...bounds.map(item => item.minY)) - inset,
      maxX: Math.max(...bounds.map(item => item.maxX)) + inset,
      maxY: Math.max(...bounds.map(item => item.maxY)) + inset,
    };
  }

  function growForStroke(page, committedStroke) {
    const next = { ...page, bounds: clone(page.bounds) };
    const bounds = strokeBounds(committedStroke);
    if (!bounds) return next;
    if (bounds.maxY >= page.bounds.maxY - BOTTOM_THRESHOLD) {
      next.bounds.maxY += VERTICAL_GROWTH;
    }
    if (bounds.minX <= page.bounds.minX + SIDE_THRESHOLD) {
      next.bounds.minX -= HORIZONTAL_GROWTH;
    }
    if (bounds.maxX >= page.bounds.maxX - SIDE_THRESHOLD) {
      next.bounds.maxX += HORIZONTAL_GROWTH;
    }
    return next;
  }

  function fitContentView(page, viewport, padding = 80) {
    const bounds = contentBounds(page, padding);
    const width = Math.max(1, bounds.maxX - bounds.minX);
    const height = Math.max(1, bounds.maxY - bounds.minY);
    const zoom = Math.min(
      MAX_ZOOM,
      Math.max(MIN_ZOOM, Math.min(viewport.width / width, viewport.height / height)),
    );
    return {
      zoom,
      panX: (viewport.width - width * zoom) / 2 - bounds.minX * zoom,
      panY: (viewport.height - height * zoom) / 2 - bounds.minY * zoom,
    };
  }

  function planRecognitionChunks(bounds, options = {}) {
    const maxWidth = Math.max(1, Number(options.maxWidth) || 1600);
    const maxHeight = Math.max(1, Number(options.maxHeight) || 1600);
    const overlap = Math.max(0, Number(options.overlap) || 0);
    const maxChunks = Math.max(1, Number(options.maxChunks) || 12);
    const worldWidth = Math.max(1, bounds.maxX - bounds.minX);
    const worldHeight = Math.max(1, bounds.maxY - bounds.minY);
    // maxWidth is an upper bound for provider payloads, not a target width.
    // Preserve native detail unless the content must be reduced to fit it.
    const scale = Math.min(1, maxWidth / worldWidth);
    const chunkWorldHeight = maxHeight / scale;
    const overlapWorld = Math.min(chunkWorldHeight - 1, overlap / scale);
    const step = Math.max(1, chunkWorldHeight - overlapWorld);
    const chunks = [];
    let minY = bounds.minY;
    while (minY < bounds.maxY) {
      const maxY = Math.min(bounds.maxY, minY + chunkWorldHeight);
      chunks.push({
        index: chunks.length,
        minX: bounds.minX,
        minY,
        maxX: bounds.maxX,
        maxY,
        outputWidth: Math.max(1, Math.ceil(worldWidth * scale)),
        outputHeight: Math.max(1, Math.ceil((maxY - minY) * scale)),
      });
      if (chunks.length > maxChunks) {
        throw new RangeError(`Recognition requires more than ${maxChunks} chunks`);
      }
      if (maxY >= bounds.maxY) break;
      minY += step;
    }
    return chunks;
  }

  function snapshotPage(page) {
    return { bounds: clone(page.bounds), strokes: clone(page.strokes) };
  }

  function restorePageSnapshot(page, snapshot) {
    page.bounds = clone(snapshot.bounds);
    page.strokes = clone(snapshot.strokes);
    return page;
  }

  return Object.freeze({
    SCHEMA_VERSION,
    createPage,
    migrateDraft,
    strokeBounds,
    contentBounds,
    growForStroke,
    fitContentView,
    planRecognitionChunks,
    snapshotPage,
    restorePageSnapshot,
  });
}));
