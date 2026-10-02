import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { ApiError, request } from '../../shared/api/client';
import type { ChapterData, CreateKnowledgePointInput, CreateKnowledgePointResponse, KnowledgePointData, KnowledgePointPageResponse, PatchKnowledgePointInput, PatchKnowledgePointResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { clearKnowledgeCommand, knowledgeFormFor, runKnowledgeCommand } from './draft-store';
import { KnowledgePointDetail } from './KnowledgePointDetail';

const uuid = () => crypto.randomUUID();

export function ChapterPoints({ userId, subjectId, chapter, onClose, onStartPoint, onOpenSession }: {
  userId: string;
  subjectId: string;
  chapter: ChapterData;
  onClose: () => void;
  onStartPoint: (context: { subjectId: string; pointId: string; pointName: string }) => void;
  onOpenSession: (sessionId: string) => void;
}) {
  const client = useQueryClient();
  const [showArchived, setShowArchived] = useState(false);
  const [selectedPointId, setSelectedPointId] = useState<string | null>(null);
  const pages = useInfiniteQuery({
    queryKey: ['knowledge-points', chapter.id, showArchived],
    initialPageParam: null as string | null,
    queryFn: ({ signal, pageParam }) => request<KnowledgePointPageResponse>(`/knowledge-points?chapter_id=${chapter.id}&archived=${showArchived}&limit=20${pageParam ? `&cursor=${pageParam}` : ''}`, { signal }),
    getNextPageParam: (page) => page.data.next_cursor ?? undefined,
  });
  const points = pages.data?.pages.flatMap((page) => page.data.items) ?? [];
  const newForm = knowledgeFormFor(userId, `knowledge-point:new:${chapter.id}`, { name: '', notes: '' });
  const [newName, setNewName] = useState(String(newForm.name ?? ''));
  const [newNotes, setNewNotes] = useState(String(newForm.notes ?? ''));
  const createKey = `knowledge-point:create:${chapter.id}`;
  const create = useMutation({
    mutationFn: () => {
      const id = uuid();
      const body: CreateKnowledgePointInput = { operation_id: id, chapter_id: chapter.id, name: newName.trim(), notes: newNotes.trim() || null };
      return runKnowledgeCommand<CreateKnowledgePointResponse>(userId, createKey, 'POST', '/knowledge-points', body);
    },
    onSuccess: () => { clearKnowledgeCommand(userId, createKey); setNewName(''); setNewNotes(''); newForm.name = ''; newForm.notes = ''; void client.invalidateQueries({ queryKey: ['knowledge-points', chapter.id] }); void client.invalidateQueries({ queryKey: ['subject-space', subjectId] }); },
    onError: (error) => { if (error instanceof ApiError && error.status === 409) { clearKnowledgeCommand(userId, createKey); void client.invalidateQueries({ queryKey: ['knowledge-points', chapter.id] }); } },
  });

  return <section className="panel knowledge-section knowledge-children" aria-labelledby="chapter-points-title">
    <div className="knowledge-breadcrumb"><button className="text-button" onClick={onClose}>← 章节列表</button><span>{chapter.name}</span></div>
    <div className="knowledge-section-heading"><div><span className="eyebrow">KNOWLEDGE POINTS</span><h2 id="chapter-points-title">知识点</h2></div><label className="category-option"><input type="checkbox" checked={showArchived} onChange={(event) => { setShowArchived(event.target.checked); setSelectedPointId(null); }} />查看归档知识点</label></div>
    {chapter.archived && <p className="muted">章节已归档，因此不能从其中开始新学习。恢复章节后，未归档知识点会重新开放。</p>}
    {pages.isPending ? <p role="status" className="muted">正在读取知识点…</p> : pages.isError ? <div><Feedback error={pages.error} /><button className="secondary" onClick={() => void pages.refetch()}>重试</button></div> : points.length === 0 ? <p className="muted">这个章节还没有知识点。可以只填写名称，之后再补充说明。</p> : <ul className="knowledge-point-list">{points.map((point) => <li key={point.id}>
      <KnowledgePointRow userId={userId} point={point} onOpen={() => setSelectedPointId(point.id)} />
    </li>)}</ul>}
    {pages.hasNextPage && <button className="secondary" disabled={pages.isFetchingNextPage} onClick={() => void pages.fetchNextPage()}>{pages.isFetchingNextPage ? '正在加载…' : '加载更多知识点'}</button>}
    {!showArchived && !chapter.archived && <form className="knowledge-create-form" onSubmit={(event) => { event.preventDefault(); if (!create.isPending && newName.trim()) create.mutate(); }}>
      <label>新知识点名称<input value={newName} maxLength={200} onChange={(event) => { setNewName(event.target.value); newForm.name = event.target.value; }} /></label>
      <label>说明（可选）<textarea value={newNotes} maxLength={20000} onChange={(event) => { setNewNotes(event.target.value); newForm.notes = event.target.value; }} /></label>
      <Feedback error={create.error} />
      {create.error && <button type="button" className="text-button" onClick={() => { clearKnowledgeCommand(userId, createKey); create.reset(); }}>取消本次保存重试</button>}
      <button disabled={create.isPending || !newName.trim()}>{create.isPending ? '正在保存知识点…' : '添加知识点'}</button>
    </form>}
    {selectedPointId && <KnowledgePointDetail key={selectedPointId} userId={userId} knowledgePointId={selectedPointId} chapterArchived={chapter.archived} onStartPoint={onStartPoint} onOpenSession={onOpenSession} />}
  </section>;
}

function KnowledgePointRow({ userId, point, onOpen }: { userId: string; point: KnowledgePointData; onOpen: () => void }) {
  const client = useQueryClient();
  const values = knowledgeFormFor(userId, `knowledge-point:${point.id}`, { name: point.name, notes: point.notes ?? '', archived: point.archived });
  const [name, setName] = useState(String(values.name ?? point.name));
  const [notes, setNotes] = useState(String(values.notes ?? point.notes ?? ''));
  const [archived, setArchived] = useState(Boolean(values.archived ?? point.archived));
  const key = `knowledge-point:update:${point.id}`;
  const patch = useMutation({
    mutationFn: () => {
      const id = uuid();
      const body: PatchKnowledgePointInput = { operation_id: id, name: name.trim(), notes: notes.trim() || null, archived };
      return runKnowledgeCommand<PatchKnowledgePointResponse>(userId, key, 'PATCH', `/knowledge-points/${point.id}`, body, `"${point.version}"`);
    },
    onSuccess: () => { clearKnowledgeCommand(userId, key); void client.invalidateQueries({ queryKey: ['knowledge-points', point.chapter_id] }); void client.invalidateQueries({ queryKey: ['knowledge-point', point.id] }); },
    onError: (error) => { if (error instanceof ApiError && error.status === 409) { clearKnowledgeCommand(userId, key); void client.invalidateQueries({ queryKey: ['knowledge-points', point.chapter_id] }); } },
  });
  return <div className="knowledge-point-row">
    <button className="chapter-open" onClick={onOpen}><strong>{point.name}</strong><span>查看记录与自评依据 →</span></button>
    <form className="chapter-edit-form" onSubmit={(event) => { event.preventDefault(); if (!patch.isPending) patch.mutate(); }}>
      <label>名称<input value={name} maxLength={200} onChange={(event) => { setName(event.target.value); values.name = event.target.value; }} /></label>
      <label>说明（可清空）<textarea value={notes} maxLength={20000} onChange={(event) => { setNotes(event.target.value); values.notes = event.target.value; }} /></label>
      <label className="category-option"><input type="checkbox" checked={archived} onChange={(event) => { setArchived(event.target.checked); values.archived = event.target.checked; }} />{archived ? '已归档（取消勾选可恢复）' : '归档知识点'}</label>
      <Feedback error={patch.error} />
      {patch.error && <button type="button" className="text-button" onClick={() => { clearKnowledgeCommand(userId, key); patch.reset(); }}>取消本次保存重试</button>}
      <button className="secondary" disabled={patch.isPending || !name.trim()}>{patch.isPending ? '正在保存…' : '保存知识点修改'}</button>
    </form>
  </div>;
}
