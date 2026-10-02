import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { AccountDataPage } from './AccountDataPage';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const envelope = (data: unknown, status = 200) =>
  new Response(JSON.stringify({ data, meta: { request_id: 'qa' } }), { status });
const failure = (status: number, code: string) =>
  new Response(JSON.stringify({ error: { code, message: 'QA test failure' }, meta: { request_id: 'qa' } }), { status });
const pathOf = (input: RequestInfo | URL) => new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');

const account = (extras: Record<string, unknown> = {}) => ({
  status: 'active', username: 'QA_TEST_owner', timezone: 'Asia/Shanghai', record_count: 12, deletion: null, ...extras,
});
const deletion = (extras: Record<string, unknown> = {}) => ({
  id: 'QA_TEST_deletion', version: 1, status: 'pending', confirmation: 'DELETE MY ACCOUNT',
  impact: { total_records: 12 }, purge_after: '2026-10-03T00:00:00+00:00',
  cancelled_at: null, completed_at: null, created_at: '2026-10-02T00:00:00+00:00', ...extras,
});

function setup(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal('fetch', fetchMock);
  const onDataRemoved = vi.fn();
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false } });
  render(<QueryClientProvider client={client}><AccountDataPage onDataRemoved={onDataRemoved} /></QueryClientProvider>);
  return { onDataRemoved };
}

describe('account data sovereignty', () => {
  it('shows the account state and an honest empty export list', async () => {
    setup(vi.fn(async (input: RequestInfo | URL) => {
      const path = pathOf(input);
      if (path === '/account') return envelope(account());
      if (path === '/account/exports') return envelope({ items: [], next_cursor: null });
      throw new Error(`Unexpected ${path}`);
    }));
    expect(await screen.findByText(/QA_TEST_owner/)).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('正常使用')).toBeInTheDocument();
    expect(await screen.findByText('还没有导出包。')).toBeInTheDocument();
  });

  it('creates an export with an operation_id equal to the Idempotency-Key', async () => {
    const posts: Array<{ headers: Headers; body: string }> = [];
    setup(vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
      const path = pathOf(input);
      if (path === '/account') return envelope(account());
      if (path === '/account/exports' && init.method === 'POST') {
        posts.push({ headers: new Headers(init.headers), body: String(init.body) });
        return envelope({ id: 'QA_TEST_export', status: 'ready', byte_size: 2048, sha256: 'abc', record_counts: {}, expires_at: null, created_at: '2026-10-02T00:00:00+00:00' }, 201);
      }
      if (path === '/account/exports') return envelope({ items: [{ id: 'QA_TEST_export', status: 'ready', byte_size: 2048, sha256: 'abc', record_counts: {}, expires_at: null, created_at: '2026-10-02T00:00:00+00:00' }], next_cursor: null });
      throw new Error(`Unexpected ${path}`);
    }));
    fireEvent.click(await screen.findByRole('button', { name: '生成导出包' }));
    await waitFor(() => expect(posts).toHaveLength(1));
    const body = JSON.parse(posts[0].body);
    expect(body.operation_id).toBe(posts[0].headers.get('Idempotency-Key'));
    expect(await screen.findByRole('button', { name: '下载' })).toBeInTheDocument();
  });

  it('reports what deletion removes and requires the exact confirmation phrase', async () => {
    const posts: Array<{ body: string }> = [];
    setup(vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
      const path = pathOf(input);
      if (path === '/account/exports') return envelope({ items: [], next_cursor: null });
      if (path === '/account/deletion' && init.method === 'POST') {
        posts.push({ body: String(init.body) });
        return failure(422, 'VALIDATION_ERROR');
      }
      if (path === '/account') return envelope(account());
      throw new Error(`Unexpected ${path}`);
    }));
    fireEvent.change(await screen.findByLabelText('确认文字'), { target: { value: 'delete' } });
    fireEvent.click(screen.getByRole('button', { name: '登记删除请求' }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(JSON.parse(posts[0].body).confirmation).toBe('delete');
    expect(await screen.findByText(/请逐字输入 DELETE MY ACCOUNT 以确认/)).toBeInTheDocument();
  });

  it('shows a pending request with its impact, the write pause and a second confirmation', async () => {
    setup(vi.fn(async (input: RequestInfo | URL) => {
      const path = pathOf(input);
      if (path === '/account') return envelope(account({ status: 'deletion_pending', deletion: deletion() }));
      if (path === '/account/exports') return envelope({ items: [], next_cursor: null });
      throw new Error(`Unexpected ${path}`);
    }));
    expect(await screen.findByText(/删除请求已登记/)).toBeInTheDocument();
    expect(screen.getByText(/12 条记录、私有附件与导出包/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '撤销删除请求' })).toBeInTheDocument();
    // The final step stays behind an explicit disclosure.
    const summary = screen.getByText('我确认要永久删除');
    const details = summary.closest('details');
    expect(details).not.toBeNull();
    expect((details as HTMLDetailsElement).open).toBe(false);
    fireEvent.click(summary);
    expect(screen.getByRole('button', { name: '永久删除我的内容' })).toBeInTheDocument();
  });

  it('cancels a pending request with If-Match and a matching key', async () => {
    const calls: Array<{ headers: Headers; body: string }> = [];
    setup(vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
      const path = pathOf(input);
      if (path === '/account/deletion/cancel' && init.method === 'POST') {
        calls.push({ headers: new Headers(init.headers), body: String(init.body) });
        return envelope(deletion({ status: 'cancelled' }));
      }
      if (path === '/account') return envelope(account({ status: 'deletion_pending', deletion: deletion() }));
      if (path === '/account/exports') return envelope({ items: [], next_cursor: null });
      throw new Error(`Unexpected ${path}`);
    }));
    fireEvent.click(await screen.findByRole('button', { name: '撤销删除请求' }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].headers.get('If-Match')).toBe('1');
    expect(JSON.parse(calls[0].body).operation_id).toBe(calls[0].headers.get('Idempotency-Key'));
    expect(await screen.findByText(/删除请求已撤销/)).toBeInTheDocument();
  });
});
