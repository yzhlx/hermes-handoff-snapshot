import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { ApiError, request } from '../../shared/api/client';
import type { ProblemData, ProblemKnowledgeLinksInput, ProblemKnowledgeLinksResponse, ProblemsResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { clearKnowledgeCommand, runKnowledgeCommand } from './draft-store';

const uuid = () => crypto.randomUUID();

export function ProblemKnowledgeLinks({ userId, subjectId, pointId, canAssociate }: { userId: string; subjectId: string; pointId: string; canAssociate: boolean }) {
  const problems = useInfiniteQuery({
    queryKey: ['subject-problems', subjectId], initialPageParam: null as string | null,
    queryFn: ({ signal, pageParam }) => request<ProblemsResponse>(`/problems?subject_id=${subjectId}&archived=false&limit=20${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ''}`, { signal }),
    getNextPageParam: (page) => page.data.next_cursor ?? undefined,
  });
  const allProblems = problems.data?.pages.flatMap((page) => page.data.items) ?? [];
  const linked = allProblems.filter((problem) => (problem.knowledge_point_ids ?? []).includes(pointId));
  const candidates = allProblems.filter((problem) => !(problem.knowledge_point_ids ?? []).includes(pointId));
  return <section className="problem-knowledge-links" aria-labelledby={`linked-problems-${pointId}`}>
    <h3 id={`linked-problems-${pointId}`}>关联题目</h3>
    <p className="muted">关联表示这道题涉及此知识点，不代表答对或已经掌握。</p>
    {!canAssociate && <p className="muted">知识点或所属章节已归档；可以查看或解除现有关系，恢复后才能新建关联。</p>}
    {problems.isPending ? <p role="status" className="muted">正在读取本学科题目…</p> : problems.isError ? <div><Feedback error={problems.error} /><button className="secondary" onClick={() => void problems.refetch()}>重试</button></div> : allProblems.length === 0 ? <p className="muted">本学科还没有已保存题目。可以在学习结束反馈中先记录文字题目。</p> : <>
      {linked.length > 0 && <ul>{linked.map((problem) => <li key={problem.id}><ProblemLinkRow userId={userId} pointId={pointId} problem={problem} linked /></li>)}</ul>}
      {candidates.length > 0 && <ul>{candidates.map((problem) => <li key={problem.id}><ProblemLinkRow userId={userId} pointId={pointId} problem={problem} linked={false} canAssociate={canAssociate} /></li>)}</ul>}
      {problems.hasNextPage && <button className="secondary" disabled={problems.isFetchingNextPage} onClick={() => void problems.fetchNextPage()}>{problems.isFetchingNextPage ? '正在加载题目…' : '加载更多题目'}</button>}
    </>}
  </section>;
}

function ProblemLinkRow({ userId, pointId, problem, linked, canAssociate = true }: { userId: string; pointId: string; problem: ProblemData; linked: boolean; canAssociate?: boolean }) {
  const client = useQueryClient();
  const [checked, setChecked] = useState(linked);
  const key = `problem-link:${problem.id}:${pointId}`;
  const mutation = useMutation({
    mutationFn: () => {
      const currentIds = problem.knowledge_point_ids ?? [];
      const knowledgePointIds = checked
        ? [...new Set([...currentIds, pointId])]
        : currentIds.filter((id) => id !== pointId);
      const operationId = uuid();
      const body: ProblemKnowledgeLinksInput = { operation_id: operationId, knowledge_point_ids: knowledgePointIds };
      return runKnowledgeCommand<ProblemKnowledgeLinksResponse>(userId, key, 'PUT', `/problems/${problem.id}/knowledge-links`, body, `"${problem.version}"`);
    },
    onSuccess: () => { clearKnowledgeCommand(userId, key); void client.invalidateQueries({ queryKey: ['subject-problems', problem.subject_id] }); void client.invalidateQueries({ queryKey: ['knowledge-evidence', pointId] }); },
    onError: (error) => { if (error instanceof ApiError && error.status === 409) { clearKnowledgeCommand(userId, key); void client.invalidateQueries({ queryKey: ['subject-problems', problem.subject_id] }); } },
  });
  const title = problem.title || problem.statement?.slice(0, 72) || '未命名题目';
  return <div className="problem-link-row">
    <label><input type="checkbox" checked={checked} disabled={mutation.isPending || problem.archived || (!canAssociate && !linked)} onChange={(event) => setChecked(event.target.checked)} />{title}{problem.is_representative && <span className="muted"> · 代表题</span>}</label>
    <Feedback error={mutation.error} />
    {mutation.error && <button type="button" className="text-button" onClick={() => { clearKnowledgeCommand(userId, key); mutation.reset(); }}>取消本次保存重试</button>}
    {checked !== linked && <button className="secondary" disabled={mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? '正在更新关联…' : checked ? '关联到此知识点' : '解除此知识点关联'}</button>}
  </div>;
}
