import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { AttachmentsPanel } from './AttachmentsPanel';
import { clearAttachmentDrafts } from './draft-store';
import type { ProblemData } from '../../shared/api/types';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); clearAttachmentDrafts(); });
it('keeps original materials readable in comparison mode without upload or unlink controls', async () => {
  const link = { link_id: 'QA_TEST_link', attachment_id: 'QA_TEST_readonly', role: 'question' as const, page_start: null, page_end: null, original_name: 'QA_TEST_source.png', detected_mime: 'image/png', byte_size: 12, status: 'ready' as const };
  const problem = { id: 'QA_TEST_source', subject_id: null, title: 'QA_TEST_source', statement: 'QA_TEST 有正文', source_note: null, correct_answer: null, is_representative: true, archived: false, version: 2, attachment_links: [link] } as ProblemData;
  const fetcher = vi.fn(async (path: string) => path.endsWith('/content') ? new Response(new Blob(['QA_TEST original'])) : Response.json({ data: { page_count: 1 } }));
  vi.stubGlobal('fetch', fetcher);
  vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:QA_TEST_readonly'), revokeObjectURL: vi.fn() });
  render(<QueryClientProvider client={createQueryClient()}><AttachmentsPanel userId="QA_TEST_user" scope="QA_TEST_comparison" problem={problem} readOnly /></QueryClientProvider>);
  expect(screen.queryByLabelText('添加附件')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '解除关联' })).not.toBeInTheDocument();
  await userEvent.setup().click(screen.getByRole('button', { name: '下载原始文件' }));
  expect(await screen.findByRole('link', { name: '下载原始附件：QA_TEST_source.png' })).toHaveAttribute('href', 'blob:QA_TEST_readonly');
  expect(fetcher.mock.calls.map(([path]) => path)).toContain('/api/v1/attachments/QA_TEST_readonly/content');
});
const envelope = (data: unknown, status = 200) => new Response(JSON.stringify({ data, meta: { request_id: 'QA_TEST_request' } }), { status });
const attachment = (id: string, status: string, name = `${id}.png`) => ({ id, version: 1, status, original_name: name, detected_mime: status === 'pending_upload' ? null : name.endsWith('.pdf') ? 'application/pdf' : name.endsWith('.webp') ? 'image/webp' : name.endsWith('.jpg') || name.endsWith('.jpeg') ? 'image/jpeg' : 'image/png', byte_size: 12, sha256: null, page_count: name.endsWith('.pdf') ? 8 : 1, failure_code: null, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z', expires_at: null });

class MockXHR {
  upload: { onprogress: ((event: ProgressEvent) => void) | null } = { onprogress: null };
  headers = new Map<string, string>(); status = 200; responseText = ''; withCredentials = false;
  onload: (() => void) | null = null; onloadend: (() => void) | null = null; onerror: (() => void) | null = null; onabort: (() => void) | null = null;
  method = ''; url = ''; body: BodyInit | null = null;
  open(method: string, url: string) { this.method = method; this.url = url; }
  setRequestHeader(name: string, value: string) { this.headers.set(name.toLowerCase(), value); }
  getResponseHeader() { return 'QA_TEST_request'; }
  send(body: BodyInit | null) {
    this.body = body;
    this.upload.onprogress?.({ lengthComputable: true, loaded: 4, total: 4 } as ProgressEvent);
    const id = this.url.split('/').at(-2)!;
    this.responseText = JSON.stringify({ data: attachment(id, 'uploaded') });
    this.onload?.(); this.onloadend?.();
  }
  abort() { this.onabort?.(); }
}

function setup(responses: { failJobFor?: string; problem?: ProblemData; failFirstLink?: boolean; failFirstInit?: boolean } = {}) {
  const ids = new Map<string, string>();
  let uploadIndex = 0;
  const linkCalls: { body: Record<string, unknown>; headers: Headers }[] = [];
  const initCalls: { body: Record<string, unknown>; headers: Headers }[] = [];
  vi.stubGlobal('XMLHttpRequest', MockXHR);
  vi.stubGlobal('fetch', vi.fn(async (input: string, init: RequestInit = {}) => {
    const path = input.replace('/api/v1', '');
    if (path === '/attachments/uploads' && init.method === 'POST') {
      const body = JSON.parse(String(init.body)) as Record<string, unknown> & { filename: string };
      initCalls.push({ body, headers: new Headers(init.headers) });
      if (responses.failFirstInit && initCalls.length === 1) throw new TypeError('offline after write');
      const id = `QA_TEST_attachment_${++uploadIndex}`;
      ids.set(id, body.filename);
      return envelope(attachment(id, 'pending_upload', body.filename), 201);
    }
    const id = path.match(/\/attachments\/(QA_TEST_attachment_\d+)/)?.[1];
    if (id && path.endsWith('/complete')) return envelope({ id: `QA_TEST_job_${id}`, attachment_id: id, kind: 'validate', status: 'queued', input_version: 1, attempt_count: 0, error_code: null }, 202);
    if (path.startsWith('/jobs/')) {
      const jobId = path.split('/').at(-1)!;
      const targetId = jobId.replace('QA_TEST_job_', '');
      return envelope({ id: jobId, attachment_id: targetId, kind: 'validate', status: targetId === responses.failJobFor ? 'failed' : 'succeeded', input_version: 1, attempt_count: 1, error_code: targetId === responses.failJobFor ? 'PROCESSING_FAILED' : null });
    }
    if (id && path === `/attachments/${id}`) return envelope(attachment(id, 'ready', ids.get(id)));
    if (responses.problem && path === `/problems/${responses.problem.id}/attachment-links` && init.method === 'POST') {
      linkCalls.push({ body: JSON.parse(String(init.body)) as Record<string, unknown>, headers: new Headers(init.headers) });
      if (responses.failFirstLink && linkCalls.length === 1) throw new TypeError('offline after write');
      return envelope({ link: { link_id: 'QA_TEST_problem_attachment_link', attachment_id: linkCalls.at(-1)!.body.attachment_id, role: 'question', page_start: null, page_end: null, original_name: ids.get(String(linkCalls.at(-1)!.body.attachment_id)), detected_mime: 'image/png', byte_size: 4, status: 'ready' }, problem_version: responses.problem.version + 1 }, 201);
    }
    throw new Error(`Unexpected request ${input}`);
  }));
  const onReadyChange = vi.fn();
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false }, mutations: { retry: false } });
  render(<QueryClientProvider client={client}><AttachmentsPanel userId="QA_TEST_user" scope="QA_TEST_scope" problem={responses.problem} onReadyChange={onReadyChange} /></QueryClientProvider>);
  return { onReadyChange, linkCalls, initCalls };
}

function rowFor(name: string) { const nameNode = screen.getByText(name); const row = nameNode.closest('.attachment-row'); if (!row) throw new Error(`No attachment row for ${name}`); return within(row as HTMLElement); }
const testFile = (name: string, type: string) => new File([new Uint8Array([1, 2, 3, 4])], name, { type });

describe('private attachment uploads', () => {
  it('clears a previous preview error when retrying succeeds', async () => {
    const attachmentId = 'QA_TEST_saved_pdf';
    const problemId = 'QA_TEST_saved_problem';
    const link = { link_id: 'QA_TEST_saved_link', attachment_id: attachmentId, role: 'question' as const, page_start: 2, page_end: 2, original_name: 'QA_TEST_saved.pdf', detected_mime: 'application/pdf', byte_size: 1024, status: 'ready' as const };
    const savedProblem = { id: problemId, subject_id: null, title: 'QA_TEST_saved', statement: null, source_note: null, correct_answer: null, is_representative: false, archived: false, version: 2, attachment_links: [link] } as ProblemData;
    let previewAttempts = 0;
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:QA_TEST_preview'), revokeObjectURL: vi.fn() });
    vi.stubGlobal('fetch', vi.fn(async (input: string) => {
      const path = input.replace('/api/v1', '');
      if (path === `/attachments/${attachmentId}`) return envelope(attachment(attachmentId, 'ready', link.original_name));
      if (path === `/attachments/${attachmentId}/jobs` && ++previewAttempts === 1) return new Response(JSON.stringify({ detail: 'temporarily unavailable' }), { status: 503 });
      if (path === `/attachments/${attachmentId}/jobs`) return envelope({ id: 'QA_TEST_preview_job', attachment_id: attachmentId, kind: 'preview', status: 'succeeded', input_version: 3, attempt_count: 1, error_code: null }, 202);
      if (path === `/attachments/${attachmentId}/preview?page=2`) return new Response(new Blob(['safe png'], { type: 'image/png' }), { status: 200, headers: { 'Content-Type': 'image/png' } });
      throw new Error(`Unexpected request ${input}`);
    }));
    const client = createQueryClient();
    client.setDefaultOptions({ queries: { retry: false }, mutations: { retry: false } });
    render(<QueryClientProvider client={client}><AttachmentsPanel userId="QA_TEST_user" scope="QA_TEST_saved_problem" problem={savedProblem} /></QueryClientProvider>);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: '查看安全预览' }));
    await screen.findByText('操作未完成。输入已保留，请稍后重试。');
    await user.click(screen.getByRole('button', { name: '查看安全预览' }));
    expect(await screen.findByRole('img', { name: '经过重新编码的题目附件页面' })).toHaveAttribute('src', 'blob:QA_TEST_preview');
    expect(screen.queryByText('操作未完成。输入已保留，请稍后重试。')).not.toBeInTheDocument();
    expect(previewAttempts).toBe(2);
  });

  it('accepts JPEG, PNG, WebP and PDF, polls actual validation jobs, and only reports ready IDs', async () => {
    const { onReadyChange } = setup();
    const user = userEvent.setup();
    await user.upload(screen.getByLabelText('添加附件'), [testFile('QA_TEST_photo.jpg', 'image/jpeg'), testFile('QA_TEST_diagram.png', 'image/png'), testFile('QA_TEST_scan.webp', 'image/webp'), testFile('QA_TEST_notes.pdf', 'application/pdf')]);
    for (const name of ['QA_TEST_photo.jpg', 'QA_TEST_diagram.png', 'QA_TEST_scan.webp', 'QA_TEST_notes.pdf']) {
      await user.click(rowFor(name).getByRole('button', { name: '上传并校验' }));
      await waitFor(() => expect(rowFor(name).getByText(/已校验/)).toBeInTheDocument());
    }
    fireEvent.change(screen.getByLabelText('QA_TEST_notes.pdf 题目页'), { target: { value: '3' } });
    await waitFor(() => expect(onReadyChange).toHaveBeenLastCalledWith([
      { attachment_id: 'QA_TEST_attachment_1', role: 'question' },
      { attachment_id: 'QA_TEST_attachment_2', role: 'question' },
      { attachment_id: 'QA_TEST_attachment_3', role: 'question' },
      { attachment_id: 'QA_TEST_attachment_4', role: 'question', page_start: 3, page_end: 3 },
    ]));
    const calls = vi.mocked(fetch).mock.calls;
    expect(calls.some(([url]) => String(url).includes('/jobs/QA_TEST_job_QA_TEST_attachment_4'))).toBe(true);
  });

  it('keeps a failed file visible while another file reaches ready, and excludes the failed file from create links', async () => {
    const { onReadyChange } = setup({ failJobFor: 'QA_TEST_attachment_2' });
    const user = userEvent.setup();
    await user.upload(screen.getByLabelText('添加附件'), [testFile('QA_TEST_good.png', 'image/png'), testFile('QA_TEST_broken.pdf', 'application/pdf')]);
    await user.click(rowFor('QA_TEST_good.png').getByRole('button', { name: '上传并校验' }));
    await waitFor(() => expect(rowFor('QA_TEST_good.png').getByText(/已校验/)).toBeInTheDocument());
    await user.click(rowFor('QA_TEST_broken.pdf').getByRole('button', { name: '上传并校验' }));
    expect(await rowFor('QA_TEST_broken.pdf').findByRole('alert')).toHaveTextContent('校验或安全预览生成失败');
    expect(screen.getByText('QA_TEST_broken.pdf')).toBeInTheDocument();
    expect(onReadyChange).toHaveBeenLastCalledWith([{ attachment_id: 'QA_TEST_attachment_1', role: 'question' }]);
  });

  it('retries a saved-problem link with the same key and body after a network failure', async () => {
    const problem = { id: 'QA_TEST_problem', subject_id: 'QA_TEST_subject', title: '题目', statement: '题干', source_note: null, correct_answer: null, is_representative: false, archived: false, version: 4, attempts: [], attachment_links: [], knowledge_point_ids: [], created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' } as ProblemData;
    const { linkCalls } = setup({ problem, failFirstLink: true });
    const user = userEvent.setup();
    await user.upload(screen.getByLabelText('添加附件'), testFile('QA_TEST_link.png', 'image/png'));
    await user.click(rowFor('QA_TEST_link.png').getByRole('button', { name: '上传并校验' }));
    await waitFor(() => expect(rowFor('QA_TEST_link.png').getByText(/已校验/)).toBeInTheDocument());
    await user.click(rowFor('QA_TEST_link.png').getByRole('button', { name: '加入此题' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('暂时无法连接书房');
    await user.click(rowFor('QA_TEST_link.png').getByRole('button', { name: '加入此题' }));
    await screen.findByText('附件已加入题目。');
    expect(linkCalls).toHaveLength(2);
    expect(linkCalls[1].body).toEqual(linkCalls[0].body);
    expect(linkCalls[1].headers.get('Idempotency-Key')).toBe(linkCalls[0].headers.get('Idempotency-Key'));
    expect(linkCalls[1].headers.get('If-Match')).toBe('"4"');
  });

  it('retries upload initialization with the same frozen body and idempotency key', async () => {
    const { initCalls } = setup({ failFirstInit: true });
    const user = userEvent.setup();
    await user.upload(screen.getByLabelText('添加附件'), testFile('QA_TEST_retry.png', 'image/png'));
    await user.click(rowFor('QA_TEST_retry.png').getByRole('button', { name: '上传并校验' }));
    expect(await rowFor('QA_TEST_retry.png').findByRole('alert')).toHaveTextContent('暂时无法连接书房');
    await user.click(rowFor('QA_TEST_retry.png').getByRole('button', { name: '重试上传 / 校验' }));
    await waitFor(() => expect(rowFor('QA_TEST_retry.png').getByText(/已校验/)).toBeInTheDocument());
    expect(initCalls).toHaveLength(2);
    expect(initCalls[1].body).toEqual(initCalls[0].body);
    expect(initCalls[1].headers.get('Idempotency-Key')).toBe(initCalls[0].headers.get('Idempotency-Key'));
  });
});
