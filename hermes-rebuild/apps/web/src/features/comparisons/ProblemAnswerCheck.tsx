import { useQuery } from '@tanstack/react-query';
import { request } from '../../shared/api/client';
import type { ProblemResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { AttemptRecord } from '../feedback/AttemptCorrection';
import { feedbackDraftFor } from '../feedback/draft-store';

/**
 * Read the selected problem's original materials and let the owner verify or
 * correct a saved attempt without leaving the comparison workspace.
 *
 * This is a real correction surface: it reuses the shared, versioned and
 * idempotent attempt PATCH. It never creates a new attempt (that needs a
 * learning session) and never changes the problem, the representative flag or
 * any mastery state.
 */
export function ProblemAnswerCheck({ userId, problemId, onClose }: { userId: string; problemId: string; onClose: () => void }) {
  const problem = useQuery({
    queryKey: ['problem-detail', problemId],
    queryFn: ({ signal }) => request<ProblemResponse>(`/problems/${encodeURIComponent(problemId)}`, { signal }),
  });
  const draft = feedbackDraftFor(userId, `comparison-check:${problemId}`);
  const data = problem.data?.data;
  const attempts = data?.attempts ?? [];
  return <section className="panel comparison-answer-check" aria-labelledby="comparison-answer-check-title">
    <div className="comparison-page-heading">
      <div>
        <span className="eyebrow">VERIFY ORIGINAL ATTEMPT</span>
        <h2 id="comparison-answer-check-title">核对原作答</h2>
        <p className="muted">核对或更正这道题的作答记录。修改只作用于该次作答，不会改动题目、代表题标记或比较结论。</p>
      </div>
      <button type="button" className="text-button" onClick={onClose}>返回对比</button>
    </div>
    {problem.isPending ? <p className="muted" role="status">正在读取题目记录…</p>
      : problem.isError ? <div><Feedback error={problem.error} /><button type="button" className="secondary" onClick={() => void problem.refetch()}>重试</button></div>
        : !data ? <p className="muted">没有找到这道题。</p> : <>
          <h3>{data.title || '未命名题目'}</h3>
          <dl className="history-detail-list">
            <div><dt>题干</dt><dd>{data.statement || '没有保存题干。'}</dd></div>
            {/* Verification happens before the answer is confirmed: conceal it behind an explicit disclosure. */}
            <div><dt>正确答案</dt><dd><details><summary>查看已保存的答案</summary><p>{data.correct_answer || '没有保存正确答案。'}</p></details></dd></div>
            {data.source_note && <div><dt>来源</dt><dd>{data.source_note}</dd></div>}
          </dl>
          <h3>作答记录</h3>
          {!attempts.length
            ? <p className="muted">这道题还没有作答记录，因此没有可核对的作答。可返回对比页从这道题开始一轮练习。</p>
            : <ol className="attempt-history">{attempts.map((attempt) => <AttemptRecord key={attempt.id} attempt={attempt} draft={draft} />)}</ol>}
        </>}
  </section>;
}
