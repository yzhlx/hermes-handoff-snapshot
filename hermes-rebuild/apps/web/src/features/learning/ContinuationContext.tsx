import { useQuery } from '@tanstack/react-query';
import { ApiError, request } from '../../shared/api/client';
import type { ReflectionResponse, SessionDetailResponse } from '../../shared/api/types';
import './continuation.css';

/** Read the original facts through the saved link; never copy them into new feedback. */
export function ContinuationContext({ userId, previousSessionId, resumeNote }: {
  userId: string; previousSessionId: string; resumeNote: string | null;
}) {
  const source = useQuery({
    queryKey: ['continuation-source', userId, previousSessionId],
    queryFn: ({ signal }) => request<SessionDetailResponse>(`/learning-sessions/${encodeURIComponent(previousSessionId)}`, { signal }),
  });
  const reflection = useQuery({
    queryKey: ['session-reflection', userId, previousSessionId],
    queryFn: async ({ signal }) => {
      try { return await request<ReflectionResponse>(`/session-reflections/${encodeURIComponent(previousSessionId)}`, { signal }); }
      catch (error) { if (error instanceof ApiError && error.status === 404) return null; throw error; }
    },
  });
  const failed = source.isError || reflection.isError;
  return <aside className="continuation-context" aria-label="上次留下的现场">
    <h3>上次留下的现场</h3>
    {source.data?.data.goal && <p>原主题：{source.data.data.goal}</p>}
    {reflection.data?.data.stuck_note && <p>上次留下的问题：{reflection.data.data.stuck_note}</p>}
    {resumeNote && <p>继续位置：{resumeNote}</p>}
    {(source.isPending || reflection.isPending) && <p role="status">正在读取上次保存的内容…</p>}
    {failed && <><p role="status">上次现场暂未完整读取，当前学习仍可继续。</p><button className="secondary" onClick={() => { void source.refetch(); void reflection.refetch(); }}>重读上次现场</button></>}
  </aside>;
}
