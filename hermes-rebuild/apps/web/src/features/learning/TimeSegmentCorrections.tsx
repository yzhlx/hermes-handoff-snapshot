import { useState } from 'react';
import { ApiError, request } from '../../shared/api/client';
import type { SessionDetailResponse } from '../../shared/api/types';
import { instantToZonedInput, zonedInputToInstant } from './zoned-time';

type Session = SessionDetailResponse['data'];
type Segment = Session['time_segments'][number];

const anomalyLabels: Record<string, string> = {
  excessive_span: '这一段跨度很长，可能是设备休眠或忘记停止计时。',
  crosses_local_day: '这一段跨越了本地学习日，可能把隔夜时间算了进来。',
};

function formatTime(value: string, timezone: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: timezone,
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function formatDuration(seconds: number) {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  if (hours > 0) return `${hours} 小时 ${minutes} 分钟`;
  if (minutes > 0) return `${minutes} 分钟 ${safeSeconds % 60} 秒`;
  return `${safeSeconds} 秒`;
}

/**
 * Timer spans the learner can bring back in line with reality (03 §3).
 *
 * Correcting a span only changes the recorded duration: it never becomes study
 * evidence or a mastery signal, and the original end time stays visible.
 */
export function TimeSegmentCorrections({
  session,
  onCorrected,
}: {
  session: Session;
  onCorrected: () => void;
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [draftEnd, setDraftEnd] = useState('');
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState('');

  async function send(segment: Segment, changes: { ended_at?: string; exclude?: boolean; correction_note?: string | null }) {
    const operationId = crypto.randomUUID();
    const body = { operation_id: operationId, ...changes };
    setBusyId(segment.id);
    setMessage('');
    try {
      await request(`/learning-sessions/${encodeURIComponent(session.id)}/time-segments/${encodeURIComponent(segment.id)}`, {
        method: 'PATCH',
        headers: { 'Idempotency-Key': operationId, 'If-Match': String(session.version) },
        body: JSON.stringify(body),
      });
      setExpandedId(null);
      setDraftEnd('');
      onCorrected();
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setMessage('这段学习在别处已经变化，已重新读取；你的输入仍保留。');
        onCorrected();
      } else if (error instanceof ApiError && error.status === 422) {
        setMessage('校正只能把这段改短，不能超过已经记录或未来的时间。输入已保留。');
      } else {
        setMessage('校正未完成。输入已保留，可以安全重试。');
      }
    } finally {
      setBusyId(null);
    }
  }

  const flagged = session.time_segments.filter((segment) => segment.review_required);
  return (
    <section className="timing-corrections" aria-labelledby="timing-corrections-title">
      <h3 id="timing-corrections-title">计时片段与校正</h3>
      <p className="muted">计时可能包含设备休眠或断线时间。异常跨度会标出来，你可以把它改短或不计入。时长不代表学习成果或掌握。</p>
      {flagged.length > 0 && (
        <p className="timing-warning" role="status">
          有 {flagged.length} 段计时看起来不合理，下面已标出，可以按实际情况修正。
        </p>
      )}
      {session.time_segments.length === 0 ? (
        <p className="muted">没有记录到计时片段。</p>
      ) : (
        <ol className="timing-segment-list">
          {session.time_segments.map((segment) => {
            const supportsTrim = Boolean(segment.ended_at);
            const open = expandedId === segment.id;
            return (
              <li key={segment.id} className={segment.review_required ? 'timing-segment flagged' : 'timing-segment'}>
                <p className="timing-segment-range">
                  {formatTime(segment.started_at, session.day_timezone)}
                  {' – '}
                  {segment.ended_at ? formatTime(segment.ended_at, session.day_timezone) : '仍在计时'}
                  {' · '}
                  {segment.excluded ? '不计入有效计时' : formatDuration(segment.duration_seconds)}
                </p>
                {segment.review_required && (
                  <ul className="timing-segment-flags">
                    {(segment.anomalies ?? []).map((code) => (
                      <li key={code}>{anomalyLabels[code] ?? code}</li>
                    ))}
                  </ul>
                )}
                {segment.correction_note && <p className="muted">你的说明：{segment.correction_note}</p>}
                {segment.original_ended_at && (
                  <p className="muted">原始结束时间：{formatTime(segment.original_ended_at, session.day_timezone)}</p>
                )}
                <div className="timing-segment-actions">
                  {supportsTrim && (
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => {
                        setExpandedId(open ? null : segment.id);
                        setDraftEnd(instantToZonedInput(segment.ended_at as string, session.day_timezone));
                      }}
                    >
                      {open ? '收起校正' : '修正结束时间'}
                    </button>
                  )}
                  <button
                    type="button"
                    className="text-button"
                    disabled={busyId === segment.id}
                    onClick={() => void send(segment, { exclude: !segment.excluded })}
                  >
                    {segment.excluded ? '恢复计入这段' : '不把这段计入'}
                  </button>
                </div>
                {open && (
                  <div className="timing-segment-editor">
                    <label>
                      实际结束时间（{session.day_timezone}）
                      <input
                        type="datetime-local"
                        value={draftEnd}
                        onChange={(event) => setDraftEnd(event.target.value)}
                      />
                    </label>
                    <label>
                      一句话说明（可选）
                      <textarea
                        maxLength={1000}
                        value={notes[segment.id] ?? segment.correction_note ?? ''}
                        onChange={(event) => setNotes((current) => ({ ...current, [segment.id]: event.target.value }))}
                      />
                    </label>
                    <div className="timing-segment-actions">
                      <button
                        type="button"
                        disabled={busyId === segment.id || !draftEnd}
                        onClick={() => {
                          const instant = zonedInputToInstant(draftEnd, session.day_timezone);
                          if (!instant) {
                            setMessage('请填写有效的结束时间。');
                            return;
                          }
                          void send(segment, { ended_at: instant, correction_note: (notes[segment.id] ?? '').trim() || null });
                        }}
                      >
                        保存校正
                      </button>
                      <button type="button" className="secondary" onClick={() => setExpandedId(null)}>
                        取消
                      </button>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      )}
      {message && <p role="status" className="muted">{message}</p>}
    </section>
  );
}
