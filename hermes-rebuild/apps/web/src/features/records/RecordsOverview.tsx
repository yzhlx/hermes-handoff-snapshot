import { useState } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { request } from '../../shared/api/client';
import type { RecordsResponse, SubjectsResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { RecordEntry } from './RecordEntry';
import '../review/review-records.css';

export function RecordsOverview({ userId, onOpenSession }: { userId: string; onOpenSession: (id: string) => void }) {
  const [from, setFrom] = useState(''); const [to, setTo] = useState(''); const [subjectId, setSubjectId] = useState('');
  const subjects = useQuery({ queryKey: ['subjects', userId], queryFn: ({ signal }) => request<SubjectsResponse>('/subjects', { signal }) });
  const params = new URLSearchParams({ limit: '100' }); if (from) params.set('from', from); if (to) params.set('to', to); if (subjectId) params.set('subject_id', subjectId);
  const records = useInfiniteQuery({ queryKey: ['records', userId, from, to, subjectId], initialPageParam: null as string | null, queryFn: ({ signal, pageParam }) => request<RecordsResponse>(`/records?${params}${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ''}`, { signal }), getNextPageParam: (page) => page.data.next_cursor ?? undefined });
  const firstPage = records.data?.pages[0]; const items = records.data?.pages.flatMap((page) => page.data.items) ?? [];
  return <section className="records-overview" aria-labelledby="records-overview-title">
    <header className="page-hero record-hero"><div><h2 id="records-overview-title">按日期查看记录</h2><p className="muted">只汇总已保存的学习现场和作答事实。</p></div><button className="text-button" onClick={() => void records.refetch()}>重新加载</button></header>
    <div className="record-filters"><label>从 <input type="date" value={from || firstPage?.data.from_date || ''} onChange={(e) => setFrom(e.target.value)} /></label><label>到 <input type="date" value={to || firstPage?.data.to_date || ''} onChange={(e) => setTo(e.target.value)} /></label><label>学科 <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)}><option value="">全部</option>{subjects.data?.data.items.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select></label></div>
    {subjects.isError && <div><Feedback error={subjects.error} /></div>}
    {records.isPending ? <p className="muted" role="status">正在读取记录…</p> : records.isError ? <div><Feedback error={records.error} /><button className="secondary" onClick={() => void records.refetch()}>重试</button></div> : <>
      {firstPage && <dl className="record-totals"><div><dt>学习现场</dt><dd>{firstPage.data.totals.session_count}</dd></div><div><dt>有内容记录</dt><dd>{firstPage.data.totals.effective_record_count}</dd></div><div><dt>待核对作答</dt><dd>{firstPage.data.totals.pending_count}</dd></div><div><dt>已核对</dt><dd>{firstPage.data.totals.checked_count}</dd></div><div><dt>独立答对</dt><dd>{firstPage.data.totals.independent_correct_count}</dd></div></dl>}
      {items.length === 0 ? <p className="panel muted">这个范围内没有匹配的学习记录。</p> : <ol className="record-list">{items.map((record) => <RecordEntry key={record.id} record={record} onOpen={onOpenSession} />)}</ol>}
      {records.hasNextPage && <button className="secondary" disabled={records.isFetchingNextPage} onClick={() => void records.fetchNextPage()}>{records.isFetchingNextPage ? '正在加载…' : '加载更早记录'}</button>}
    </>}
  </section>;
}
