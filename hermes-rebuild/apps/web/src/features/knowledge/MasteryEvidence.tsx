import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { components } from '../../../../../packages/contracts/src/schema';
import { ApiError, request } from '../../shared/api/client';
import type { CreateMasteryAssessmentInput, CreateMasteryAssessmentResponse, KnowledgePointEvidenceResponse, ProblemAttemptResponse, ProblemResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { errorCategoryLabels } from '../../shared/ui/labels';
import { clearKnowledgeCommand, knowledgeFormFor, runKnowledgeCommand } from './draft-store';

type Level = components['schemas']['MasteryLevel'];
const uuid = () => crypto.randomUUID();
const levels: { value: Level; label: string; explanation: string }[] = [
  { value: 'unfamiliar', label: '陌生', explanation: '目前还不熟悉这个内容。' },
  { value: 'encountered', label: '接触过', explanation: '见过或读过，但还不一定能独立完成。' },
  { value: 'typical', label: '典型题可完成', explanation: '常见题型能完成，仍可能需要提示或核对。' },
  { value: 'independent', label: '可以独立完成', explanation: '由你声明目前可以独立完成。' },
  { value: 'variant_stable', label: '变式比较稳定', explanation: '由你声明变式下也较稳定；请说明变化。' },
];
const statusLabel = { unsupported: '暂无已核证据', current: '来源仍匹配', stale: '来源后来有变化' } as const;
const independenceLabels: Record<components['schemas']['Independence'], string> = { independent: '独立完成', hinted: '有一些提示', after_answer: '看过答案后完成', unable: '基本不会' };
const resultLabels: Record<string, string> = { correct: '正确', partial: '部分正确', incorrect: '错误' };

export function MasteryEvidence({ userId, pointId, pointVersion }: { userId: string; pointId: string; pointVersion: number }) {
  const client = useQueryClient();
  const evidence = useQuery({ queryKey: ['knowledge-evidence', pointId], queryFn: ({ signal }) => request<KnowledgePointEvidenceResponse>(`/knowledge-points/${pointId}/evidence`, { signal }) });
  const draft = knowledgeFormFor(userId, `mastery:${pointId}`, { level: '', reason: '', variantNote: '', evidenceAttemptIds: [] });
  const [level, setLevel] = useState(String(draft.level ?? ''));
  const [reason, setReason] = useState(String(draft.reason ?? ''));
  const [variantNote, setVariantNote] = useState(String(draft.variantNote ?? ''));
  const [selectedIds, setSelectedIds] = useState<string[]>(Array.isArray(draft.evidenceAttemptIds) ? draft.evidenceAttemptIds.filter((id): id is string => typeof id === 'string') : []);
  const [openedSource, setOpenedSource] = useState<{ attemptId: string; problemId: string } | null>(null);
  const [conflict, setConflict] = useState(false);
  const operationKey = `mastery:${pointId}`;
  const submit = useMutation({
    mutationFn: () => {
      if (!levels.some((item) => item.value === level)) throw new Error('请选择一个自评等级。');
      if (level === 'variant_stable' && selectedIds.length > 0 && !variantNote.trim()) throw new Error('关联变式证据时，请说明具体变化。');
      const operationId = uuid();
      const body: CreateMasteryAssessmentInput = { operation_id: operationId, knowledge_point_id: pointId, level: level as Level, reason: reason.trim() || null, variant_note: variantNote.trim() || null, evidence_attempt_ids: selectedIds };
      return runKnowledgeCommand<CreateMasteryAssessmentResponse>(userId, operationKey, 'POST', '/mastery-assessments', body, `"${pointVersion}"`);
    },
    onSuccess: () => { clearKnowledgeCommand(userId, operationKey); setConflict(false); setLevel(''); setReason(''); setVariantNote(''); setSelectedIds([]); Object.assign(draft, { level: '', reason: '', variantNote: '', evidenceAttemptIds: [] }); void client.invalidateQueries({ queryKey: ['knowledge-evidence', pointId] }); void client.invalidateQueries({ queryKey: ['knowledge-point', pointId] }); },
    onError: (error) => { if (error instanceof ApiError && error.status === 409) { clearKnowledgeCommand(userId, operationKey); setConflict(true); void client.invalidateQueries({ queryKey: ['knowledge-point', pointId] }); void client.invalidateQueries({ queryKey: ['knowledge-evidence', pointId] }); } },
  });
  const counts = evidence.data?.data.counts;
  const refs = evidence.data?.data.source_refs ?? [];
  const recordedErrorCategories = evidence.data?.data.error_categories.filter((item) => item.attempt_count > 0) ?? [];
  const selectedLevel = levels.find((item) => item.value === level);

  return <section className="mastery-evidence" aria-labelledby={`mastery-title-${pointId}`}>
    <header><span className="eyebrow">USER SELF-ASSESSMENT</span><h3 id={`mastery-title-${pointId}`}>掌握自评与可追溯记录</h3></header>
    {evidence.isPending ? <p className="muted" role="status">正在读取实际作答和自评历史…</p> : evidence.isError ? <div><Feedback error={evidence.error} /><button className="secondary" onClick={() => void evidence.refetch()}>重试读取依据</button></div> : <>
      <p className="muted">当前状态：{evidence.data.data.assessments[0] ? levels.find((item) => item.value === evidence.data.data.assessments[0].level)?.label : '未设置'}。状态由你的自评记录决定，不会根据计时或题目数量自动升级。</p>
      {counts!.attempt_count > 0 && <div className="evidence-count-grid">
        <EvidenceCount label="关联作答" value={counts!.attempt_count} />
        <EvidenceCount label="待核对" value={counts!.pending_count} />
        <EvidenceCount label="已核对" value={counts!.checked_count} />
        <EvidenceCount label="已核对正确" value={counts!.checked_correct_count} />
        <EvidenceCount label="独立且核对正确" value={counts!.independent_correct_count} />
        <EvidenceCount label="已核对正确比例" value={counts!.checked_correct_rate === null ? '暂无已核对记录' : `${Math.round(counts!.checked_correct_rate * 100)}%`} />
      </div>}
      <div className="evidence-streak"><strong>{evidence.data.data.recent_checked_streak.label}</strong><span>另有 {evidence.data.data.recent_checked_streak.pending_count} 次待核对；待核对记录不进入这个已核对序列。</span></div>
      <div className="evidence-errors"><h4>已记录的错误原因</h4>{recordedErrorCategories.length === 0 ? <p className="muted">暂无已记录的错误原因。</p> : <>
        <ul>{recordedErrorCategories.slice(0, 3).map((item) => <li key={item.category}>{errorCategoryLabels[item.category]}：{item.attempt_count} 次</li>)}</ul>
        {recordedErrorCategories.length > 3 && <details><summary>查看其余 {recordedErrorCategories.length - 3} 类</summary><ul>{recordedErrorCategories.slice(3).map((item) => <li key={item.category}>{errorCategoryLabels[item.category]}：{item.attempt_count} 次</li>)}</ul></details>}
      </>}</div>
      <h4>作答来源</h4>
      {refs.length === 0 ? <p className="muted">暂无可追溯的作答记录。</p> : <ul className="evidence-source-list">{refs.map((ref) => <li key={`${ref.attempt_id}:${ref.attempt_version}`}><button className="text-button" onClick={() => setOpenedSource({ attemptId: ref.attempt_id, problemId: ref.problem_id })}>打开原题与这次作答 →</button><span>记录版本 {ref.attempt_version} · 题目版本 {ref.problem_version}</span></li>)}</ul>}
      <h4>你的自评历史</h4>
      {evidence.data.data.assessments.length === 0 ? <p className="muted">未设置。你可以自评，也可以先积累真实作答记录。</p> : <ol className="assessment-history">{evidence.data.data.assessments.map((assessment) => <li key={assessment.id}>
        <div className="assessment-heading"><strong>{levels.find((item) => item.value === assessment.level)?.label ?? assessment.level}</strong><span className={`evidence-status status-${assessment.evidence_status}`}>{statusLabel[assessment.evidence_status]}</span></div>
        <p>{assessment.evidence_message}</p>{assessment.reason && <p>自评说明：{assessment.reason}</p>}{assessment.variant_note && <p>你记录的变式：{assessment.variant_note}</p>}
        <span className="muted">{new Date(assessment.created_at).toLocaleString('zh-CN')} · 来自知识点版本 {assessment.knowledge_point_version}</span>
        {assessment.source_refs.map((ref) => <button key={ref.attempt_id} className="text-button" onClick={() => setOpenedSource({ attemptId: ref.attempt_id, problemId: ref.problem_id })}>查看来源作答</button>)}
      </li>)}</ol>}
      <form className="mastery-form" onSubmit={(event) => { event.preventDefault(); if (!submit.isPending) submit.mutate(); }}>
        <h4>记录一条新的自评</h4>
        <label>掌握参考状态<select value={level} onChange={(event) => { setLevel(event.target.value); draft.level = event.target.value; }}><option value="">未设置</option>{levels.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select></label>
        {selectedLevel && <p className="muted">{selectedLevel.explanation}</p>}
        <label>自评理由（可选）<textarea maxLength={2000} value={reason} onChange={(event) => { setReason(event.target.value); draft.reason = event.target.value; }} /></label>
        <label>变式/条件变化说明（可选）<textarea maxLength={2000} value={variantNote} onChange={(event) => { setVariantNote(event.target.value); draft.variantNote = event.target.value; }} /></label>
        <fieldset className="evidence-choices"><legend>关联真实作答（可选）</legend>{refs.length === 0 ? <p className="muted">还没有可选作答记录；没有证据时也可以明确保存为自评。</p> : refs.map((ref) => <label key={ref.attempt_id}><input type="checkbox" checked={selectedIds.includes(ref.attempt_id)} onChange={() => setSelectedIds((old) => { const next = old.includes(ref.attempt_id) ? old.filter((id) => id !== ref.attempt_id) : [...old, ref.attempt_id]; draft.evidenceAttemptIds = next; return next; })} />题目 {ref.problem_id.slice(0, 8)} · 作答 {ref.attempt_id.slice(0, 8)}</label>)}</fieldset>
        {conflict && <p className="muted" role="status">知识点已在其他窗口更新。已重新读取当前版本，输入仍保留；检查后可再次保存。</p>}
        <Feedback error={submit.error} />
        {submit.error && <button type="button" className="text-button" onClick={() => { clearKnowledgeCommand(userId, operationKey); submit.reset(); }}>放弃本次保存命令</button>}
        <button disabled={submit.isPending || !level}>{submit.isPending ? '正在保存自评…' : '保存这条自评'}</button>
      </form>
    </>}
    {openedSource && <EvidenceSourceDialog attemptId={openedSource.attemptId} problemId={openedSource.problemId} onClose={() => setOpenedSource(null)} />}
  </section>;
}

function EvidenceCount({ label, value }: { label: string; value: number | string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function EvidenceSourceDialog({ attemptId, problemId, onClose }: { attemptId: string; problemId: string; onClose: () => void }) {
  const attempt = useQuery({ queryKey: ['problem-attempt', attemptId], queryFn: ({ signal }) => request<ProblemAttemptResponse>(`/problem-attempts/${attemptId}`, { signal }) });
  const problem = useQuery({ queryKey: ['problem', problemId], queryFn: ({ signal }) => request<ProblemResponse>(`/problems/${problemId}`, { signal }) });
  return <dialog className="evidence-source-dialog" open aria-labelledby="evidence-source-title">
    <div className="evidence-source-heading"><h4 id="evidence-source-title">实际题目与作答来源</h4><button className="text-button" onClick={onClose}>关闭</button></div>
    {attempt.isPending || problem.isPending ? <p role="status" className="muted">正在读取原始记录…</p> : attempt.isError || problem.isError ? <div><Feedback error={attempt.error ?? problem.error} /><button className="secondary" onClick={() => { void attempt.refetch(); void problem.refetch(); }}>重试</button></div> : <>
      <h5>{problem.data.data.title || '未命名题目'}</h5><p className="problem-statement">{problem.data.data.statement || '未保存题干文字。'}</p>
      <p>独立程度：{independenceLabels[attempt.data.data.independence]} · 核对状态：{attempt.data.data.answer_check === 'checked' ? '已核对' : '待核对'}</p>
      {attempt.data.data.result && <p>核对结果：{resultLabels[attempt.data.data.result]}</p>}
      {attempt.data.data.attempt_text && <p className="problem-statement">作答过程：{attempt.data.data.attempt_text}</p>}
      {attempt.data.data.stuck_note && <p className="problem-statement">卡点：{attempt.data.data.stuck_note}</p>}
    </>}
  </dialog>;
}
