import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { ApiError, request } from '../../shared/api/client';
import type { ChapterData, ChapterPageResponse, CreateChapterInput, CreateChapterResponse, PatchChapterInput, PatchChapterResponse, SubjectSpaceResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { ChapterPoints } from './ChapterPoints';
import { clearKnowledgeCommand, knowledgeFormFor, runKnowledgeCommand } from './draft-store';
import { ProblemRecordDetail } from './ProblemRecordDetail';

const uuid = () => crypto.randomUUID();

export function SubjectSpace({ userId, subjectId, onBack, onOpenSession, onStartPoint, onCompareProblem }: {
  userId: string;
  subjectId: string;
  onBack: () => void;
  onOpenSession: (sessionId: string) => void;
  onStartPoint: (context: { subjectId: string; pointId: string; pointName: string }) => void;
  onCompareProblem?: (problemId: string) => void;
}) {
  const client = useQueryClient();
  const space = useQuery({
    queryKey: ['subject-space', subjectId],
    queryFn: ({ signal }) => request<SubjectSpaceResponse>(`/subjects/${subjectId}/space`, { signal }),
  });
  const [showArchived, setShowArchived] = useState(false);
  const [openProblemId, setOpenProblemId] = useState<string | null>(null);
  const chapterPages = useInfiniteQuery({
    queryKey: ['chapters', subjectId, showArchived],
    initialPageParam: null as string | null,
    queryFn: ({ signal, pageParam }) => request<ChapterPageResponse>(`/chapters?subject_id=${subjectId}&archived=${showArchived}&limit=20${pageParam ? `&cursor=${pageParam}` : ''}`, { signal }),
    getNextPageParam: (page) => page.data.next_cursor ?? undefined,
  });
  const chapters = (chapterPages.data?.pages.flatMap((page) => page.data.items) ?? []).sort((a, b) => a.order_index - b.order_index || a.name.localeCompare(b.name, 'zh-CN'));
  const [selectedChapter, setSelectedChapter] = useState<ChapterData | null>(null);
  const newForm = knowledgeFormFor(userId, `chapter:new:${subjectId}`, { name: '' });
  const [newName, setNewName] = useState(String(newForm.name ?? ''));
  const createKey = `chapter:create:${subjectId}`;
  const createChapter = useMutation({
    mutationFn: () => {
      const id = uuid();
      const body: CreateChapterInput = { operation_id: id, subject_id: subjectId, name: newName.trim(), order_index: chapters.length };
      return runKnowledgeCommand<CreateChapterResponse>(userId, createKey, 'POST', '/chapters', body);
    },
    onSuccess: () => { clearKnowledgeCommand(userId, createKey); setNewName(''); newForm.name = ''; void client.invalidateQueries({ queryKey: ['chapters', subjectId] }); void client.invalidateQueries({ queryKey: ['subject-space', subjectId] }); },
    onError: (error) => { if (error instanceof ApiError && error.status === 409) { clearKnowledgeCommand(userId, createKey); void client.invalidateQueries({ queryKey: ['chapters', subjectId] }); } },
  });

  return <section className="workspace knowledge-space" aria-labelledby="subject-space-title">
    <div className="knowledge-breadcrumb"><button className="text-button" onClick={onBack}>← 学科</button><span>学科空间</span></div>
    {space.isPending ? <p className="muted" role="status">正在读取学科空间…</p> : space.isError ? <div><Feedback error={space.error} /><button className="secondary" onClick={() => void space.refetch()}>重试</button></div> : <>
      <header className="page-hero subject-hero"><span className="eyebrow">{space.data.data.subject.group_label || 'SUBJECT'}</span><h1 id="subject-space-title">{space.data.data.subject.name}</h1><p className="muted">按章节整理你的学习内容。没有记录的地方会保持空白。</p></header>
      <section className="panel knowledge-section" aria-labelledby="chapters-title">
        <div className="knowledge-section-heading"><div><span className="eyebrow">CHAPTERS</span><h2 id="chapters-title">章节</h2></div><label className="category-option"><input type="checkbox" checked={showArchived} onChange={(event) => { setShowArchived(event.target.checked); setSelectedChapter(null); }} />查看归档章节</label></div>
        {chapterPages.isPending ? <p role="status" className="muted">正在读取章节…</p> : chapterPages.isError ? <div><Feedback error={chapterPages.error} /><button className="secondary" onClick={() => void chapterPages.refetch()}>重试</button></div> : chapters.length === 0 ? <p className="muted">还没有章节。可以先添加一个名称，之后再补充知识点。</p> : <ol className="chapter-list">{chapters.map((chapter) => <li key={chapter.id}>
          <ChapterRow userId={userId} chapter={chapter} onOpen={() => setSelectedChapter(chapter)} onUpdated={(updated) => setSelectedChapter((current) => current?.id === updated.id ? updated : current)} />
        </li>)}</ol>}
        {chapterPages.hasNextPage && <button className="secondary" disabled={chapterPages.isFetchingNextPage} onClick={() => void chapterPages.fetchNextPage()}>{chapterPages.isFetchingNextPage ? '正在加载…' : '加载更多章节'}</button>}
        {!showArchived && <form className="knowledge-create-form" onSubmit={(event) => { event.preventDefault(); if (!createChapter.isPending && newName.trim()) createChapter.mutate(); }}>
          <label>新章节名称<input value={newName} maxLength={200} onChange={(event) => { setNewName(event.target.value); newForm.name = event.target.value; }} /></label>
          <Feedback error={createChapter.error} />
          {createChapter.error && <button type="button" className="text-button" onClick={() => { clearKnowledgeCommand(userId, createKey); createChapter.reset(); }}>取消本次保存重试</button>}
          <button disabled={createChapter.isPending || !newName.trim()}>{createChapter.isPending ? '正在保存章节…' : '添加章节'}</button>
        </form>}
      </section>
      <section className="panel knowledge-section" aria-labelledby="recent-title">
        <span className="eyebrow">RECENT RECORDS</span><h2 id="recent-title">最近记录</h2>
        <div className="knowledge-recent-grid">
          <div><h3>学习现场</h3>{space.data.data.recent_sessions.length === 0 ? <p className="muted">暂无学习记录。</p> : <ul>{space.data.data.recent_sessions.map((session) => <li key={session.id}><button className="text-button" onClick={() => onOpenSession(session.id)}>{session.goal || '自由学习'} · {session.status === 'ended' ? '已结束' : session.status === 'paused' ? '已暂停' : '进行中'} →</button></li>)}</ul>}</div>
          <div><h3>题目</h3>{space.data.data.recent_problems.length === 0 ? <p className="muted">暂无题目记录。</p> : <ul>{space.data.data.recent_problems.map((problem) => <li key={problem.id}><button className="text-button" onClick={() => setOpenProblemId(problem.id)}>{problem.title || problem.statement?.slice(0, 70) || '未命名题目'} →</button></li>)}</ul>}</div>
        </div>
      </section>
      {openProblemId && <ProblemRecordDetail userId={userId} problemId={openProblemId} onClose={() => setOpenProblemId(null)} onCompare={onCompareProblem ? () => onCompareProblem(openProblemId) : undefined} />}
      {selectedChapter && <ChapterPoints key={`${selectedChapter.id}:${selectedChapter.version}`} userId={userId} subjectId={subjectId} chapter={selectedChapter} onClose={() => setSelectedChapter(null)} onStartPoint={onStartPoint} onOpenSession={onOpenSession} />}
    </>}
  </section>;
}

function ChapterRow({ userId, chapter, onOpen, onUpdated }: { userId: string; chapter: ChapterData; onOpen: () => void; onUpdated: (chapter: ChapterData) => void }) {
  const client = useQueryClient();
  const values = knowledgeFormFor(userId, `chapter:${chapter.id}`, { name: chapter.name, order_index: chapter.order_index, archived: chapter.archived });
  const [name, setName] = useState(String(values.name ?? chapter.name));
  const [orderIndex, setOrderIndex] = useState(Number(values.order_index ?? chapter.order_index));
  const [archived, setArchived] = useState(Boolean(values.archived ?? chapter.archived));
  const key = `chapter:update:${chapter.id}`;
  const patch = useMutation({
    mutationFn: () => {
      const id = uuid();
      const body: PatchChapterInput = { operation_id: id, name: name.trim(), order_index: orderIndex, archived };
      return runKnowledgeCommand<PatchChapterResponse>(userId, key, 'PATCH', `/chapters/${chapter.id}`, body, `"${chapter.version}"`);
    },
    onSuccess: (response) => { clearKnowledgeCommand(userId, key); onUpdated(response.data); void client.invalidateQueries({ queryKey: ['chapters', chapter.subject_id] }); void client.invalidateQueries({ queryKey: ['subject-space', chapter.subject_id] }); },
    onError: (error) => { if (error instanceof ApiError && error.status === 409) { clearKnowledgeCommand(userId, key); void client.invalidateQueries({ queryKey: ['chapters', chapter.subject_id] }); } },
  });
  return <div className="chapter-row">
    <button className="chapter-open" onClick={onOpen}><strong>{chapter.name}</strong><span>管理知识点 →</span></button>
    <form className="chapter-edit-form" onSubmit={(event) => { event.preventDefault(); if (!patch.isPending) patch.mutate(); }}>
      <label>名称<input value={name} maxLength={200} onChange={(event) => { setName(event.target.value); values.name = event.target.value; }} /></label>
      <label>排序<input type="number" min={0} max={100000} value={orderIndex} onChange={(event) => { const value = Number(event.target.value); setOrderIndex(value); values.order_index = value; }} /></label>
      <label className="category-option"><input type="checkbox" checked={archived} onChange={(event) => { setArchived(event.target.checked); values.archived = event.target.checked; }} />{archived ? '已归档（取消勾选可恢复）' : '归档章节'}</label>
      <Feedback error={patch.error} />
      {patch.error && <button type="button" className="text-button" onClick={() => { clearKnowledgeCommand(userId, key); patch.reset(); }}>取消本次保存重试</button>}
      <button className="secondary" disabled={patch.isPending || !name.trim()}>{patch.isPending ? '正在保存…' : '保存章节修改'}</button>
    </form>
  </div>;
}
