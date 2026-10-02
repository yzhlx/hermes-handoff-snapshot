import { afterEach, expect, it, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClientProvider } from '@tanstack/react-query';
import { App } from './App';
import { homeFixture } from './test-home-fixture';
import { createQueryClient } from './query-client';
import { setCsrfToken, setUnauthorizedHandler } from '../shared/api/client';
import { clearLearningDraft, learningDraftFor } from '../features/learning/draft-store';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); setCsrfToken(undefined); setUnauthorizedHandler(undefined); clearLearningDraft(); });
it('signs in, mounts the learning scene, and clears private cached data on logout', async () => {
  const calls: { path: string; init: RequestInit }[] = [];
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
    calls.push({ path, init });
    if (path.endsWith('/auth/session')) return new Response('{"error":{"code":"unauthorized"}}', { status: 401 });
    if (path.endsWith('/auth/login')) return Response.json({ data: { user: { id: 'QA_TEST_user', username: 'QA_TEST_user', timezone: 'Asia/Shanghai' }, csrf_token: 'test-csrf' }, meta: { request_id: 'test' } });
    if (path.endsWith('/auth/logout')) return new Response(null, { status: 204 });
    if (path.endsWith('/home')) return Response.json({ data: homeFixture(), meta: { request_id: 'test' } });
    if (path.endsWith('/subjects')) return Response.json({ data: { items: [] }, meta: { request_id: 'test' } });
    if (path.endsWith('/current')) return Response.json({ data: null, meta: { request_id: 'test' } });
    if (path.includes('/learning-sessions?limit=')) return Response.json({ data: { items: [], next_cursor: null }, meta: { request_id: 'test' } });
    return Response.json({ data: { status: 'ok' }, meta: { request_id: 'test' } });
  }));
  const client = createQueryClient();
  render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText('用户名'), 'QA_TEST_user');
  await user.type(screen.getByLabelText('密码'), 'test-password');
  await user.click(screen.getByRole('button', { name: '进入书房 →' }));
  await user.click(await screen.findByRole('button', { name: '开始一段学习 →' }));
  await screen.findByLabelText('这次想学什么？');
  await user.type(screen.getByLabelText('这次想学什么？'), 'draft before explicit logout');
  expect(client.getQueryData(['subjects'])).toBeDefined();
  await user.click(screen.getByRole('button', { name: '退出' }));
  await screen.findByLabelText('用户名');
  expect(client.getQueryData(['subjects'])).toBeUndefined();
  expect(client.getQueryData(['learning', 'current'])).toBeUndefined();
  expect(learningDraftFor('QA_TEST_user').goal).toBe('');
  const logout = calls.find((call) => call.path.endsWith('/auth/logout'));
  expect(new Headers(logout?.init.headers).get('X-CSRF-Token')).toBe('test-csrf');
});

it.each([true, false])('retains the draft and uncertain operation only when the same user signs back in: %s', async (sameUser) => {
  const auth = (id: string) => ({ data: { user: { id, username: id, timezone: 'Asia/Shanghai' }, csrf_token: 'test-csrf' }, meta: { request_id: 'test' } });
  const commands: RequestInit[] = [];
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
    if (path.endsWith('/auth/session')) return Response.json(auth('QA_TEST_owner'));
    if (path.endsWith('/auth/login')) return Response.json(auth(sameUser ? 'QA_TEST_owner' : 'QA_TEST_other'));
    if (path.endsWith('/home')) return Response.json({ data: homeFixture(), meta: { request_id: 'test' } });
    if (path.endsWith('/subjects')) return Response.json({ data: { items: [{ id: 'math', name: '数学' }] }, meta: { request_id: 'test' } });
    if (path.endsWith('/current')) return Response.json({ data: null, meta: { request_id: 'test' } });
    if (path.includes('/learning-sessions?limit=')) return Response.json({ data: { items: [], next_cursor: null }, meta: { request_id: 'test' } });
    if (path.endsWith('/learning-sessions')) {
      commands.push(init);
      if (commands.length === 1) return new Response('{"error":{"code":"unauthorized"}}', { status: 401 });
      return Response.json({ data: { id: 'QA_TEST_session', goal: '保留未确认目标', subject_id: 'math', status: 'active', version: 1, started_at: '2026-09-30T01:00:00Z', ended_at: null, day_timezone: 'Asia/Shanghai', learning_date: '2026-09-30' }, meta: { request_id: 'test' } }, { status: 201 });
    }
    return Response.json({ data: { status: 'ok' }, meta: { request_id: 'test' } });
  }));
  const client = createQueryClient();
  render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: '开始一段学习 →' }));
  await user.type(await screen.findByLabelText('这次想学什么？'), '保留未确认目标');
  await user.selectOptions(screen.getByLabelText('学科'), 'math');
  await user.click(screen.getByRole('button', { name: '开始这一段学习 →' }));
  await user.type(await screen.findByLabelText('用户名'), sameUser ? 'QA_TEST_owner' : 'QA_TEST_other');
  await user.type(screen.getByLabelText('密码'), 'test-password');
  await user.click(screen.getByRole('button', { name: '进入书房 →' }));
  const goal = await screen.findByLabelText('这次想学什么？');
  if (sameUser) {
    expect(goal).toHaveValue('保留未确认目标');
    expect(screen.getByLabelText('学科')).toHaveValue('math');
    await user.click(screen.getByRole('button', { name: '开始这一段学习 →' }));
    await screen.findByRole('button', { name: '暂停学习' });
    expect(commands).toHaveLength(2);
    expect(commands[0].body).toBe(commands[1].body);
    expect(new Headers(commands[0].headers).get('Idempotency-Key')).toBe(new Headers(commands[1].headers).get('Idempotency-Key'));
  } else {
    expect(goal).toHaveValue('');
    expect(screen.getByLabelText('学科')).toHaveValue('');
    expect(learningDraftFor('QA_TEST_other').startOperation).toBeNull();
  }
});

it('keeps a selected method separate from the user goal and sends its id when starting', async () => {
  let createPayload: Record<string, unknown> | undefined;
  const method = {
    id: 'active-recall',
    title: '主动回忆',
    summary: '合上材料后回忆。',
    problem: '检查能否离开原文复述。',
    situations: ['刚听完课'],
    steps: ['合上资料', '回忆要点'],
    pitfalls: ['把重读当回忆'],
    content_version: 1,
  };
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit = {}) => {
    if (path.endsWith('/auth/session')) return Response.json({ data: { user: { id: 'QA_TEST_user', username: 'QA_TEST_user', timezone: 'Asia/Shanghai' }, csrf_token: 'csrf' }, meta: { request_id: 'test' } });
    if (path.endsWith('/health/ready')) return Response.json({ data: { status: 'ok' }, meta: { request_id: 'test' } });
    if (path.endsWith('/home')) return Response.json({ data: homeFixture(), meta: { request_id: 'test' } });
    if (path.endsWith('/subjects')) return Response.json({ data: { items: [] }, meta: { request_id: 'test' } });
    if (path.endsWith('/current')) return Response.json({ data: null, meta: { request_id: 'test' } });
    if (path.endsWith('/learning-methods')) return Response.json({ data: { items: [method] }, meta: { request_id: 'test' } });
    if (path.endsWith('/learning-situations')) return Response.json({ data: { items: [] }, meta: { request_id: 'test' } });
    if (path.endsWith('/learning-sessions')) {
      createPayload = JSON.parse(String(init.body)) as Record<string, unknown>;
      return Response.json({ data: { id: 'QA_TEST_session', goal: '复习傅里叶变换', subject_id: null, method_id: 'active-recall', status: 'active', version: 1, started_at: '2026-09-30T01:00:00Z', ended_at: null, day_timezone: 'Asia/Shanghai', learning_date: '2026-09-30', timing_enabled: false, time_segments: [], effective_duration_seconds: 0 }, meta: { request_id: 'test' } }, { status: 201 });
    }
    return Response.json({ data: { status: 'ok' }, meta: { request_id: 'test' } });
  }));
  const client = createQueryClient();
  render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: '学习方法' }));
  await user.click(await screen.findByRole('button', { name: '查看方法与步骤' }));
  await user.click(screen.getByRole('button', { name: '用「主动回忆」开始' }));
  expect(await screen.findByText('学习方法：主动回忆')).toBeInTheDocument();
  await user.type(screen.getByLabelText('这次想学什么？'), '复习傅里叶变换');
  await user.click(screen.getByRole('button', { name: '开始这一段学习 →' }));
  await screen.findByText('学习方法：主动回忆');
  expect(createPayload).toMatchObject({ goal: '复习傅里叶变换', method_id: 'active-recall' });
});
