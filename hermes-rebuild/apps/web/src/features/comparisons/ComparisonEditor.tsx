import { useState } from 'react';
import { ApiError } from '../../shared/api/client';
import type { ComparisonData, CreateComparisonInput, CreateComparisonResponse, PatchComparisonInput, PatchComparisonResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { comparisonDraftFor, comparisonCommandFor, comparisonCommandIsUncertain, clearComparisonCommand, markComparisonCommandUncertain, runComparisonCommand, type ComparisonDraftFields } from './draft-store';
import { ProblemSourcePanel } from './ProblemSourcePanel';

const fields = [
  ['conditions', '条件'], ['known_values', '已知量'], ['formulas', '公式'], ['entry_point', '入口'],
  ['diagram', '图形'], ['boundary', '边界'], ['assumptions', '隐含假设'], ['conclusion', '结论'],
] as const;
const blankFields: ComparisonDraftFields = {
  conditions: '', known_values: '', formulas: '', entry_point: '', diagram: '', boundary: '', assumptions: '', conclusion: '',
};
const uuid = () => crypto.randomUUID();

export function ComparisonEditor({ userId, comparison, leftProblemId, rightProblemId, leftAttemptId, rightAttemptId, onLeftAttemptChange, onRightAttemptChange, onCancel, onSaved, retryVersion, onRereadLatest }: {
  userId: string;
  comparison?: ComparisonData;
  leftProblemId: string;
  rightProblemId: string;
  leftAttemptId: string | null;
  rightAttemptId: string | null;
  onLeftAttemptChange?: (id: string | null) => void;
  onRightAttemptChange?: (id: string | null) => void;
  onCancel: () => void;
  onSaved: (id: string) => void;
  retryVersion?: number | null;
  onRereadLatest?: () => Promise<ComparisonData | null>;
}) {
  const draftKey = comparison ? `edit:${comparison.id}` : `new:${leftProblemId}:${rightProblemId}`;
  const commandKey = comparison ? `save:${comparison.id}` : `create:${draftKey}`;
  const initial = comparison ? Object.fromEntries(fields.map(([key]) => [key, comparison[key] ?? ''])) as ComparisonDraftFields : blankFields;
  const draft = comparisonDraftFor(userId, draftKey, initial);
  const [values, setValues] = useState<ComparisonDraftFields>(() => ({ ...draft }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [hasConflict, setHasConflict] = useState(false);
  const [acceptedVersion, setAcceptedVersion] = useState<number | null>(null);
  const [latestSnapshot, setLatestSnapshot] = useState<ComparisonData | null>(null);
  const [uncertain, setUncertain] = useState(() => comparisonCommandIsUncertain(userId, commandKey));
  const frozen = comparisonCommandFor(userId, commandKey);
  const frozenBody = frozen?.body;
  const effectiveLeftAttemptId = uncertain && frozenBody && 'left_attempt_id' in frozenBody ? frozenBody.left_attempt_id ?? null : leftAttemptId;
  const effectiveRightAttemptId = uncertain && frozenBody && 'right_attempt_id' in frozenBody ? frozenBody.right_attempt_id ?? null : rightAttemptId;
  const nonEmpty = fields.some(([key]) => Boolean(values[key]?.trim()));

  const update = (key: keyof ComparisonDraftFields, value: string) => {
    const next = { ...values, [key]: value };
    setValues(next);
    Object.assign(draft, next);
    setError(null);
    setMessage(null);
  };

  const save = async () => {
    if (saving || !nonEmpty) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    const operationId = uuid();
    try {
      if (comparison) {
        const version = acceptedVersion ?? retryVersion ?? comparison.version;
        const body: PatchComparisonInput = { operation_id: operationId, ...compactFields(values) };
        const fingerprint = JSON.stringify({ method: 'PATCH', id: comparison.id, version, body: { ...body, operation_id: undefined } });
        const response = await runComparisonCommand<PatchComparisonResponse>(userId, commandKey, {
          fingerprint, operationId, method: 'PATCH', path: `/problem-comparisons/${encodeURIComponent(comparison.id)}`,
          ifMatch: `"${version}"`, body,
        });
        clearComparisonCommand(userId, commandKey);
        onSaved(response.data.id);
      } else {
        const body: CreateComparisonInput = {
          operation_id: operationId,
          left_problem_id: leftProblemId,
          right_problem_id: rightProblemId,
          left_attempt_id: effectiveLeftAttemptId,
          right_attempt_id: effectiveRightAttemptId,
          ...compactFields(values),
        };
        const fingerprint = JSON.stringify({ method: 'POST', body: { ...body, operation_id: undefined } });
        const response = await runComparisonCommand<CreateComparisonResponse>(userId, commandKey, {
          fingerprint, operationId, method: 'POST', path: '/problem-comparisons', body,
        });
        clearComparisonCommand(userId, commandKey);
        onSaved(response.data.id);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error('保存失败，输入仍保留。'));
      const apiError = caught instanceof ApiError ? caught : null;
      if (apiError && (apiError.status === 409 || apiError.status === 422)) {
        clearComparisonCommand(userId, commandKey);
        setUncertain(false);
        if (apiError.status === 409 && comparison) {
          setHasConflict(true);
          setAcceptedVersion(null);
          setLatestSnapshot(null);
        }
      } else if (!apiError || apiError.status === 0 || apiError.status >= 500) {
        markComparisonCommandUncertain(userId, commandKey);
        setUncertain(true);
      }
    } finally {
      setSaving(false);
    }
  };

  const reread = async () => {
    try {
      const latest = await onRereadLatest?.();
      if (!latest) return;
      setLatestSnapshot(latest);
      setAcceptedVersion(latest.version);
      setError(null);
      setMessage(`已读取最新版本 v${latest.version}。请核对下方服务器内容；当前本地输入仍保留。`);
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error('读取最新版本失败，请重试。'));
    }
  };

  return <section className="comparison-editor" aria-labelledby="comparison-editor-title">
    <header className="comparison-page-heading"><div><span className="eyebrow">TWO EXAMPLES</span><h2 id="comparison-editor-title">{comparison ? '整理这组对比例子' : '填写两题的差异'}</h2><p className="muted">比较只记录你写下的观察；不会自动推断相似、改变作答结果或判定掌握。</p></div></header>
    <div className="comparison-source-grid">
      <ProblemSourcePanel userId={userId} problemId={leftProblemId} attemptId={effectiveLeftAttemptId} onAttemptChange={uncertain ? undefined : onLeftAttemptChange} label="左例" />
      <ProblemSourcePanel userId={userId} problemId={rightProblemId} attemptId={effectiveRightAttemptId} onAttemptChange={uncertain ? undefined : onRightAttemptChange} label="右例" />
    </div>
    <div className="comparison-observation-grid">
      {fields.map(([key, label]) => <label key={key}>{label}<textarea maxLength={2000} disabled={uncertain || saving} value={values[key] ?? ''} onChange={(event) => update(key, event.target.value)} placeholder="按你观察到的内容记录，可暂时留空。" /><span className="muted comparison-character-count">{(values[key] ?? '').length}/2000</span></label>)}
    </div>
    {uncertain && <p className="comparison-warning" role="status">上次请求结果不确定。为避免重复创建或覆盖，请先使用原请求重试；表单和作答选择暂时锁定。</p>}
    {latestSnapshot && <details className="comparison-latest-snapshot" open><summary>读取到的服务器版本 v{latestSnapshot.version}</summary><dl>{fields.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{latestSnapshot[key] || '暂未填写'}</dd></div>)}</dl></details>}
    {!nonEmpty && <p className="muted">至少填写一个维度后才能保存。返回或跳过不会创建比较记录。</p>}
    <Feedback error={error} />
    {message && <p className="muted" role="status">{message}</p>}
    <div className="comparison-actions">
      <button type="button" className="secondary" onClick={onCancel} disabled={saving}>返回，不保存</button>
      {hasConflict && <button type="button" className="secondary" onClick={() => void reread()} disabled={saving}>读取最新版本</button>}
      <button type="button" disabled={saving || (!uncertain && !nonEmpty) || (hasConflict && acceptedVersion === null && !retryVersion)} onClick={() => void save()}>{saving ? '正在保存…' : uncertain ? '使用原请求安全重试' : comparison ? '保存比较' : '保存对比记录'}</button>
    </div>
  </section>;
}

function compactFields(values: ComparisonDraftFields) {
  return Object.fromEntries(fields.map(([key]) => [key, values[key]?.trim() || null]));
}
