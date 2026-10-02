import { useEffect, useMemo, useState } from 'react';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, request } from '../../shared/api/client';
import type { SuggestionActionInput, SuggestionData, SuggestionPageResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { reviewCommandFor, selectReviewOwner, setReviewCommand } from './draft-store';
import './review-records.css';

const labels: Record<SuggestionData['kind'], string> = { continue: '继续学习', unverified: '待核对', review: '可以复习', repeated_error: '反复出现的错误' };
const statuses: Record<SuggestionData['status'], string> = { available: '可查看', accepted: '已接受', snoozed: '稍后', dismissed: '已忽略', stale: '来源已变化' };
const newId = () => crypto.randomUUID();
function refDate(value: string, timezone: string) { return `${new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short', timeZone: timezone }).format(new Date(value))} ${timezone}`; }

export function SuggestionsPage({ userId, timezone = 'UTC', onStart, onOpenSession, onOpenProblem }: {
  userId: string;
  timezone?: string;
  onStart: (choice: { subjectId: string | null; knowledgePointId: string | null; goal: string }) => void;
  onOpenSession: (id: string) => void;
  onOpenProblem: (id: string) => void;
}) {
  const [status, setStatus] = useState<SuggestionData['status'] | 'all'>('available');
  const [selected, setSelected] = useState<string[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [snoozeDate, setSnoozeDate] = useState('');
  const client = useQueryClient();
  useEffect(() => { selectReviewOwner(userId); setSelected([]); }, [userId]);
  const query = useInfiniteQuery({
    queryKey: ['suggestions', userId, status],
    initialPageParam: null as string | null,
    queryFn: ({ signal, pageParam }) => request<SuggestionPageResponse>(`/suggestions?limit=100${status === 'all' ? '&status=all' : `&status=${status}`}${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ''}`, { signal }),
    getNextPageParam: (page) => page.data.next_cursor ?? undefined,
  });
  const items = query.data?.pages.flatMap((page) => page.data.items) ?? [];
  const selectedItems = useMemo(() => selected.map((id) => items.find((item) => item.id === id)).filter((item): item is SuggestionData => Boolean(item)), [items, selected]);
  const openRef = (ref: SuggestionData['source_refs'][number]) => {
    if (ref.session_id || ref.kind === 'session') onOpenSession(ref.session_id ?? ref.id);
    else if (ref.problem_id || ref.kind === 'problem') onOpenProblem(ref.problem_id ?? ref.id);
  };
  async function act(item: SuggestionData, action: SuggestionActionInput['action']) {
    let command = reviewCommandFor(item.id);
    if (!command || command.action !== action) {
      const operationId = newId();
      const snoozedUntil = action === 'snooze' && snoozeDate ? new Date(`${snoozeDate}T23:59:59`).toISOString() : undefined;
      const body: SuggestionActionInput = { operation_id: operationId, action, ...(snoozedUntil ? { snoozed_until: snoozedUntil } : {}) };
      command = { operationId, action, version: item.version, body, ...(snoozedUntil ? { snoozedUntil } : {}) };
      setReviewCommand(item.id, command);
    }
    const activeCommand = command;
    if (!activeCommand) return;
    setBusyId(item.id); setMessage('');
    try {
      await request(`/suggestions/${encodeURIComponent(item.id)}/actions`, { method: 'POST', headers: { 'If-Match': String(activeCommand.version), 'Idempotency-Key': activeCommand.operationId }, body: JSON.stringify(activeCommand.body) });
      setReviewCommand(item.id, null);
      setSelected((current) => current.filter((id) => id !== item.id));
      await client.invalidateQueries({ queryKey: ['suggestions', userId] });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setReviewCommand(item.id, null);
        await client.invalidateQueries({ queryKey: ['suggestions', userId] });
        setMessage('这条建议的来源已更新，已重新读取最新状态。');
      } else if (error instanceof ApiError && error.status === 422) {
        setReviewCommand(item.id, null);
        setMessage('稍后日期或操作参数未通过校验。请选择服务端当前日期之后、365 天以内的日期再提交。');
      } else setMessage('操作未完成。命令已保留，可以安全重试。');
    } finally { setBusyId(null); }
  }
  async function startSuggestion(id: string) {
    setMessage('');
    try {
      const fresh = await request<{ data: SuggestionData }>(`/suggestions/${encodeURIComponent(id)}`);
      if (fresh.data.status !== 'available') {
        setMessage('这条建议已经变化，已刷新列表，请重新选择当前可用的建议。');
        await client.invalidateQueries({ queryKey: ['suggestions', userId] });
        return;
      }
      onStart({ subjectId: fresh.data.subject_id ?? null, knowledgePointId: fresh.data.knowledge_point_id ?? null, goal: fresh.data.reason });
    } catch {
      setMessage('暂时无法核对这条建议的最新来源，请刷新后再试。');
      await client.invalidateQueries({ queryKey: ['suggestions', userId] });
    }
  }
  return <section className="workspace review-page" aria-labelledby="suggestions-title">
    <header className="history-heading page-head"><div><span className="eyebrow">REVIEW WHEN YOU CHOOSE</span><h1 id="suggestions-title">可以考虑复习</h1><p className="muted">每条建议都附有理由和来源。选择多少、何时开始由你决定。</p></div><button className="text-button" onClick={() => void query.refetch()}>重新加载</button></header>
    <label className="review-filter">查看状态 <select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}><option value="available">可查看</option><option value="accepted">已接受</option><option value="snoozed">稍后</option><option value="dismissed">已忽略</option><option value="stale">来源已变化</option><option value="all">全部状态</option></select></label>
    {query.isPending ? <p role="status" className="muted">正在读取建议…</p> : query.isError ? <div><Feedback error={query.error} /><button className="secondary" onClick={() => void query.refetch()}>重试</button></div> : items.length === 0 ? <p className="panel muted">当前没有这类建议。你可以稍后再查看，不需要补做任何内容。</p> : <div className="suggestion-list">{items.map((item) => <article className="panel suggestion-card" key={item.id}>
      <label className="suggestion-select"><input type="checkbox" aria-label={`选择：${labels[item.kind]}，${item.reason}`} disabled={item.status !== 'available'} checked={selected.includes(item.id)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))} />加入本地复习队列</label>
      <div className="history-entry-heading"><span className="eyebrow">{labels[item.kind]}</span><span>{statuses[item.status]}</span></div><h2>{item.reason}</h2>
      <p className="muted">规则 {item.rule_version} · 来源版本 {item.source_revision}</p>
      {item.status === 'snoozed' && item.snoozed_until && <p className="muted">稍后至 {refDate(item.snoozed_until, timezone)}</p>}
      <ul className="source-list">{item.source_refs.map((ref) => <li key={`${ref.kind}:${ref.id}:${ref.version}`}>{ref.session_id || ref.kind === 'session' || ref.problem_id || ref.kind === 'problem' ? <button className="text-button" onClick={() => openRef(ref)}>{ref.label} · v{ref.version} · {refDate(ref.occurred_at, timezone)} →</button> : <span>{ref.label} · v{ref.version} · {refDate(ref.occurred_at, timezone)}</span>}</li>)}</ul>
      <div className="suggestion-actions">{item.status === 'available' && <><button className="secondary" onClick={() => void startSuggestion(item.id)}>进入学习</button><button disabled={busyId === item.id} onClick={() => void act(item, 'accept')}>接受建议</button><label>稍后到 <input type="date" value={snoozeDate} onChange={(event) => setSnoozeDate(event.target.value)} aria-label="稍后查看日期（留空为7天后）" /></label><button className="secondary" disabled={busyId === item.id} onClick={() => void act(item, 'snooze')}>{snoozeDate ? '稍后查看' : '7 天后再看'}</button><button className="text-button" disabled={busyId === item.id} onClick={() => void act(item, 'dismiss')}>忽略</button></>}{item.status === 'stale' && <span className="muted">来源已变化，不能再据此开始学习。</span>}</div>
    </article>)}</div>}
    {message && <p role="status" className="muted">{message}</p>}
    {query.hasNextPage && <button className="secondary" disabled={query.isFetchingNextPage} onClick={() => void query.fetchNextPage()}>{query.isFetchingNextPage ? '正在加载…' : '加载更多建议'}</button>}
    {selectedItems.length > 0 && <aside className="panel review-queue" aria-label="本地复习队列"><h2>你的复习队列（{selectedItems.length}）</h2><p className="muted">选择下一条开始；队列只保存在当前页面，不会自动接受或启动其他建议。</p><ol>{selectedItems.map((item) => <li key={item.id}>{labels[item.kind]}：{item.reason}</li>)}</ol><button onClick={() => void startSuggestion(selectedItems[0].id)}>开始队列中的第一项</button><button className="secondary" onClick={() => setSelected([])}>清空选择</button></aside>}
  </section>;
}
