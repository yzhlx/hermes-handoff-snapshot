import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { request } from '../../shared/api/client';
import type { CreateProblemInput, CreateProblemResponse, ProblemResponse, ProblemsResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { feedbackDraftFor } from './draft-store';
import { ReflectionEditor } from './ReflectionEditor';
import { ProblemDetailCapture } from './ProblemDetail';
import { AttachmentsPanel, type AttachmentQueueState } from '../attachments/AttachmentsPanel';
import { attachmentDraftFor, consumeReadyAttachmentDrafts } from '../attachments/draft-store';
import { operationId, optionalText } from './problem-utils';
import './feedback.css';

export function SessionFeedback({ userId, sessionId, subjectId }: {
  userId: string; sessionId: string; subjectId: string | null;
}) {
  const queryClient = useQueryClient();
  const draft = feedbackDraftFor(userId, sessionId);
  const [problemTitle, setProblemTitle] = useState(draft.problemTitle);
  const [problemStatement, setProblemStatement] = useState(draft.problemStatement);
  const [problemId, setProblemId] = useState<string | null>(draft.problemId);
  const [attachmentQueue, setAttachmentQueue] = useState<AttachmentQueueState>({ readyLinks: [], incompleteCount: 0, readyQuestion: false });
  const [showArchived, setShowArchived] = useState(false);
  const problems = useQuery({
    queryKey: ['problems', subjectId ?? 'all', showArchived],
    queryFn: ({ signal }) => request<ProblemsResponse>(
      `/problems?limit=50${showArchived ? '&archived=true' : ''}${subjectId ? `&subject_id=${encodeURIComponent(subjectId)}` : ''}`, { signal },
    ),
  });
  const selectedProblem = useQuery({
    queryKey: ['problem', problemId],
    queryFn: ({ signal }) => request<ProblemResponse>(`/problems/${problemId}`, { signal }),
    enabled: Boolean(problemId),
  });
  const problemItems = Array.isArray(problems.data?.data?.items) ? problems.data.data.items : [];

  const createProblem = useMutation({
    mutationFn: async () => {
      if (attachmentQueue.incompleteCount > 0) throw new Error('请先完成每个附件的上传和校验，或移除未完成项，再保存题目。');
      const attachmentLinks = attachmentQueue.readyLinks;
      const payload = { title: optionalText(problemTitle), statement: optionalText(problemStatement), subject_id: subjectId, attachment_links: attachmentLinks };
      if (!payload.statement && !attachmentLinks.some((link) => link.role === 'question')) throw new Error('请填写题干文字，或先上传并校验一个题目附件。');
      const fingerprint = JSON.stringify(payload);
      if (draft.problemOperation?.fingerprint !== fingerprint) draft.problemOperation = { fingerprint, id: operationId() };
      const body: CreateProblemInput = { ...payload, source_note: null, operation_id: draft.problemOperation.id };
      return request<CreateProblemResponse>('/problems', {
        method: 'POST', headers: { 'Idempotency-Key': draft.problemOperation.id },
        body: JSON.stringify(body),
      });
    },
    onSuccess: (response) => {
      setProblemId(response.data.id);
      consumeReadyAttachmentDrafts(attachmentDraftFor(userId, `feedback:${sessionId}`));
      draft.problemId = response.data.id;
      draft.problemOperation = null;
      setProblemTitle(response.data.title ?? '');
      setProblemStatement(response.data.statement ?? '');
      draft.problemTitle = response.data.title ?? '';
      draft.problemStatement = response.data.statement ?? '';
      void queryClient.invalidateQueries({ queryKey: ['problems'] });
    },
  });

  return (
    <section className="panel session-feedback" aria-labelledby={`feedback-title-${sessionId}`}>
      <div className="feedback-flow">
        <div className="feedback-step">
          <div className="section-label"><span className="dot" />本次反馈 · 可补充</div>
          <h3 id={`feedback-title-${sessionId}`}>留下一点真实现场</h3>
          <ReflectionEditor userId={userId} sessionId={sessionId} />
        </div>
        <div className="feedback-step problem-capture">
          <h4>记录本次做过的题</h4>
          <p className="muted">可以输入题干文字，也可以仅上传题目附件。附件通过校验后才会和题目一起保存。</p>
          <form onSubmit={(event) => { event.preventDefault(); if (!createProblem.isPending) createProblem.mutate(); }}>
            <label>题目简名（可选）<input maxLength={300} value={problemTitle} disabled={Boolean(problemId)} onChange={(event) => { setProblemTitle(event.target.value); draft.problemTitle = event.target.value; }} /></label>
            <label>题干文字（可选）<textarea maxLength={50000} value={problemStatement} disabled={Boolean(problemId)} onChange={(event) => { setProblemStatement(event.target.value); draft.problemStatement = event.target.value; }} /></label>
            {!problemId && <AttachmentsPanel userId={userId} scope={`feedback:${sessionId}`} onQueueStateChange={setAttachmentQueue} />}
            <div className="problem-capture__actions">
              {!problemStatement.trim() && !attachmentQueue.readyQuestion && <p className="muted" role="status">题干文字或已校验的题目附件至少填写一种。</p>}
              {attachmentQueue.incompleteCount > 0 && <p className="muted" role="status">请先完成每个附件的上传和校验，或移除未完成项，再保存题目。</p>}
              <Feedback error={createProblem.error} />
              <button type="submit" disabled={createProblem.isPending || Boolean(problemId) || attachmentQueue.incompleteCount > 0 || (!problemStatement.trim() && !attachmentQueue.readyQuestion)}>{createProblem.isPending ? '正在保存题目…' : problemId ? '题目已保存' : '保存题目'}</button>
            </div>
          </form>
          {problems.isError && <Feedback error={problems.error} />}
          <label className="category-option"><input type="checkbox" checked={showArchived} onChange={(event) => { setShowArchived(event.target.checked); setProblemId(null); draft.problemId = null; }} />查看归档题目</label>
          {problemItems.length ? (
            <label>选择已有题目继续练习
              <select value={problemId ?? ''} onChange={(event) => { const id = event.target.value || null; setProblemId(id); draft.problemId = id; }}>
                <option value="">选择题目</option>
                {problemItems.map((item) => <option key={item.id} value={item.id}>{item.title || item.statement?.slice(0, 60) || '未命名题目'}</option>)}
              </select>
            </label>
          ) : null}
          {problemId && selectedProblem.data?.data && (
            <ProblemDetailCapture key={problemId} problem={selectedProblem.data.data} userId={userId} sessionId={sessionId} attachmentScope={`feedback:${sessionId}`} />
          )}
        </div>
      </div>
    </section>
  );
}
