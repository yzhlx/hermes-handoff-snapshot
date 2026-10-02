const test = require('node:test');
const assert = require('node:assert/strict');
const model = require('../../../../outputs/learning-os-canvas-model.js');

const stroke = points => ({
  id: 'stroke-1',
  tool: 'draw',
  color: '#172127',
  baseWidth: 4,
  points,
});

test('creates a world-coordinate page', () => {
  const page = model.createPage({ width: 1000, height: 800, id: 'page-1' });
  assert.deepEqual(page.bounds, { minX: 0, minY: 0, maxX: 1000, maxY: 1200 });
  assert.deepEqual(page.strokes, []);
  assert.deepEqual(page.undoStack, []);
  assert.deepEqual(page.redoStack, []);
});

test('migrates schema v1 without changing stroke metadata', () => {
  const draft = {
    schemaVersion: 1,
    savedAt: '2026-07-21T00:00:00Z',
    pages: [{
      id: 'p',
      strokes: [{
        id: 's',
        tool: 'draw',
        color: '#000',
        baseWidth: 3,
        points: [{ x: .25, y: .5, pressure: .7, t: 12 }],
      }],
    }],
  };
  const migrated = model.migrateDraft(draft, { width: 1200, height: 1800 });
  assert.equal(migrated.schemaVersion, 2);
  assert.equal(migrated.coordinateSpace, 'world-css-px');
  assert.equal(migrated.pages[0].strokes[0].id, 's');
  assert.deepEqual(migrated.pages[0].strokes[0].points[0], {
    x: 300,
    y: 900,
    pressure: .7,
    t: 12,
  });
});

test('keeps schema v2 world coordinates unchanged', () => {
  const draft = {
    schemaVersion: 2,
    coordinateSpace: 'world-css-px',
    pages: [{
      id: 'p',
      bounds: { minX: -400, minY: 0, maxX: 1000, maxY: 1800 },
      strokes: [stroke([{ x: -200, y: 900, pressure: .5, t: 1 }])],
    }],
  };
  const migrated = model.migrateDraft(draft, { width: 1200, height: 1800 });
  assert.deepEqual(migrated.pages[0].bounds, draft.pages[0].bounds);
  assert.equal(migrated.pages[0].strokes[0].points[0].x, -200);
});

test('grows only approached edges after a committed stroke', () => {
  const page = model.createPage({ width: 1000, height: 800, id: 'p' });
  const next = model.growForStroke(page, stroke([
    { x: 40, y: 1100, pressure: .5, t: 1 },
    { x: 15, y: 1180, pressure: .5, t: 2 },
  ]));
  assert.deepEqual(next.bounds, { minX: -400, minY: 0, maxX: 1000, maxY: 1800 });
  assert.deepEqual(page.bounds, { minX: 0, minY: 0, maxX: 1000, maxY: 1200 });
});

test('grows the right edge independently', () => {
  const page = model.createPage({ width: 1000, height: 800, id: 'p' });
  const next = model.growForStroke(page, stroke([
    { x: 950, y: 200, pressure: .5, t: 1 },
    { x: 995, y: 240, pressure: .5, t: 2 },
  ]));
  assert.deepEqual(next.bounds, { minX: 0, minY: 0, maxX: 1400, maxY: 1200 });
});

test('computes content bounds including width and padding', () => {
  const page = model.createPage({ width: 1000, height: 800, id: 'p' });
  page.strokes = [stroke([{ x: 100, y: 200 }, { x: 900, y: 1000 }])];
  assert.deepEqual(model.contentBounds(page, 10), {
    minX: 88,
    minY: 188,
    maxX: 912,
    maxY: 1012,
  });
});

test('fits all content with padding without mutating the page', () => {
  const page = model.createPage({ width: 1000, height: 800, id: 'p' });
  page.strokes = [stroke([{ x: 100, y: 200 }, { x: 900, y: 1000 }])];
  const before = JSON.stringify(page);
  const view = model.fitContentView(page, { width: 800, height: 600 }, 80);
  assert.ok(view.zoom >= .5 && view.zoom <= 3);
  assert.ok(Number.isFinite(view.panX));
  assert.ok(Number.isFinite(view.panY));
  assert.equal(JSON.stringify(page), before);
});

test('plans ordered overlapping recognition chunks', () => {
  const chunks = model.planRecognitionChunks(
    { minX: 0, minY: 0, maxX: 1200, maxY: 3600 },
    { maxWidth: 1600, maxHeight: 1600, overlap: 120, maxChunks: 12 },
  );
  assert.equal(chunks.length, 3);
  assert.equal(chunks[0].index, 0);
  assert.equal(chunks[0].outputWidth, 1200);
  assert.equal(chunks[0].outputHeight, 1600);
  assert.equal(chunks[1].minY, chunks[0].maxY - 120);
  assert.equal(chunks[2].index, 2);
});

test('rejects recognition plans exceeding the chunk limit', () => {
  assert.throws(
    () => model.planRecognitionChunks(
      { minX: 0, minY: 0, maxX: 1200, maxY: 30000 },
      { maxWidth: 1600, maxHeight: 1600, overlap: 120, maxChunks: 12 },
    ),
    /more than 12 chunks/,
  );
});

test('snapshots and restores strokes and paper bounds independently', () => {
  const page = model.createPage({ width: 1000, height: 800, id: 'p' });
  page.strokes = [stroke([{ x: 100, y: 200 }])];
  const snapshot = model.snapshotPage(page);
  page.strokes[0].points[0].x = 500;
  page.bounds.maxY = 2400;
  model.restorePageSnapshot(page, snapshot);
  assert.equal(page.strokes[0].points[0].x, 100);
  assert.equal(page.bounds.maxY, 1200);
});
