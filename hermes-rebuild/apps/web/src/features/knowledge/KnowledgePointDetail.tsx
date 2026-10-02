import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { ApiError, request } from '../../shared/api/client';
import type { KnowledgePointData, KnowledgePointResponse, PatchKnowledgePointInput, PatchKnowledgePointResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { clearKnowledgeCommand, knowledgeFormFor, runKnowledgeCommand } from './draft-store';
import { MasteryEvidence } from './MasteryEvidence';
import { ProblemKnowledgeLinks } from './ProblemKnowledgeLinks';
import { PointSessionRecords } from './PointSessionRecords';

const uuid = () => crypto.randomUUID();

export function KnowledgePointDetail({ userId, knowledgePointId, chapterArchived, onStartPoint, onOpenSession }: {
  userId: string;
  knowledgePointId: string;
  chapterArchived: boolean;
  onStartPoint: (context: { subjectId: string; pointId: string; pointName: string }) => void;
  onOpenSession: (sessionId: string) => void;
}) {
  const point = useQuery({ queryKey: ['knowledge-point', knowledgePointId], queryFn: ({ signal }) => request<KnowledgePointResponse>(`/knowledge-points/${knowledgePointId}`, { signal }) });
  if (point.isPending) return <section className="knowledge-point-detail"><p className="muted" role="status">正在读取知识点…</p></section>;
  if (point.isError) return <section className="knowledge-point-detail"><Feedback error={point.error} /><button className="secondary" onClick={() => void point.refetch()}>重试</button></section>;
  return <KnowledgePointEditor key={`${point.data.data.id}:${point.data.data.version}`} userId={userId} point={point.data.data} chapterArchived={chapterArchived} onStartPoint={onStartPoint} onOpenSession={onOpenSession} />;
}

function KnowledgePointEditor({ userId, point: data, chapterArchived, onStartPoint, onOpenSession }: {
  userId: string;
  point: KnowledgePointData;
  chapterArchived: boolean;
  onStartPoint: (context: { subjectId: string; pointId: string; pointName: string }) => void;
  onOpenSession: (sessionId: string) => void;
}) {
  const client = useQueryClient();
  const values = knowledgeFormFor(userId, `knowledge-point:${data.id}`, { name: data.name, notes: data.notes ?? '', archived: data.archived });
  const [name, setName] = useState(String(values.name ?? data.name));
  const [notes, setNotes] = useState(String(values.notes ?? data.notes ?? ''));
  const [archived, setArchived] = useState(Boolean(values.archived ?? data.archived));
  const key = `knowledge-point:update:${data.id}`;
  const patch = useMutation({
    mutationFn: () => {
      const id = uuid();
      const body: PatchKnowledgePointInput = { operation_id: id, name: name.trim(), notes: notes.trim() || null, archived };
      return runKnowledgeCommand<PatchKnowledgePointResponse>(userId, key, 'PATCH', `/knowledge-points/${data.id}`, body, `"${data.version}"`);
    },
    onSuccess: () => { clearKnowledgeCommand(userId, key); void client.invalidateQueries({ queryKey: ['knowledge-point', data.id] }); void client.invalidateQueries({ queryKey: ['knowledge-points'] }); },
    onError: (error) => { if (error instanceof ApiError && error.status === 409) { clearKnowledgeCommand(userId, key); void client.invalidateQueries({ queryKey: ['knowledge-point', data.id] }); } },
  });
  const canStart = !data.archived && !chapterArchived;

  return <section className="knowledge-point-detail" aria-labelledby={`point-title-${data.id}`}>
    <header className="knowledge-point-heading"><div><span className="eyebrow">KNOWLEDGE POINT</span><h2 id={`point-title-${data.id}`}>{data.name}</h2></div>
      <button disabled={!canStart} onClick={() => onStartPoint({ subjectId: data.subject_id, pointId: data.id, pointName: data.name })}>从这里开始学习 →</button>
    </header>
    {!canStart && <p className="muted">知识点或所属章节已归档，恢复后可以从这里开始学习。</p>}
    {data.notes && <p className="problem-statement">{data.notes}</p>}
    <details className="knowledge-edit-details"><summary>编辑知识点名称、说明或归档状态</summary><form onSubmit={(event) => { event.preventDefault(); if (!patch.isPending) patch.mutate(); }}>
      <label>名称<input maxLength={200} value={name} onChange={(event) => { setName(event.target.value); values.name = event.target.value; }} /></label>
      <label>说明（可清空）<textarea maxLength={20000} value={notes} onChange={(event) => { setNotes(event.target.value); values.notes = event.target.value; }} /></label>
      <label className="category-option"><input type="checkbox" checked={archived} onChange={(event) => { setArchived(event.target.checked); values.archived = event.target.checked; }} />{archived ? '已归档（取消勾选可恢复）' : '归档知识点'}</label>
      <Feedback error={patch.error} />
      {patch.error && <button type="button" className="text-button" onClick={() => { clearKnowledgeCommand(userId, key); patch.reset(); }}>取消本次保存重试</button>}
      <button className="secondary" disabled={patch.isPending || !name.trim()}>{patch.isPending ? '正在保存…' : '保存知识点修改'}</button>
    </form></details>
    <ProblemKnowledgeLinks userId={userId} subjectId={data.subject_id} pointId={data.id} canAssociate={canStart} />
    <PointSessionRecords pointId={data.id} onOpenSession={onOpenSession} />
    <MasteryEvidence userId={userId} pointId={data.id} pointVersion={data.version} />
  </section>;
}
