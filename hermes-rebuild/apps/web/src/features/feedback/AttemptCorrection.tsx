import { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ApiError, request } from '../../shared/api/client';
import type { ProblemAttemptData, UpdateAttemptInput, UpdateAttemptResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { errorOptions, operationId, optionalText, type ErrorCategory, type ResultValue } from './problem-utils';
import type { FeedbackDraft } from './draft-store';

export const independenceLabel: Record<ProblemAttemptData['independence'], string> = {
  independent: '独立完成', hinted: '有一些提示', after_answer: '看过答案后完成', unable: '基本不会',
};
export const attemptResultLabel: Record<string, string> = { correct: '核对正确', partial: '核对为部分正确', incorrect: '核对错误' };
const errorLabel: Record<string, string> = Object.fromEntries(errorOptions.map(([key, label]) => [key, label]));

/** Read-only rendering of one saved attempt, with the shared correction control. */
export function AttemptRecord({ attempt, draft }: { attempt: ProblemAttemptData; draft: FeedbackDraft }) {
  return <li>
    <strong>{attempt.answer_check === 'pending' ? '尚未核对' : attemptResultLabel[attempt.result ?? '']}</strong>
    <span>{independenceLabel[attempt.independence]} · {new Date(attempt.occurred_at).toLocaleString('zh-CN')}</span>
    {attempt.attempt_text && <p>{attempt.attempt_text}</p>}
    {attempt.error_categories.length > 0 && <p>记录的原因：{attempt.error_categories.map((key) => errorLabel[key] ?? key).join('、')}</p>}
    {attempt.stuck_note && <p className="muted">卡点：{attempt.stuck_note}</p>}
    <AttemptCorrection draft={draft} attempt={attempt} />
  </li>;
}

/**
 * Inline correction form for one attempt. Writes a real, versioned, idempotent
 * PATCH to /problem-attempts/{id}; a 409 keeps the local input and re-reads.
 * The draft store is injected so the same control works from the learning
 * session and from the comparison workspace (which has no session).
 */
export function AttemptCorrection({ draft, attempt }: { draft: FeedbackDraft; attempt: ProblemAttemptData }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const pending = draft.correctionOperations[attempt.id];
  const pendingBody = pending?.body;
  const [answerCheck, setAnswerCheck] = useState((pendingBody?.answer_check as ProblemAttemptData['answer_check'] | undefined) ?? attempt.answer_check);
  const [result, setResult] = useState((pendingBody?.result as ResultValue | null | undefined) ?? attempt.result ?? '');
  const [independence, setIndependence] = useState((pendingBody?.independence as ProblemAttemptData['independence'] | undefined) ?? attempt.independence);
  const [attemptText, setAttemptText] = useState(typeof pendingBody?.attempt_text === 'string' ? pendingBody.attempt_text : attempt.attempt_text ?? '');
  const [stuckNote, setStuckNote] = useState(typeof pendingBody?.stuck_note === 'string' ? pendingBody.stuck_note : attempt.stuck_note ?? '');
  const [otherNote, setOtherNote] = useState(typeof pendingBody?.other_error_note === 'string' ? pendingBody.other_error_note : attempt.other_error_note ?? '');
  const [categories, setCategories] = useState<ErrorCategory[]>((pendingBody?.error_categories as ErrorCategory[] | undefined) ?? attempt.error_categories as ErrorCategory[]);
  useEffect(() => {
    if (editing) return;
    setAnswerCheck(attempt.answer_check);
    setResult(attempt.result ?? '');
    setIndependence(attempt.independence);
    setAttemptText(attempt.attempt_text ?? '');
    setStuckNote(attempt.stuck_note ?? '');
    setOtherNote(attempt.other_error_note ?? '');
    setCategories(attempt.error_categories);
  }, [attempt.version, editing]);
  const operation = useMutation({
    mutationFn: async () => {
      const old = draft.correctionOperations[attempt.id];
      if (old?.body && old.path && old.ifMatch) return request<UpdateAttemptResponse>(old.path, {
        method: 'PATCH', headers: { 'Idempotency-Key': old.id, 'If-Match': old.ifMatch }, body: JSON.stringify(old.body),
      });
      if (answerCheck === 'checked' && !result) throw new Error('已对答案时请选择结果。');
      if (answerCheck === 'pending' && result) throw new Error('暂时没有答案时不能填写结果。');
      if (result === 'correct' && categories.length) throw new Error('完全正确时不能同时标记错误原因。');
      const patch: Omit<UpdateAttemptInput, 'operation_id'> = {};
      const nextResult = answerCheck === 'checked' && result ? result as ResultValue : null;
      if (answerCheck !== attempt.answer_check) patch.answer_check = answerCheck;
      if (nextResult !== attempt.result) patch.result = nextResult;
      if (independence !== attempt.independence) patch.independence = independence;
      const nextAttemptText = optionalText(attemptText);
      const nextStuckNote = optionalText(stuckNote);
      const nextOtherNote = categories.includes('other') ? optionalText(otherNote) : null;
      if (nextAttemptText !== (attempt.attempt_text ?? null)) patch.attempt_text = nextAttemptText;
      if (nextStuckNote !== (attempt.stuck_note ?? null)) patch.stuck_note = nextStuckNote;
      if (JSON.stringify(categories) !== JSON.stringify(attempt.error_categories)) patch.error_categories = categories;
      if (nextOtherNote !== (attempt.other_error_note ?? null)) patch.other_error_note = nextOtherNote;
      if (Object.keys(patch).length === 0) throw new Error('没有检测到需要修改的内容。');
      const fingerprint = JSON.stringify({ ...patch, version: attempt.version });
      const id = operationId();
      const body: UpdateAttemptInput = { ...patch, operation_id: id };
      const record = { fingerprint, id, method: 'PATCH' as const, path: `/problem-attempts/${attempt.id}`, ifMatch: `"${attempt.version}"`, body };
      draft.correctionOperations[attempt.id] = record;
      return request<UpdateAttemptResponse>(record.path!, {
        method: 'PATCH', headers: { 'Idempotency-Key': record.id, 'If-Match': record.ifMatch! },
        body: JSON.stringify(record.body),
      });
    },
    onSuccess: () => {
      delete draft.correctionOperations[attempt.id];
      setEditing(false);
      void queryClient.invalidateQueries({ queryKey: ['problem'] });
      void queryClient.invalidateQueries({ queryKey: ['problem-detail'] });
      void queryClient.invalidateQueries({ queryKey: ['comparison-problems'] });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        delete draft.correctionOperations[attempt.id];
        void queryClient.invalidateQueries({ queryKey: ['problem'] });
        void queryClient.invalidateQueries({ queryKey: ['problem-detail'] });
      }
    },
  });
  if (!editing) return <button type="button" className="text-button" onClick={() => setEditing(true)}>编辑这次作答记录</button>;
  return <form className="attempt-correction" onSubmit={(event) => { event.preventDefault(); if (!operation.isPending) operation.mutate(); }}>
    <label>独立程度<select value={independence} onChange={(event) => setIndependence(event.target.value as ProblemAttemptData['independence'])}><option value="independent">独立完成</option><option value="hinted">有一些提示</option><option value="after_answer">看过答案后完成</option><option value="unable">基本不会</option></select></label>
    <label>核对状态<select value={answerCheck} onChange={(event) => { const next = event.target.value as ProblemAttemptData['answer_check']; setAnswerCheck(next); if (next === 'pending') { setResult(''); setCategories([]); setOtherNote(''); } }}><option value="pending">暂时没有答案</option><option value="checked">已经对过答案</option></select></label>
    {answerCheck === 'checked' && <label>实际结果<select value={result} onChange={(event) => { const next = event.target.value as typeof result; setResult(next); if (next === 'correct') { setCategories([]); setOtherNote(''); } }}><option value="">请选择</option><option value="correct">正确</option><option value="partial">部分正确</option><option value="incorrect">错误</option></select></label>}
    <label>作答过程<textarea maxLength={10000} value={attemptText} onChange={(event) => setAttemptText(event.target.value)} /></label>
    <label>卡住的位置<textarea maxLength={5000} value={stuckNote} onChange={(event) => setStuckNote(event.target.value)} /></label>
    {answerCheck === 'checked' && result !== 'correct' && <fieldset className="error-categories"><legend>错误原因</legend>{errorOptions.map(([key, label]) => <label className="category-option" key={key}><input type="checkbox" checked={categories.includes(key)} onChange={() => setCategories((old) => old.includes(key) ? old.filter((item) => item !== key) : [...old, key])} />{label}</label>)}</fieldset>}
    {categories.includes('other') && <label>其他错误说明<input maxLength={2000} value={otherNote} onChange={(event) => setOtherNote(event.target.value)} /></label>}
    <Feedback error={operation.error} />
    {operation.isError && <p className="muted" role="status">修改未保存，输入已保留；若提示版本冲突，请重新读取后再保存。</p>}
    <div className="session-actions"><button type="button" className="secondary" onClick={() => { delete draft.correctionOperations[attempt.id]; setEditing(false); }}>取消</button><button type="submit" disabled={operation.isPending}>{operation.isPending ? '正在保存…' : '保存修正'}</button></div>
  </form>;
}
