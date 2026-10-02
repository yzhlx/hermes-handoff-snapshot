import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { request } from '../../shared/api/client';
import type { AdvisorListResponse, AdvisorRunData, AdvisorRunResponse, CancelAdvisorInput, CancelAdvisorResponse, CreateAdvisorInput, CreateAdvisorResponse, SubjectsResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import './advisor.css';

type CitedText = AdvisorRunData['facts'][number];
type EvidenceRef = AdvisorRunData['evidence_refs'][number];

const uuid = () => crypto.randomUUID();

const STATUS_TEXT: Record<string, string> = {
  ready: '已完成',
  insufficient: '记录不足',
  degraded: '部分降级',
  blocked: '已阻断',
  cancelled: '已取消',
};

function statusText(status: string) { return STATUS_TEXT[status] ?? status; }

function formatTime(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function resolveCitation(id: string, evidenceRefs: EvidenceRef[]) {
  const match = evidenceRefs.find((ref) => ref.id === id);
  return match?.label || id;
}

/**
 * Optional AI advisor. It only explains the owner's own records: facts come
 * from saved evidence, interpretations are marked as possible, and nothing
 * here writes back to problems, attempts, mastery or comparisons. The copy is
 * a suggestion surface, never a command.
 */
export function AdvisorPage({ userId }: { userId: string }) {
  const client = useQueryClient();
  const [subjectId, setSubjectId] = useState('');
  const [topic, setTopic] = useState('');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [createOperation, setCreateOperation] = useState<string | null>(null);
  const [createError, setCreateError] = useState<Error | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [cancelError, setCancelError] = useState<Error | null>(null);

  const subjects = useQuery({
    queryKey: ['subjects', userId],
    queryFn: ({ signal }) => request<SubjectsResponse>('/subjects', { signal }),
  });
  const list = useQuery({
    queryKey: ['advisor-runs', userId],
    queryFn: ({ signal }) => request<AdvisorListResponse>('/advisor/analyses?limit=50', { signal }),
    refetchInterval: 15_000,
  });
  const detail = useQuery({
    queryKey: ['advisor-run', userId, selectedRunId],
    queryFn: ({ signal }) => request<AdvisorRunResponse>(`/advisor/analyses/${encodeURIComponent(selectedRunId ?? '')}`, { signal }),
    enabled: Boolean(selectedRunId),
  });

  const runs = [...(list.data?.data.items ?? [])].sort((left, right) => right.created_at.localeCompare(left.created_at));
  const selected = detail.data?.data ?? null;
  const subjectName = (id: string | null) => subjects.data?.data.items.find((subject) => subject.id === id)?.name ?? null;

  const submitCreate = async (operationId: string) => {
    setCreating(true); setCreateError(null);
    try {
      const body: CreateAdvisorInput = {
        operation_id: operationId,
        topic: topic.trim() ? topic.trim() : null,
        subject_id: subjectId || null,
        knowledge_point_id: null,
      };
      const response = await request<CreateAdvisorResponse>('/advisor/analyses', {
        method: 'POST',
        headers: { 'Idempotency-Key': operationId },
        body: JSON.stringify(body),
      });
      setSelectedRunId(response.data.id);
      setCreateOperation(null);
      setTopic('');
      setSubjectId('');
      await client.invalidateQueries({ queryKey: ['advisor-runs', userId] });
    } catch (error) {
      setCreateError(error instanceof Error ? error : new Error('操作未完成，请稍后重试。'));
    } finally { setCreating(false); }
  };
  const startCreate = () => { const operationId = uuid(); setCreateOperation(operationId); void submitCreate(operationId); };
  const retryCreate = () => { if (createOperation) void submitCreate(createOperation); };

  const cancelRun = async (runId: string) => {
    const operationId = uuid();
    setCancellingId(runId); setCancelError(null);
    try {
      const body: CancelAdvisorInput = { operation_id: operationId };
      await request<CancelAdvisorResponse>(`/advisor/analyses/${encodeURIComponent(runId)}/cancel`, {
        method: 'POST',
        headers: { 'Idempotency-Key': operationId },
        body: JSON.stringify(body),
      });
      await Promise.all([
        client.invalidateQueries({ queryKey: ['advisor-runs', userId] }),
        client.invalidateQueries({ queryKey: ['advisor-run', userId, runId] }),
      ]);
    } catch (error) {
      setCancelError(error instanceof Error ? error : new Error('操作未完成，请稍后重试。'));
    } finally { setCancellingId(null); }
  };

  return <section className="workspace advisor-page" aria-labelledby="advisor-title">
    <header className="advisor-page-heading page-head">
      <div>
        <span className="eyebrow">OPTIONAL AI ADVISOR</span>
        <h1 id="advisor-title">Hermes 顾问</h1>
        <p className="muted">可以让 Hermes 帮你看看这些记录说明了什么。顾问只做解释，不会改写你的记录，也不会替你决定下一步。</p>
      </div>
    </header>

    <form className="panel advisor-start" aria-labelledby="advisor-start-title" onSubmit={(event) => { event.preventDefault(); if (!creating) startCreate(); }}>
      <div className="advisor-start-heading">
        <span className="eyebrow">START AN ANALYSIS</span>
        <h2 id="advisor-start-title">让 Hermes 看看这些记录</h2>
        <p className="muted">可以选择一个学科，或写下你想了解的主题。顾问只读取已有记录，不会新增或改动它们。</p>
      </div>
      <label className="advisor-field" htmlFor="advisor-subject">学科
        <select id="advisor-subject" value={subjectId} onChange={(event) => setSubjectId(event.target.value)}>
          <option value="">不指定学科</option>
          {subjects.data?.data.items.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
        </select>
      </label>
      <label className="advisor-field" htmlFor="advisor-topic">想了解的主题（可选）
        <textarea id="advisor-topic" rows={4} maxLength={2000} value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="例如：这两次练习的差异说明了什么？" />
      </label>
      <p className="advisor-character-count muted" aria-live="polite">{topic.length} / 2000</p>
      {subjects.isError && <Feedback error={subjects.error} />}
      {createError && <div className="advisor-start-error">
        <Feedback error={createError} />
        <button type="button" className="secondary" disabled={creating || !createOperation} onClick={retryCreate}>{creating ? '正在重试…' : '重试这次分析'}</button>
      </div>}
      <div className="advisor-actions">
        <button type="submit" disabled={creating}>{creating ? '正在整理…' : '让 Hermes 看看'}</button>
      </div>
    </form>

    <section className="panel advisor-history" aria-labelledby="advisor-history-title">
      <span className="eyebrow">PAST ANALYSES</span>
      <h2 id="advisor-history-title">过去的分析</h2>
      {list.isPending ? <p className="muted" role="status">正在读取过去的分析…</p>
        : list.isError ? <div><Feedback error={list.error} /><button type="button" className="secondary" onClick={() => void list.refetch()}>重试</button></div>
          : runs.length === 0 ? <p className="muted">还没有分析记录。可以先发起一次，让 Hermes 看看这些学习记录。</p>
            : <ol className="advisor-history-list">{runs.map((run) => <li key={run.id}>
              <button
                type="button"
                className={run.id === selectedRunId ? 'advisor-run-entry selected' : 'advisor-run-entry'}
                aria-current={run.id === selectedRunId ? 'true' : undefined}
                aria-label={`打开分析：${run.topic || '未命名分析'}`}
                onClick={() => setSelectedRunId(run.id)}
              >
                <strong>{run.topic || '未命名分析'}</strong>
                <span className="muted">{statusText(run.status)} · {formatTime(run.created_at)}</span>
              </button>
            </li>)}</ol>}
    </section>

    {selectedRunId && <section className="panel advisor-run" aria-labelledby="advisor-run-title">
      {detail.isPending ? <p className="muted" role="status">正在读取这次分析…</p>
        : detail.isError ? <div><Feedback error={detail.error} /><button type="button" className="secondary" onClick={() => void detail.refetch()}>重试</button><button type="button" className="text-button" onClick={() => setSelectedRunId(null)}>收起</button></div>
          : !selected ? <p className="muted">没有找到这次分析。</p>
            : <AdvisorRunReport run={selected} subjectName={subjectName(selected.subject_id)} cancelling={cancellingId === selected.id} cancelError={cancellingId === selected.id ? cancelError : null} onCancel={() => void cancelRun(selected.id)} />}
    </section>}
  </section>;
}

function AdvisorRunReport({ run, subjectName, cancelling, cancelError, onCancel }: {
  run: AdvisorRunData;
  subjectName: string | null;
  cancelling: boolean;
  cancelError: Error | null;
  onCancel: () => void;
}) {
  return <>
    <header className="advisor-run-heading">
      <div>
        <span className="eyebrow">ANALYSIS</span>
        <h2 id="advisor-run-title">{run.topic || '未命名分析'}</h2>
        <p className="muted">{statusText(run.status)} · {formatTime(run.created_at)}{subjectName ? ` · ${subjectName}` : ''} · 依据 {run.evidence_count} 条记录</p>
      </div>
      {run.status !== 'cancelled' && <div className="advisor-actions">
        <button type="button" className="secondary" disabled={cancelling} onClick={onCancel}>{cancelling ? '正在取消…' : '取消本次分析'}</button>
      </div>}
    </header>

    {run.summary && <p className="advisor-summary">{run.summary}</p>}

    <AdvisorBanner run={run} />

    <p className="advisor-privacy">{run.privacy.external === false
      ? '本次分析不发送到外部服务。'
      : `本次分析会发送到外部服务：${run.privacy.provider}。范围：${run.privacy.scope}。`}</p>

    <CitedSection id="advisor-facts" className="advisor-facts" eyebrow="RECORDED FACTS" title="记录事实"
      help="来自你自己学习记录的事实，未经模型改写。" items={run.facts} evidenceRefs={run.evidence_refs}
      empty="这次没有可展示的记录事实。" />

    <CitedSection id="advisor-inferences" className="advisor-inferences" eyebrow="POSSIBLE INTERPRETATIONS" title="可能解释"
      help="AI 的解释只是一种可能，需要你自行判断。" items={run.inferences} evidenceRefs={run.evidence_refs}
      empty={run.status === 'blocked' ? '模型输出未通过安全校验，已丢弃，因此这里没有解释。' : '这次没有可展示的解释。'} />

    <section className="advisor-section advisor-missing" aria-labelledby="advisor-missing-title">
      <span className="eyebrow">STILL MISSING</span>
      <h3 id="advisor-missing-title">还缺什么</h3>
      <p className="muted">要让解释更贴近事实，这些信息可能有用。</p>
      {run.missing_information.length === 0
        ? <p className="muted">暂时没有发现明显缺失的信息。</p>
        : <ul className="advisor-missing-list">{run.missing_information.map((item, index) => <li key={`${index}:${item}`}>{item}</li>)}</ul>}
    </section>

    <details className="advisor-versions">
      <summary>版本信息</summary>
      <dl>
        <div><dt>数据版本</dt><dd>{run.data_version}</dd></div>
        <div><dt>模型</dt><dd>{run.model_id}</dd></div>
        <div><dt>提示词版本</dt><dd>{run.prompt_version}</dd></div>
        <div><dt>策略版本</dt><dd>{run.policy_version}</dd></div>
        <div><dt>规则版本</dt><dd>{run.rule_version}</dd></div>
      </dl>
    </details>

    {cancelError && <Feedback error={cancelError} />}
  </>;
}

function AdvisorBanner({ run }: { run: AdvisorRunData }) {
  if (run.status === 'degraded') return <div className="advisor-banner degraded" role="status">
    <p>AI 暂时不可用；下面的记录事实仍来自你自己的学习记录。</p>
    {run.degradation_reason && <small>原因：{run.degradation_reason}</small>}
  </div>;
  if (run.status === 'blocked') return <div className="advisor-banner blocked" role="status">
    <p>本次模型输出未通过安全校验，已丢弃，不会改写你的记录。</p>
    {run.degradation_reason && <small>原因：{run.degradation_reason}</small>}
  </div>;
  if (run.status === 'insufficient') return <div className="advisor-banner insufficient" role="status">
    <p>记录还不足，可以先开始学习。</p>
  </div>;
  if (run.status === 'cancelled') return <div className="advisor-banner cancelled" role="status">
    <p>这次分析已取消，没有生成新的解释。</p>
  </div>;
  return null;
}

function CitedSection({ id, className, eyebrow, title, help, items, evidenceRefs, empty }: {
  id: string;
  className: string;
  eyebrow: string;
  title: string;
  help: string;
  items: CitedText[];
  evidenceRefs: EvidenceRef[];
  empty: string;
}) {
  return <section className={`advisor-section ${className}`} aria-labelledby={`${id}-title`}>
    <span className="eyebrow">{eyebrow}</span>
    <h3 id={`${id}-title`}>{title}</h3>
    <p className="muted">{help}</p>
    {items.length === 0 ? <p className="muted">{empty}</p> : <ul className="advisor-cited-list">{items.map((item, index) => <li key={`${index}:${item.text}`}>
      <p className="advisor-cited-text">{item.text}</p>
      {item.source_refs.length > 0 && <p className="advisor-citations">{item.source_refs.map((ref) => <span key={ref} className="advisor-citation">{resolveCitation(ref, evidenceRefs)}</span>)}</p>}
    </li>)}</ul>}
  </section>;
}
