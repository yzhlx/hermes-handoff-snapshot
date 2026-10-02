import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ContinuationContext } from './ContinuationContext';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><ContinuationContext userId="QA_TEST_owner" previousSessionId="QA_TEST_previous" resumeNote="QA_TEST 第三题" /></QueryClientProvider>);
}
it('restores topic and stuck question from a persisted link after an empty-cache mount', async () => {
  const fetcher = vi.fn(async (path: string) => Response.json({ data: path.includes('/session-reflections/') ? { stuck_note: 'QA_TEST 为什么是一排δ？' } : { goal: 'QA_TEST 采样' } }));
  vi.stubGlobal('fetch', fetcher);
  mount();
  expect(await screen.findByText('原主题：QA_TEST 采样')).toBeInTheDocument();
  expect(await screen.findByText('上次留下的问题：QA_TEST 为什么是一排δ？')).toBeInTheDocument();
  expect(screen.getByText('继续位置：QA_TEST 第三题')).toBeInTheDocument();
  expect(fetcher.mock.calls.map(([path]) => path).sort()).toEqual(['/api/v1/learning-sessions/QA_TEST_previous', '/api/v1/session-reflections/QA_TEST_previous']);
});
it('allows a previous session without reflection and does not fabricate a stuck question', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => path.includes('/session-reflections/') ? Response.json({ error: { code: 'RESOURCE_NOT_FOUND' } }, { status: 404 }) : Response.json({ data: { goal: 'QA_TEST 只有继续说明' } })));
  mount();
  await screen.findByText('原主题：QA_TEST 只有继续说明');
  expect(screen.queryByText(/上次留下的问题：/)).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '重读上次现场' })).not.toBeInTheDocument();
});
it('keeps the saved position visible when source reads fail and offers recovery', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({ error: { code: 'unavailable' } }, { status: 503 })));
  mount();
  expect(await screen.findByRole('button', { name: '重读上次现场' })).toBeInTheDocument();
  expect(screen.getByText('继续位置：QA_TEST 第三题')).toBeInTheDocument();
  expect(screen.getByText('上次现场暂未完整读取，当前学习仍可继续。')).toBeInTheDocument();
});
