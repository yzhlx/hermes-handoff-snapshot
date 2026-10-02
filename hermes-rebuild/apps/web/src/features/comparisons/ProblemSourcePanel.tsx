import { useQuery } from '@tanstack/react-query';
import { request } from '../../shared/api/client';
import type { ProblemResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { AttachmentsPanel } from '../attachments/AttachmentsPanel';

export function ProblemSourcePanel({ userId, problemId, attemptId, onAttemptChange, label }: {
  userId: string;
  problemId: string;
  attemptId: string | null;
  onAttemptChange?: (attemptId: string | null) => void;
  label: string;
}) {
  const problem = useQuery({
    queryKey: ['problem-detail', userId, problemId],
    queryFn: ({ signal }) => request<ProblemResponse>(`/problems/${encodeURIComponent(problemId)}`, { signal }),
  });
  const data = problem.data?.data;
  const attempt = data?.attempts?.find((item) => item.id === attemptId) ?? null;

  return <section className="comparison-source" aria-label={`${label}原题材料`}>
    <header><span className="eyebrow">{label}</span><h3>{data?.title || '题目材料'}</h3></header>
    {problem.isPending ? <p className="muted" role="status">正在读取原题材料…</p> : problem.isError ? <div><Feedback error={problem.error} /><button className="secondary" type="button" onClick={() => void problem.refetch()}>重试读取材料</button></div> : data ? <>
      <dl className="comparison-source-facts">
        <div><dt>题干</dt><dd>{data.statement || '没有保存题干。'}</dd></div>
        <div><dt>正确答案</dt><dd>{data.correct_answer || '没有保存正确答案。'}</dd></div>
        {data.source_note && <div><dt>来源</dt><dd>{data.source_note}</dd></div>}
      </dl>
      {onAttemptChange && <label>关联一次原作答（可选）
        <select value={attemptId ?? ''} onChange={(event) => onAttemptChange(event.target.value || null)}>
          <option value="">不关联作答</option>
          {data.attempts?.map((item) => <option key={item.id} value={item.id}>{formatAttempt(item)}</option>)}
        </select>
      </label>}
      {attemptId && <div className="comparison-attempt">
        {!attempt ? <p className="muted">所关联的作答当前无法读取。重新载入题目材料可再次检查。</p> : <>
          <strong>原作答 · {attempt.answer_check === 'checked' ? `已核对：${resultLabel(attempt.result)}` : '待核对'}</strong>
          <p>{attempt.attempt_text || '没有保存作答过程。'}</p>
          <p className="muted">独立程度：{independenceLabel(attempt.independence)}{attempt.stuck_note ? ` · 卡点：${attempt.stuck_note}` : ''}</p>
        </>}
      </div>}
      <AttachmentsPanel userId={userId} scope={`problem:${problemId}`} problem={data} readOnly />
    </> : null}
  </section>;
}

function formatAttempt(attempt: NonNullable<ProblemResponse['data']['attempts']>[number]) {
  const result = attempt.answer_check === 'checked' ? `已核对 · ${resultLabel(attempt.result)}` : '待核对';
  const text = attempt.attempt_text?.trim().slice(0, 46);
  return `${result}${text ? ` · ${text}` : ''}`;
}

function resultLabel(result: string | null | undefined) {
  return result === 'correct' ? '正确' : result === 'partial' ? '部分正确' : result === 'incorrect' ? '错误' : '未记录';
}

function independenceLabel(value: string) {
  return value === 'independent' ? '独立完成' : value === 'hinted' ? '有提示' : value === 'after_answer' ? '看过答案后' : '未能作答';
}
