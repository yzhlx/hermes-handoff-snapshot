import { homeFixture } from './test-home-fixture';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClientProvider } from '@tanstack/react-query';
import { App } from './App';
import { createQueryClient } from './query-client';
import { setCsrfToken, setUnauthorizedHandler } from '../shared/api/client';
import { clearLearningDraft, learningDraftFor } from '../features/learning/draft-store';
import { clearReviewDrafts } from '../features/review';

afterEach(() => {
  cleanup(); vi.unstubAllGlobals(); clearLearningDraft(); clearReviewDrafts();
  setCsrfToken(undefined); setUnauthorizedHandler(undefined);
});

it.each([false, true])('enters learning without a write and preserves an uncertain start command: %s', async (uncertain) => {
  const writes: string[] = [];
  const candidate = {
    id: 'QA_TEST_suggestion', version: 1, kind: 'review', status: 'available',
    subject_id: 'math', knowledge_point_id: 'QA_TEST_point', problem_id: null,
    reason: 'QA_TEST 从边界条件开始', source_refs: [], source_revision: 'QA_TEST_revision',
    rule_version: 'suggestions-1', generated_at: '2026-10-01T09:00:00Z',
    expires_at: null, snoozed_until: null,
  };
  const envelope = (data: unknown) => Response.json({ data, meta: { request_id: 'QA_TEST' } });
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit = {}) => {
    if (init.method === 'POST') { writes.push(path); throw new Error('Unexpected automatic write'); }
    if (path.endsWith('/home')) return Response.json({ data: homeFixture(), meta: { request_id: 'QA_TEST_home' } });
    if (path.endsWith('/auth/session')) return envelope({ user: { id: 'QA_TEST_owner', username: 'QA_TEST_owner', timezone: 'Asia/Shanghai' }, csrf_token: 'QA_TEST_csrf' });
    if (path.endsWith('/health/ready')) return envelope({ status: 'ok' });
    if (path.endsWith('/current')) return envelope(null);
    if (path.endsWith('/subjects')) return envelope({ items: [{ id: 'math', name: '数学' }] });
    if (path.endsWith('/suggestions/QA_TEST_suggestion')) return envelope(candidate);
    if (path.includes('/suggestions?')) return envelope({ items: [candidate], next_cursor: null, rule_version: 'suggestions-1' });
    if (path.endsWith('/quotes/today')) return envelope({ daily_quote: { local_date: '2026-10-01', day_timezone: 'Asia/Shanghai', quote: null, reason: 'no_eligible_quotes', preference: null } });
    throw new Error(`Unexpected request: ${path}`);
  }));
  const draft = learningDraftFor('QA_TEST_owner');
  draft.goal = 'QA_TEST 尚未确认的原目标';
  if (uncertain) draft.startOperation = { id: 'QA_TEST_frozen', payload: 'QA_TEST_original_payload' };
  const frozen = draft.startOperation;
  render(<QueryClientProvider client={createQueryClient()}><App /></QueryClientProvider>);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: '可考虑复习' }));
  await user.click(await screen.findByRole('button', { name: '进入学习' }));
  await waitFor(() => expect(screen.getByLabelText('这次想学什么？')).toHaveValue(uncertain ? 'QA_TEST 尚未确认的原目标' : candidate.reason));
  expect(learningDraftFor('QA_TEST_owner').startOperation).toBe(frozen);
  expect(writes).toEqual([]);
  if (!uncertain) {
    expect(screen.getByLabelText('学科')).toHaveValue('math');
    expect(learningDraftFor('QA_TEST_owner').knowledgePointId).toBe('QA_TEST_point');
  }
});
