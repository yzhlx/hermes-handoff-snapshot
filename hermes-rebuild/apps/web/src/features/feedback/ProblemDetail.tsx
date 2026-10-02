import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ApiError, request } from '../../shared/api/client';
import type { CreateAttemptInput, CreateAttemptResponse, ProblemData, ProblemPatchInput, UpdateProblemResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { AttachmentsPanel } from '../attachments/AttachmentsPanel';
import { feedbackDraftFor } from './draft-store';
import { AttemptRecord } from './AttemptCorrection';
import { errorOptions, operationId, optionalText, type ErrorCategory } from './problem-utils';

export function ProblemDetailCapture({ problem, userId, sessionId, attachmentScope }: { problem: ProblemData; userId: string; sessionId: string; attachmentScope?: string }) {
  const attempts = problem.attempts ?? [];
  return <div className="problem-detail">
    <h5>{problem.title || '题目材料'}</h5>
    {problem.statement && <p className="problem-statement">{problem.statement}</p>}
    <AttachmentsPanel userId={userId} scope={attachmentScope ?? `problem:${problem.id}`} problem={problem} />
    <ProblemMetadataEditor key={problem.id} problem={problem} userId={userId} sessionId={sessionId} />
    <p className="muted">已保存 {attempts.length} 次作答；每次尝试都会保留。</p>
    {attempts.length > 0 && <ol className="attempt-history">
      {attempts.map((attempt) => <AttemptRecord key={attempt.id} attempt={attempt} draft={feedbackDraftFor(userId, sessionId)} />)}
    </ol>}
    {problem.archived ? <p className="muted">这道题已归档；可以查看历史与更正记录，恢复后才能追加作答。</p> : <ProblemAttemptCapture key={`${problem.id}:${attempts.length}`} userId={userId} sessionId={sessionId} problemId={problem.id} />}
  </div>;
}

function ProblemMetadataEditor({ problem, userId, sessionId }: { problem: ProblemData; userId: string; sessionId: string }) {
  const queryClient = useQueryClient();
  const draft = feedbackDraftFor(userId, sessionId);
  const pending = draft.problemCorrectionOperations[problem.id];
  const pendingBody = pending?.body;
  const [title, setTitle] = useState(typeof pendingBody?.title === 'string' ? pendingBody.title : problem.title ?? '');
  const [statement, setStatement] = useState(typeof pendingBody?.statement === 'string' ? pendingBody.statement : problem.statement ?? '');
  const [sourceNote, setSourceNote] = useState(typeof pendingBody?.source_note === 'string' ? pendingBody.source_note : problem.source_note ?? '');
  const [answer, setAnswer] = useState(typeof pendingBody?.correct_answer === 'string' ? pendingBody.correct_answer : problem.correct_answer ?? '');
  const [representative, setRepresentative] = useState(typeof pendingBody?.is_representative === 'boolean' ? pendingBody.is_representative : problem.is_representative);
  const [archived, setArchived] = useState(typeof pendingBody?.archived === 'boolean' ? pendingBody.archived : problem.archived);
  const mutation = useMutation({
    mutationFn: async () => {
      const old = draft.problemCorrectionOperations[problem.id];
      if (old?.body && old.path && old.ifMatch) return request<UpdateProblemResponse>(old.path, { method: 'PATCH', headers: { 'Idempotency-Key': old.id, 'If-Match': old.ifMatch }, body: JSON.stringify(old.body) });
      const fingerprint = JSON.stringify({ title: optionalText(title), statement: optionalText(statement), source_note: optionalText(sourceNote), correct_answer: optionalText(answer), is_representative: representative, archived, version: problem.version });
      const id = operationId();
      const body: ProblemPatchInput = { title: optionalText(title), statement: optionalText(statement), source_note: optionalText(sourceNote), correct_answer: optionalText(answer), is_representative: representative, archived, operation_id: id };
      const operation = { id, fingerprint, method: 'PATCH' as const, path: `/problems/${problem.id}`, ifMatch: `"${problem.version}"`, body };
      draft.problemCorrectionOperations[problem.id] = operation;
      return request<UpdateProblemResponse>(operation.path, { method: 'PATCH', headers: { 'Idempotency-Key': operation.id, 'If-Match': operation.ifMatch }, body: JSON.stringify(operation.body) });
    },
    onSuccess: () => { delete draft.problemCorrectionOperations[problem.id]; void queryClient.invalidateQueries({ queryKey: ['problem', problem.id] }); void queryClient.invalidateQueries({ queryKey: ['problems'] }); },
    onError: (error) => { if (error instanceof ApiError && error.status === 409) { delete draft.problemCorrectionOperations[problem.id]; void queryClient.invalidateQueries({ queryKey: ['problem', problem.id] }); } },
  });
  return <details className="problem-metadata-editor"><summary>编辑题目资料与状态</summary><form onSubmit={(event) => { event.preventDefault(); if (!mutation.isPending) mutation.mutate(); }}>
    <label>题目简名<input maxLength={300} value={title} onChange={(event) => setTitle(event.target.value)} /></label>
    <label>题干文字<textarea maxLength={50000} value={statement} onChange={(event) => setStatement(event.target.value)} /></label>
    <label>参考答案<textarea maxLength={50000} value={answer} onChange={(event) => setAnswer(event.target.value)} /></label>
    <label>来源备注<textarea maxLength={10000} value={sourceNote} onChange={(event) => setSourceNote(event.target.value)} /></label>
    <label className="category-option"><input type="checkbox" checked={representative} onChange={(event) => setRepresentative(event.target.checked)} />标记为代表题</label>
    <label className="category-option"><input type="checkbox" checked={archived} onChange={(event) => setArchived(event.target.checked)} />归档此题</label>
    <Feedback error={mutation.error} /><button type="submit" disabled={mutation.isPending}>{mutation.isPending ? '正在保存…' : '保存题目修改'}</button>
  </form></details>;
}


function ProblemAttemptCapture({ userId, sessionId, problemId }: { userId: string; sessionId: string; problemId: string }) {
  const queryClient = useQueryClient();
  const draft = feedbackDraftFor(userId, sessionId);
  const [independence, setIndependence] = useState(draft.independence);
  const [answerCheck, setAnswerCheck] = useState(draft.answerCheck);
  const [result, setResult] = useState(draft.result);
  const [attemptText, setAttemptText] = useState(draft.attemptText);
  const [stuckNote, setStuckNote] = useState(draft.attemptStuckNote);
  const [categories, setCategories] = useState<ErrorCategory[]>(draft.errorCategories as ErrorCategory[]);
  const [otherNote, setOtherNote] = useState(draft.otherErrorNote);
  const [saved, setSaved] = useState(false);
  const createAttempt = useMutation({
    mutationFn: async () => {
      if (answerCheck === 'checked' && !result) throw new Error('已对答案时，请选择正确、部分正确或错误。');
      if (answerCheck === 'pending' && result) throw new Error('暂时没有答案时不能填写结果。');
      if (result === 'correct' && categories.length) throw new Error('完全正确时不能同时标记错误原因。');
      const payload = { problem_id: problemId, session_id: sessionId, independence, answer_check: answerCheck,
        result: answerCheck === 'checked' && result ? result : null, attempt_text: optionalText(attemptText),
        error_categories: categories, other_error_note: optionalText(otherNote), stuck_note: optionalText(stuckNote) };
      const fingerprint = JSON.stringify(payload);
      if (draft.attemptOperation?.fingerprint !== fingerprint) draft.attemptOperation = { fingerprint, id: operationId() };
      const body: CreateAttemptInput = { ...payload, operation_id: draft.attemptOperation.id };
      return request<CreateAttemptResponse>('/problem-attempts', {
        method: 'POST', headers: { 'Idempotency-Key': draft.attemptOperation.id },
        body: JSON.stringify(body),
      });
    },
    onSuccess: () => {
      draft.attemptOperation = null;
      setSaved(true);
      setIndependence('independent'); setAnswerCheck('pending'); setResult(''); setAttemptText(''); setCategories([]); setOtherNote(''); setStuckNote('');
      Object.assign(draft, { independence: 'independent', answerCheck: 'pending', result: '', attemptText: '', errorCategories: [], otherErrorNote: '', attemptStuckNote: '' });
      void queryClient.invalidateQueries({ queryKey: ['problem', problemId] });
    },
  });
  const toggleCategory = (category: ErrorCategory) => {
    const next = categories.includes(category) ? categories.filter((item) => item !== category) : [...categories, category];
    setCategories(next); draft.errorCategories = next;
  };
  return (
    <div className="attempt-capture">
      <h5>记录这次作答</h5>
      <form onSubmit={(event) => { event.preventDefault(); if (!createAttempt.isPending) createAttempt.mutate(); }}>
        <label>独立程度
          <select value={independence} onChange={(event) => { const value = event.target.value as typeof independence; setIndependence(value); draft.independence = value; }}>
            <option value="independent">独立完成</option><option value="hinted">有一些提示</option><option value="after_answer">看过答案以后完成</option><option value="unable">基本不会</option>
          </select>
        </label>
        <label>核对状态
          <select value={answerCheck} onChange={(event) => { const value = event.target.value as typeof answerCheck; setAnswerCheck(value); draft.answerCheck = value; if (value === 'pending') { setResult(''); draft.result = ''; setCategories([]); draft.errorCategories = []; setOtherNote(''); draft.otherErrorNote = ''; } }}>
            <option value="pending">暂时没有答案</option><option value="checked">已经对过答案</option>
          </select>
        </label>
        {answerCheck === 'checked' && <label>核对结果
          <select value={result} onChange={(event) => { const value = event.target.value as typeof result; setResult(value); draft.result = value; if (value === 'correct') { setCategories([]); draft.errorCategories = []; } }}>
            <option value="">请选择</option><option value="correct">正确</option><option value="partial">部分正确</option><option value="incorrect">错误</option>
          </select>
        </label>}
        <label>作答过程（可选）<textarea maxLength={10000} value={attemptText} onChange={(event) => { setAttemptText(event.target.value); draft.attemptText = event.target.value; }} /></label>
        <label>卡住的位置（可选）<textarea maxLength={5000} value={stuckNote} onChange={(event) => { setStuckNote(event.target.value); draft.attemptStuckNote = event.target.value; }} /></label>
        {answerCheck === 'checked' && result !== 'correct' && <fieldset className="error-categories">
          <legend>错误原因（可多选，不确定可不选）</legend>
          {errorOptions.map(([value, label]) => <label key={value} className="category-option"><input type="checkbox" checked={categories.includes(value)} onChange={() => toggleCategory(value)} />{label}</label>)}
          {categories.includes('other') && <label>其他说明<input maxLength={2000} value={otherNote} onChange={(event) => { setOtherNote(event.target.value); draft.otherErrorNote = event.target.value; }} /></label>}
        </fieldset>}
        <Feedback error={createAttempt.error} />
        {saved && <p role="status" className="success-text">这次作答已单独保存，可再次练习并追加新记录。</p>}
        <button type="submit" disabled={createAttempt.isPending}>{createAttempt.isPending ? '正在保存作答…' : '保存这次作答'}</button>
      </form>
    </div>
  );
}
