import { homeFixture } from './test-home-fixture';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClientProvider } from '@tanstack/react-query';
import { App } from './App';
import { createQueryClient } from './query-client';
import { setCsrfToken, setUnauthorizedHandler } from '../shared/api/client';
import { clearLearningDraft, learningDraftFor } from '../features/learning/draft-store';
import { clearFeedbackDrafts } from '../features/feedback';
import { attachmentDraftFor, clearAttachmentDrafts } from '../features/attachments';
import { clearQuotePendingOperations } from '../features/quotes/Quotes';

afterEach(() => {
  cleanup(); vi.unstubAllGlobals(); setCsrfToken(undefined); setUnauthorizedHandler(undefined);
  clearLearningDraft(); clearFeedbackDrafts(); clearQuotePendingOperations(); clearAttachmentDrafts();
});

const auth = (id: string) => ({ data: { user: { id, username: id, timezone: 'Asia/Shanghai' }, csrf_token: 'QA_TEST_csrf' }, meta: { request_id: 'QA_TEST_auth' } });

it.each([true, false])('retains uncertain learning input only for the same signed-in owner: %s', async (sameUser) => {
  const commands: RequestInit[] = [];
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit = {}) => {
    if (path.endsWith('/home')) return Response.json({ data: homeFixture(), meta: { request_id: 'QA_TEST_home' } });
    if (path.endsWith('/auth/session')) return Response.json(auth('QA_TEST_owner'));
    if (path.endsWith('/auth/login')) return Response.json(auth(sameUser ? 'QA_TEST_owner' : 'QA_TEST_other'));
    if (path.endsWith('/subjects')) return Response.json({ data: { items: [{ id: 'math', name: '数学' }] }, meta: { request_id: 'QA_TEST' } });
    if (path.endsWith('/current')) return Response.json({ data: null, meta: { request_id: 'QA_TEST' } });
    if (path.includes('/learning-sessions?limit=')) return Response.json({ data: { items: [], next_cursor: null }, meta: { request_id: 'QA_TEST' } });
    if (path.endsWith('/quotes/today')) return Response.json({ data: { daily_quote: { local_date: '2026-09-30', day_timezone: 'Asia/Shanghai', quote: null, reason: 'no_eligible_quotes', preference: null } }, meta: { request_id: 'QA_TEST' } });
    if (path.endsWith('/learning-sessions')) {
      commands.push(init);
      if (commands.length === 1) return new Response('{"error":{"code":"unauthorized"}}', { status: 401 });
      return Response.json({ data: { id: 'QA_TEST_session', goal: '保留未确认目标', subject_id: 'math', status: 'active', version: 1, started_at: '2026-09-30T01:00:00Z', ended_at: null, day_timezone: 'Asia/Shanghai', learning_date: '2026-09-30', timing_enabled: false, time_segments: [], effective_duration_seconds: 0, kind: 'free' }, meta: { request_id: 'QA_TEST' } }, { status: 201 });
    }
    throw new Error(`Unexpected request: ${path}`);
  }));
  render(<QueryClientProvider client={createQueryClient()}><App /></QueryClientProvider>);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: '开始一段学习 →' }));
  await user.type(await screen.findByLabelText('这次想学什么？'), '保留未确认目标');
  await user.selectOptions(screen.getByLabelText('学科'), 'math');
  const file = new File(['QA_TEST_private_bytes'], 'QA_TEST_pending.png', { type: 'image/png' });
  const controller = new AbortController();
  attachmentDraftFor('QA_TEST_owner', 'QA_TEST_auth_context').items.push({
    clientId: 'QA_TEST_client', file, declaredMime: 'image/png',
    uploadOperationId: 'QA_TEST_init', putOperationId: 'QA_TEST_put', completeOperationId: 'QA_TEST_complete',
    attachment: null, status: 'selected', progress: 0, error: null, role: 'question', page: 1, abortController: controller,
  });
  await user.click(screen.getByRole('button', { name: '开始这一段学习 →' }));
  await user.type(await screen.findByLabelText('用户名'), sameUser ? 'QA_TEST_owner' : 'QA_TEST_other');
  await user.type(screen.getByLabelText('密码'), 'test-password');
  await user.click(screen.getByRole('button', { name: '进入书房 →' }));
  const goal = await screen.findByLabelText('这次想学什么？');
  if (sameUser) {
    expect(attachmentDraftFor('QA_TEST_owner', 'QA_TEST_auth_context').items[0]?.file).toBe(file);
    expect(controller.signal.aborted).toBe(false);
    expect(goal).toHaveValue('保留未确认目标');
    expect(screen.getByLabelText('学科')).toHaveValue('math');
    await user.click(screen.getByRole('button', { name: '开始这一段学习 →' }));
    await screen.findByRole('button', { name: '暂停学习' });
    expect(commands).toHaveLength(2);
    expect(commands[0].body).toBe(commands[1].body);
    expect(new Headers(commands[0].headers).get('Idempotency-Key')).toBe(new Headers(commands[1].headers).get('Idempotency-Key'));
  } else {
    expect(attachmentDraftFor('QA_TEST_other', 'QA_TEST_auth_context').items).toHaveLength(0);
    expect(controller.signal.aborted).toBe(true);
    expect(goal).toHaveValue('');
    expect(screen.getByLabelText('学科')).toHaveValue('');
    expect(learningDraftFor('QA_TEST_other').startOperation).toBeNull();
  }
});

it('keeps selected learning method as session metadata while restoring the start form', async () => {
  let createPayload: Record<string, unknown> | undefined;
  const method = {
    id: 'active-recall', title: '主动回忆', summary: '合上材料后回忆。', problem: '检查能否离开原文复述。',
    situations: ['刚听完课'], steps: ['合上资料', '回忆要点'], pitfalls: ['把重读当回忆'], content_version: 1,
  };
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit = {}) => {
    if (path.endsWith('/home')) return Response.json({ data: homeFixture(), meta: { request_id: 'QA_TEST_home' } });
    if (path.endsWith('/auth/session')) return Response.json(auth('QA_TEST_user'));
    if (path.endsWith('/health/ready')) return Response.json({ data: { status: 'ok' }, meta: { request_id: 'QA_TEST' } });
    if (path.endsWith('/subjects')) return Response.json({ data: { items: [] }, meta: { request_id: 'QA_TEST' } });
    if (path.endsWith('/current')) return Response.json({ data: null, meta: { request_id: 'QA_TEST' } });
    if (path.endsWith('/learning-methods')) return Response.json({ data: { items: [method] }, meta: { request_id: 'QA_TEST' } });
    if (path.endsWith('/learning-situations')) return Response.json({ data: { items: [] }, meta: { request_id: 'QA_TEST' } });
    if (path.endsWith('/quotes/today')) return Response.json({ data: { daily_quote: { local_date: '2026-09-30', day_timezone: 'Asia/Shanghai', quote: null, reason: 'no_eligible_quotes', preference: null } }, meta: { request_id: 'QA_TEST' } });
    if (path.endsWith('/learning-sessions')) {
      createPayload = JSON.parse(String(init.body)) as Record<string, unknown>;
      return Response.json({ data: { id: 'QA_TEST_session', goal: '复习傅里叶变换', subject_id: null, method_id: 'active-recall', status: 'active', version: 1, started_at: '2026-09-30T01:00:00Z', ended_at: null, day_timezone: 'Asia/Shanghai', learning_date: '2026-09-30', timing_enabled: false, time_segments: [], effective_duration_seconds: 0, kind: 'free' }, meta: { request_id: 'QA_TEST' } }, { status: 201 });
    }
    throw new Error(`Unexpected request: ${path}`);
  }));
  render(<QueryClientProvider client={createQueryClient()}><App /></QueryClientProvider>);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: '学习方法' }));
  await user.click(await screen.findByRole('button', { name: '查看方法与步骤' }));
  await user.click(screen.getByRole('button', { name: '用「主动回忆」开始' }));
  expect(await screen.findByText('学习方法：主动回忆')).toBeInTheDocument();
  await user.type(screen.getByLabelText('这次想学什么？'), '复习傅里叶变换');
  await user.click(screen.getByRole('button', { name: '开始这一段学习 →' }));
  expect(createPayload).toMatchObject({ goal: '复习傅里叶变换', method_id: 'active-recall' });
});
