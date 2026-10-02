import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { clearComparisonDrafts } from './draft-store';
import { ComparisonsPage } from './ComparisonsPage';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); clearComparisonDrafts(); });

const envelope = (data: unknown, status = 200) => new Response(JSON.stringify({ data, meta: { request_id: 'qa' } }), { status });
const failure = (status: number, code: string) => new Response(JSON.stringify({ error: { code, message: 'QA test failure' }, meta: { request_id: 'qa' } }), { status });
const problem = (id: string, title: string, extras: Record<string, unknown> = {}) => ({
  id, title, statement: `${title} 题干`, correct_answer: `${title} 答案`, source_note: null, subject_id: 'QA_TEST_subject',
  archived: false, is_representative: false, knowledge_point_ids: [], attachment_links: [], attempts: [], version: 1,
  created_at: '2026-09-01T10:00:00Z', updated_at: '2026-09-01T10:00:00Z', ...extras,
});
const comparison = (extras: Record<string, unknown> = {}) => ({
  id: 'QA_TEST_comparison', version: 1, left_problem_id: 'QA_TEST_left', right_problem_id: 'QA_TEST_right',
  left_attempt_id: null, right_attempt_id: null, conditions: null, known_values: null, formulas: null,
  entry_point: null, diagram: null, boundary: null, assumptions: null, conclusion: null, archived: false,
  created_at: '2026-09-01T10:00:00Z', updated_at: '2026-09-01T10:00:00Z',
  source_versions: { QA_TEST_left: 1, QA_TEST_right: 1 }, source_changed: false, ...extras,
});
const setup = (fetchMock: ReturnType<typeof vi.fn>) => {
  vi.stubGlobal('fetch', fetchMock);
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false } });
  const props = { userId: 'QA_TEST_user', onOpenProblem: vi.fn(), onStartProblem: vi.fn() };
  const renderPage = () => render(<QueryClientProvider client={client}><ComparisonsPage {...props} /></QueryClientProvider>);
  return { props, renderPage };
};

async function pickBothProblems() {
  fireEvent.click(await screen.findByRole('button', { name: '新建对比' }));
  fireEvent.click((await screen.findAllByRole('button', { name: '选作左例' }))[0]!);
  fireEvent.click((await screen.findAllByRole('button', { name: '选作右例' }))[1]!);
  fireEvent.click(screen.getByRole('button', { name: '继续填写差异' }));
  expect(await screen.findByRole('heading', { name: '填写两题的差异' })).toBeInTheDocument();
}

describe('problem comparison workflows', () => {
  it('allows skipping selection without sending a comparison write', async () => {
    const calls: Array<{ url: string; method: string }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
      calls.push({ url: path, method: init?.method ?? 'GET' });
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/problem-comparisons') return envelope({ items: [], next_cursor: null });
      if (path === '/problems') return envelope({ items: [problem('QA_TEST_left', 'QA_TEST 左题')], next_cursor: null });
      throw new Error(`Unexpected ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: '新建对比' }));
    fireEvent.click(await screen.findByRole('button', { name: '跳过，不保存' }));
    expect(await screen.findByRole('heading', { name: '双例对比' })).toBeInTheDocument();
    expect(calls.some((call) => call.url === '/problem-comparisons' && call.method === 'POST')).toBe(false);
  });

  it('saves a partial comparison with idempotency and keeps user text for an exact retry after an uncertain response and remount', async () => {
    const postCalls: Array<{ headers: Headers; body: string }> = [];
    let postCount = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/problems' && init?.method !== 'PATCH') return envelope({ items: [problem('QA_TEST_left', 'QA_TEST 左题'), problem('QA_TEST_right', 'QA_TEST 右题')], next_cursor: null });
      if (path.startsWith('/problems/')) return envelope(problem(path.split('/').at(-1) ?? '', 'QA_TEST 原题'));
      if (path === '/problem-comparisons' && init?.method === 'GET') return envelope({ items: [], next_cursor: null });
      if (path === '/problem-comparisons' && init?.method === 'POST') {
        postCalls.push({ headers: new Headers(init.headers), body: String(init.body) });
        postCount += 1;
        if (postCount === 1) return failure(503, 'TEMPORARY');
        return envelope(comparison({ conditions: 'QA_TEST 共同条件' }), 201);
      }
      if (path === '/problem-comparisons/QA_TEST_comparison') return envelope(comparison({ conditions: 'QA_TEST 共同条件' }));
      throw new Error(`Unexpected ${init?.method ?? 'GET'} ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    const view = renderPage();
    await pickBothProblems();
    fireEvent.change(screen.getByLabelText(/条件/), { target: { value: 'QA_TEST 共同条件' } });
    fireEvent.click(screen.getByRole('button', { name: '保存对比记录' }));
    expect(await screen.findByText(/暂时无法连接|操作未完成/)).toBeInTheDocument();
    expect(screen.getByLabelText(/条件/)).toBeDisabled();
    view.unmount();

    renderPage();
    const recoveredInput = await screen.findByLabelText(/条件/);
    expect(recoveredInput).toHaveValue('QA_TEST 共同条件');
    expect(recoveredInput).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: '使用原请求安全重试' }));
    await waitFor(() => expect(postCount).toBe(2));
    expect(postCalls[1]?.headers.get('Idempotency-Key')).toBe(postCalls[0]?.headers.get('Idempotency-Key'));
    expect(postCalls[1]?.body).toBe(postCalls[0]?.body);
    expect(JSON.parse(postCalls[0]?.body ?? '{}')).toMatchObject({ left_problem_id: 'QA_TEST_left', right_problem_id: 'QA_TEST_right', conditions: 'QA_TEST 共同条件' });
  });

  it('retains comparison input across a version conflict and requires an explicit reread before retry', async () => {
    let reads = 0;
    const patchCalls: Array<{ headers: Headers; body: string }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/problems/QA_TEST_left') return envelope(problem('QA_TEST_left', 'QA_TEST 左题'));
      if (path === '/problems/QA_TEST_right') return envelope(problem('QA_TEST_right', 'QA_TEST 右题'));
      if (path === '/problem-comparisons') return envelope({ items: [comparison()], next_cursor: null });
      if (path === '/problem-comparisons/QA_TEST_comparison' && init?.method === 'PATCH') {
        patchCalls.push({ headers: new Headers(init.headers), body: String(init.body) });
        if (patchCalls.length === 1) return failure(409, 'VERSION_CONFLICT');
        return envelope(comparison({ version: 3, conditions: 'QA_TEST 本地保留输入' }));
      }
      if (path === '/problem-comparisons/QA_TEST_comparison') {
        reads += 1;
        return envelope(comparison({ version: reads > 1 ? 2 : 1, conditions: reads > 1 ? 'QA_TEST 服务器新内容' : null }));
      }
      throw new Error(`Unexpected ${init?.method ?? 'GET'} ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: '编辑文字' }));
    fireEvent.change(await screen.findByLabelText(/条件/), { target: { value: 'QA_TEST 本地保留输入' } });
    fireEvent.click(screen.getByRole('button', { name: '保存比较' }));
    expect(await screen.findByText(/另一台设备更新/)).toBeInTheDocument();
    expect(screen.getByLabelText(/条件/)).toHaveValue('QA_TEST 本地保留输入');
    fireEvent.click(screen.getByRole('button', { name: '读取最新版本' }));
    expect(await screen.findByText('QA_TEST 服务器新内容')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '保存比较' }));
    await waitFor(() => expect(patchCalls).toHaveLength(2));
    expect(patchCalls[0]?.headers.get('If-Match')).toBe('"1"');
    expect(patchCalls[1]?.headers.get('If-Match')).toBe('"2"');
    expect(JSON.parse(patchCalls[1]?.body ?? '{}')).toMatchObject({ conditions: 'QA_TEST 本地保留输入' });
  });

  it('shows a source-changed warning while preserving the saved comparison text and current original materials', async () => {
    const stale = comparison({ source_changed: true, conditions: 'QA_TEST 当时观察到的条件差异' });
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/problem-comparisons') return envelope({ items: [stale], next_cursor: null });
      if (path === '/problem-comparisons/QA_TEST_comparison') return envelope(stale);
      if (path === '/problems/QA_TEST_left') return envelope(problem('QA_TEST_left', 'QA_TEST 左题更新版', { version: 2, statement: 'QA_TEST 更新后的题干' }));
      if (path === '/problems/QA_TEST_right') return envelope(problem('QA_TEST_right', 'QA_TEST 右题'));
      throw new Error(`Unexpected ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    expect(await screen.findByText(/原题或作答在保存比较后有更新/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '查看材料与比较' }));
    expect(await screen.findByRole('heading', { name: '两题的对比记录' })).toBeInTheDocument();
    expect(screen.getByText(/以下显示当前原材料/)).toBeInTheDocument();
    expect(await screen.findByText('QA_TEST 更新后的题干')).toBeInTheDocument();
    expect(screen.getByText('QA_TEST 当时观察到的条件差异')).toBeInTheDocument();
  });

  it('opens the titled problem library and marks a representative through the versioned problem command', async () => {
    const patchCalls: Array<{ headers: Headers; body: string }> = [];
    let representative = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/problem-comparisons') return envelope({ items: [], next_cursor: null });
      if (path === '/problems' && init?.method === 'PATCH') {
        patchCalls.push({ headers: new Headers(init.headers), body: String(init.body) });
        representative = true;
        return envelope({ problem: problem('QA_TEST_left', 'QA_TEST 左题', { is_representative: true, version: 2 }) });
      }
      if (path === '/problems/QA_TEST_left' && init?.method === 'PATCH') {
        patchCalls.push({ headers: new Headers(init.headers), body: String(init.body) });
        representative = true;
        return envelope(problem('QA_TEST_left', 'QA_TEST 左题', { is_representative: true, version: 2 }));
      }
      if (path === '/problems') return envelope({ items: [problem('QA_TEST_left', 'QA_TEST 左题', { is_representative: representative })], next_cursor: null });
      if (path === '/problems/QA_TEST_left') return envelope(problem('QA_TEST_left', 'QA_TEST 左题'));
      throw new Error(`Unexpected ${init?.method ?? 'GET'} ${path}`);
    });
    const { renderPage, props } = setup(fetchMock);
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: '浏览题目与代表题' }));
    fireEvent.click(await screen.findByRole('button', { name: '标记为代表题' }));
    await waitFor(() => expect(patchCalls).toHaveLength(1));
    expect(patchCalls[0]?.headers.get('If-Match')).toBe('"1"');
    expect(patchCalls[0]?.headers.get('Idempotency-Key')).toBeTruthy();
    expect(JSON.parse(patchCalls[0]?.body ?? '{}')).toMatchObject({ is_representative: true });
    expect(await screen.findByRole('button', { name: '取消代表题' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '查看与核对原作答' }));
    // The quick action opens a real verification surface, not a read-only detail page.
    expect(await screen.findByRole('heading', { name: '核对原作答' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: '作答记录' })).toBeInTheDocument();
    expect(await screen.findByText('这道题还没有作答记录，因此没有可核对的作答。可返回对比页从这道题开始一轮练习。')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '编辑这次作答记录' })).toBeNull();
    const checkPanel = screen.getByRole('region', { name: '核对原作答' });
    fireEvent.click(within(checkPanel).getByRole('button', { name: '返回对比' }));
    await waitFor(() => expect(screen.queryByRole('heading', { name: '核对原作答' })).toBeNull());
    expect(props.onOpenProblem).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '开始新练习' }));
    expect(props.onStartProblem).toHaveBeenCalledWith(expect.objectContaining({ problemId: 'QA_TEST_left', goal: '复习：QA_TEST 左题' }));
  });

  it('verifies and corrects an existing attempt from the comparison workspace without a learning session', async () => {
    const attempt = {
      id: 'QA_TEST_attempt', problem_id: 'QA_TEST_left', version: 1, occurrence_index: 1,
      independence: 'independent', answer_check: 'pending', result: null, attempt_text: 'QA_TEST 原始作答',
      error_categories: [], other_error_note: null, stuck_note: null,
      occurred_at: '2026-09-01T10:00:00Z', created_at: '2026-09-01T10:00:00Z', updated_at: '2026-09-01T10:00:00Z',
    };
    const patchCalls: Array<{ headers: Headers; body: string }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/problem-comparisons') return envelope({ items: [], next_cursor: null });
      if (path === '/problems') return envelope({ items: [problem('QA_TEST_left', 'QA_TEST 左题', { attempts: [attempt] })], next_cursor: null });
      if (path === '/problems/QA_TEST_left') return envelope(problem('QA_TEST_left', 'QA_TEST 左题', { attempts: [attempt] }));
      if (path === '/problem-attempts/QA_TEST_attempt' && init?.method === 'PATCH') {
        patchCalls.push({ headers: new Headers(init.headers), body: String(init.body) });
        return envelope({ attempt: { ...attempt, answer_check: 'checked', result: 'partial', version: 2 } });
      }
      throw new Error(`Unexpected ${init?.method ?? 'GET'} ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: '浏览题目与代表题' }));
    fireEvent.click(await screen.findByRole('button', { name: '查看与核对原作答' }));
    // The saved attempt is shown read-only first, with a real correction control.
    expect(await screen.findByText('QA_TEST 原始作答')).toBeInTheDocument();
    expect(screen.getByText('尚未核对')).toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: '编辑这次作答记录' }));
    fireEvent.change(screen.getByLabelText('核对状态'), { target: { value: 'checked' } });
    fireEvent.change(screen.getByLabelText('实际结果'), { target: { value: 'partial' } });
    fireEvent.click(screen.getByRole('button', { name: '保存修正' }));
    await waitFor(() => expect(patchCalls).toHaveLength(1));
    // Versioned, idempotent correction that only changes the attempt facts.
    expect(patchCalls[0]?.headers.get('If-Match')).toBe('"1"');
    expect(patchCalls[0]?.headers.get('Idempotency-Key')).toBeTruthy();
    const body = JSON.parse(patchCalls[0]?.body ?? '{}');
    expect(body).toMatchObject({ answer_check: 'checked', result: 'partial' });
    expect(body.operation_id).toBe(patchCalls[0]?.headers.get('Idempotency-Key'));
    // No comparison write and no problem write is triggered by verification.
    expect(patchCalls.every((call) => call.headers.get('If-Match') === '"1"')).toBe(true);
  });

  it('keeps correction input and re-reads when the attempt version conflicts', async () => {
    const attempt = {
      id: 'QA_TEST_attempt', problem_id: 'QA_TEST_left', version: 1, occurrence_index: 1,
      independence: 'independent', answer_check: 'pending', result: null, attempt_text: 'QA_TEST 原始作答',
      error_categories: [], other_error_note: null, stuck_note: null,
      occurred_at: '2026-09-01T10:00:00Z', created_at: '2026-09-01T10:00:00Z', updated_at: '2026-09-01T10:00:00Z',
    };
    const patchCalls: Array<{ headers: Headers; body: string }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/problem-comparisons') return envelope({ items: [], next_cursor: null });
      if (path === '/problems') return envelope({ items: [problem('QA_TEST_left', 'QA_TEST 左题', { attempts: [attempt] })], next_cursor: null });
      if (path === '/problems/QA_TEST_left') return envelope(problem('QA_TEST_left', 'QA_TEST 左题', { attempts: [attempt] }));
      if (path === '/problem-attempts/QA_TEST_attempt' && init?.method === 'PATCH') {
        patchCalls.push({ headers: new Headers(init.headers), body: String(init.body) });
        return failure(409, 'VERSION_CONFLICT');
      }
      throw new Error(`Unexpected ${init?.method ?? 'GET'} ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: '浏览题目与代表题' }));
    fireEvent.click(await screen.findByRole('button', { name: '查看与核对原作答' }));
    fireEvent.click(await screen.findByRole('button', { name: '编辑这次作答记录' }));
    fireEvent.change(screen.getByLabelText('卡住的位置'), { target: { value: 'QA_TEST 本地保留卡点' } });
    fireEvent.click(screen.getByRole('button', { name: '保存修正' }));
    await waitFor(() => expect(patchCalls).toHaveLength(1));
    // A conflict must not silently drop the user's typing.
    expect(screen.getByLabelText('卡住的位置')).toHaveValue('QA_TEST 本地保留卡点');
    expect(await screen.findByText(/修改未保存，输入已保留/)).toBeInTheDocument();
  });
});
