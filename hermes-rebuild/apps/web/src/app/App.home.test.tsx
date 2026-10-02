import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClientProvider } from '@tanstack/react-query';
import { App } from './App';
import { createQueryClient } from './query-client';
import { homeFixture } from './test-home-fixture';
import { clearLearningDraft, learningDraftFor } from '../features/learning/draft-store';
import { setCsrfToken, setUnauthorizedHandler } from '../shared/api/client';
import type { RecordData } from '../shared/api/types';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); clearLearningDraft(); setCsrfToken(undefined); setUnauthorizedHandler(undefined); });

it.each([false, true])('continues an ended session only after confirmation and preserves a frozen start: %s', async (uncertain) => {
  const original = learningDraftFor('QA_TEST_owner');
  original.goal = 'QA_TEST 尚未确认的目标';
  if (uncertain) original.startOperation = { id: 'QA_TEST_frozen', payload: 'QA_TEST_original_payload' };
  const frozen = original.startOperation;
  const last: RecordData = {
    id: 'QA_TEST_previous', version: 3, goal: 'QA_TEST 昨天的学习', subject_id: 'math', subject_name: '数学',
    status: 'ended', learning_date: '2026-09-30', day_timezone: 'Asia/Shanghai',
    started_at: '2026-09-30T08:00:00Z', ended_at: '2026-09-30T09:00:00Z', resume_note: 'QA_TEST 从第三题继续',
    summary: 'QA_TEST 检查边界', recalled_text: null, missing_parts: null, stuck_note: null,
    attempt_count: 0, pending_count: 0, checked_count: 0, independent_correct_count: 0, effective: true, source_refs: [],
  };
  const base = homeFixture();
  const home = { ...base, sections: { ...base.sections, continue_learning: { ...base.sections.continue_learning, status: 'ready', data: { current: null, last } } } };
  const writes: Array<Record<string, unknown>> = [];
  const envelope = (data: unknown) => Response.json({ data, meta: { request_id: 'QA_TEST' } });
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit = {}) => {
    if (path.endsWith('/auth/session')) return envelope({ user: { id: 'QA_TEST_owner', username: 'QA_TEST_owner', timezone: 'Asia/Shanghai' }, csrf_token: 'QA_TEST_csrf' });
    if (path.endsWith('/health/ready')) return envelope({ status: 'ok' });
    if (path.endsWith('/home')) return envelope(home);
    if (path.endsWith('/learning-sessions/QA_TEST_previous')) return envelope(last);
    if (path.endsWith('/session-reflections/QA_TEST_previous')) return envelope({ stuck_note: 'QA_TEST 为什么采样后出现一排δ？' });
    if (path.endsWith('/current')) return envelope(null);
    if (path.endsWith('/subjects')) return envelope({ items: [{ id: 'math', name: '数学' }] });
    if (path.endsWith('/quotes/today')) return envelope(base.sections.quote?.data);
    if (path.endsWith('/learning-sessions') && init.method === 'POST') {
      const body = JSON.parse(String(init.body)) as Record<string, unknown>; writes.push(body);
      return envelope({ ...last, id: 'QA_TEST_new', status: 'active', ended_at: null, version: 1, timing_enabled: false, effective_duration_seconds: 0, time_segments: [], kind: 'free', ...body });
    }
    throw new Error(`Unexpected request: ${path}`);
  }));
  render(<QueryClientProvider client={createQueryClient()}><App /></QueryClientProvider>);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: /继续上次/ }));
  if (!uncertain) {
    expect(await screen.findByText('原主题：QA_TEST 昨天的学习')).toBeInTheDocument();
    expect(await screen.findByText('上次留下的问题：QA_TEST 为什么采样后出现一排δ？')).toBeInTheDocument();
  }
  const goal = await screen.findByLabelText('这次想学什么？');
  await waitFor(() => expect(goal).toHaveValue(uncertain ? original.goal : last.goal));
  expect(writes).toHaveLength(0);
  if (uncertain) {
    expect(learningDraftFor('QA_TEST_owner').startOperation).toBe(frozen);
    expect(learningDraftFor('QA_TEST_owner').previousSessionId).toBeNull();
  } else {
    expect(screen.getByLabelText('学科')).toHaveValue('math');
    await user.click(screen.getByRole('button', { name: '开始这一段学习 →' }));
    await screen.findByRole('button', { name: '暂停学习' });
    expect(writes).toHaveLength(1);
    expect(writes[0]).toMatchObject({ previous_session_id: last.id, resume_note: last.resume_note, goal: last.goal, subject_id: 'math' });
    expect(learningDraftFor('QA_TEST_owner').previousSessionId).toBeNull();
    expect(learningDraftFor('QA_TEST_owner').resumeNote).toBeNull();
  }
});
