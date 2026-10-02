import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { AdvisorPage } from './AdvisorPage';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const envelope = (data: unknown, status = 200) => new Response(JSON.stringify({ data, meta: { request_id: 'qa' } }), { status });
const failure = (status: number, code: string) => new Response(JSON.stringify({ error: { code, message: 'QA test failure' }, meta: { request_id: 'qa' } }), { status });
const run = (extras: Record<string, unknown> = {}) => ({
  id: 'QA_TEST_run', status: 'ready', topic: 'QA_TEST 主题',
  subject_id: null, knowledge_point_id: null,
  facts: [{ text: 'QA_TEST 事实一', source_refs: ['QA_TEST_ev1'] }],
  inferences: [{ text: 'QA_TEST 解释一', source_refs: ['QA_TEST_ev1'] }],
  missing_information: ['QA_TEST 缺少的记录'],
  summary: 'QA_TEST 总结',
  degradation_reason: null,
  evidence_count: 1,
  evidence_refs: [{ id: 'QA_TEST_ev1', kind: 'attempt', version: 1, label: 'QA_TEST 第二次练习' }],
  data_version: 'dv1', model_id: 'm1', prompt_version: 'p1', policy_version: 'po1', rule_version: 'r1',
  privacy: { external: false, provider: 'none', scope: 'local_only' },
  created_at: '2026-09-30T10:00:00Z', updated_at: '2026-09-30T10:00:00Z',
  ...extras,
});
const setup = (fetchMock: ReturnType<typeof vi.fn>) => {
  vi.stubGlobal('fetch', fetchMock);
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false } });
  const renderPage = () => render(<QueryClientProvider client={client}><AdvisorPage userId="QA_TEST_user" /></QueryClientProvider>);
  return { renderPage };
};
const pathOf = (input: RequestInfo | URL) => new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');

async function openRun(name = '打开分析：QA_TEST 主题') {
  fireEvent.click(await screen.findByRole('button', { name }));
}

describe('optional AI advisor', () => {
  it('renders facts, possible interpretations and missing information as three distinct labelled sections', async () => {
    const ready = run({ facts: [{ text: 'QA_TEST 事实一', source_refs: ['QA_TEST_ev1', 'QA_TEST_unknown'] }] });
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = pathOf(input);
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/advisor/analyses') return envelope({ items: [ready], next_cursor: null });
      if (path === '/advisor/analyses/QA_TEST_run') return envelope(ready);
      throw new Error(`Unexpected ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    await openRun();

    // Three distinct sections, each with its own eyebrow label.
    const facts = await screen.findByRole('region', { name: '记录事实' });
    const inferences = screen.getByRole('region', { name: '可能解释' });
    const missing = screen.getByRole('region', { name: '还缺什么' });
    expect(within(facts).getByText('RECORDED FACTS')).toBeInTheDocument();
    expect(within(inferences).getByText('POSSIBLE INTERPRETATIONS')).toBeInTheDocument();
    expect(within(missing).getByText('STILL MISSING')).toBeInTheDocument();

    expect(within(facts).getByText('QA_TEST 事实一')).toBeInTheDocument();
    expect(within(inferences).getByText('QA_TEST 解释一')).toBeInTheDocument();
    expect(within(missing).getByText('QA_TEST 缺少的记录')).toBeInTheDocument();

    // Citations resolve ids through evidence_refs to their label, falling back to the id.
    expect(within(facts).getByText('QA_TEST 第二次练习')).toBeInTheDocument();
    expect(within(facts).getByText('QA_TEST_unknown')).toBeInTheDocument();
    expect(within(facts).queryByText('QA_TEST_ev1')).toBeNull();
    expect(within(inferences).getByText('QA_TEST 第二次练习')).toBeInTheDocument();
  });

  it('shows the honest degraded banner and still renders facts and missing information', async () => {
    const degraded = run({ status: 'degraded', degradation_reason: 'provider_timeout' });
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = pathOf(input);
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/advisor/analyses') return envelope({ items: [degraded], next_cursor: null });
      if (path === '/advisor/analyses/QA_TEST_run') return envelope(degraded);
      throw new Error(`Unexpected ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    await openRun();
    expect(await screen.findByText('AI 暂时不可用；下面的记录事实仍来自你自己的学习记录。')).toBeInTheDocument();
    expect(screen.getByText('QA_TEST 事实一')).toBeInTheDocument();
    expect(screen.getByText('QA_TEST 缺少的记录')).toBeInTheDocument();
  });

  it('renders facts but no inferences when the model output is blocked', async () => {
    const blocked = run({ status: 'blocked', inferences: [] });
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = pathOf(input);
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/advisor/analyses') return envelope({ items: [blocked], next_cursor: null });
      if (path === '/advisor/analyses/QA_TEST_run') return envelope(blocked);
      throw new Error(`Unexpected ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    await openRun();
    expect(await screen.findByText('本次模型输出未通过安全校验，已丢弃，不会改写你的记录。')).toBeInTheDocument();
    const facts = screen.getByRole('region', { name: '记录事实' });
    expect(within(facts).getByText('QA_TEST 事实一')).toBeInTheDocument();
    const inferences = screen.getByRole('region', { name: '可能解释' });
    expect(within(inferences).queryAllByRole('listitem')).toHaveLength(0);
    expect(within(inferences).getByText('模型输出未通过安全校验，已丢弃，因此这里没有解释。')).toBeInTheDocument();
  });

  it('shows the standard insufficient-records message', async () => {
    const insufficient = run({ status: 'insufficient', missing_information: ['QA_TEST 还需要更多练习'] });
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = pathOf(input);
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/advisor/analyses') return envelope({ items: [insufficient], next_cursor: null });
      if (path === '/advisor/analyses/QA_TEST_run') return envelope(insufficient);
      throw new Error(`Unexpected ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    await openRun();
    expect(await screen.findByText('记录还不足，可以先开始学习。')).toBeInTheDocument();
    expect(screen.getByText('QA_TEST 还需要更多练习')).toBeInTheDocument();
  });

  it('creates a run with an operation_id equal to the Idempotency-Key header', async () => {
    const postCalls: Array<{ headers: Headers; body: string }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = pathOf(input);
      if (path === '/subjects') return envelope({ items: [{ id: 'QA_TEST_subject', name: 'QA_TEST 学科' }] });
      if (path === '/advisor/analyses' && init?.method === 'POST') {
        postCalls.push({ headers: new Headers(init.headers), body: String(init.body) });
        return envelope(run(), 201);
      }
      if (path === '/advisor/analyses') return envelope({ items: [], next_cursor: null });
      if (path === '/advisor/analyses/QA_TEST_run') return envelope(run());
      throw new Error(`Unexpected ${init?.method ?? 'GET'} ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    const subject = await screen.findByLabelText('学科');
    await screen.findByRole('option', { name: 'QA_TEST 学科' });
    fireEvent.change(subject, { target: { value: 'QA_TEST_subject' } });
    fireEvent.change(screen.getByLabelText('想了解的主题（可选）'), { target: { value: 'QA_TEST 输入' } });
    fireEvent.click(screen.getByRole('button', { name: '让 Hermes 看看' }));
    await waitFor(() => expect(postCalls).toHaveLength(1));
    const body = JSON.parse(postCalls[0]?.body ?? '{}');
    expect(body.operation_id).toBe(postCalls[0]?.headers.get('Idempotency-Key'));
    expect(body).toMatchObject({ topic: 'QA_TEST 输入', subject_id: 'QA_TEST_subject', knowledge_point_id: null });
  });

  it('cancels a run with a new operation_id and a matching Idempotency-Key', async () => {
    const createCalls: Array<{ headers: Headers; body: string }> = [];
    const cancelCalls: Array<{ headers: Headers; body: string }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = pathOf(input);
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/advisor/analyses' && init?.method === 'POST') {
        createCalls.push({ headers: new Headers(init.headers), body: String(init.body) });
        return envelope(run(), 201);
      }
      if (path === '/advisor/analyses/QA_TEST_run/cancel' && init?.method === 'POST') {
        cancelCalls.push({ headers: new Headers(init.headers), body: String(init.body) });
        return envelope(run({ status: 'cancelled' }));
      }
      if (path === '/advisor/analyses') return envelope({ items: [], next_cursor: null });
      if (path === '/advisor/analyses/QA_TEST_run') return envelope(cancelCalls.length > 0 ? run({ status: 'cancelled' }) : run());
      throw new Error(`Unexpected ${init?.method ?? 'GET'} ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    fireEvent.change(await screen.findByLabelText('想了解的主题（可选）'), { target: { value: 'QA_TEST 取消用例' } });
    fireEvent.click(screen.getByRole('button', { name: '让 Hermes 看看' }));
    await waitFor(() => expect(createCalls).toHaveLength(1));
    fireEvent.click(await screen.findByRole('button', { name: '取消本次分析' }));
    await waitFor(() => expect(cancelCalls).toHaveLength(1));
    const createBody = JSON.parse(createCalls[0]?.body ?? '{}');
    const cancelBody = JSON.parse(cancelCalls[0]?.body ?? '{}');
    expect(createBody.operation_id).toBe(createCalls[0]?.headers.get('Idempotency-Key'));
    expect(cancelBody.operation_id).toBe(cancelCalls[0]?.headers.get('Idempotency-Key'));
    expect(cancelBody.operation_id).not.toBe(createBody.operation_id);
    expect(await screen.findByText('这次分析已取消，没有生成新的解释。')).toBeInTheDocument();
  });

  it('keeps the typed topic and offers a retry when creating fails', async () => {
    const postCalls: Array<{ headers: Headers; body: string }> = [];
    let createAttempts = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = pathOf(input);
      if (path === '/subjects') return envelope({ items: [] });
      if (path === '/advisor/analyses' && init?.method === 'POST') {
        createAttempts += 1;
        postCalls.push({ headers: new Headers(init.headers), body: String(init.body) });
        // First create fails, a safe retry with the same operation succeeds.
        if (createAttempts === 1) return failure(503, 'TEMPORARY');
        return envelope(run(), 201);
      }
      if (path === '/advisor/analyses') return envelope({ items: [], next_cursor: null });
      if (path === '/advisor/analyses/QA_TEST_run') return envelope(run());
      throw new Error(`Unexpected ${init?.method ?? 'GET'} ${path}`);
    });
    const { renderPage } = setup(fetchMock);
    renderPage();
    fireEvent.change(await screen.findByLabelText('想了解的主题（可选）'), { target: { value: 'QA_TEST 保留输入' } });
    fireEvent.click(screen.getByRole('button', { name: '让 Hermes 看看' }));
    expect(await screen.findByText(/输入已保留/)).toBeInTheDocument();
    expect(screen.getByLabelText('想了解的主题（可选）')).toHaveValue('QA_TEST 保留输入');
    fireEvent.click(screen.getByRole('button', { name: '重试这次分析' }));
    await waitFor(() => expect(createAttempts).toBe(2));
    expect(postCalls[1]?.body).toBe(postCalls[0]?.body);
    expect(JSON.parse(postCalls[1]?.body ?? '{}').operation_id).toBe(postCalls[1]?.headers.get('Idempotency-Key'));
  });
});
