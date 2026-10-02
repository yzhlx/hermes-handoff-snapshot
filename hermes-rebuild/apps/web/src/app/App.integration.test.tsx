import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App } from './App';
import { homeFixture } from './test-home-fixture';
import { clearQuotePendingOperations } from '../features/quotes/Quotes';
import { clearFeedbackDrafts } from '../features/feedback/draft-store';
import { clearLearningDraft } from '../features/learning/draft-store';
import { setCsrfToken, setUnauthorizedHandler } from '../shared/api/client';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  clearQuotePendingOperations();
  clearFeedbackDrafts();
  clearLearningDraft();
  setCsrfToken(undefined);
  setUnauthorizedHandler(undefined);
});

const quoteText = 'QA_TEST_保持自己的学习节奏';
const auth = {
  user: { id: 'QA_TEST_owner', username: 'QA_TEST_owner', timezone: 'Asia/Shanghai' },
  csrf_token: 'QA_TEST_csrf',
};
const envelope = (data: unknown) => new Response(JSON.stringify({ data, meta: { request_id: 'QA_TEST_app' } }));

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
  return client;
}

function server() {
  const writes: RequestInit[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
    if (url.endsWith('/auth/session')) return envelope(auth);
    if (url.endsWith('/health/ready')) return envelope({ status: 'ready' });
    if (url.endsWith('/learning-sessions/current')) return envelope(null);
    if (url.endsWith('/home')) {
      const home = homeFixture();
      home.sections.quote = { status: 'ready', source_revision: 'QA_TEST_quote', error: null, data: { daily_quote: { local_date: '2026-09-30', day_timezone: 'Asia/Shanghai', quote: { id: 'q01', text: quoteText, author: null }, reason: null, preference: null } } };
      return envelope(home);
    }
    if (url.endsWith('/subjects')) return envelope({ items: [] });
    if (url.includes('/learning-sessions?')) return envelope({ items: [], next_cursor: null });
    if (url.endsWith('/learning-methods')) return envelope({ items: [
      { id: 'active-recall', title: '主动回忆', summary: 'QA_TEST 先回想再看。', problem: 'QA_TEST', situations: [], steps: [], pitfalls: [] },
      { id: 'worked-example-compare', title: '双例对比', summary: 'QA_TEST 比较两道路径。', problem: 'QA_TEST', situations: [], steps: [], pitfalls: [] },
    ] });
    if (url.endsWith('/learning-situations')) return envelope({ items: [] });
    if (url.endsWith('/problem-comparisons')) return envelope({ items: [], next_cursor: null });
    if (url.includes('/stuck-points')) return envelope({ items: [], next_cursor: null });
    if (url.includes('/problems?') || url.endsWith('/problems')) return envelope({ items: [], next_cursor: null });
    if (url.endsWith('/quotes/today')) return envelope({ daily_quote: {
      local_date: '2026-09-30', day_timezone: 'Asia/Shanghai',
      quote: { id: 'q01', text: quoteText, author: null }, reason: null, preference: null,
    } });
    if (url.endsWith('/quotes/favorites')) return envelope({ items: [], disliked: [], next_cursor: null });
    if (url.endsWith('/auth/logout')) {
      writes.push(init);
      return new Response(null, { status: 204 });
    }
    throw new Error(`Unexpected test request: ${url}`);
  }));
  return writes;
}

describe('study room integration', () => {
  it('shows the daily quote in the study room and removes it from the learning scene', async () => {
    server();
    mount();
    const user = userEvent.setup();
    expect(await screen.findByText(`“${quoteText}”`)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^学习现场$/ }));
    await screen.findByLabelText('这次想学什么？');
    expect(screen.queryByText(`“${quoteText}”`)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^书房$/ }));
    expect(await screen.findByText(`“${quoteText}”`)).toBeInTheDocument();
    await user.click(within(screen.getByRole('navigation', { name: '书房导航' })).getByRole('button', { name: /^我的金句$/ }));
    expect(await screen.findByRole('heading', { name: '我的金句' })).toBeInTheDocument();
    expect(screen.queryByText(`“${quoteText}”`)).not.toBeInTheDocument();
  });

  it('clears private query data after confirmed logout and sends the CSRF token', async () => {
    const writes = server();
    const client = mount();
    await screen.findByText(`“${quoteText}”`);
    client.setQueryData(['session-reflection', 'QA_TEST_session'], { data: { summary: 'QA_TEST_private' } });
    client.setQueryData(['problem', 'QA_TEST_problem'], { data: { statement: 'QA_TEST_private_problem' } });
    await userEvent.setup().click(screen.getByRole('button', { name: '退出' }));
    await screen.findByRole('heading', { name: '回到你的书房' });
    await waitFor(() => expect(client.getQueryData(['session-reflection', 'QA_TEST_session'])).toBeUndefined());
    expect(client.getQueryData(['problem', 'QA_TEST_problem'])).toBeUndefined();
    expect(client.getQueryData(['quotes', auth.user.id, 'today'])).toBeUndefined();
    expect(screen.queryByText(`“${quoteText}”`)).not.toBeInTheDocument();
    expect(writes).toHaveLength(1);
    expect(new Headers(writes[0].headers).get('X-CSRF-Token')).toBe(auth.csrf_token);
  });

  it('navigates to the problem comparison workspace from the study room navigation', async () => {
    server();
    mount();
    const user = userEvent.setup();
    const navigation = await screen.findByRole('navigation', { name: '书房导航' });
    await user.click(within(navigation).getByRole('button', { name: /^题目与对比$/ }));
    expect(await screen.findByRole('heading', { name: '双例对比' })).toBeInTheDocument();
    expect(screen.getByText(/这里的比较不会代替原作答或掌握依据/)).toBeInTheDocument();
  });

  it('routes the two-example learning method entry to the comparison workspace', async () => {
    server();
    mount();
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: /^学习方法$/ }));
    expect(await screen.findByRole('heading', { name: '学习方法' })).toBeInTheDocument();
    // Open the two-example method card specifically, then use its start action.
    const cards = await screen.findAllByRole('button', { name: '查看方法与步骤' });
    await user.click(cards[cards.length - 1]!);
    const start = await screen.findByRole('button', { name: /开始$/ });
    await user.click(start);
    expect(await screen.findByRole('heading', { name: '双例对比' })).toBeInTheDocument();
    expect(screen.queryByLabelText('这次想学什么？')).not.toBeInTheDocument();
  });

  it('reaches the independent stuck point surface from the study room navigation', async () => {
    server();
    mount();
    const user = userEvent.setup();
    const navigation = await screen.findByRole('navigation', { name: '书房导航' });
    await user.click(within(navigation).getByRole('button', { name: /^卡壳点$/ }));
    expect(await screen.findByRole('heading', { name: '卡壳点' })).toBeInTheDocument();
    // No records yet: the surface says so honestly instead of inventing content.
    expect(await screen.findByText(/现在没有仍然卡住的地方/)).toBeInTheDocument();
    // With no learning session available, the create control cannot be used yet.
    expect(screen.getByRole('button', { name: '记下这个卡壳点' })).toBeDisabled();
  });

  it('hides the saved answer by default while verifying original materials from the comparison workspace', async () => {
    const problem = {
      id: 'QA_TEST_problem', title: 'QA_TEST 待核对题目', statement: 'QA_TEST 题干', correct_answer: 'QA_TEST 敏感答案',
      source_note: null, subject_id: 'QA_TEST_subject', archived: false, is_representative: false,
      knowledge_point_ids: [], attachment_links: [], attempts: [], version: 1,
      created_at: '2026-09-01T10:00:00Z', updated_at: '2026-09-01T10:00:00Z',
    };
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.endsWith('/auth/session')) return envelope(auth);
      if (url.endsWith('/health/ready')) return envelope({ status: 'ready' });
      if (url.endsWith('/learning-sessions/current')) return envelope(null);
      if (url.endsWith('/home')) return envelope(homeFixture());
      if (url.endsWith('/subjects')) return envelope({ items: [] });
      if (url.endsWith('/problem-comparisons')) return envelope({ items: [], next_cursor: null });
      if (url.includes('/problems?')) return envelope({ items: [problem], next_cursor: null });
      if (url.endsWith('/problems/QA_TEST_problem')) return envelope(problem);
      throw new Error(`Unexpected test request: ${url}`);
    }));
    mount();
    const user = userEvent.setup();
    const navigation = await screen.findByRole('navigation', { name: '书房导航' });
    await user.click(within(navigation).getByRole('button', { name: /^题目与对比$/ }));
    await user.click(await screen.findByRole('button', { name: '浏览题目与代表题' }));
    await user.click(await screen.findByRole('button', { name: '查看与核对原作答' }));
    // The verification surface must not show the saved answer until asked:
    // it is wrapped in a collapsed disclosure, not rendered in the open.
    expect(await screen.findByRole('heading', { name: '核对原作答' })).toBeInTheDocument();
    const panel = screen.getByRole('region', { name: '核对原作答' });
    expect(within(panel).getByText('题干')).toBeInTheDocument();
    expect(within(panel).getByText('QA_TEST 题干')).toBeInTheDocument();
    const disclosure = within(panel).getByText('查看已保存的答案');
    expect(disclosure).toBeInTheDocument();
    const details = disclosure.closest('details');
    expect(details).not.toBeNull();
    expect((details as HTMLDetailsElement).open).toBe(false);
    expect(within(details as HTMLElement).getByText('QA_TEST 敏感答案')).toBeInTheDocument();
  });
});
