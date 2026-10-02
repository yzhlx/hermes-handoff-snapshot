import { useState } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { request } from '../../shared/api/client';
import type { LearningMethodsResponse, SessionDetailResponse, SessionHistoryResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { SessionFeedback } from '../feedback';
import { TimeSegmentCorrections } from './TimeSegmentCorrections';

const historyKey = ['learning', 'history'] as const;
const statusLabel: Record<SessionDetailResponse['data']['status'], string> = {
  active: '进行中', paused: '已暂停', ended: '已结束', cancelled: '已取消',
};
function formatTime(value: string, timezone: string) {
  return new Intl.DateTimeFormat('zh-CN', { timeZone: timezone, month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}
function formatDuration(seconds: number) {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const remainingSeconds = safeSeconds % 60;
  return hours > 0 ? `${hours} 小时 ${minutes} 分钟` : minutes > 0 ? `${minutes} 分钟 ${remainingSeconds} 秒` : `${remainingSeconds} 秒`;
}
export function SessionHistory({ userId, initialSelectedSessionId = null, detailOnly = false }: { userId: string; initialSelectedSessionId?: string | null; detailOnly?: boolean }) {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(initialSelectedSessionId);
  const history = useInfiniteQuery({
    enabled: !detailOnly,
    queryKey: historyKey,
    initialPageParam: null as string | null,
    queryFn: async ({ signal, pageParam }) => {
      const cursorQuery = pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : '';
      const response: unknown = await request<SessionHistoryResponse>(
        `/learning-sessions?limit=20${cursorQuery}`,
        { signal },
      );
      if (!response || typeof response !== 'object' || !('data' in response)) {
        throw new Error('学习记录响应格式不正确，尚未显示记录。');
      }
      const data = response.data;
      if (!data || typeof data !== 'object' || !('items' in data) || !Array.isArray(data.items)) {
        throw new Error('学习记录响应格式不正确，尚未显示记录。');
      }
      return response as SessionHistoryResponse;
    },
    getNextPageParam: (lastPage) => lastPage.data.next_cursor ?? undefined,
  });
  const detail = useQuery({
    queryKey: ['learning', 'history-detail', selectedSessionId],
    queryFn: ({ signal }) => request<SessionDetailResponse>(
      `/learning-sessions/${selectedSessionId}`,
      { signal },
    ),
    enabled: Boolean(selectedSessionId),
  });
  const methods = useQuery({
    queryKey: ['learning-methods'],
    queryFn: ({ signal }) => request<LearningMethodsResponse>('/learning-methods', { signal }),
    enabled: Boolean(detail.data?.data.method_id),
  });
  const methodName = detail.data?.data.method_id
    ? methods.data?.data.items.find((item) => item.id === detail.data?.data.method_id)?.title
    : undefined;
  const items = history.data?.pages.flatMap((page) => page.data.items) ?? [];

  return (
    <section className="workspace session-history" aria-labelledby="history-title">
      {!detailOnly && <><header className="history-heading page-head">
        <div>
          <span className="eyebrow">LEARNING RECORDS</span>
          <h1 id="history-title">最近的学习现场</h1>
        </div>
        <button className="text-button" disabled={history.isFetching} onClick={() => void history.refetch()}>
          重新加载
        </button>
      </header>
      {history.isPending ? (
        <p className="muted" role="status">正在读取已保存的学习记录…</p>
      ) : history.isError ? (
        <div>
          <Feedback error={history.error} />
          <button className="secondary" onClick={() => void history.refetch()}>重试</button>
        </div>
      ) : items.length === 0 ? (
        <p className="muted history-empty">保存一段学习后，这里会显示真实的现场记录。</p>
      ) : (
        <ol className="history-list">
          {items.map((item) => (
            <li key={item.id}>
              <span className={`history-marker status-${item.status}`} aria-hidden="true" />
              <div className="history-entry">
                <div className="history-entry-heading">
                  <strong>{item.goal || '自由学习'}</strong>
                  <span>{statusLabel[item.status]}</span>
                </div>
                  <p>{formatTime(item.started_at, item.day_timezone)}</p>
                {item.timing_enabled && (
                  <p className="history-duration">
                    有效计时：{formatDuration(item.effective_duration_seconds)}
                    <span> · 计时不是学习成果或掌握证据</span>
                  </p>
                  )}
                  <button
                    className="history-detail-button"
                    aria-expanded={selectedSessionId === item.id}
                    onClick={() => setSelectedSessionId(item.id)}
                  >
                    查看记录
                  </button>
                </div>
            </li>
          ))}
        </ol>
      )}
      {history.hasNextPage && (
        <button
          className="secondary"
          disabled={history.isFetchingNextPage}
          onClick={() => void history.fetchNextPage()}
        >
          {history.isFetchingNextPage ? '正在加载…' : '加载更早记录'}
        </button>
      )}
      </>}
      {selectedSessionId && (
        <section className="panel history-detail" aria-labelledby="history-detail-title">
          <div className="history-heading">
            <h2 id="history-detail-title">学习现场详情</h2>
            <button className="text-button" onClick={() => setSelectedSessionId(null)}>收起</button>
          </div>
          {detail.isPending ? (
            <p role="status" className="muted">正在读取这条记录…</p>
          ) : detail.isError ? (
            <div><Feedback error={detail.error} /><button className="secondary" onClick={() => void detail.refetch()}>重试</button></div>
          ) : (
            <>
            <dl className="history-detail-list">
              <div><dt>学习内容</dt><dd>{detail.data.data.goal || '自由学习'}</dd></div>
              <div><dt>状态</dt><dd>{statusLabel[detail.data.data.status]}</dd></div>
              {detail.data.data.resume_note && <div><dt>下次继续</dt><dd>{detail.data.data.resume_note}</dd></div>}
              <div><dt>学习日期</dt><dd>{detail.data.data.learning_date}（{detail.data.data.day_timezone}）</dd></div>
              <div><dt>开始时间</dt><dd>{formatTime(detail.data.data.started_at, detail.data.data.day_timezone)}</dd></div>
              {detail.data.data.ended_at && (
                <div><dt>结束时间</dt><dd>{formatTime(detail.data.data.ended_at, detail.data.data.day_timezone)}</dd></div>
              )}
              {detail.data.data.method_id && (
                <div><dt>学习方法</dt><dd>{methodName ?? '方法信息暂不可用'}</dd></div>
              )}
              {detail.data.data.timing_enabled ? (
                <div>
                  <dt>有效计时</dt>
                  <dd>{formatDuration(detail.data.data.effective_duration_seconds)} · 不代表学习成果或掌握</dd>
                </div>
              ) : <div><dt>计时</dt><dd>本次未启用计时</dd></div>}
            </dl>
            {detail.data.data.timing_enabled && (
              <TimeSegmentCorrections session={detail.data.data} onCorrected={() => void detail.refetch()} />
            )}
            {detail.data.data.status === 'ended' && (
              <SessionFeedback userId={userId} sessionId={detail.data.data.id} subjectId={detail.data.data.subject_id} />
            )}
            </>
          )}
        </section>
      )}
    </section>
  );
}
