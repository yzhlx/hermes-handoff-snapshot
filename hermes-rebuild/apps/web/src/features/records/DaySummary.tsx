import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { request } from '../../shared/api/client';
import type { DaySummaryResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { Lulu } from '../companion';
import '../review/review-records.css';

function sourceDate(value: string, timezone: string) { return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short', timeZone: timezone }).format(new Date(value)); }

export function DaySummary({ userId, onOpenSession, onOpenProblem }: { userId: string; onOpenSession: (id: string) => void; onOpenProblem: (id: string) => void }) {
  const [date, setDate] = useState('');
  const summary = useQuery({ queryKey: ['day-summary', userId, date], queryFn: ({ signal }) => request<DaySummaryResponse>(`/day-summary${date ? `?date=${encodeURIComponent(date)}` : ''}`, { signal }) });
  const data = summary.data?.data;
  const openRef = (ref: DaySummaryResponse['data']['source_refs'][number]) => {
    if (ref.session_id || ref.kind === 'session') onOpenSession(ref.session_id ?? ref.id);
    else if (ref.problem_id || ref.kind === 'problem') onOpenProblem(ref.problem_id ?? ref.id);
  };
  const sourceLink = (ref: DaySummaryResponse['data']['source_refs'][number]) => <>{ref.session_id || ref.kind === 'session' || ref.problem_id || ref.kind === 'problem' ? <button className="text-button" onClick={() => openRef(ref)}>{ref.label} · v{ref.version} →</button> : <span>{ref.label} · v{ref.version}</span>}</>;
  const block = (title: string, items: { text: string; source_refs: DaySummaryResponse['data']['source_refs'] }[]) => <section className="day-summary-block"><h3>{title}</h3>{items.length === 0 ? <p className="muted">暂无已保存的内容。</p> : <ul>{items.map((item, index) => <li key={`${title}-${index}`}><p>{item.text}</p>{item.source_refs.map((ref) => <span className="day-source-ref" key={`${ref.kind}:${ref.id}:${ref.version}`}>{sourceLink(ref)} <small>{data ? sourceDate(ref.occurred_at, data.timezone) : ref.occurred_at} · {data?.timezone ?? 'UTC'}</small></span>)}</li>)}</ul>}</section>;
  return <section className="workspace day-summary" aria-labelledby="day-summary-title"><header className="history-heading page-head"><div><span className="eyebrow">A FACTUAL DAY CLOSE</span><h1 id="day-summary-title">今日收尾</h1><p className="muted">根据当天保存的记录整理，不需要补打卡。</p></div><label>日期 <input type="date" value={date || data?.date || ''} onChange={(event) => setDate(event.target.value)} /></label></header>
    {summary.isPending ? <p role="status" className="muted">正在读取当天记录…</p> : summary.isError ? <div><Feedback error={summary.error} /><button className="secondary" onClick={() => void summary.refetch()}>重试</button></div> : data && <>
      <p className="muted">{data.date} · {data.timezone} · 规则 {data.rule_version}</p>
      <dl className="record-totals"><div><dt>学习现场</dt><dd>{data.session_count}</dd></div><div><dt>有内容记录</dt><dd>{data.effective_record_count}</dd></div><div><dt>待核对作答</dt><dd>{data.pending_count}</dd></div><div><dt>已核对</dt><dd>{data.checked_count}</dd></div><div><dt>独立答对</dt><dd>{data.independent_correct_count}</dd></div></dl>
      {data.effective_record_count === 0 && data.pending_count === 0 && data.checked_count === 0 ? <p className="panel muted">这一天没有保存可收尾的学习内容。无需补记；有记录后这里会显示实际事实。</p> : null}
      <div className="day-summary-grid">{block('学到了什么', data.learned)}{block('有证据的变化', data.changes)}{block('卡点', data.stuck_points)}{block('以后可以回顾', data.review_candidates)}</div>
      <section className="day-summary-block"><h3>已记录的错误类别</h3>{data.error_categories.length === 0 ? <p className="muted">暂无已核对的错误类别。</p> : <ul>{data.error_categories.map((item) => <li key={item.category}><strong>{item.category} · {item.count} 次</strong>{item.source_refs.map((ref) => <span className="day-source-ref" key={`${ref.kind}:${ref.id}:${ref.version}`}>{sourceLink(ref)} <small>{data ? sourceDate(ref.occurred_at, data.timezone) : ref.occurred_at} · {data.timezone}</small></span>)}</li>)}</ul>}</section>
      <details className="day-source-details"><summary>查看当天所有来源（{data.source_refs.length}）</summary><ul>{data.source_refs.map((ref) => <li key={`${ref.kind}:${ref.id}:${ref.version}`}>{sourceLink(ref)}</li>)}</ul></details>
      <Lulu context={data.effective_record_count === 0 ? 'empty' : 'summary'} userId={userId} />
    </>}
  </section>;
}
