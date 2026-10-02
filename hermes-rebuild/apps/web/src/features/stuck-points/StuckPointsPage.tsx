import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, request } from '../../shared/api/client';
import type { SessionHistoryResponse, StuckPointData, StuckPointPageResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import {
  selectStuckPointOwner,
  setStuckPointCreate,
  setStuckPointUpdate,
  stuckPointCreateFor,
  stuckPointUpdateFor,
} from './draft-store';
import './stuck-points.css';

const newId = () => crypto.randomUUID();
type Filter = 'open' | 'resolved' | 'all';
const filters: Record<Filter, string> = { open: '仍然卡住', resolved: '已经过去', all: '全部' };

function refDate(value: string, timezone: string) {
  return `${new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short', timeZone: timezone }).format(new Date(value))} ${timezone}`;
}

/**
 * Independent stuck point surface (FR-030 / FR-036).
 *
 * A stuck point is one sentence about where learning actually broke. It has its
 * own open/resolved lifecycle and never claims mastery: resolving one only says
 * the learner got past that spot.
 */
export function StuckPointsPage({ userId, timezone = 'UTC', onOpenSession }: {
  userId: string;
  timezone?: string;
  onOpenSession: (id: string) => void;
}) {
  const client = useQueryClient();
  const [filter, setFilter] = useState<Filter>('open');
  const [draftText, setDraftText] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');
  useEffect(() => { selectStuckPointOwner(userId); setFilter('open'); setDraftText(''); setSessionId(''); setEditingId(null); setMessage(''); }, [userId]);
  const points = useQuery({
    queryKey: ['stuck-points', userId, filter],
    queryFn: ({ signal }) => request<StuckPointPageResponse>(`/stuck-points?limit=100${filter === 'all' ? '' : `&status=${filter}`}`, { signal }),
  });
  const sessions = useQuery({ queryKey: ['sessions', userId], queryFn: ({ signal }) => request<SessionHistoryResponse>('/learning-sessions?limit=20', { signal }) });
  const items = points.data?.data.items ?? [];
  const sessionItems = sessions.data?.data.items ?? [];
  const chosenSession = sessionId || sessionItems[0]?.id || '';
  async function createPoint() {
    const text = draftText.trim();
    if (!chosenSession) { setMessage('还没有可关联的学习现场。先开始一次学习，再回来记下卡壳点。'); return; }
    if (!text) { setMessage('用一句话写下刚刚卡在哪里即可。'); return; }
    let command = stuckPointCreateFor();
    if (!command || command.text !== text || command.sessionId !== chosenSession) {
      command = { operationId: newId(), sessionId: chosenSession, text };
      setStuckPointCreate(command);
    }
    setBusyId('create'); setMessage('');
    try {
      await request('/stuck-points', { method: 'POST', headers: { 'Idempotency-Key': command.operationId }, body: JSON.stringify({ operation_id: command.operationId, session_id: command.sessionId, text: command.text }) });
      setStuckPointCreate(null); setDraftText('');
      await client.invalidateQueries({ queryKey: ['stuck-points', userId] });
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) { setStuckPointCreate(null); setMessage('卡壳点需要一句话，最多 1000 字。'); }
      else if (error instanceof ApiError && error.status === 404) { setStuckPointCreate(null); setMessage('这次学习现场已不可用，请重新选择。'); }
      else setMessage('保存未完成。内容已保留，可以安全重试。');
    } finally { setBusyId(null); }
  }
  async function send(point: StuckPointData, changes: { text?: string; status?: 'open' | 'resolved'; resolution_note?: string | null }) {
    const stored = stuckPointUpdateFor(point.id);
    let command = stored && stored.version === point.version && JSON.stringify(stored.body) === JSON.stringify({ operation_id: stored.operationId, ...changes }) ? stored : null;
    if (!command) {
      const operationId = newId();
      command = { operationId, version: point.version, body: { operation_id: operationId, ...changes } };
      setStuckPointUpdate(point.id, command);
    }
    const activeCommand = command;
    setBusyId(point.id); setMessage('');
    try {
      await request(`/stuck-points/${encodeURIComponent(point.id)}`, { method: 'PATCH', headers: { 'If-Match': String(activeCommand.version), 'Idempotency-Key': activeCommand.operationId }, body: JSON.stringify(activeCommand.body) });
      setStuckPointUpdate(point.id, null);
      setEditingId(null);
      await client.invalidateQueries({ queryKey: ['stuck-points', userId] });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setStuckPointUpdate(point.id, null);
        await client.invalidateQueries({ queryKey: ['stuck-points', userId] });
        setMessage('这条卡壳点在别处已经变化，已重新读取最新状态；你的输入仍保留。');
      } else if (error instanceof ApiError && error.status === 422) { setStuckPointUpdate(point.id, null); setMessage('内容未通过校验，请检查后再试。'); }
      else setMessage('修改未完成。输入已保留，可以安全重试。');
    } finally { setBusyId(null); }
  }
  return <section className="workspace stuck-points-page" aria-labelledby="stuck-points-title">
    <header className="history-heading page-head"><div><span className="eyebrow">WHERE IT ACTUALLY BROKE</span><h1 id="stuck-points-title">卡壳点</h1><p className="muted">只记一句话：刚刚真正卡在哪里。可以以后再看，也可以标成已经过去。这里不做掌握判定。</p></div><button className="text-button" onClick={() => void points.refetch()}>重新加载</button></header>
    <div className="panel stuck-point-create">
      <label>关联的学习现场<select value={chosenSession} onChange={(event) => setSessionId(event.target.value)} disabled={sessionItems.length === 0}>{sessionItems.length === 0 ? <option value="">还没有学习现场</option> : sessionItems.map((session) => <option key={session.id} value={session.id}>{(session.goal || '自由学习').slice(0, 40)} · {session.learning_date}</option>)}</select></label>
      <label>刚刚真正卡在哪里<textarea maxLength={1000} value={draftText} onChange={(event) => setDraftText(event.target.value)} placeholder="例如：为什么 ωs = 2π/T？" /></label>
      <div className="stuck-point-actions"><button disabled={busyId === 'create' || sessionItems.length === 0} onClick={() => void createPoint()}>记下这个卡壳点</button><span className="muted">{draftText.trim().length}/1000</span></div>
    </div>
    {sessions.isError && <div><Feedback error={sessions.error} /></div>}
    <div className="stuck-point-filters"><label>查看 <select value={filter} onChange={(event) => setFilter(event.target.value as Filter)}>{(Object.keys(filters) as Filter[]).map((key) => <option key={key} value={key}>{filters[key]}</option>)}</select></label></div>
    {points.isPending ? <p role="status" className="muted">正在读取卡壳点…</p> : points.isError ? <div><Feedback error={points.error} /><button className="secondary" onClick={() => void points.refetch()}>重试</button></div> : items.length === 0 ? <p className="panel muted">{filter === 'open' ? '现在没有仍然卡住的地方。这不代表必须去找，只是暂时没有记录。' : '这个范围里没有卡壳点记录。'}</p> : <ol className="stuck-point-list">{items.map((point) => <li className="panel stuck-point-card" key={point.id}>
      <div className="stuck-point-head"><span className={`stuck-point-status ${point.status === 'open' ? 'is-open' : ''}`}>{point.status === 'open' ? '仍然卡住' : '已经过去'}</span><span className="muted">v{point.version}</span></div>
      {editingId === point.id ? <div className="stuck-point-create"><textarea maxLength={1000} value={editText} onChange={(event) => setEditText(event.target.value)} aria-label="修改卡壳点文字" /><div className="stuck-point-actions"><button disabled={busyId === point.id} onClick={() => void send(point, { text: editText.trim() })}>保存修改</button><button className="secondary" onClick={() => setEditingId(null)}>取消</button></div></div> : <p className="stuck-point-text">{point.text}</p>}
      <div className="stuck-point-meta muted"><span>{refDate(point.created_at, timezone)}</span>{point.resolved_at && <span>标记于 {refDate(point.resolved_at, timezone)}</span>}{point.knowledge_point_id && <span>已关联知识点</span>}<button className="text-button" onClick={() => onOpenSession(point.session_id)}>打开学习现场 →</button></div>
      {point.resolution_note && <p className="muted">当时是怎么过去的：{point.resolution_note}</p>}
      <div className="stuck-point-actions">
        {point.status === 'open'
          ? <><label>一句话说明怎么过去的（可选）<textarea maxLength={2000} value={notes[point.id] ?? ''} onChange={(event) => setNotes((current) => ({ ...current, [point.id]: event.target.value }))} /></label><button disabled={busyId === point.id} onClick={() => void send(point, { status: 'resolved', resolution_note: (notes[point.id] ?? '').trim() || null })}>标记为已经过去</button></>
          : <button className="secondary" disabled={busyId === point.id} onClick={() => void send(point, { status: 'open', resolution_note: null })}>重新标为仍然卡住</button>}
        {editingId !== point.id && <button className="text-button" onClick={() => { setEditingId(point.id); setEditText(point.text); }}>修改文字</button>}
      </div>
    </li>)}</ol>}
    {message && <p role="status" className="muted">{message}</p>}
  </section>;
}
