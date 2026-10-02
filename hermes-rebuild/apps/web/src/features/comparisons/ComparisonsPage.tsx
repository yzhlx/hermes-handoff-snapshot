import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { ApiError, request } from '../../shared/api/client';
import type { ComparisonData, ComparisonPageResponse, ComparisonResponse, PatchComparisonInput, PatchComparisonResponse, ProblemData, ProblemPatchInput, ProblemResponse, ProblemsResponse, SubjectsResponse, UpdateProblemResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { clearComparisonCommand, comparisonWorkspaceFor, runComparisonCommand, selectComparisonOwner, type ComparisonWorkspaceDraft } from './draft-store';
import { ComparisonEditor } from './ComparisonEditor';
import { ProblemAnswerCheck } from './ProblemAnswerCheck';
import { ProblemSourcePanel } from './ProblemSourcePanel';
import './comparisons.css';

type Mode = ComparisonWorkspaceDraft['mode'];
const uuid = () => crypto.randomUUID();

export function ComparisonsPage({ userId, initialProblemId = null, onOpenProblem, onStartProblem }: {
  userId: string;
  initialProblemId?: string | null;
  onOpenProblem: (id: string) => void;
  onStartProblem: (context: { problemId: string; subjectId: string | null; goal: string }) => void;
}) {
  return <ComparisonWorkspace key={userId} userId={userId} initialProblemId={initialProblemId} onOpenProblem={onOpenProblem} onStartProblem={onStartProblem} />;
}

function ComparisonWorkspace({ userId, initialProblemId, onOpenProblem, onStartProblem }: {
  userId: string;
  initialProblemId: string | null;
  onOpenProblem: (id: string) => void;
  onStartProblem: (context: { problemId: string; subjectId: string | null; goal: string }) => void;
}) {
  const client = useQueryClient();
  const workspace = comparisonWorkspaceFor(userId);
  const [mode, setModeState] = useState<Mode>(initialProblemId ? 'select' : workspace.mode);
  const [leftProblemId, setLeftProblemIdState] = useState(initialProblemId ?? workspace.leftProblemId);
  const [rightProblemId, setRightProblemIdState] = useState(initialProblemId ? '' : workspace.rightProblemId);
  const [leftAttemptId, setLeftAttemptIdState] = useState<string | null>(initialProblemId ? null : workspace.leftAttemptId);
  const [rightAttemptId, setRightAttemptIdState] = useState<string | null>(initialProblemId ? null : workspace.rightAttemptId);
  const [comparisonId, setComparisonIdState] = useState<string | null>(initialProblemId ? null : workspace.comparisonId);
  const [showArchived, setShowArchived] = useState(false);
  const [subjectId, setSubjectId] = useState('');
  const [representativeOnly, setRepresentativeOnly] = useState(false);
  const [problemFilter, setProblemFilter] = useState('');
  const [listArchived, setListArchived] = useState(false);
  const [checkProblemId, setCheckProblemId] = useState<string | null>(null);

  useEffect(() => { selectComparisonOwner(userId); }, [userId]);
  useEffect(() => {
    workspace.mode = mode;
    workspace.comparisonId = comparisonId;
    workspace.leftProblemId = leftProblemId;
    workspace.rightProblemId = rightProblemId;
    workspace.leftAttemptId = leftAttemptId;
    workspace.rightAttemptId = rightAttemptId;
  }, [workspace, mode, comparisonId, leftProblemId, rightProblemId, leftAttemptId, rightAttemptId]);

  const setMode = (next: Mode) => { setModeState(next); workspace.mode = next; };
  const setLeftProblemId = (next: string) => { setLeftProblemIdState(next); workspace.leftProblemId = next; };
  const setRightProblemId = (next: string) => { setRightProblemIdState(next); workspace.rightProblemId = next; };
  const setLeftAttemptId = (next: string | null) => { setLeftAttemptIdState(next); workspace.leftAttemptId = next; };
  const setRightAttemptId = (next: string | null) => { setRightAttemptIdState(next); workspace.rightAttemptId = next; };
  const setComparisonId = (next: string | null) => { setComparisonIdState(next); workspace.comparisonId = next; };

  const subjects = useQuery({ queryKey: ['subjects', userId], queryFn: ({ signal }) => request<SubjectsResponse>('/subjects', { signal }) });
  const listParams = new URLSearchParams({ limit: '20', archived: String(listArchived) });
  if (subjectId) listParams.set('subject_id', subjectId);
  if (problemFilter) listParams.set('problem_id', problemFilter);
  const comparisons = useInfiniteQuery({
    queryKey: ['problem-comparisons', userId, subjectId, problemFilter, listArchived],
    initialPageParam: null as string | null,
    queryFn: ({ signal, pageParam }) => request<ComparisonPageResponse>(`/problem-comparisons?${listParams}${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ''}`, { signal }),
    getNextPageParam: (page) => page.data.next_cursor ?? undefined,
    enabled: mode === 'list',
  });
  const filterProblems = useInfiniteQuery({
    queryKey: ['comparison-filter-problems', userId, subjectId], initialPageParam: null as string | null,
    queryFn: ({ signal, pageParam }) => request<ProblemsResponse>(`/problems?archived=false&limit=50${subjectId ? `&subject_id=${encodeURIComponent(subjectId)}` : ''}${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ''}`, { signal }),
    getNextPageParam: (page) => page.data.next_cursor ?? undefined,
    enabled: mode === 'list',
  });
  const problemParams = new URLSearchParams({ limit: '20', archived: String(showArchived) });
  if (subjectId) problemParams.set('subject_id', subjectId);
  if (representativeOnly) problemParams.set('representative', 'true');
  const problems = useInfiniteQuery({
    queryKey: ['comparison-problems', userId, subjectId, showArchived, representativeOnly],
    initialPageParam: null as string | null,
    queryFn: ({ signal, pageParam }) => request<ProblemsResponse>(`/problems?${problemParams}${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ''}`, { signal }),
    getNextPageParam: (page) => page.data.next_cursor ?? undefined,
    enabled: mode === 'select' || mode === 'library',
  });
  const comparisonDetail = useQuery({
    queryKey: ['problem-comparison', userId, comparisonId],
    queryFn: ({ signal }) => request<ComparisonResponse>(`/problem-comparisons/${encodeURIComponent(comparisonId ?? '')}`, { signal }),
    enabled: mode === 'detail' || mode === 'edit' ? Boolean(comparisonId) : false,
  });
  const selected = comparisonDetail.data?.data;
  const problemItems = problems.data?.pages.flatMap((page) => page.data.items) ?? [];
  const comparisonItems = comparisons.data?.pages.flatMap((page) => page.data.items) ?? [];
  const leftProblem = problemItems.find((item) => item.id === leftProblemId);
  const rightProblem = problemItems.find((item) => item.id === rightProblemId);

  const startNew = () => {
    setLeftProblemId(initialProblemId ?? ''); setRightProblemId('');
    setLeftAttemptId(null); setRightAttemptId(null); setShowArchived(false);
    setComparisonId(null);
    setMode('select');
  };
  const browseLibrary = () => { setMode('library'); setShowArchived(false); setRepresentativeOnly(false); };
  const choose = (problemId: string, side: 'left' | 'right') => {
    if (side === 'left') { setLeftProblemId(problemId); setLeftAttemptId(null); }
    else { setRightProblemId(problemId); setRightAttemptId(null); }
  };
  const openDetail = (id: string) => { setComparisonId(id); setMode('detail'); };
  const cancelEditor = () => setMode(comparisonId ? 'detail' : 'select');
  const saved = async (id: string) => {
    await client.invalidateQueries({ queryKey: ['problem-comparisons', userId] });
    setComparisonId(id); setMode('detail');
  };
  const archive = async (comparison: ComparisonData) => {
    const operationId = uuid();
    const body: PatchComparisonInput = { operation_id: operationId, archived: !comparison.archived };
    const key = `archive:${comparison.id}`;
    const fingerprint = JSON.stringify({ id: comparison.id, version: comparison.version, archived: !comparison.archived });
    try {
      await runComparisonCommand<PatchComparisonResponse>(userId, key, {
        fingerprint, operationId, method: 'PATCH', path: `/problem-comparisons/${encodeURIComponent(comparison.id)}`,
        ifMatch: `"${comparison.version}"`, body,
      });
      clearComparisonCommand(userId, key);
      await client.invalidateQueries({ queryKey: ['problem-comparisons', userId] });
      if (comparison.id === comparisonId) await client.invalidateQueries({ queryKey: ['problem-comparison', userId, comparisonId] });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        clearComparisonCommand(userId, key);
        await client.invalidateQueries({ queryKey: ['problem-comparisons', userId] });
      }
      throw error;
    }
  };

  return <section className="workspace comparisons-page" aria-labelledby="comparisons-title">
    {checkProblemId && <ProblemAnswerCheck userId={userId} problemId={checkProblemId} onClose={() => setCheckProblemId(null)} />}
    {mode === 'list' && <>
      <header className="comparison-page-heading page-head"><div><span className="eyebrow">TWO EXAMPLES</span><h1 id="comparisons-title">双例对比</h1><p className="muted">自己选择两道题，记录看见的差异。这里的比较不会代替原作答或掌握依据。</p></div><div className="comparison-actions"><button type="button" className="secondary" onClick={browseLibrary}>浏览题目与代表题</button><button type="button" onClick={startNew}>新建对比</button></div></header>
      <div className="comparison-filter-row">
        <label>学科<select value={subjectId} onChange={(event) => setSubjectId(event.target.value)}><option value="">全部学科</option>{subjects.data?.data.items.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select></label>
        <label>涉及题目<select value={problemFilter} onChange={(event) => setProblemFilter(event.target.value)}><option value="">全部题目</option>{filterProblems.data?.pages.flatMap((page) => page.data.items).map((problem) => <option key={problem.id} value={problem.id}>{problem.title || problem.statement?.slice(0, 60) || '未命名题目'}</option>)}</select></label>
        <label className="comparison-check"><input type="checkbox" checked={listArchived} onChange={(event) => setListArchived(event.target.checked)} />查看已归档</label>
      </div>
      {filterProblems.hasNextPage && <button type="button" className="text-button" disabled={filterProblems.isFetchingNextPage} onClick={() => void filterProblems.fetchNextPage()}>加载更多题目以供筛选</button>}
      {subjects.isError && <Feedback error={subjects.error} />}
      {comparisons.isPending ? <p className="muted" role="status">正在读取已保存的对比…</p> : comparisons.isError ? <div><Feedback error={comparisons.error} /><button type="button" className="secondary" onClick={() => void comparisons.refetch()}>重试</button></div> : comparisonItems.length === 0 ? <div className="panel comparison-empty"><h2>{listArchived ? '没有已归档对比' : '还没有双例对比'}</h2><p className="muted">选择两道本人题目后，可以从条件、公式、入口或结论等维度记录差异。跳过选择不会写入任何比较事实。</p><button type="button" onClick={startNew}>选择两道题</button></div> : <ol className="comparison-record-list">{comparisonItems.map((item) => <li className="panel" key={item.id}>
        <div className="comparison-record-heading"><div><span className="eyebrow">{item.archived ? '已归档' : '已保存'}</span><h2>题目对比</h2></div><span className="muted">v{item.version}</span></div>
        <div className="comparison-record-sources"><button type="button" className="text-button" onClick={() => onOpenProblem(item.left_problem_id)}>左例题目 →</button><button type="button" className="text-button" onClick={() => onOpenProblem(item.right_problem_id)}>右例题目 →</button></div>
        <p>{item.conclusion || firstText(item) || '已保存一组部分比较。'}</p>
        {item.source_changed && <p className="comparison-warning">原题或作答在保存比较后有更新；这条比较仍保留原结论。</p>}
        <div className="comparison-actions"><button type="button" className="secondary" onClick={() => openDetail(item.id)}>查看材料与比较</button><button type="button" className="text-button" onClick={() => { setComparisonId(item.id); setMode('edit'); }}>编辑文字</button><ArchiveButton archived={item.archived} onToggle={() => archive(item)} /></div>
      </li>)}</ol>}
      {comparisons.hasNextPage && <button className="secondary" type="button" disabled={comparisons.isFetchingNextPage} onClick={() => void comparisons.fetchNextPage()}>{comparisons.isFetchingNextPage ? '正在加载…' : '加载更多对比'}</button>}
    </>}

    {mode === 'select' && <section aria-labelledby="comparison-select-title">
      <header className="comparison-page-heading"><div><span className="eyebrow">CHOOSE TWO PROBLEMS</span><h1 id="comparison-select-title">选择两道题</h1><p className="muted">请选择不同的题目。没有代表题时，可以从全部题目中选择。</p></div><button type="button" className="text-button" onClick={() => setMode('list')}>跳过，不保存</button></header>
      <div className="comparison-filter-row">
        <label>学科<select value={subjectId} onChange={(event) => setSubjectId(event.target.value)}><option value="">全部学科</option>{subjects.data?.data.items.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select></label>
        <label className="comparison-check"><input type="checkbox" checked={representativeOnly} onChange={(event) => setRepresentativeOnly(event.target.checked)} />只看代表题</label>
        <label className="comparison-check"><input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} />查看归档题目</label>
      </div>
      <div className="comparison-selection-status"><span>左例：{leftProblem?.title || (leftProblemId ? '已选题目' : '尚未选择')}</span><span>右例：{rightProblem?.title || (rightProblemId ? '已选题目' : '尚未选择')}</span></div>
      {problems.isPending ? <p className="muted" role="status">正在读取题目…</p> : problems.isError ? <div><Feedback error={problems.error} /><button type="button" className="secondary" onClick={() => void problems.refetch()}>重试</button></div> : problemItems.length === 0 ? <div className="panel comparison-empty"><p className="muted">{representativeOnly ? '还没有代表题。取消“只看代表题”后，可从全部题目中选择。' : '目前没有可显示的题目。'}</p><button type="button" className="secondary" onClick={() => setMode('list')}>返回，不保存</button></div> : <ol className="comparison-problem-list">{problemItems.map((problem) => <ProblemChoiceRow key={problem.id} userId={userId} problem={problem} leftProblemId={leftProblemId} rightProblemId={rightProblemId} onChoose={(id, side) => { if (side) choose(id, side); }} onStartProblem={onStartProblem} onCheck={setCheckProblemId} />)}</ol>}
      {problems.hasNextPage && <button type="button" className="secondary" disabled={problems.isFetchingNextPage} onClick={() => void problems.fetchNextPage()}>{problems.isFetchingNextPage ? '正在加载…' : '加载更多题目'}</button>}
      <div className="comparison-actions"><button type="button" className="secondary" onClick={() => setMode('list')}>返回，不保存</button><button type="button" disabled={!leftProblemId || !rightProblemId || leftProblemId === rightProblemId} onClick={() => setMode('edit')}>继续填写差异</button></div>
    </section>}

    {mode === 'library' && <section aria-labelledby="comparison-library-title">
      <header className="comparison-page-heading"><div><span className="eyebrow">PROBLEM LIBRARY</span><h1 id="comparison-library-title">题目与代表题</h1><p className="muted">可查看和核对原作答、开始一轮新练习、标记代表题，或从单题发起对比。标记不会判定掌握。</p></div><button type="button" className="text-button" onClick={() => setMode('list')}>返回对比</button></header>
      <div className="comparison-filter-row">
        <label>学科<select value={subjectId} onChange={(event) => setSubjectId(event.target.value)}><option value="">全部学科</option>{subjects.data?.data.items.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select></label>
        <label className="comparison-check"><input type="checkbox" checked={representativeOnly} onChange={(event) => setRepresentativeOnly(event.target.checked)} />只看代表题</label>
        <label className="comparison-check"><input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} />查看归档题目</label>
      </div>
      {problems.isPending ? <p role="status" className="muted">正在读取题目…</p> : problems.isError ? <div><Feedback error={problems.error} /><button type="button" className="secondary" onClick={() => void problems.refetch()}>重试</button></div> : problemItems.length === 0 ? <div className="panel comparison-empty"><p className="muted">{representativeOnly ? '还没有代表题。可取消筛选后从全部题目标记。' : '还没有可显示的题目。'}</p></div> : <ol className="comparison-problem-list">{problemItems.map((problem) => <ProblemChoiceRow key={problem.id} userId={userId} problem={problem} leftProblemId="" rightProblemId="" onChoose={(id) => { setLeftProblemId(id); setRightProblemId(''); setLeftAttemptId(null); setRightAttemptId(null); setComparisonId(null); setMode('select'); }} onStartProblem={onStartProblem} onCheck={setCheckProblemId} library />)}</ol>}
      {problems.hasNextPage && <button type="button" className="secondary" disabled={problems.isFetchingNextPage} onClick={() => void problems.fetchNextPage()}>{problems.isFetchingNextPage ? '正在加载…' : '加载更多题目'}</button>}
    </section>}

    {mode === 'edit' && !comparisonId && leftProblemId && rightProblemId && <ComparisonEditor key={`new:${userId}:${leftProblemId}:${rightProblemId}`} userId={userId} leftProblemId={leftProblemId} rightProblemId={rightProblemId} leftAttemptId={leftAttemptId} rightAttemptId={rightAttemptId} onLeftAttemptChange={setLeftAttemptId} onRightAttemptChange={setRightAttemptId} onCancel={cancelEditor} onSaved={(id) => void saved(id)} />}
    {mode === 'detail' && (comparisonDetail.isPending ? <p role="status" className="muted">正在读取对比…</p> : comparisonDetail.isError ? <div><Feedback error={comparisonDetail.error} /><button type="button" className="secondary" onClick={() => void comparisonDetail.refetch()}>重新读取</button><button type="button" className="text-button" onClick={() => setMode('list')}>返回列表</button></div> : selected && <ComparisonDetail userId={userId} comparison={selected} onBack={() => setMode('list')} onEdit={() => setMode('edit')} onOpenProblem={onOpenProblem} onStartProblem={onStartProblem} onArchive={() => void archive(selected)} />)}
    {mode === 'edit' && comparisonId && (comparisonDetail.isPending ? <p role="status" className="muted">正在读取待编辑的对比…</p> : comparisonDetail.isError ? <div><Feedback error={comparisonDetail.error} /><button type="button" className="secondary" onClick={() => void comparisonDetail.refetch()}>重新读取</button></div> : selected && <ComparisonEditor key={`edit:${userId}:${selected.id}`} userId={userId} comparison={selected} leftProblemId={selected.left_problem_id} rightProblemId={selected.right_problem_id} leftAttemptId={selected.left_attempt_id} rightAttemptId={selected.right_attempt_id} onCancel={cancelEditor} onSaved={(id) => void saved(id)} onRereadLatest={async () => {
      const latest = await comparisonDetail.refetch();
      return latest.data?.data ?? null;
    }} />)}
  </section>;
}

function ComparisonDetail({ userId, comparison, onBack, onEdit, onOpenProblem, onStartProblem, onArchive }: {
  userId: string; comparison: ComparisonData; onBack: () => void; onEdit: () => void;
  onOpenProblem: (id: string) => void;
  onStartProblem: (context: { problemId: string; subjectId: string | null; goal: string }) => void;
  onArchive: () => void;
}) {
  return <section className="comparison-detail" aria-labelledby="comparison-detail-title">
    <div className="comparison-page-heading"><div><button type="button" className="text-button" onClick={onBack}>← 对比列表</button><h1 id="comparison-detail-title">两题的对比记录</h1></div><div className="comparison-actions"><button type="button" className="secondary" onClick={onEdit}>编辑文字</button><ArchiveButton archived={comparison.archived} onToggle={onArchive} /></div></div>
    {comparison.source_changed && <p className="comparison-warning" role="status">原题或作答内容后来有更新。以下显示当前原材料；已保存的比较文字仍是你当时记录的内容。</p>}
    <div className="comparison-source-grid">
      <div><ProblemSourcePanel userId={userId} problemId={comparison.left_problem_id} attemptId={comparison.left_attempt_id} label="左例" /><SourceActions problemId={comparison.left_problem_id} onOpenProblem={onOpenProblem} onStartProblem={onStartProblem} /></div>
      <div><ProblemSourcePanel userId={userId} problemId={comparison.right_problem_id} attemptId={comparison.right_attempt_id} label="右例" /><SourceActions problemId={comparison.right_problem_id} onOpenProblem={onOpenProblem} onStartProblem={onStartProblem} /></div>
    </div>
    <section className="panel comparison-saved-observations" aria-label="已保存的比较观察">
      <h2>你记录的差异</h2><dl>{FIELDS.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{comparison[key] || <span className="muted">暂未填写</span>}</dd></div>)}</dl>
      <p className="muted">作答核对与独立程度以各题原记录为准。本比较不会更改它们。</p>
    </section>
  </section>;
}

function ProblemChoiceRow({ userId, problem, leftProblemId, rightProblemId, onChoose, onStartProblem, onCheck, library = false }: {
  userId: string; problem: ProblemData; leftProblemId: string; rightProblemId: string;
  onChoose: (problemId: string, side?: 'left' | 'right') => void;
  onStartProblem: (context: { problemId: string; subjectId: string | null; goal: string }) => void;
  onCheck: (id: string) => void;
  library?: boolean;
}) {
  return <li className="panel">
    <div><span className="eyebrow">{problem.is_representative ? '代表题' : problem.archived ? '已归档' : '题目'}</span><h2>{problem.title || '未命名题目'}</h2><p className="muted">{problem.statement || '没有保存题干。'}</p></div>
    <ProblemQuickActions userId={userId} problem={problem} onStartProblem={onStartProblem} onCompare={() => onChoose(problem.id)} onCheck={onCheck} library={library} />
    {!library && <div className="comparison-actions"><button type="button" className="secondary" disabled={problem.id === rightProblemId} onClick={() => onChoose(problem.id, 'left')}>{problem.id === leftProblemId ? '左例已选' : '选作左例'}</button><button type="button" className="secondary" disabled={problem.id === leftProblemId} onClick={() => onChoose(problem.id, 'right')}>{problem.id === rightProblemId ? '右例已选' : '选作右例'}</button></div>}
  </li>;
}

function ProblemQuickActions({ userId, problem, onStartProblem, onCompare, onCheck, library }: {
  userId: string; problem: ProblemData;
  onStartProblem: (context: { problemId: string; subjectId: string | null; goal: string }) => void;
  onCompare: () => void; onCheck: (id: string) => void; library: boolean;
}) {
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const mark = async () => {
    if (busy) return;
    setBusy(true); setError(null);
    const operationId = uuid();
    const nextRepresentative = !problem.is_representative;
    const body: ProblemPatchInput = { operation_id: operationId, is_representative: nextRepresentative };
    const fingerprint = JSON.stringify({ problemId: problem.id, version: problem.version, is_representative: nextRepresentative });
    const key = `representative:${problem.id}`;
    try {
      await runComparisonCommand<UpdateProblemResponse>(userId, key, {
        fingerprint, operationId, method: 'PATCH', path: `/problems/${encodeURIComponent(problem.id)}`,
        ifMatch: `"${problem.version}"`, body,
      });
      clearComparisonCommand(userId, key);
      await Promise.all([
        client.invalidateQueries({ queryKey: ['comparison-problems', userId] }),
        client.invalidateQueries({ queryKey: ['problem-detail', userId, problem.id] }),
        client.invalidateQueries({ queryKey: ['problem', problem.id] }),
        client.invalidateQueries({ queryKey: ['problems'] }),
      ]);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        clearComparisonCommand(userId, key);
        await client.invalidateQueries({ queryKey: ['comparison-problems', userId] });
        setError(new Error('题目刚被更新，已重新读取列表。请确认当前状态后再点一次。'));
      } else setError(caught instanceof Error ? caught : new Error('代表题状态更新失败，稍后可重试。'));
    } finally { setBusy(false); }
  };
  return <div className="comparison-actions comparison-problem-quick-actions">
    <button type="button" className="text-button" onClick={() => onCheck(problem.id)}>查看与核对原作答</button>
    <button type="button" className="text-button" disabled={busy || problem.archived} onClick={() => void mark()}>{busy ? '正在保存…' : problem.is_representative ? '取消代表题' : '标记为代表题'}</button>
    <button type="button" className="secondary" disabled={problem.archived} onClick={() => onStartProblem({ problemId: problem.id, subjectId: problem.subject_id, goal: `复习：${problem.title || '这道题'}` })}>开始新练习</button>
    {library && <button type="button" className="secondary" disabled={problem.archived} onClick={onCompare}>对比此题</button>}
    {error && <Feedback error={error} />}
  </div>;
}

function SourceActions({ problemId, onOpenProblem, onStartProblem }: { problemId: string; onOpenProblem: (id: string) => void; onStartProblem: (context: { problemId: string; subjectId: string | null; goal: string }) => void }) {
  const problem = useQuery({ queryKey: ['problem-detail', problemId], queryFn: ({ signal }) => request<ProblemResponse>(`/problems/${encodeURIComponent(problemId)}`, { signal }) });
  return <div className="comparison-actions"><button type="button" className="text-button" onClick={() => onOpenProblem(problemId)}>打开题目详情</button><button type="button" className="secondary" onClick={() => onStartProblem({ problemId, subjectId: problem.data?.data.subject_id ?? null, goal: `复习：${problem.data?.data.title || '这道题'}` })}>从此题开始学习</button></div>;
}

function ArchiveButton({ archived, onToggle }: { archived: boolean; onToggle: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const run = async () => {
    if (busy) return;
    setBusy(true); setError(null);
    try { await onToggle(); } catch (caught) { setError(caught instanceof Error ? caught : new Error('操作失败，请重试。')); }
    finally { setBusy(false); }
  };
  return <span className="comparison-archive-action"><button type="button" className="text-button" disabled={busy} onClick={() => void run()}>{busy ? '正在更新…' : archived ? '恢复' : '归档'}</button>{error && <Feedback error={error} />}</span>;
}

const FIELDS = [
  ['conditions', '条件'], ['known_values', '已知量'], ['formulas', '公式'], ['entry_point', '入口'],
  ['diagram', '图形'], ['boundary', '边界'], ['assumptions', '隐含假设'], ['conclusion', '结论'],
] as const;
function firstText(item: ComparisonData) { return FIELDS.map(([key]) => item[key]).find((value) => Boolean(value?.trim())) ?? null; }
