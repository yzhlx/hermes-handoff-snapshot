import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { clearQuotePendingOperations, DailyQuote, MyQuotes } from './Quotes';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  clearQuotePendingOperations();
});

const envelope = (data: unknown, status = 200) =>
  new Response(JSON.stringify({ data, meta: { request_id: 'QA_TEST_quote_request' } }), { status });

const quote = { id: 'q01', text: '且以微渺而恒定的努力，对抗盛大而冗长的空虚。', author: null };
const preference = {
  quote_id: quote.id,
  text: quote.text,
  favorited: true,
  disliked: false,
  version: 1,
  updated_at: '2026-09-30T08:00:00+00:00',
};

function todayData(currentQuote: typeof quote | null = quote, currentPreference: typeof preference | null = null) {
  return {
    daily_quote: {
      local_date: '2026-09-30',
      day_timezone: 'Asia/Shanghai',
      quote: currentQuote,
      reason: currentQuote ? null : 'disliked_today',
      preference: currentPreference,
    },
  };
}

function mount(element: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}>{element}</QueryClientProvider>);
  return client;
}

describe('daily quote and personal quote library', () => {
  it('shows the exact quote, creates a favorite with a first-write precondition, and keeps the author unknown', async () => {
    let saved = false;
    const fetcher = vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/quotes/today')) return envelope(todayData(quote, saved ? { ...preference, favorited: true } : null));
      if (url.endsWith('/quotes/favorites')) return envelope({ items: saved ? [{ ...preference, favorited: true }] : [], disliked: [], next_cursor: null });
      expect(url).toContain(`/quotes/${quote.id}/preference`);
      expect(init.method).toBe('PUT');
      expect(JSON.parse(String(init.body))).toEqual({ favorited: true, disliked: false });
      expect(new Headers(init.headers).get('If-None-Match')).toBe('*');
      expect(new Headers(init.headers).get('If-Match')).toBeNull();
      saved = true;
      return envelope({ preference: { ...preference, favorited: true }, daily_quote: todayData(quote).daily_quote });
    });
    vi.stubGlobal('fetch', fetcher);
    mount(<DailyQuote userId="QA_TEST_user" onOpenMyQuotes={vi.fn()} />);
    expect(await screen.findByText(`“${quote.text}”`)).toBeInTheDocument();
    expect(screen.queryByText(/未知作者/)).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: '收藏' }));
    await screen.findByRole('button', { name: '已收藏' });
    const preferenceRequest = fetcher.mock.calls.find(([url, init]) => String(url).includes('/preference') && init?.method === 'PUT')?.[1];
    expect(preferenceRequest).toBeDefined();
    expect(new Headers(preferenceRequest?.headers).get('Idempotency-Key')).toBeTruthy();
  });

  it('hides a disliked quote for the day instead of silently picking another one', async () => {
    let disliked = false;
    const fetcher = vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/quotes/today')) return envelope(todayData(disliked ? null : quote, disliked ? { ...preference, disliked: true } : null));
      if (url.includes('/preference')) {
        expect(JSON.parse(String(init.body))).toEqual({ favorited: false, disliked: true });
        expect(new Headers(init.headers).get('If-None-Match')).toBe('*');
        disliked = true;
        return envelope({ preference: { ...preference, favorited: false, disliked: true }, daily_quote: todayData(null).daily_quote });
      }
      return envelope({ items: [], disliked: [], next_cursor: null });
    });
    vi.stubGlobal('fetch', fetcher);
    mount(<DailyQuote userId="QA_TEST_user" onOpenMyQuotes={vi.fn()} />);
    await screen.findByText(`“${quote.text}”`);
    await userEvent.setup().click(screen.getByRole('button', { name: '不喜欢' }));
    expect(await screen.findByText('今天这句话已收起。')).toBeInTheDocument();
    expect(screen.queryByText(`“${quote.text}”`)).not.toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([url]) => String(url).endsWith('/quotes/today'))).toHaveLength(2);
  });

  it('restores a disliked quote independently from favorites using the saved version', async () => {
    let disliked = true;
    const fetcher = vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/quotes/favorites')) return envelope({ items: [], disliked: disliked ? [{ ...preference, favorited: false, disliked: true }] : [], next_cursor: null });
      expect(url).toContain(`/quotes/${quote.id}/preference`);
      expect(JSON.parse(String(init.body))).toEqual({ favorited: false, disliked: false });
      expect(new Headers(init.headers).get('If-Match')).toBe('"1"');
      expect(new Headers(init.headers).get('If-None-Match')).toBeNull();
      disliked = false;
      return envelope({ preference: { ...preference, favorited: false, disliked: false, version: 2 } });
    });
    vi.stubGlobal('fetch', fetcher);
    mount(<MyQuotes userId="QA_TEST_user" />);
    await screen.findByText('不喜欢的句子');
    await userEvent.setup().click(screen.getByRole('button', { name: '撤销不喜欢' }));
    await waitFor(() => expect(screen.getByText('没有屏蔽的句子。')).toBeInTheDocument());
  });

  it('reuses the same operation after a 401 and component remount for the same owner', async () => {
    let commandCount = 0;
    let favorited = true;
    const commands: Array<{ key: string | null; body: string | null }> = [];
    const fetcher = vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/quotes/favorites')) return envelope({ items: favorited ? [{ ...preference }] : [], disliked: [], next_cursor: null });
      if (url.includes('/preference')) {
        commandCount++;
        commands.push({ key: new Headers(init.headers).get('Idempotency-Key'), body: String(init.body ?? null) });
        if (commandCount === 1) return new Response(JSON.stringify({ error: { code: 'UNAUTHENTICATED', request_id: 'expired' } }), { status: 401 });
        favorited = false;
        return envelope({ preference: { ...preference, favorited: false, version: 2 } });
      }
      throw new Error(`Unexpected URL: ${url}`);
    });
    vi.stubGlobal('fetch', fetcher);
    const firstClient = mount(<MyQuotes userId="QA_TEST_user" />);
    await screen.findByRole('button', { name: '取消收藏' });
    await userEvent.setup().click(screen.getByRole('button', { name: '取消收藏' }));
    await screen.findByRole('alert');
    expect(commands).toHaveLength(1);
    firstClient.clear();
    cleanup();

    mount(<MyQuotes userId="QA_TEST_user" />);
    await screen.findByRole('heading', { name: '待确认的操作' });
    await userEvent.setup().click(screen.getByRole('button', { name: '重试保存' }));
    await waitFor(() => expect(commands).toHaveLength(2));
    await waitFor(() => expect(screen.getByText('这里还没有收藏的句子。')).toBeInTheDocument());
    expect(commands[1]).toEqual(commands[0]);
  });

  it('clears uncertain preference commands on deliberate logout', async () => {
    const fetcher = vi.fn(async (url: string, _init: RequestInit = {}) => {
      if (url.endsWith('/quotes/favorites')) return envelope({ items: [{ ...preference }], disliked: [], next_cursor: null });
      if (url.includes('/preference')) throw new TypeError('offline');
      throw new Error(`Unexpected URL: ${url}`);
    });
    vi.stubGlobal('fetch', fetcher);
    mount(<MyQuotes userId="QA_TEST_user" />);
    await screen.findByRole('button', { name: '取消收藏' });
    await userEvent.setup().click(screen.getByRole('button', { name: '取消收藏' }));
    await screen.findByRole('alert');
    clearQuotePendingOperations();
    cleanup();
    mount(<MyQuotes userId="QA_TEST_user" />);
    await screen.findByRole('button', { name: '取消收藏' });
    expect(screen.queryByRole('heading', { name: '待确认的操作' })).not.toBeInTheDocument();
  });
});
