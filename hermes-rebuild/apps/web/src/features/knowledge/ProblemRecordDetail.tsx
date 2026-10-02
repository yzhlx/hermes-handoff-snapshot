import { useQuery } from '@tanstack/react-query';
import { request } from '../../shared/api/client';
import type { ProblemResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { AttachmentsPanel } from '../attachments/AttachmentsPanel';

export function ProblemRecordDetail({ userId, problemId, onClose, onCompare, concealAnswer = false }: { userId: string; problemId: string; onClose: () => void; onCompare?: () => void; concealAnswer?: boolean }) {
  const problem = useQuery({
    queryKey: ['problem-detail', problemId],
    queryFn: ({ signal }) => request<ProblemResponse>(`/problems/${problemId}`, { signal }),
  });
  return <section className="panel history-detail" aria-labelledby="problem-record-title">
    <div className="history-heading"><h2 id="problem-record-title">题目记录详情</h2><button className="text-button" onClick={onClose}>收起</button></div>
    {problem.isPending ? <p className="muted" role="status">正在读取题目记录…</p> : problem.isError ? <div><Feedback error={problem.error} /><button className="secondary" onClick={() => void problem.refetch()}>重试</button></div> : <>
      <h3>{problem.data.data.title || '未命名题目'}</h3>
      {onCompare && <button className="secondary" onClick={onCompare}>选择另一题对比 →</button>}
      <dl className="history-detail-list">
        <div><dt>题干</dt><dd>{problem.data.data.statement || '没有保存题干。'}</dd></div>
        <div><dt>正确答案</dt><dd>{concealAnswer ? <details><summary>查看已保存的答案</summary><p>{problem.data.data.correct_answer || '没有保存正确答案。'}</p></details> : problem.data.data.correct_answer || '没有保存正确答案。'}</dd></div>
        {problem.data.data.source_note && <div><dt>来源</dt><dd>{problem.data.data.source_note}</dd></div>}
      </dl>
      <AttachmentsPanel userId={userId} scope={`problem:${problemId}`} problem={problem.data.data} />
      <h3>作答记录</h3>
      {!problem.data.data.attempts?.length ? <p className="muted">这道题还没有作答记录。</p> : <ol className="history-list">{problem.data.data.attempts.map((attempt) => <li key={attempt.id}><div className="history-entry">
        <strong>{attempt.answer_check === 'checked' ? `已核对 · ${attempt.result === 'correct' ? '正确' : attempt.result === 'partial' ? '部分正确' : '错误'}` : '待核对'}</strong>
        <p>{attempt.attempt_text || '没有保存作答过程。'}</p>
        <p className="muted">独立程度：{attempt.independence === 'independent' ? '独立完成' : attempt.independence === 'hinted' ? '有提示' : attempt.independence === 'after_answer' ? '看过答案后' : '未能作答'}{attempt.stuck_note ? ` · 卡点：${attempt.stuck_note}` : ''}</p>
      </div></li>)}</ol>}
    </>}
  </section>;
}
