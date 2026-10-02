import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, request } from '../../shared/api/client';
import type { CreateReflectionInput, CreateReflectionResponse, ReflectionResponse, UpdateReflectionInput } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { feedbackDraftFor } from './draft-store';

const reflectionKey = (sessionId: string) => ['session-reflection', sessionId] as const;
const operationId = () => crypto.randomUUID();
const optionalText = (value: string) => value.trim() || null;

export function ReflectionEditor({ userId, sessionId }: { userId: string; sessionId: string }) {
  const client = useQueryClient();
  const draft = feedbackDraftFor(userId, sessionId);
  const [values, setValues] = useState(() => ({
    summary: draft.summary, recalledText: draft.recalledText,
    referenceChecked: draft.referenceChecked, missingParts: draft.missingParts,
    stuckNote: draft.stuckNote, resumeNote: draft.resumeNote,
  }));
  const [saved, setSaved] = useState(false);
  const reflection = useQuery({
    queryKey: reflectionKey(sessionId),
    queryFn: ({ signal }) => request<ReflectionResponse>(`/session-reflections/${sessionId}`, { signal }),
    retry: false,
  });
  useEffect(() => {
    const persisted = reflection.data?.data;
    if (!persisted) return;
    const draftHasContent = [draft.summary, draft.recalledText, draft.missingParts, draft.stuckNote, draft.resumeNote].some(Boolean);
    if (draftHasContent) return;
    const restored = {
      summary: persisted.summary ?? '', recalledText: persisted.recalled_text ?? '',
      referenceChecked: persisted.reference_checked === null ? '' as const : persisted.reference_checked ? 'yes' as const : 'no' as const,
      missingParts: persisted.missing_parts ?? '', stuckNote: persisted.stuck_note ?? '', resumeNote: persisted.resume_note ?? '',
    };
    setValues(restored);
    Object.assign(draft, {
      summary: restored.summary, recalledText: restored.recalledText,
      referenceChecked: restored.referenceChecked, missingParts: restored.missingParts,
      stuckNote: restored.stuckNote, resumeNote: restored.resumeNote,
    });
  }, [reflection.data, draft]);
  const update = (key: keyof typeof values, value: string) => {
    setValues((old) => ({ ...old, [key]: value }));
    Object.assign(draft, { [key]: value });
  };
  const save = useMutation({
    mutationFn: async () => {
      const payload = {
        summary: optionalText(values.summary), recalled_text: optionalText(values.recalledText),
        reference_checked: values.referenceChecked === '' ? null : values.referenceChecked === 'yes',
        missing_parts: optionalText(values.missingParts), stuck_note: optionalText(values.stuckNote), resume_note: optionalText(values.resumeNote),
      };
      if (![payload.summary, payload.recalled_text, payload.missing_parts, payload.stuck_note].some(Boolean)) {
        throw new Error('请至少记录实际完成内容、回忆结果、遗漏或卡点中的一项。');
      }
      const fingerprint = JSON.stringify(payload);
      if (draft.reflectionOperation?.fingerprint !== fingerprint) {
        const persisted = reflection.data?.data;
        const id = operationId();
        const method = persisted ? 'PATCH' : 'POST';
        const path = persisted ? `/session-reflections/${sessionId}` : '/session-reflections';
        const body: UpdateReflectionInput | CreateReflectionInput = persisted
          ? { ...payload, operation_id: id }
          : { ...payload, session_id: sessionId, operation_id: id };
        draft.reflectionOperation = {
          fingerprint, id, method, path,
          ...(persisted ? { ifMatch: `"${persisted.version}"` } : {}),
          body: body as unknown as Record<string, unknown>,
        };
      }
      const operation = draft.reflectionOperation;
      if (!operation?.method || !operation.path || !operation.body) throw new Error('无法创建反馈操作，请重试。');
      const headers: Record<string, string> = { 'Idempotency-Key': operation.id };
      if (operation.ifMatch) headers['If-Match'] = operation.ifMatch;
      return operation.method === 'PATCH'
        ? request<ReflectionResponse>(operation.path, { method: 'PATCH', headers, body: JSON.stringify(operation.body) })
        : request<CreateReflectionResponse>(operation.path, { method: 'POST', headers, body: JSON.stringify(operation.body) });
    },
    onSuccess: (response) => {
      client.setQueryData(reflectionKey(sessionId), response);
      draft.reflectionOperation = null;
      setSaved(true);
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        draft.reflectionOperation = null;
        void client.invalidateQueries({ queryKey: reflectionKey(sessionId) });
      }
    },
  });
  const reflectionNotFound = reflection.isError && reflection.error instanceof ApiError && reflection.error.status === 404;
  const canWrite = !reflection.isPending && (!reflection.isError || reflectionNotFound);

  return <div className="reflection-editor">
    {reflection.isPending && <p role="status" className="muted">正在读取已保存反馈…</p>}
    {reflectionNotFound && <p className="muted">还没有已保存的反馈，填写后可以保存。</p>}
    {reflection.isError && !reflectionNotFound && <><Feedback error={reflection.error} /><button type="button" className="text-button" onClick={() => void reflection.refetch()}>重新读取</button></>}
    <form onSubmit={(event) => { event.preventDefault(); if (!save.isPending && canWrite) save.mutate(); }}>
      <label>这次实际做了什么？（可选）<textarea maxLength={10000} value={values.summary} onChange={(event) => update('summary', event.target.value)} /></label>
      <label>离开资料后，能回忆或解释什么？（可选）<textarea maxLength={10000} value={values.recalledText} onChange={(event) => update('recalledText', event.target.value)} /></label>
      <label>是否对照了资料或答案？（可选）<select value={values.referenceChecked} onChange={(event) => update('referenceChecked', event.target.value)}><option value="">暂不记录</option><option value="yes">已对照</option><option value="no">没有对照</option></select></label>
      <label>发现的遗漏（可选）<textarea maxLength={10000} value={values.missingParts} onChange={(event) => update('missingParts', event.target.value)} /></label>
      <label>卡住的地方（一句话即可，可选）<textarea maxLength={2000} value={values.stuckNote} onChange={(event) => update('stuckNote', event.target.value)} /></label>
      <label>下次想从哪里继续？（可选）<input maxLength={2000} value={values.resumeNote} onChange={(event) => update('resumeNote', event.target.value)} /></label>
      <Feedback error={save.error} />
      {saved && <p className="success-text" role="status">反馈已保存，可之后继续补充。</p>}
      <button type="submit" disabled={save.isPending || !canWrite}>{save.isPending ? '正在保存反馈…' : reflection.data ? '更新本次反馈' : '保存本次反馈'}</button>
    </form>
  </div>;
}
