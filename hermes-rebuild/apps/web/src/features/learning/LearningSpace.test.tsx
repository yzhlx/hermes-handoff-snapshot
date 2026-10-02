import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { LearningSpace } from './LearningSpace';
import { SessionHistory } from './SessionHistory';
import { clearLearningDraft, learningDraftFor } from './draft-store';
import { clearFeedbackDrafts } from '../feedback';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); clearLearningDraft(); clearFeedbackDrafts(); });
const envelope = (data: unknown, status = 200) => new Response(JSON.stringify({ data, meta: { request_id: 'test-request' } }), { status });
const session = { id: 'test-session', subject_id: null, goal: 'QA_TEST_复习函数', status: 'active', version: 1, started_at: '2026-09-30T01:00:00Z', ended_at: null, day_timezone: 'Asia/Shanghai', learning_date: '2026-09-30' };
function mount() { const client = createQueryClient(); client.setDefaultOptions({ queries: { retry: false }, mutations: { retry: false } }); render(<QueryClientProvider client={client}><LearningSpace userId="QA_TEST_user" /></QueryClientProvider>); return client; }
describe('learning scene', () => {
  it('keeps the ended knowledge session subject on the created problem despite editing the next-session form', async () => {
    const subjectId = 'QA_TEST_signal_subject';
    const pointId = 'QA_TEST_signal_point';
    const subjectAfterEnd = 'QA_TEST_other_subject';
    const draft = learningDraftFor('QA_TEST_user');
    draft.subject = subjectId; draft.knowledgePointId = pointId; draft.knowledgePointName = '卷积定理'; draft.goal = '复习卷积定理';
    let startBody: Record<string, unknown> | undefined;
    let problemBody: Record<string, unknown> | undefined;
    const active = { ...session, id: 'QA_TEST_linked_session', subject_id: subjectId, knowledge_point_id: pointId, goal: '复习卷积定理', status: 'active', version: 1 };
    const fetchMock = vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/subjects')) return envelope({ items: [{ id: subjectId, name: '信号与系统' }, { id: subjectAfterEnd, name: '其他学科' }] });
      if (url.endsWith('/current')) return envelope(null);
      if (url.includes(`/knowledge-points/${pointId}`)) return envelope({ id: pointId, subject_id: subjectId, chapter_id: 'QA_TEST_chapter', name: '卷积定理', notes: null, archived: false, version: 1 });
      if (url.includes('/learning-sessions?limit=')) return envelope({ items: [], next_cursor: null });
      if (url.endsWith('/learning-sessions')) { startBody = JSON.parse(String(init.body)) as Record<string, unknown>; return envelope(active, 201); }
      if (url.endsWith(`/learning-sessions/${active.id}/end`)) return envelope({ ...active, status: 'ended', version: 2, ended_at: '2026-09-30T01:05:00Z' });
      if (url.endsWith(`/session-reflections/${active.id}`)) return new Response('{}', { status: 404 });
      if (url.includes('/problems?')) return envelope({ items: [], next_cursor: null });
      if (url.endsWith('/problems')) { problemBody = JSON.parse(String(init.body)) as Record<string, unknown>; return envelope({ id: 'QA_TEST_created_problem', subject_id: problemBody.subject_id, title: problemBody.title, statement: problemBody.statement, correct_answer: null, source_note: null, archived: false, is_representative: false, knowledge_point_ids: [], attempts: [], version: 1 }, 201); }
      if (url.endsWith('/problems/QA_TEST_created_problem')) return envelope({ id: 'QA_TEST_created_problem', subject_id: subjectId, title: 'QA_TEST 题目', statement: 'QA_TEST 题干', correct_answer: null, source_note: null, archived: false, is_representative: false, knowledge_point_ids: [], attempts: [], version: 1 });
      throw new Error(`Unexpected URL ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    mount();
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: '开始这一段学习 →' }));
    await user.click(await screen.findByRole('button', { name: '结束并保存这一段' }));
    await screen.findByLabelText('题干文字（可选）');
    await user.selectOptions(screen.getByLabelText('学科'), subjectAfterEnd);
    await user.type(screen.getByLabelText('题目简名（可选）'), 'QA_TEST 题目');
    await user.type(screen.getByLabelText('题干文字（可选）'), 'QA_TEST 题干');
    await user.click(screen.getByRole('button', { name: '保存题目' }));
    await screen.findByRole('heading', { name: '记录这次作答' });
    expect(startBody).toMatchObject({ subject_id: subjectId, knowledge_point_id: pointId });
    expect(problemBody?.subject_id).toBe(subjectId);
  });

  it('keeps a free-learning problem unassigned even if the next-session form selects a subject', async () => {
    const nextSubjectId = 'QA_TEST_subject_after_free_session';
    const draft = learningDraftFor('QA_TEST_user');
    draft.goal = 'QA_TEST 自由学习';
    let problemBody: Record<string, unknown> | undefined;
    const freeSession = { ...session, id: 'QA_TEST_free_session', subject_id: null, knowledge_point_id: null, goal: 'QA_TEST 自由学习', status: 'active', version: 1 };
    const fetchMock = vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/subjects')) return envelope({ items: [{ id: nextSubjectId, name: '之后选的学科' }] });
      if (url.endsWith('/current')) return envelope(null);
      if (url.includes('/learning-sessions?limit=')) return envelope({ items: [], next_cursor: null });
      if (url.endsWith('/learning-sessions')) return envelope(freeSession, 201);
      if (url.endsWith(`/learning-sessions/${freeSession.id}/end`)) return envelope({ ...freeSession, status: 'ended', version: 2, ended_at: '2026-09-30T01:05:00Z' });
      if (url.endsWith(`/session-reflections/${freeSession.id}`)) return new Response('{}', { status: 404 });
      if (url.includes('/problems?')) return envelope({ items: [], next_cursor: null });
      if (url.endsWith('/problems')) { problemBody = JSON.parse(String(init.body)) as Record<string, unknown>; return envelope({ id: 'QA_TEST_free_problem', subject_id: null, title: problemBody.title, statement: problemBody.statement, correct_answer: null, source_note: null, archived: false, is_representative: false, knowledge_point_ids: [], attempts: [], version: 1 }, 201); }
      if (url.endsWith('/problems/QA_TEST_free_problem')) return envelope({ id: 'QA_TEST_free_problem', subject_id: null, title: 'QA_TEST 自由题', statement: 'QA_TEST 自由题干', correct_answer: null, source_note: null, archived: false, is_representative: false, knowledge_point_ids: [], attempts: [], version: 1 });
      throw new Error(`Unexpected URL ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    mount();
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: '开始这一段学习 →' }));
    await user.click(await screen.findByRole('button', { name: '结束并保存这一段' }));
    await screen.findByLabelText('题干文字（可选）');
    await user.selectOptions(screen.getByLabelText('学科'), nextSubjectId);
    await user.type(screen.getByLabelText('题目简名（可选）'), 'QA_TEST 自由题');
    await user.type(screen.getByLabelText('题干文字（可选）'), 'QA_TEST 自由题干');
    await user.click(screen.getByRole('button', { name: '保存题目' }));
    await screen.findByRole('heading', { name: '记录这次作答' });
    expect(problemBody?.subject_id).toBeNull();
  });

  it('persists the selected knowledge point and subject in the actual start request', async () => {
    const draft = learningDraftFor('QA_TEST_user');
    draft.subject = 'QA_TEST_subject'; draft.knowledgePointId = 'QA_TEST_point'; draft.knowledgePointName = '卷积定理'; draft.goal = '复习卷积定理';
    let startBody: Record<string, unknown> | undefined;
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
      if (url.endsWith('/subjects')) return envelope({ items: [{ id: 'QA_TEST_subject', name: '信号与系统' }] });
      if (url.endsWith('/current')) return envelope(null);
      if (url.includes('/knowledge-points/QA_TEST_point')) return envelope({ id: 'QA_TEST_point', subject_id: 'QA_TEST_subject', chapter_id: 'QA_TEST_chapter', name: '卷积定理', notes: null, archived: false, version: 1 });
      if (url.includes('/learning-sessions?limit=')) return envelope({ items: [], next_cursor: null });
      if (url.endsWith('/learning-sessions')) { startBody = JSON.parse(String(init.body)) as Record<string, unknown>; return envelope({ ...session, subject_id: 'QA_TEST_subject', knowledge_point_id: 'QA_TEST_point' }, 201); }
      throw new Error(`Unexpected URL ${url}`);
    }));
    mount();
    await userEvent.setup().click(await screen.findByRole('button', { name: '开始这一段学习 →' }));
    await screen.findByRole('button', { name: '暂停学习' });
    expect(startBody).toMatchObject({ subject_id: 'QA_TEST_subject', knowledge_point_id: 'QA_TEST_point', goal: '复习卷积定理' });
  });
  it('keeps the draft and reuses the same command id after an ambiguous network failure', async () => {
    const commands: RequestInit[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
      if (url.endsWith('/subjects')) return envelope({ items: [{ id: 'math', name: '数学' }] });
      if (url.endsWith('/current')) return envelope(null);
      if (url.includes('/learning-sessions?limit=')) return envelope({ items: [], next_cursor: null });
      commands.push(init);
      if (commands.length === 1) throw new TypeError('offline');
      return envelope(session, 201);
    }));
    mount(); const user = userEvent.setup();
    await user.type(await screen.findByLabelText('这次想学什么？'), 'QA_TEST_复习函数');
    await user.click(screen.getByRole('button', { name: '开始这一段学习 →' }));
    await screen.findByRole('alert');
    expect(screen.getByLabelText('这次想学什么？')).toHaveValue('QA_TEST_复习函数');
    await user.click(screen.getByRole('button', { name: '开始这一段学习 →' }));
    await screen.findByRole('button', { name: '暂停学习' });
    expect(commands).toHaveLength(2);
    expect(commands[0].body).toBe(commands[1].body);
    expect(new Headers(commands[0].headers).get('Idempotency-Key')).toBe(new Headers(commands[1].headers).get('Idempotency-Key'));
  });
  it('refreshes the remote scene on conflict and leaves an unsubmitted draft intact', async () => {
    let currentCalls = 0;
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.endsWith('/subjects')) return envelope({ items: [] });
      if (url.endsWith('/current')) { currentCalls++; return envelope(null); }
      if (url.includes('/learning-sessions?limit=')) return envelope({ items: [], next_cursor: null });
      return new Response(JSON.stringify({ error: { code: 'active_session_exists', request_id: 'test-conflict' } }), { status: 409 });
    }));
    mount(); const user = userEvent.setup();
    await user.type(await screen.findByLabelText('这次想学什么？'), '保留这段输入');
    await user.click(screen.getByRole('button', { name: '开始这一段学习 →' }));
    await screen.findByText('请求编号：test-conflict');
    await waitFor(() => expect(currentCalls).toBe(2));
    expect(screen.getByLabelText('这次想学什么？')).toHaveValue('保留这段输入');
  });
  it('restores the active scene and ends it using its actual version', async () => {
    let command: RequestInit | undefined;
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
      if (url.endsWith('/subjects')) return envelope({ items: [] });
      if (url.endsWith('/current')) return envelope(session);
      if (url.includes('/learning-sessions?limit=')) return envelope({ items: [session], next_cursor: null });
      if (url.includes('/session-reflections/')) return new Response('{}', { status: 404 });
      if (url.includes('/problems?')) return envelope({ items: [], next_cursor: null });
      command = init; return envelope({ ...session, status: 'ended', version: 2 });
    }));
    mount(); const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: '结束并保存这一段' }));
    await screen.findByText('这一段学习已保存，尚未记录掌握情况。');
    expect(new Headers(command?.headers).get('If-Match')).toBe('"1"');
    expect(screen.getByLabelText('这次想学什么？')).toHaveValue('');
  });

  it('pauses and resumes the same session using each server version', async () => {
    const requests: Array<{ url: string; init: RequestInit }> = [];
    let remote = { ...session };
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/subjects')) return envelope({ items: [] });
      if (url.endsWith('/current')) return envelope(remote);
      if (url.includes('/learning-sessions?limit=')) return envelope({ items: [remote], next_cursor: null });
      requests.push({ url, init });
      const action = url.endsWith('/pause') ? 'paused' : 'active';
      remote = { ...remote, status: action, version: remote.version + 1 };
      return envelope(remote);
    }));
    mount();
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: '暂停学习' }));
    await screen.findByRole('button', { name: '继续学习' });
    await user.click(screen.getByRole('button', { name: '继续学习' }));
    await screen.findByRole('button', { name: '暂停学习' });

    expect(requests.map(({ url }) => url.split('/').at(-1))).toEqual(['pause', 'resume']);
    expect(new Headers(requests[0].init.headers).get('If-Match')).toBe('"1"');
    expect(new Headers(requests[1].init.headers).get('If-Match')).toBe('"2"');
    expect(requests.every(({ init }) => new Headers(init.headers).has('Idempotency-Key'))).toBe(true);
  });

  it('requires confirmation before cancel and then shows the actual cancelled record', async () => {
    let remote: (typeof session & { timing_enabled: boolean }) | null = {
      ...session,
      timing_enabled: false,
    };
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/subjects')) return envelope({ items: [] });
      if (url.endsWith('/current')) return envelope(remote);
      if (url.includes('/learning-sessions?limit=')) {
        return envelope({ items: remote ? [remote] : [{ ...session, status: 'cancelled', version: 2 }], next_cursor: null });
      }
      expect(url).toContain('/learning-sessions/test-session/cancel');
      expect(new Headers(init.headers).get('If-Match')).toBe('"1"');
      remote = null;
      return envelope({ ...session, status: 'cancelled', version: 2 });
    }));
    const client = mount();
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: '取消本段' }));
    expect(screen.getByRole('dialog')).toHaveTextContent('不会删除已经保存的记录');
    expect(screen.getByRole('button', { name: '确认取消本段' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '确认取消本段' }));
    await screen.findByLabelText('这次想学什么？');
    expect(client.getQueryData(['learning', 'current'])).toEqual({ data: null });
  });

  it('records optional timing separately and displays only server-backed elapsed time', async () => {
    let createBody: string | undefined;
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/subjects')) return envelope({ items: [] });
      if (url.endsWith('/current')) return envelope(null);
      if (url.includes('/learning-sessions?limit=')) return envelope({ items: [], next_cursor: null });
      createBody = String(init.body);
      return envelope({
        ...session,
        timing_enabled: true,
        effective_duration_seconds: 42,
        time_segments: [{ id: 'segment-1', started_at: session.started_at, ended_at: null, duration_seconds: 42 }],
      }, 201);
    }));
    mount();
    const user = userEvent.setup();
    await user.click(await screen.findByLabelText('记录本次有效计时（可选）'));
    await user.click(screen.getByRole('button', { name: '开始这一段学习 →' }));
    await screen.findByText(/本段有效计时：42 秒/);
    expect(JSON.parse(createBody ?? '{}')).toMatchObject({ timing_enabled: true });
    expect(screen.getByRole('timer')).toHaveTextContent('暂停时间不计入');
  });

  it('renders cancelled history entries and recorded time without claiming mastery', async () => {
    const cancelled = {
      ...session,
      status: 'cancelled',
      method_id: null,
      timing_enabled: true,
      time_segments: [{ id: 'segment-1', started_at: session.started_at, ended_at: session.started_at, duration_seconds: 75 }],
      effective_duration_seconds: 75,
    };
    vi.stubGlobal('fetch', vi.fn(async () => envelope({ items: [cancelled], next_cursor: null })));
    const client = createQueryClient();
    client.setDefaultOptions({ queries: { retry: false } });
    render(<QueryClientProvider client={client}><SessionHistory userId="QA_TEST_user" /></QueryClientProvider>);
    expect(await screen.findByText('已取消')).toBeInTheDocument();
    expect(screen.getByText('有效计时：1 分钟 15 秒')).toBeInTheDocument();
    expect(screen.getByText(/计时不是学习成果或掌握证据/)).toBeInTheDocument();
  });

  it('loads an actual session detail when the user opens a history entry', async () => {
    const saved = {
      ...session,
      status: 'ended',
      method_id: null,
      ended_at: '2026-09-30T01:10:00Z',
      timing_enabled: true,
      time_segments: [{
        id: 'segment-1',
        started_at: session.started_at,
        ended_at: '2026-09-30T01:05:00Z',
        duration_seconds: 300,
      }],
      effective_duration_seconds: 300,
    };
    const calls: string[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      calls.push(url);
      if (url.endsWith('/test-session')) return envelope(saved);
      return envelope({ items: [saved], next_cursor: null });
    }));
    const client = createQueryClient();
    client.setDefaultOptions({ queries: { retry: false } });
    render(<QueryClientProvider client={client}><SessionHistory userId="QA_TEST_user" /></QueryClientProvider>);
    await userEvent.setup().click(await screen.findByRole('button', { name: '查看记录' }));
    expect(await screen.findByRole('heading', { name: '学习现场详情' })).toBeInTheDocument();
    expect(screen.getByText('2026-09-30（Asia/Shanghai）')).toBeInTheDocument();
    expect(screen.getByText('有效计时')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: '学习现场详情' })).toHaveTextContent('5 分钟 0 秒');
    expect(calls.some((url) => url.endsWith('/learning-sessions/test-session'))).toBe(true);
    expect(screen.queryByText('掌握状态')).not.toBeInTheDocument();
  });

  it('loads older persisted records with the server cursor', async () => {
    const older = { ...session, id: 'older-session', goal: 'QA_TEST_更早的一段', status: 'ended' };
    const calls: string[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      calls.push(url);
      if (url.includes('cursor=history-cursor')) {
        return envelope({ items: [older], next_cursor: null });
      }
      return envelope({ items: [session], next_cursor: 'history-cursor' });
    }));
    const client = createQueryClient();
    client.setDefaultOptions({ queries: { retry: false } });
    render(<QueryClientProvider client={client}><SessionHistory userId="QA_TEST_user" /></QueryClientProvider>);
    expect(await screen.findByText('QA_TEST_复习函数')).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: '加载更早记录' }));
    expect(await screen.findByText('QA_TEST_更早的一段')).toBeInTheDocument();
    expect(calls.some((url) => url.includes('cursor=history-cursor'))).toBe(true);
    expect(screen.queryByRole('button', { name: '加载更早记录' })).not.toBeInTheDocument();
  });

  it('shows malformed history responses as a recoverable error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => envelope({ unexpected: 'shape' })));
    const client = createQueryClient();
    client.setDefaultOptions({ queries: { retry: false } });
    render(<QueryClientProvider client={client}><SessionHistory userId="QA_TEST_user" /></QueryClientProvider>);
    expect(await screen.findByText('学习记录响应格式不正确，尚未显示记录。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重试' })).toBeInTheDocument();
  });
});
