import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { SessionFeedback } from './SessionFeedback';
import { clearFeedbackDrafts } from './draft-store';
import { clearAttachmentDrafts } from '../attachments/draft-store';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); clearFeedbackDrafts(); clearAttachmentDrafts(); });
const envelope = (data: unknown, status = 200) => new Response(JSON.stringify({ data, meta: { request_id: 'qa-request' } }), { status });
const problem = {
  id: 'QA_TEST_problem', subject_id: 'QA_TEST_subject', title: 'QA_TEST_极限题', statement: '求这个极限',
  source_note: null, correct_answer: null, is_representative: false, archived: false, version: 1, attempts: [],
};
const attempt = {
  id: 'QA_TEST_attempt', problem_id: problem.id, session_id: 'QA_TEST_session', occurred_at: '2026-09-30T10:00:00Z',
  created_at: '2026-09-30T10:00:00Z', updated_at: '2026-09-30T10:01:00Z', independence: 'hinted', answer_check: 'pending',
  result: null, attempt_text: '过程旧值', stuck_note: '卡点旧值', error_categories: ['other'], other_error_note: '说明旧值',
  verified_at: '2026-09-30T10:01:00Z', version: 1, evidence_eligibility: { eligible: false, reasons: [] },
};

function mount() {
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false }, mutations: { retry: false } });
  render(<QueryClientProvider client={client}><SessionFeedback userId="QA_TEST_user" sessionId="QA_TEST_session" subjectId="QA_TEST_subject" /></QueryClientProvider>);
  return client;
}

describe('session feedback and problem attempts', () => {
  it('does not create a textless problem until a question attachment has actually reached ready', async () => {
    const createCalls: string[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/session-reflections/QA_TEST_session')) return new Response('{}', { status: 404 });
      if (url.includes('/problems?')) return envelope({ items: [], next_cursor: null });
      if (url.endsWith('/problems') && init.method === 'POST') { createCalls.push(url); return envelope(problem, 201); }
      throw new Error(`Unexpected request ${url}`);
    }));
    mount();
    const user = userEvent.setup();
    await user.upload(screen.getByLabelText('添加附件'), new File(['png'], 'QA_TEST_pending.png', { type: 'image/png' }));
    await user.type(screen.getByLabelText('题干文字（可选）'), '已填写题干');
    expect(screen.getByRole('button', { name: '保存题目' })).toBeDisabled();
    expect(screen.getByText('请先完成每个附件的上传和校验，或移除未完成项，再保存题目。')).toBeInTheDocument();
    expect(createCalls).toEqual([]);
  });

  it('creates an attachment-only question with the ready PDF page linked in the same request', async () => {
    const savedBodies: Record<string, unknown>[] = [];
    vi.stubGlobal('XMLHttpRequest', class {
      upload = { onprogress: null as ((event: ProgressEvent) => void) | null };
      status = 200; responseText = ''; withCredentials = false; onload: (() => void) | null = null; onloadend: (() => void) | null = null; onerror: (() => void) | null = null; onabort: (() => void) | null = null;
      open() {} setRequestHeader() {} getResponseHeader() { return 'QA_TEST_request'; }
      send() { this.responseText = JSON.stringify({ data: attachmentData }); this.upload.onprogress?.({ lengthComputable: true, loaded: 4, total: 4 } as ProgressEvent); this.onload?.(); this.onloadend?.(); }
      abort() { this.onabort?.(); }
    });
    const attachmentId = 'QA_TEST_pdf_attachment';
    const attachmentData = { id: attachmentId, version: 2, status: 'uploaded', original_name: 'QA_TEST_only.pdf', detected_mime: 'application/pdf', byte_size: 4, page_count: 1, failure_code: null, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z', expires_at: null };
    const readyData = { ...attachmentData, version: 3, status: 'ready' };
    const question = { link_id: 'QA_TEST_link', attachment_id: attachmentId, role: 'question', page_start: 1, page_end: 1, original_name: 'QA_TEST_only.pdf', detected_mime: 'application/pdf', byte_size: 4, status: 'ready' };
    const savedProblem = { ...problem, id: 'QA_TEST_textless_problem', title: 'QA_TEST_pdf题', statement: null, attachment_links: [question], attempts: [] };
    vi.stubGlobal('fetch', vi.fn(async (input: string, init: RequestInit = {}) => {
      const path = input.replace('/api/v1', '');
      if (path === '/session-reflections/QA_TEST_session') return new Response('{}', { status: 404 });
      if (path.includes('/problems?')) return envelope({ items: [], next_cursor: null });
      if (path === '/attachments/uploads') return envelope({ ...attachmentData, version: 1, status: 'pending_upload' }, 201);
      if (path.endsWith(`/attachments/${attachmentId}/complete`)) return envelope({ id: 'QA_TEST_validate_job', attachment_id: attachmentId, kind: 'validate', status: 'queued', input_version: 2, attempt_count: 0, error_code: null }, 202);
      if (path === '/jobs/QA_TEST_validate_job') return envelope({ id: 'QA_TEST_validate_job', attachment_id: attachmentId, kind: 'validate', status: 'succeeded', input_version: 2, attempt_count: 1, error_code: null });
      if (path === `/attachments/${attachmentId}`) return envelope(readyData);
      if (path === '/problems' && init.method === 'POST') { savedBodies.push(JSON.parse(String(init.body)) as Record<string, unknown>); return envelope(savedProblem, 201); }
      if (path === `/problems/${savedProblem.id}`) return envelope(savedProblem);
      throw new Error(`Unexpected request ${input}`);
    }));
    mount();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('题目简名（可选）'), 'QA_TEST_pdf题');
    await user.upload(screen.getByLabelText('添加附件'), new File(['PDF!'], 'QA_TEST_only.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: '上传并校验' }));
    await screen.findByText(/已校验/);
    await waitFor(() => expect(screen.getByRole('button', { name: '保存题目' })).not.toBeDisabled());
    await user.click(screen.getByRole('button', { name: '保存题目' }));
    await screen.findByRole('heading', { name: '记录这次作答' });
    await waitFor(() => expect(savedBodies).toHaveLength(1));
    expect(savedBodies).toHaveLength(1);
    expect(savedBodies[0]).toMatchObject({ statement: null, attachment_links: [{ attachment_id: attachmentId, role: 'question', page_start: 1, page_end: 1 }] });
  });

  it('saves feedback, a text problem, and a pending attempt as separate honest records', async () => {
    const saved: RequestInit[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/session-reflections/QA_TEST_session')) return new Response('{}', { status: 404 });
      if (url.includes('/problems?')) return envelope({ items: [], next_cursor: null });
      if (url.endsWith('/session-reflections')) {
        saved.push(init);
        return envelope({ id: 'QA_TEST_reflection', session_id: 'QA_TEST_session', summary: '做了两道题', recalled_text: null, reference_checked: null, missing_parts: null, stuck_note: null, resume_note: null, version: 1 });
      }
      if (url.endsWith('/problems')) {
        saved.push(init);
        return envelope({ ...problem, attempts: [] }, 201);
      }
      if (url.includes('/problems/QA_TEST_problem')) return envelope(problem);
      if (url.endsWith('/problem-attempts')) {
        saved.push(init);
        return envelope({ id: 'QA_TEST_attempt' }, 201);
      }
      throw new Error(`Unexpected request ${url}`);
    }));

    mount();
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText('这次实际做了什么？（可选）'), '做了两道题');
    await user.click(screen.getByRole('button', { name: '保存本次反馈' }));
    expect(await screen.findByText('反馈已保存，可之后继续补充。')).toBeInTheDocument();

    await user.type(screen.getByLabelText('题目简名（可选）'), 'QA_TEST_极限题');
    await user.type(screen.getByLabelText('题干文字（可选）'), '求这个极限');
    await user.click(screen.getByRole('button', { name: '保存题目' }));
    await screen.findByRole('heading', { name: '记录这次作答' });
    await user.selectOptions(screen.getByLabelText('核对状态'), 'pending');
    await user.type(screen.getByLabelText('卡住的位置（可选）'), '不知道如何换元');
    await user.click(screen.getByRole('button', { name: '保存这次作答' }));
    expect(await screen.findByText('这次作答已单独保存，可再次练习并追加新记录。')).toBeInTheDocument();

    const reflectionBody = JSON.parse(String(saved[0].body));
    expect(reflectionBody).toMatchObject({ session_id: 'QA_TEST_session', summary: '做了两道题' });
    const problemBody = JSON.parse(String(saved[1].body));
    expect(problemBody).toMatchObject({ title: 'QA_TEST_极限题', statement: '求这个极限' });
    const attemptBody = JSON.parse(String(saved[2].body));
    expect(attemptBody).toMatchObject({ answer_check: 'pending', result: null, independence: 'independent', stuck_note: '不知道如何换元' });
    expect(new Headers(saved[0].headers).get('Idempotency-Key')).toBe(reflectionBody.operation_id);
    expect(new Headers(saved[1].headers).get('Idempotency-Key')).toBe(problemBody.operation_id);
    expect(new Headers(saved[2].headers).get('Idempotency-Key')).toBe(attemptBody.operation_id);
  });

  it('keeps a checked result mandatory and does not submit an unchecked result', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.endsWith('/session-reflections/QA_TEST_session')) return new Response('{}', { status: 404 });
      if (url.includes('/problems?')) return envelope({ items: [problem], next_cursor: null });
      if (url.endsWith('/problems/QA_TEST_problem')) return envelope(problem);
      throw new Error(`Unexpected request ${url}`);
    }));
    mount();
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText('选择已有题目继续练习'), 'QA_TEST_problem');
    await user.selectOptions(await screen.findByLabelText('核对状态'), 'checked');
    await user.click(screen.getByRole('button', { name: '保存这次作答' }));
    expect(await screen.findByText('已对答案时，请选择正确、部分正确或错误。')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText('核对结果')).toBeInTheDocument());
  });

  it('retries an uncertain feedback create with the same endpoint, body, and idempotency key', async () => {
    const creates: RequestInit[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/session-reflections/QA_TEST_session')) return new Response('{}', { status: 404 });
      if (url.includes('/problems?')) return envelope({ items: [], next_cursor: null });
      if (url.endsWith('/session-reflections')) {
        creates.push(init);
        if (creates.length === 1) throw new TypeError('offline after request');
        return envelope({ id: 'QA_TEST_reflection', session_id: 'QA_TEST_session', summary: 'QA_TEST_已经做了题', recalled_text: null, reference_checked: null, missing_parts: null, stuck_note: null, resume_note: null, version: 1 });
      }
      throw new Error(`Unexpected request ${url}`);
    }));
    mount();
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText('这次实际做了什么？（可选）'), 'QA_TEST_已经做了题');
    await user.click(screen.getByRole('button', { name: '保存本次反馈' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('暂时无法连接书房');
    await user.click(screen.getByRole('button', { name: '保存本次反馈' }));
    expect(await screen.findByText('反馈已保存，可之后继续补充。')).toBeInTheDocument();
    expect(creates).toHaveLength(2);
    expect(creates[0].body).toBe(creates[1].body);
    expect(new Headers(creates[0].headers).get('Idempotency-Key')).toBe(new Headers(creates[1].headers).get('Idempotency-Key'));
  });

  it('edits only text facts as a PATCH and leaves verification fields untouched', async () => {
    const updates: { url: string; init: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/session-reflections/QA_TEST_session')) return new Response('{}', { status: 404 });
      if (url.includes('/problems?')) return envelope({ items: [problem], next_cursor: null });
      if (url.endsWith(`/problems/${problem.id}`)) return envelope({ ...problem, attempts: [attempt] });
      if (url.endsWith(`/problem-attempts/${attempt.id}`) && init.method === 'PATCH') {
        updates.push({ url, init });
        return envelope({ ...attempt, independence: 'independent', attempt_text: null, stuck_note: null, other_error_note: null, error_categories: ['other'], version: 2, verified_at: attempt.verified_at });
      }
      throw new Error(`Unexpected request ${url}`);
    }));
    mount();
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText('选择已有题目继续练习'), problem.id);
    await user.click(await screen.findByRole('button', { name: '编辑这次作答记录' }));
    await user.clear(screen.getByLabelText('作答过程'));
    await user.clear(screen.getByLabelText('卡住的位置'));
    await user.clear(screen.getByLabelText('其他错误说明'));
    await user.click(screen.getByRole('button', { name: '保存修正' }));
    await waitFor(() => expect(updates).toHaveLength(1));
    const body = JSON.parse(String(updates[0].init.body));
    expect(body).toMatchObject({ attempt_text: null, stuck_note: null, other_error_note: null });
    expect(body).not.toHaveProperty('independence');
    expect(body).not.toHaveProperty('answer_check');
    expect(body).not.toHaveProperty('result');
    expect(new Headers(updates[0].init.headers).get('If-Match')).toBe('"1"');
    expect(new Headers(updates[0].init.headers).get('Idempotency-Key')).toBe(body.operation_id);
    expect(attempt.verified_at).toBe('2026-09-30T10:01:00Z');
  });

  it('corrects independence, answer check, result, and error categories together', async () => {
    const updates: RequestInit[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/session-reflections/QA_TEST_session')) return new Response('{}', { status: 404 });
      if (url.includes('/problems?')) return envelope({ items: [problem], next_cursor: null });
      if (url.endsWith(`/problems/${problem.id}`)) return envelope({ ...problem, attempts: [attempt] });
      if (url.endsWith(`/problem-attempts/${attempt.id}`) && init.method === 'PATCH') {
        updates.push(init);
        return envelope({ ...attempt, answer_check: 'checked', result: 'partial', independence: 'independent', error_categories: ['condition'], version: 2, verified_at: '2026-09-30T10:05:00Z' });
      }
      throw new Error(`Unexpected request ${url}`);
    }));
    mount();
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText('选择已有题目继续练习'), problem.id);
    await user.click(await screen.findByRole('button', { name: '编辑这次作答记录' }));
    await user.selectOptions(screen.getAllByLabelText('独立程度')[0], 'independent');
    await user.selectOptions(screen.getAllByLabelText('核对状态')[0], 'checked');
    await user.selectOptions(screen.getByLabelText('实际结果'), 'partial');
    await user.click(screen.getByLabelText('条件判断'));
    await user.click(screen.getByRole('button', { name: '保存修正' }));
    await waitFor(() => expect(updates).toHaveLength(1));
    const body = JSON.parse(String(updates[0].body));
    expect(body).toMatchObject({ answer_check: 'checked', result: 'partial', independence: 'independent', error_categories: ['other', 'condition'] });
  });

  it('retries an uncertain attempt correction with the same frozen version, body, and key', async () => {
    const updates: RequestInit[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/session-reflections/QA_TEST_session')) return new Response('{}', { status: 404 });
      if (url.includes('/problems?')) return envelope({ items: [problem], next_cursor: null });
      if (url.endsWith(`/problems/${problem.id}`)) return envelope({ ...problem, attempts: [attempt] });
      if (url.endsWith(`/problem-attempts/${attempt.id}`) && init.method === 'PATCH') {
        updates.push(init);
        if (updates.length === 1) throw new TypeError('offline after request');
        return envelope({ ...attempt, attempt_text: 'QA_TEST_更新作答', version: 2 });
      }
      throw new Error(`Unexpected request ${url}`);
    }));
    mount();
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText('选择已有题目继续练习'), problem.id);
    await user.click(await screen.findByRole('button', { name: '编辑这次作答记录' }));
    await user.clear(screen.getByLabelText('作答过程'));
    await user.type(screen.getByLabelText('作答过程'), 'QA_TEST_更新作答');
    await user.click(screen.getByRole('button', { name: '保存修正' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('暂时无法连接书房');
    await user.click(screen.getByRole('button', { name: '保存修正' }));
    await waitFor(() => expect(updates).toHaveLength(2));
    expect(updates[0].body).toBe(updates[1].body);
    expect(new Headers(updates[0].headers).get('Idempotency-Key')).toBe(new Headers(updates[1].headers).get('Idempotency-Key'));
    expect(new Headers(updates[0].headers).get('If-Match')).toBe('"1"');
  });

  it('edits problem metadata and saves representative and archive status', async () => {
    const updates: RequestInit[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/session-reflections/QA_TEST_session')) return new Response('{}', { status: 404 });
      if (url.includes('/problems?')) return envelope({ items: [problem], next_cursor: null });
      if (url.endsWith(`/problems/${problem.id}`) && init.method === 'PATCH') {
        updates.push(init);
        return envelope({ ...problem, title: 'QA_TEST_更新标题', is_representative: true, archived: true, version: 2 });
      }
      if (url.endsWith(`/problems/${problem.id}`)) return envelope({ ...problem, attempts: [] });
      throw new Error(`Unexpected request ${url}`);
    }));
    mount();
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText('选择已有题目继续练习'), problem.id);
    await user.click(await screen.findByText('编辑题目资料与状态'));
    await user.clear(screen.getByLabelText('题目简名'));
    await user.type(screen.getByLabelText('题目简名'), 'QA_TEST_更新标题');
    await user.click(screen.getByLabelText('标记为代表题'));
    await user.click(screen.getByLabelText('归档此题'));
    await user.click(screen.getByRole('button', { name: '保存题目修改' }));
    await waitFor(() => expect(updates).toHaveLength(1));
    const body = JSON.parse(String(updates[0].body));
    expect(body).toMatchObject({ title: 'QA_TEST_更新标题', is_representative: true, archived: true });
    expect(new Headers(updates[0].headers).get('If-Match')).toBe('"1"');
    expect(new Headers(updates[0].headers).get('Idempotency-Key')).toBe(body.operation_id);
  });

  it('filters archived problems and restores one before allowing new attempts', async () => {
    const archivedProblem = { ...problem, archived: true };
    const updates: RequestInit[] = [];
    let restored = false;
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.endsWith('/session-reflections/QA_TEST_session')) return new Response('{}', { status: 404 });
      if (url.includes('archived=true')) return envelope({ items: [archivedProblem], next_cursor: null });
      if (url.includes('/problems?')) return envelope({ items: [], next_cursor: null });
      if (url.endsWith(`/problems/${problem.id}`) && init.method === 'PATCH') {
        updates.push(init);
        restored = true;
        return envelope({ ...problem, archived: false, version: 2 });
      }
      if (url.endsWith(`/problems/${problem.id}`)) return envelope({ ...(restored ? problem : archivedProblem), attempts: [] });
      throw new Error(`Unexpected request ${url}`);
    }));
    mount();
    const user = userEvent.setup();
    await user.click(await screen.findByLabelText('查看归档题目'));
    await user.selectOptions(await screen.findByLabelText('选择已有题目继续练习'), problem.id);
    expect(await screen.findByText('这道题已归档；可以查看历史与更正记录，恢复后才能追加作答。')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '记录这次作答' })).not.toBeInTheDocument();
    await user.click(screen.getByText('编辑题目资料与状态'));
    await user.click(screen.getByLabelText('归档此题'));
    await user.click(screen.getByRole('button', { name: '保存题目修改' }));
    await waitFor(() => expect(updates).toHaveLength(1));
    expect(JSON.parse(String(updates[0].body))).toMatchObject({ archived: false });
    expect(await screen.findByRole('heading', { name: '记录这次作答' })).toBeInTheDocument();
  });
});
