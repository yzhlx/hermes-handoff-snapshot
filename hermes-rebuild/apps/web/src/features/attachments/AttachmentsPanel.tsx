import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, request, requestBlob, uploadBinary } from '../../shared/api/client';
import type { AttachmentJobResponse, AttachmentLinkData, AttachmentResponse, CompleteAttachmentInput, CreateAttachmentUploadInput, CreateProblemAttachmentLinkInput, CreateProblemAttachmentResponse, CreatePreviewJobInput, ProblemData } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { addAttachmentDraft, attachmentDraftFor, type AttachmentDraftItem, type AttachmentRole } from './draft-store';

const IMAGE_LIMIT = 10 * 1024 * 1024;
const PDF_LIMIT = 30 * 1024 * 1024;
const ALLOWED: Record<string, { mime: string; limit: number }> = {
  '.jpg': { mime: 'image/jpeg', limit: IMAGE_LIMIT }, '.jpeg': { mime: 'image/jpeg', limit: IMAGE_LIMIT },
  '.png': { mime: 'image/png', limit: IMAGE_LIMIT }, '.webp': { mime: 'image/webp', limit: IMAGE_LIMIT },
  '.pdf': { mime: 'application/pdf', limit: PDF_LIMIT },
};
const roles: { value: AttachmentRole; label: string }[] = [
  { value: 'question', label: '题目' }, { value: 'attempt', label: '作答' },
  { value: 'answer', label: '答案' }, { value: 'source', label: '来源' },
];
const newId = () => crypto.randomUUID();
const delay = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));
const itemIsPdf = (item: AttachmentDraftItem) => (item.declaredMime ?? item.file.type) === 'application/pdf';
function descriptorFor(file: File) {
  const extension = Object.keys(ALLOWED).find((candidate) => file.name.toLowerCase().endsWith(candidate));
  if (!extension) throw new Error('仅支持 JPEG、PNG、WebP 图片和 PDF 文件。');
  const descriptor = ALLOWED[extension];
  if (file.size <= 0 || file.size > descriptor.limit) throw new Error(extension === '.pdf' ? 'PDF 文件上限为 30 MiB。' : '图片文件上限为 10 MiB。');
  if (file.type && file.type !== descriptor.mime) throw new Error('文件扩展名与浏览器识别类型不一致，请重新选择文件。');
  return descriptor;
}

export type ReadyAttachmentSelection = { attachment_id: string; role: AttachmentRole; page_start?: number; page_end?: number };
export type AttachmentQueueState = { readyLinks: ReadyAttachmentSelection[]; incompleteCount: number; readyQuestion: boolean };

/** Single public attachment control used by feedback capture and saved problem detail. */
export function AttachmentsPanel({ userId, scope, problem, onReadyChange, onQueueStateChange, readOnly = false }: {
  userId: string; scope: string; problem?: ProblemData; readOnly?: boolean;
  onReadyChange?: (links: ReadyAttachmentSelection[]) => void;
  onQueueStateChange?: (state: AttachmentQueueState) => void;
}) {
  const queryClient = useQueryClient();
  const draft = attachmentDraftFor(userId, scope);
  const [, rerender] = useState(0);
  const bump = () => rerender((value) => value + 1);
  const [message, setMessage] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ key: string; url: string } | null>(null);
  const [download, setDownload] = useState<{ key: string; url: string; name: string } | null>(null);
  const lastReadySignature = useRef('');
  const persistedLinks = problem?.attachment_links ?? [];
  const selected = useMemo(() => draft.items.filter((item) => item.status === 'ready' && item.attachment), [draft.items, draft.items.map((item) => `${item.clientId}:${item.status}`).join('|')]);
  const readySignature = JSON.stringify(selected.map((item) => [item.attachment!.id, item.role, item.page]));
  const queueSignature = JSON.stringify(draft.items.map((item) => [item.clientId, item.status, item.role, item.page]));
  const lastQueueSignature = useRef('');
  useEffect(() => {
    if (!onReadyChange || lastReadySignature.current === readySignature) return;
    lastReadySignature.current = readySignature;
    onReadyChange(selected.map((item) => ({ attachment_id: item.attachment!.id, role: item.role, ...(itemIsPdf(item) ? { page_start: item.page, page_end: item.page } : {}) })));
  }, [selected, onReadyChange, readySignature]);
  useEffect(() => {
    if (!onQueueStateChange || lastQueueSignature.current === queueSignature) return;
    lastQueueSignature.current = queueSignature;
    const readyLinks = selected.map((item) => ({ attachment_id: item.attachment!.id, role: item.role, ...(itemIsPdf(item) ? { page_start: item.page, page_end: item.page } : {}) }));
    onQueueStateChange({ readyLinks, incompleteCount: draft.items.filter((item) => item.status !== 'ready').length, readyQuestion: readyLinks.some((link) => link.role === 'question') });
  }, [onQueueStateChange, queueSignature, selected, draft]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview.url); }, [preview]);
  useEffect(() => () => { if (download) URL.revokeObjectURL(download.url); }, [download]);

  const runUpload = useMutation({
    onMutate: () => setMessage(null),
    mutationFn: async (item: AttachmentDraftItem) => {
      item.abortController = new AbortController();
      const signal = item.abortController.signal;
      item.error = null;
      if (!item.attachment) {
        item.status = 'uploading'; item.progress = 0; bump();
        const descriptor = descriptorFor(item.file);
        item.declaredMime = descriptor.mime;
        const input: CreateAttachmentUploadInput = { operation_id: item.uploadOperationId, filename: item.file.name, declared_mime: descriptor.mime, byte_size: item.file.size };
        const created = await request<AttachmentResponse>('/attachments/uploads', { method: 'POST', headers: { 'Idempotency-Key': item.uploadOperationId }, body: JSON.stringify(input), signal });
        item.attachment = created.data;
      } else {
        item.attachment = (await request<AttachmentResponse>(`/attachments/${item.attachment.id}`, { signal })).data;
      }
      if (item.attachment.status === 'rejected') throw new Error('服务端已拒绝这个文件。请移除此项后重新选择符合格式与内容要求的文件。');
      if (item.attachment.status === 'pending_upload') {
        item.status = 'uploading'; bump();
        const uploaded = await uploadBinary<AttachmentResponse>(`/attachments/${item.attachment.id}/content`, item.file, item.declaredMime ?? item.attachment.detected_mime ?? 'application/octet-stream', item.putOperationId, (percent) => { item.progress = percent; bump(); }, signal);
        item.attachment = uploaded.data;
      }
      if (item.attachment.status === 'uploaded' || item.attachment.status === 'validating') {
        item.status = 'processing'; bump();
        const completeBody: CompleteAttachmentInput = { operation_id: item.completeOperationId };
        const completed = await request<AttachmentJobResponse>(`/attachments/${item.attachment.id}/complete`, { method: 'POST', headers: { 'Idempotency-Key': item.completeOperationId }, body: JSON.stringify(completeBody), signal });
        let job = completed.data;
        for (let attempt = 0; attempt < 90; attempt += 1) {
          if (job.status === 'failed') throw new Error('文件校验或安全预览生成失败；原文件仍保留，可重试或移除此项。');
          if (job.status === 'succeeded') break;
          await delay(700);
          job = (await request<AttachmentJobResponse>(`/jobs/${job.id}`, { signal })).data;
        }
        if (job.status !== 'succeeded') throw new Error('文件仍在处理中。可以稍后重试，上传内容会保留。');
        item.attachment = (await request<AttachmentResponse>(`/attachments/${item.attachment.id}`, { signal })).data;
        if (item.attachment.status !== 'ready') throw new Error('文件处理尚未完成；附件未加入题目。可以稍后重试。');
      }
      if (item.attachment.status !== 'ready') throw new Error('上传状态已失效。请移除此项后重新选择文件。');
      item.status = 'ready'; item.progress = 100; item.abortController = null;
      return item;
    },
    onSuccess: () => { setMessage('文件已通过校验，可以加入题目。'); bump(); },
    onError: (error, item) => {
      const wasAborted = item.abortController?.signal.aborted;
      item.abortController = null;
      if (wasAborted) return;
      item.status = 'failed'; item.error = error instanceof Error ? error.message : '上传失败，请重试。'; bump();
    },
  });

  const linkMutation = useMutation({
    onMutate: () => setMessage(null),
    mutationFn: async (attachment: AttachmentDraftItem) => {
      if (!problem || !attachment.attachment) return;
      const version = problem.version;
      const fingerprint = JSON.stringify({ attachment_id: attachment.attachment.id, role: attachment.role, page: attachment.page, version });
      const commandKey = `link:${attachment.clientId}`;
      let command = draft.commands[commandKey];
      if (!command || command.fingerprint !== fingerprint) {
        const id = newId();
        const body: CreateProblemAttachmentLinkInput = { operation_id: id, attachment_id: attachment.attachment.id, role: attachment.role,
          ...(itemIsPdf(attachment) ? { page_start: attachment.page, page_end: attachment.page } : {}) };
        command = { fingerprint, id, ifMatch: `"${version}"`, body };
        draft.commands[commandKey] = command;
      }
      return request<CreateProblemAttachmentResponse>(`/problems/${problem.id}/attachment-links`, { method: 'POST', headers: { 'Idempotency-Key': command.id, 'If-Match': command.ifMatch }, body: JSON.stringify(command.body) });
    },
    onSuccess: async (_result, item) => { delete draft.commands[`link:${item.clientId}`]; if (item.attachment) draft.items = draft.items.filter((entry) => entry.clientId !== item.clientId); setMessage('附件已加入题目。'); bump(); await queryClient.invalidateQueries({ queryKey: ['problem', problem?.id] }); await queryClient.invalidateQueries({ queryKey: ['problem-detail', problem?.id] }); },
    onError: async (error, item) => { if (error instanceof ApiError && error.status === 409) { delete draft.commands[`link:${item.clientId}`]; await queryClient.invalidateQueries({ queryKey: ['problem', problem?.id] }); await queryClient.invalidateQueries({ queryKey: ['problem-detail', problem?.id] }); } },
  });
  const unlinkMutation = useMutation({
    onMutate: () => setMessage(null),
    mutationFn: async (link: AttachmentLinkData) => {
      if (!problem) return;
      const version = problem.version;
      const fingerprint = JSON.stringify({ link_id: link.link_id, version });
      const commandKey = `unlink:${link.link_id}`;
      let command = draft.commands[commandKey];
      if (!command || command.fingerprint !== fingerprint) {
        const id = newId();
        command = { fingerprint, id, ifMatch: `"${version}"`, body: { operation_id: id } };
        draft.commands[commandKey] = command;
      }
      return request(`/problems/${problem.id}/attachment-links/${link.link_id}`, { method: 'DELETE', headers: { 'Idempotency-Key': command.id, 'If-Match': command.ifMatch }, body: JSON.stringify(command.body) });
    },
    onSuccess: async (_result, link) => { delete draft.commands[`unlink:${link.link_id}`]; await queryClient.invalidateQueries({ queryKey: ['problem', problem?.id] }); await queryClient.invalidateQueries({ queryKey: ['problem-detail', problem?.id] }); },
    onError: async (error, link) => { if (error instanceof ApiError && error.status === 409) { delete draft.commands[`unlink:${link.link_id}`]; await queryClient.invalidateQueries({ queryKey: ['problem', problem?.id] }); await queryClient.invalidateQueries({ queryKey: ['problem-detail', problem?.id] }); } },
  });

  const addFiles = (files: FileList | null) => {
    if (!files?.length) return;
    const incoming = Array.from(files);
    const total = draft.items.length + persistedLinks.length + incoming.length;
    if (total > 10) { setMessage('每道题最多关联 10 个附件；请先移除多余文件。'); return; }
    for (const file of incoming) addAttachmentDraft(draft, file);
    setMessage(null); bump();
  };
  const showBlob = async (attachmentId: string, page: number, mode: 'preview' | 'download', filename?: string) => {
    setMessage(null);
    try {
      if (mode === 'preview') {
        const operationId = newId();
        const body: CreatePreviewJobInput = { operation_id: operationId, kind: 'preview', page };
        let job = (await request<AttachmentJobResponse>(`/attachments/${attachmentId}/jobs`, { method: 'POST', headers: { 'Idempotency-Key': operationId }, body: JSON.stringify(body) })).data;
        for (let attempt = 0; job.status !== 'succeeded' && attempt < 90; attempt += 1) {
          if (job.status === 'failed') throw new Error('安全页面预览生成失败。你仍可下载原始附件或稍后重试。');
          await delay(700);
          job = (await request<AttachmentJobResponse>(`/jobs/${job.id}`)).data;
        }
        if (job.status !== 'succeeded') throw new Error('页面仍在生成安全预览，请稍后重试。');
        const blob = await requestBlob(`/attachments/${attachmentId}/preview?page=${page}`);
        if (blob.type !== 'image/png') throw new Error('服务没有返回安全 PNG 预览，页面未显示。');
        const url = URL.createObjectURL(blob);
        setPreview((current) => { if (current) URL.revokeObjectURL(current.url); return { key: `${attachmentId}:${page}`, url }; });
      } else {
        const blob = await requestBlob(`/attachments/${attachmentId}/content`);
        const url = URL.createObjectURL(blob);
        setDownload((current) => { if (current) URL.revokeObjectURL(current.url); return { key: attachmentId, url, name: filename ?? '附件下载' }; });
      }
    } catch (error) { setMessage(error instanceof Error ? error.message : '附件读取失败，请重试。'); }
  };

  return <section className="attachments-panel" aria-label="题目附件">
    <div className="attachments-heading"><div><h4>题目附件</h4><p className="muted">JPEG、PNG、WebP 单个不超过 10 MiB；PDF 不超过 30 MiB。文件会经过服务端校验。</p></div><span className="attachments-count">{persistedLinks.length + draft.items.length}/10</span></div>
    {!readOnly && <label className="attachment-picker">添加附件<input type="file" multiple accept="image/jpeg,image/png,image/webp,application/pdf,.jpg,.jpeg,.png,.webp,.pdf" disabled={persistedLinks.length + draft.items.length >= 10} onChange={(event) => { addFiles(event.currentTarget.files); event.currentTarget.value = ''; }} /></label>}
    <p className="muted">PDF 需先完成安全校验；文字识别暂不支持。刷新页面前请先完成当前上传，尚未上传的文件需要重新选择。</p>
    {message && <p role="status" className="success-text">{message}</p>}
    {persistedLinks.map((link) => <PersistedAttachment key={link.link_id} link={link} problem={problem} onPreview={(page) => showBlob(link.attachment_id, page, 'preview')} onDownload={() => showBlob(link.attachment_id, 1, 'download', link.original_name)} onUnlink={() => unlinkMutation.mutate(link)} unlinking={unlinkMutation.isPending} readOnly={readOnly} />)}
    {!readOnly && draft.items.map((item) => <div className="attachment-row" key={item.clientId}>
      <div className="attachment-file"><strong>{item.file.name}</strong><span>{formatBytes(item.file.size)} · {item.status === 'ready' ? '已校验' : item.status === 'processing' ? '正在校验文件，预览会按需生成' : item.status === 'uploading' ? `正在上传 ${item.progress}%` : item.status === 'failed' ? '需要处理' : '待上传'}</span></div>
      <label>{item.file.name} 用途<select value={item.role} onChange={(event) => { item.role = event.target.value as AttachmentRole; bump(); }}>{roles.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}</select></label>
      {itemIsPdf(item) && <label>{item.file.name} 题目页<input type="number" min={1} max={100} value={item.page} onChange={(event) => { item.page = Math.max(1, Number(event.target.value) || 1); bump(); }} /></label>}
      {item.status === 'uploading' && <progress max={100} value={item.progress} aria-label={`${item.file.name} 上传进度`} />}
      {item.error && <p className="attachment-error" role="alert">{item.error}</p>}
      {item.status !== 'ready' && item.attachment?.status !== 'rejected' && <button type="button" className="secondary" disabled={runUpload.isPending} onClick={() => { setMessage(null); runUpload.mutate(item); }}>{item.status === 'failed' ? '重试上传 / 校验' : item.status === 'processing' ? '继续检查' : '上传并校验'}</button>}
      {item.status === 'ready' && problem && <button type="button" disabled={linkMutation.isPending} onClick={() => linkMutation.mutate(item)}>加入此题</button>}
      {item.status === 'ready' && item.attachment && <button type="button" className="secondary" onClick={() => void showBlob(item.attachment!.id, item.page, 'preview')}>查看安全预览</button>}
      <button type="button" className="text-button" disabled={runUpload.isPending || linkMutation.isPending} onClick={() => { draft.items = draft.items.filter((entry) => entry.clientId !== item.clientId); bump(); }}>移除此项</button>
    </div>)}
    {preview && <figure className="attachment-preview"><img src={preview.url} alt="经过重新编码的题目附件页面" /><figcaption>安全预览 · 页面图像</figcaption></figure>}
    {download && <a className="attachment-download" href={download.url} download={download.name}>下载原始附件：{download.name}</a>}
    {(runUpload.error || linkMutation.error || unlinkMutation.error) && <Feedback error={runUpload.error ?? linkMutation.error ?? unlinkMutation.error} />}
    <p className="muted attachment-recognition">题目文字识别：暂不可用。附件原件和安全页面预览可查看。</p>
  </section>;
}

function PersistedAttachment({ link, problem, onPreview, onDownload, onUnlink, unlinking, readOnly }: {
  link: AttachmentLinkData; problem?: ProblemData; onPreview: (page: number) => void; onDownload: () => void; onUnlink: () => void; unlinking: boolean; readOnly?: boolean;
}) {
  const metadata = useQuery({ queryKey: ['attachment', link.attachment_id], queryFn: ({ signal }) => request<AttachmentResponse>(`/attachments/${link.attachment_id}`, { signal }) });
  const [page, setPage] = useState(link.page_start ?? 1);
  const isPdf = link.detected_mime === 'application/pdf';
  const pageCount = metadata.data?.data.page_count ?? (isPdf ? 100 : 1);
  const isLastQuestion = link.role === 'question' && persistedQuestionCount(problem) === 1 && !problem?.statement;
  return <div className="attachment-row persisted-attachment">
    <div className="attachment-file"><strong>{link.original_name}</strong><span>{roles.find((role) => role.value === link.role)?.label ?? link.role} · {formatBytes(link.byte_size)} · 已校验</span></div>
    {isPdf && <label>预览页<input aria-label={`${link.original_name} 预览页`} type="number" min={1} max={pageCount} value={page} onChange={(event) => setPage(Math.max(1, Number(event.target.value) || 1))} /></label>}
    <button type="button" className="secondary" onClick={() => onPreview(page)}>查看安全预览</button>
    <button type="button" className="secondary" onClick={onDownload}>下载原始文件</button>
    {problem && !readOnly && <button type="button" className="text-button" disabled={unlinking || isLastQuestion} title={isLastQuestion ? '题目没有正文，至少保留一个题目附件。' : undefined} onClick={onUnlink}>解除关联</button>}
    {metadata.isError && <Feedback error={metadata.error} />}
  </div>;
}

function persistedQuestionCount(problem?: ProblemData) { return problem?.attachment_links?.filter((item) => item.role === 'question').length ?? 0; }
function formatBytes(bytes: number) { return bytes < 1024 * 1024 ? `${Math.max(1, Math.ceil(bytes / 1024))} KiB` : `${(bytes / (1024 * 1024)).toFixed(1)} MiB`; }
