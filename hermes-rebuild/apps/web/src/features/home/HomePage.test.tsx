import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { HomeResponse } from '../../shared/api/types';
import { HomePage, type HomePageProps } from './HomePage';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const quoteData = { daily_quote: { local_date: '2035-04-03', day_timezone: 'Asia/Shanghai', quote: null, reason: 'no_eligible_quotes', preference: null } };
const section = <T,>(data: T, status: 'ready' | 'empty' | 'unavailable' = 'empty') => ({ status, data, source_revision: 'QA_TEST_home_v1', error: status === 'unavailable' ? { code: 'temporarily_unavailable', message: '这部分暂时无法读取。' } : null });
function payload(overrides: Record<string, unknown> = {}): HomeResponse {
  return { data: {
    date: '2035-04-03', timezone: 'Asia/Shanghai', rule_version: 'QA_TEST_home_rule',
    sections: {
      quote: section(quoteData),
      subjects: section({ items: [
        { id: 'QA_TEST_math', name: '数学', group_label: '公共课' },
        { id: 'QA_TEST_english', name: '英语', group_label: '公共课' },
        { id: 'QA_TEST_politics', name: '政治', group_label: '公共课' },
        { id: 'QA_TEST_signal', name: '信号与系统', group_label: '专业课' },
        { id: 'QA_TEST_circuit', name: '电路', group_label: '专业课' },
      ] }, 'ready'),
      continue_learning: section({ current: null, last: null }),
      suggestions: section({ items: [], has_more: false }),
      methods: section({ items: [
        { id: 'QA_TEST_method_recall', title: '主动回忆', summary: '先试着从记忆中说出来。', content_version: 1 },
        { id: 'QA_TEST_method_practice', title: '刻意练习', summary: '从一个具体问题开始。', content_version: 1 },
        { id: 'QA_TEST_method_explain', title: '费曼讲解', summary: '用自己的话讲一遍。', content_version: 1 },
      ] }, 'ready'),
      changes: section({ from_date: '2035-03-28', to_date: '2035-04-03', items: [], effective_learning_days: 0, rule_version: 'QA_TEST_changes', source_revision: 'QA_TEST_changes_v1' }),
      review: section({ items: [], has_more: false }),
    },
  }, meta: { request_id: 'QA_TEST_home' }, ...overrides } as unknown as HomeResponse;
}

function mount(props: Partial<HomePageProps> = {}, seededQuote?: unknown) {
  const callbacks = {
    onOpenSubject: vi.fn(), onStartFree: vi.fn(), onContinue: vi.fn(), onOpenMethods: vi.fn(),
    onStartMethod: vi.fn(), onOpenReview: vi.fn(), onOpenSession: vi.fn(), onOpenProblem: vi.fn(),
    onOpenSummary: vi.fn(), onOpenMyQuotes: vi.fn(),
  };
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  if (seededQuote) client.setQueryData(['quotes', 'QA_TEST_user', 'today'], seededQuote);
  render(<QueryClientProvider client={client}><HomePage userId="QA_TEST_user" {...callbacks} {...props} /></QueryClientProvider>);
  return { callbacks, client };
}

const envelope = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });
function responseData(data: unknown) { return { data, meta: { request_id: 'QA_TEST_home' } }; }

describe('HomePage', () => {
  it('shows equal real subject entries, the three method choices, and the server date without starting learning', async () => {
    const requests: RequestInit[] = [];
    const fetcher = vi.fn(async (url: string, init?: RequestInit) => { requests.push(init ?? {}); return url.endsWith('/home') ? envelope(payload()) : envelope(responseData(quoteData)); });
    vi.stubGlobal('fetch', fetcher);
    const { callbacks } = mount();
    for (const subject of ['数学', '英语', '政治', '信号与系统', '电路']) await screen.findByRole('button', { name: `${subject} →` });
    expect(screen.getByText('2035-04-03 · Asia/Shanghai')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '主动回忆' })).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: '电路 →' }));
    expect(callbacks.onOpenSubject).toHaveBeenCalledWith('QA_TEST_circuit');
    expect(requests.every((init) => init.method === undefined || init.method === 'GET')).toBe(true);
    expect(callbacks.onStartFree).not.toHaveBeenCalled();
  });

  it('restores the current active or paused scene through onContinue(null)', async () => {
    const body = payload();
    body.data.sections.continue_learning = section({ current: {
      id: 'QA_TEST_active', status: 'paused', goal: '复习卷积', subject_id: 'QA_TEST_math', effective_duration_seconds: 420,
    }, last: null }, 'ready') as never;
    vi.stubGlobal('fetch', vi.fn(async (url: string) => url.endsWith('/home') ? envelope(body) : envelope(responseData(quoteData))));
    const { callbacks } = mount();
    await userEvent.setup().click(await screen.findByRole('button', { name: '继续当前现场 →' }));
    expect(callbacks.onContinue).toHaveBeenCalledExactlyOnceWith(null);
  });

  it('offers a true ended-record continuation and keeps the optional free start separate', async () => {
    const body = payload();
    body.data.sections.continue_learning = section({ current: null, last: {
      id: 'QA_TEST_last', goal: '做完电路例题', resume_note: '从戴维南等效继续', stuck_note: '不知道如何选择等效端口', learning_date: '2035-04-02', subject_id: 'QA_TEST_circuit', subject_name: '电路', summary: '整理了一个卡点',
    } }, 'ready') as never;
    vi.stubGlobal('fetch', vi.fn(async (url: string) => url.endsWith('/home') ? envelope(body) : envelope(responseData(quoteData))));
    const { callbacks } = mount();
    expect(await screen.findByText('做完电路例题')).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.tagName === 'P' && element.textContent === '继续位置：从戴维南等效继续')).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.tagName === 'P' && element.textContent === '上次卡点：不知道如何选择等效端口')).toBeInTheDocument();
    await userEvent.setup().click(await screen.findByRole('button', { name: '继续上次 →' }));
    expect(callbacks.onContinue).toHaveBeenCalledWith(expect.objectContaining({ id: 'QA_TEST_last', goal: '做完电路例题', resume_note: '从戴维南等效继续', stuck_note: '不知道如何选择等效端口' }));
    expect(callbacks.onStartFree).not.toHaveBeenCalled();
  });

  it('shows evidence reasons and opens their source in the account timezone context', async () => {
    const body = payload();
    const source = { id: 'QA_TEST_source_session', kind: 'session', label: 'QA_TEST 已保存学习现场', version: 2, occurred_at: '2035-04-02T02:00:00Z', session_id: 'QA_TEST_source_session' };
    const item = { id: 'QA_TEST_suggestion', kind: 'unverified', reason: '这道题的作答还没有核对。', status: 'available', generated_at: '2035-04-02T02:00:00Z', rule_version: 'QA_TEST_rule', source_revision: 'QA_TEST_revision', version: 1, source_refs: [source] };
    body.data.sections.suggestions = section({ items: [item], has_more: false }, 'ready') as never;
    vi.stubGlobal('fetch', vi.fn(async (url: string) => url.endsWith('/home') ? envelope(body) : envelope(responseData(quoteData))));
    const { callbacks } = mount();
    expect(await screen.findByText('这道题的作答还没有核对。')).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: /QA_TEST 已保存学习现场 · v2/ }));
    expect(callbacks.onOpenSession).toHaveBeenCalledWith('QA_TEST_source_session');
  });

  it('retries an unavailable section independently while keeping the other loaded sections', async () => {
    const initial = payload();
    initial.data.sections.methods = section(null, 'unavailable') as never;
    const fetcher = vi.fn(async (url: string) => {
      if (url.endsWith('/home')) return envelope(initial);
      if (url.includes('/home?section=methods')) {
        return envelope(responseData({ ...payload().data, sections: { methods: section({ items: [{ id: 'QA_TEST_method_fixed', title: '主动回忆', summary: '从记忆提取。', content_version: 1 }] }, 'ready') } }));
      }
      return envelope(responseData(quoteData));
    });
    vi.stubGlobal('fetch', fetcher);
    mount();
    const user = userEvent.setup();
    const sectionHeading = await screen.findByRole('heading', { name: '学习方法' });
    const sectionElement = sectionHeading.closest('section');
    expect(sectionElement).not.toBeNull();
    await user.click(within(sectionElement!).getByRole('button', { name: '重试' }));
    expect(await screen.findByRole('button', { name: '用这个方法开始 →' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '数学 →' })).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith('/api/v1/home?section=methods', expect.anything());
  });

  it('keeps the loaded home intact and shows an alert when an isolated retry fails', async () => {
    const initial = payload();
    initial.data.sections.methods = section(null, 'unavailable') as never;
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.endsWith('/home')) return envelope(initial);
      if (url.includes('/home?section=methods')) return new Response(JSON.stringify({ error: { code: 'unavailable' } }), { status: 503 });
      return envelope(responseData(quoteData));
    }));
    mount();
    const sectionElement = (await screen.findByRole('heading', { name: '学习方法' })).closest('section');
    await userEvent.setup().click(within(sectionElement!).getByRole('button', { name: '重试' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('操作未完成');
    expect(screen.getByRole('button', { name: '数学 →' })).toBeInTheDocument();
  });

  it('reloads the full home when an isolated retry crosses the account date or rule boundary', async () => {
    const initial = payload();
    initial.data.sections.methods = section(null, 'unavailable') as never;
    const next = payload();
    next.data.date = '2035-04-04';
    next.data.rule_version = 'QA_TEST_next_rule';
    let fullReads = 0;
    const fetcher = vi.fn(async (url: string) => {
      if (url === '/api/v1/home') return envelope(fullReads++ > 0 ? next : initial);
      if (url.includes('/home?section=methods')) return envelope(responseData({
        ...next.data, sections: { methods: section({ items: [] }) },
      }));
      return envelope(responseData(quoteData));
    });
    vi.stubGlobal('fetch', fetcher);
    mount();
    const methodHeading = await screen.findByRole('heading', { name: '学习方法' });
    await userEvent.setup().click(within(methodHeading.closest('section')!).getByRole('button', { name: '重试' }));
    expect(await screen.findByText('2035-04-04 · Asia/Shanghai')).toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([url]) => url === '/api/v1/home')).toHaveLength(2);
    expect(screen.getByRole('button', { name: '数学 →' })).toBeInTheDocument();
  });

  it('invalidates yesterday’s cached quote when a methods retry crosses midnight', async () => {
    const initial = payload();
    initial.data.sections.methods = section(null, 'unavailable') as never;
    const yesterdayQuoteData = { daily_quote: { local_date: '2035-04-03', day_timezone: 'Asia/Shanghai', quote: { id: 'QA_TEST_quote_yesterday', text: 'QA_TEST 昨日金句', author: null }, reason: null, preference: null } };
    const todayQuoteData = { daily_quote: { local_date: '2035-04-04', day_timezone: 'Asia/Shanghai', quote: { id: 'QA_TEST_quote_today', text: 'QA_TEST 今日金句', author: null }, reason: null, preference: null } };
    initial.data.sections.quote = section(yesterdayQuoteData, 'ready') as never;
    const next = payload();
    next.data.date = '2035-04-04';
    next.data.sections.quote = section(todayQuoteData, 'ready') as never;
    let fullReads = 0;
    let crossedBoundary = false;
    const fetcher = vi.fn(async (url: string) => {
      if (url === '/api/v1/home') {
        if (fullReads++ > 0) crossedBoundary = true;
        return envelope(crossedBoundary ? next : initial);
      }
      if (url.includes('/home?section=methods')) return envelope(responseData({ ...next.data, sections: { methods: section({ items: [] }) } }));
      if (url.endsWith('/quotes/today')) {
        const selectedQuote = crossedBoundary ? todayQuoteData : yesterdayQuoteData;
        return envelope(responseData(selectedQuote));
      }
      return envelope(responseData(quoteData));
    });
    vi.stubGlobal('fetch', fetcher);
    const staleCache = { data: yesterdayQuoteData, meta: { request_id: 'QA_TEST_yesterday_cache' } };
    mount({}, staleCache);
    const methodsHeading = await screen.findByRole('heading', { name: '学习方法' });
    await userEvent.setup().click(within(methodsHeading.closest('section')!).getByRole('button', { name: '重试' }));
    expect(await screen.findByText('“QA_TEST 今日金句”')).toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([url]) => url === '/api/v1/quotes/today')).toHaveLength(2);
  });

  it('keeps the prior sections visible when a required boundary refresh fails', async () => {
    const initial = payload();
    initial.data.sections.methods = section(null, 'unavailable') as never;
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url === '/api/v1/home') return new Response(JSON.stringify({ error: { code: 'unavailable' } }), { status: 503 });
      if (url.includes('/home?section=methods')) return envelope(responseData({
        ...payload().data, date: '2035-04-04', sections: { methods: section({ items: [] }) },
      }));
      return envelope(responseData(quoteData));
    }));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    client.setQueryData(['home', 'QA_TEST_user'], initial);
    render(<QueryClientProvider client={client}><HomePage userId="QA_TEST_user" onOpenSubject={vi.fn()} onStartFree={vi.fn()} onContinue={vi.fn()} onOpenMethods={vi.fn()} onStartMethod={vi.fn()} onOpenReview={vi.fn()} onOpenSession={vi.fn()} onOpenProblem={vi.fn()} onOpenSummary={vi.fn()} onOpenMyQuotes={vi.fn()} /></QueryClientProvider>);
    const methodHeading = await screen.findByRole('heading', { name: '学习方法' });
    await userEvent.setup().click(within(methodHeading.closest('section')!).getByRole('button', { name: '重试' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('操作未完成');
    expect(screen.getByRole('button', { name: '数学 →' })).toBeInTheDocument();
    expect(screen.getByText('2035-04-03 · Asia/Shanghai')).toBeInTheDocument();
  });

  it('refreshes the quote query after quote-section retry instead of keeping stale cached text', async () => {
    const initial = payload();
    initial.data.sections.quote = section(null, 'unavailable') as never;
    const newQuote = { daily_quote: { local_date: '2035-04-03', day_timezone: 'Asia/Shanghai', quote: { id: 'QA_TEST_quote_new', text: 'QA_TEST 新金句', author: null }, reason: null, preference: null } };
    let currentQuote: unknown = { daily_quote: { local_date: '2035-04-03', day_timezone: 'Asia/Shanghai', quote: { id: 'QA_TEST_quote_old', text: 'QA_TEST 旧金句', author: null }, reason: null, preference: null } };
    const fetcher = vi.fn(async (url: string) => {
      if (url.endsWith('/home')) return envelope(initial);
      if (url.includes('/home?section=quote')) { currentQuote = newQuote; return envelope(responseData({ ...payload().data, sections: { quote: section(newQuote) } })); }
      if (url.endsWith('/quotes/today')) return envelope(responseData(currentQuote));
      return envelope(responseData(quoteData));
    });
    vi.stubGlobal('fetch', fetcher);
    const cachedQuote = { data: { daily_quote: { local_date: '2035-04-03', day_timezone: 'Asia/Shanghai', quote: { id: 'QA_TEST_quote_old', text: 'QA_TEST 旧金句', author: null }, reason: null, preference: null } }, meta: { request_id: 'QA_TEST_cached_quote' } };
    mount({}, cachedQuote);
    const quoteHeading = await screen.findByRole('heading', { name: '今日金句' });
    await userEvent.setup().click(within(quoteHeading.closest('section')!).getByRole('button', { name: '重试' }));
    expect(await screen.findByText('“QA_TEST 新金句”')).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith('/api/v1/quotes/today', expect.anything());
  });

  it('retains a direct free-learning action when the whole home endpoint is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ error: { code: 'unavailable' } }), { status: 503 })));
    const { callbacks } = mount();
    await userEvent.setup().click(await screen.findByRole('button', { name: '开始一段学习 →' }));
    expect(callbacks.onStartFree).toHaveBeenCalledOnce();
  });

  it('shows a safe retry view for malformed successful responses without sections', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => envelope({ data: { date: '2035-04-03', timezone: 'Asia/Shanghai', rule_version: 'bad' } })));
    mount();
    expect(await screen.findByRole('heading', { name: '书房暂时无法载入' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '开始一段学习 →' })).toBeInTheDocument();
  });

  it('isolates malformed individual section data while keeping valid home sections available', async () => {
    const body = payload();
    body.data.sections.changes = section({ items: [{ text: '无来源的错误数据' }], effective_learning_days: -1, from_date: 'bad', to_date: 'bad' }) as never;
    vi.stubGlobal('fetch', vi.fn(async (url: string) => url.endsWith('/home') ? envelope(body) : envelope(responseData(quoteData))));
    mount();
    expect(await screen.findByRole('heading', { name: '近七日记录' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重试' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '数学 →' })).toBeInTheDocument();
  });
});
