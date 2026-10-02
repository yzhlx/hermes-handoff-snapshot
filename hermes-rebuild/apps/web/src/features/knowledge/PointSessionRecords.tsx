import { useInfiniteQuery } from '@tanstack/react-query';
import { request } from '../../shared/api/client';
import type { SessionHistoryResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';

export function PointSessionRecords({ pointId, onOpenSession }: { pointId: string; onOpenSession: (sessionId: string) => void }) {
  const sessions = useInfiniteQuery({
    queryKey: ['sessions-for-knowledge-point', pointId], initialPageParam: null as string | null,
    queryFn: ({ signal, pageParam }) => request<SessionHistoryResponse>(`/learning-sessions?limit=20${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ''}`, { signal }),
    getNextPageParam: (page) => page.data.next_cursor ?? undefined,
  });
  const matching = sessions.data?.pages.flatMap((page) => page.data.items).filter((session) => session.knowledge_point_id === pointId) ?? [];
  return <section className="point-session-records" aria-labelledby={`point-sessions-${pointId}`}>
    <h3 id={`point-sessions-${pointId}`}>关联学习现场</h3>
    {sessions.isPending ? <p className="muted" role="status">正在读取与此知识点关联的真实学习现场…</p> : sessions.isError ? <div><Feedback error={sessions.error} /><button className="secondary" onClick={() => void sessions.refetch()}>重试</button></div> : matching.length === 0 ? <p className="muted">已读取的学习现场中暂未找到关联记录。</p> : <ul>{matching.map((session) => <li key={session.id}><button className="text-button" onClick={() => onOpenSession(session.id)}>{session.goal || '自由学习'} · {session.status === 'ended' ? '已结束' : session.status === 'paused' ? '已暂停' : session.status === 'cancelled' ? '已取消' : '进行中'} →</button></li>)}</ul>}
    {sessions.hasNextPage && <button className="secondary" disabled={sessions.isFetchingNextPage} onClick={() => void sessions.fetchNextPage()}>{sessions.isFetchingNextPage ? '正在加载…' : '查找更早的关联学习现场'}</button>}
  </section>;
}
