import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { StuckPointsPage } from './StuckPointsPage';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const envelope = (data: unknown, status = 200) => new Response(JSON.stringify({ data, meta: { request_id: 'qa' } }), { status });
const failure = (status: number, code: string) => new Response(JSON.stringify({ error: { code, message: 'QA test failure' }, meta: { request_id: 'qa' } }), { status });
const urlOf = (input: RequestInfo | URL) => new URL(String(input), 'http://localhost');
const pathOf = (input: RequestInfo | URL) => urlOf(input).pathname.replace('/api/v1', '');

const session = { id: 'QA_TEST_session', goal: 'QA_TEST 采样复习', learning_date: '2026-09-30' };
const point = (extras: Record<string, unknown> = {}) => ({
  id: 'QA_TEST_point', version: 1, session_id: 'QA_TEST_session', attempt_id: null,
  knowledge_point_id: null, text: 'QA_TEST 为什么采样后出现一排 δ？', status: 'open',
  resolved_at: null, resolution_note: null,
  created_at: '2026-09-30T10:00:00Z', updated_at: '2026-09-30T10:00:00Z',
  ...extras,
});

const setup = (fetchMock: ReturnType<typeof vi.fn>, onOpenSession = vi.fn()) => {
  vi.stubGlobal('fetch', fetchMock);
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false } });
  const renderPage = () => render(
    <QueryClientProvider client={client}>
      <StuckPointsPage userId="QA_TEST_user" timezone="Asia/Shanghai" onOpenSession={onOpenSession} />
    </QueryClientProvider>,
  );
  return { renderPage, onOpenSession };
};

describe('stuck points', () => {
  it('lists open stuck points by default and can switch to the resolved view', async () => {
    const open = point();
    const resolved = point({ id: 'QA_TEST_done', text: 'QA_TEST 参考点为什么换', status: 'resolved', resolved_at: '2026-09-30T11:00:00Z', version: 2 });
    const seen: Array<string | null> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = pathOf(input);
      if (path === '/learning-sessions') return envelope({ items: [session], next_cursor: null });
      if (path === '/stuck-points') {
        const status = urlOf(input).searchParams.get('status');
        seen.push(status);
        return envelope({ items: status === 'resolved' ? [resolved] : [open], next_cursor: null });
      }
      throw new Error(`Unexpected ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();

    const openCard = (await screen.findByText('QA_TEST 为什么采样后出现一排 δ？')).closest('li') as HTMLElement;
    expect(within(openCard).getByText('仍然卡住')).toBeInTheDocument();
    expect(seen).toContain('open');

    fireEvent.change(screen.getByLabelText('查看'), { target: { value: 'resolved' } });
    const doneCard = (await screen.findByText('QA_TEST 参考点为什么换')).closest('li') as HTMLElement;
    expect(within(doneCard).getByText('已经过去')).toBeInTheDocument();
    expect(seen).toContain('resolved');
  });

  it('shows an honest empty state instead of inventing content', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = pathOf(input);
      if (path === '/learning-sessions') return envelope({ items: [session], next_cursor: null });
      if (path === '/stuck-points') return envelope({ items: [], next_cursor: null });
      throw new Error(`Unexpected ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    expect(await screen.findByText('现在没有仍然卡住的地方。这不代表必须去找，只是暂时没有记录。')).toBeInTheDocument();
  });

  it('creates a stuck point for the chosen session with operation_id equal to the Idempotency-Key', async () => {
    const posts: Array<{ headers: Headers; body: string }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = pathOf(input);
      if (path === '/learning-sessions') return envelope({ items: [session], next_cursor: null });
      if (path === '/stuck-points' && init?.method === 'POST') {
        posts.push({ headers: new Headers(init.headers), body: String(init.body) });
        return envelope(point(), 201);
      }
      if (path === '/stuck-points') return envelope({ items: [], next_cursor: null });
      throw new Error(`Unexpected ${init?.method ?? 'GET'} ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    fireEvent.change(await screen.findByLabelText('刚刚真正卡在哪里'), { target: { value: 'QA_TEST 为什么上下限可以直接代？' } });
    fireEvent.click(screen.getByRole('button', { name: '记下这个卡壳点' }));
    await waitFor(() => expect(posts).toHaveLength(1));
    const body = JSON.parse(posts[0]?.body ?? '{}');
    expect(body.operation_id).toBe(posts[0]?.headers.get('Idempotency-Key'));
    expect(body).toMatchObject({ session_id: 'QA_TEST_session', text: 'QA_TEST 为什么上下限可以直接代？' });
    expect(await screen.findByLabelText('刚刚真正卡在哪里')).toHaveValue('');
  });

  it('keeps the typed text and retries with the same operation id when saving fails', async () => {
    const posts: Array<{ headers: Headers; body: string }> = [];
    let attempts = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = pathOf(input);
      if (path === '/learning-sessions') return envelope({ items: [session], next_cursor: null });
      if (path === '/stuck-points' && init?.method === 'POST') {
        attempts += 1;
        posts.push({ headers: new Headers(init.headers), body: String(init.body) });
        if (attempts === 1) return failure(503, 'TEMPORARY');
        return envelope(point(), 201);
      }
      if (path === '/stuck-points') return envelope({ items: [], next_cursor: null });
      throw new Error(`Unexpected ${init?.method ?? 'GET'} ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    fireEvent.change(await screen.findByLabelText('刚刚真正卡在哪里'), { target: { value: 'QA_TEST 保留输入' } });
    fireEvent.click(screen.getByRole('button', { name: '记下这个卡壳点' }));
    expect(await screen.findByText(/内容已保留/)).toBeInTheDocument();
    expect(screen.getByLabelText('刚刚真正卡在哪里')).toHaveValue('QA_TEST 保留输入');
    fireEvent.click(screen.getByRole('button', { name: '记下这个卡壳点' }));
    await waitFor(() => expect(attempts).toBe(2));
    expect(posts[1]?.body).toBe(posts[0]?.body);
  });

  it('resolves a stuck point with a note, then re-opens it, using If-Match and a matching key', async () => {
    const patches: Array<{ headers: Headers; body: string }> = [];
    let current = point();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = pathOf(input);
      if (path === '/learning-sessions') return envelope({ items: [session], next_cursor: null });
      if (path === '/stuck-points/QA_TEST_point' && init?.method === 'PATCH') {
        patches.push({ headers: new Headers(init.headers), body: String(init.body) });
        const parsed = JSON.parse(String(init.body));
        current = parsed.status === 'resolved'
          ? point({ status: 'resolved', resolved_at: '2026-09-30T11:00:00Z', resolution_note: parsed.resolution_note, version: 2 })
          : point({ version: 3 });
        return envelope(current);
      }
      if (path === '/stuck-points') return envelope({ items: [current], next_cursor: null });
      throw new Error(`Unexpected ${init?.method ?? 'GET'} ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    const card = (await screen.findByText('QA_TEST 为什么采样后出现一排 δ？')).closest('li');
    expect(card).not.toBeNull();
    fireEvent.change(within(card as HTMLElement).getByLabelText('一句话说明怎么过去的（可选）'), { target: { value: 'QA_TEST 换元后清楚' } });
    fireEvent.click(within(card as HTMLElement).getByRole('button', { name: '标记为已经过去' }));
    await waitFor(() => expect(patches).toHaveLength(1));
    const resolveBody = JSON.parse(patches[0]?.body ?? '{}');
    expect(patches[0]?.headers.get('If-Match')).toBe('1');
    expect(resolveBody.operation_id).toBe(patches[0]?.headers.get('Idempotency-Key'));
    expect(resolveBody).toMatchObject({ status: 'resolved', resolution_note: 'QA_TEST 换元后清楚' });

    const reopened = await screen.findByRole('button', { name: '重新标为仍然卡住' });
    fireEvent.click(reopened);
    await waitFor(() => expect(patches).toHaveLength(2));
    const reopenBody = JSON.parse(patches[1]?.body ?? '{}');
    expect(patches[1]?.headers.get('If-Match')).toBe('2');
    expect(reopenBody).toMatchObject({ status: 'open', resolution_note: null });
  });

  it('edits the sentence and preserves input when the version conflicts', async () => {
    const patches: Array<{ headers: Headers; body: string }> = [];
    let attempts = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = pathOf(input);
      if (path === '/learning-sessions') return envelope({ items: [session], next_cursor: null });
      if (path === '/stuck-points/QA_TEST_point' && init?.method === 'PATCH') {
        attempts += 1;
        patches.push({ headers: new Headers(init.headers), body: String(init.body) });
        if (attempts === 1) return failure(409, 'VERSION_CONFLICT');
        return envelope(point({ text: 'QA_TEST 改好的句子', version: 2 }));
      }
      if (path === '/stuck-points') return envelope({ items: [point()], next_cursor: null });
      throw new Error(`Unexpected ${init?.method ?? 'GET'} ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: '修改文字' }));
    fireEvent.change(screen.getByLabelText('修改卡壳点文字'), { target: { value: 'QA_TEST 改好的句子' } });
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
    expect(await screen.findByText(/已重新读取最新状态；你的输入仍保留/)).toBeInTheDocument();
    expect(patches[0]?.headers.get('If-Match')).toBe('1');
    expect(JSON.parse(patches[0]?.body ?? '{}')).toMatchObject({ text: 'QA_TEST 改好的句子' });
  });
});
