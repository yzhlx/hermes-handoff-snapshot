import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, request } from '../../shared/api/client';
import type {
  CurrentSessionResponse,
  LearningMethodsResponse,
  LearningSituationsResponse,
  SessionResponse,
  SubjectsResponse,
  KnowledgePointResponse,
} from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { learningDraftFor } from './draft-store';
import { SessionFeedback } from '../feedback';
import { Lulu } from '../companion';
import { ContinuationContext } from './ContinuationContext';
import './learning.css';

const currentKey = ['learning', 'current'] as const;
const historyKey = ['learning', 'history'] as const;
type Session = NonNullable<CurrentSessionResponse['data']>;
type LifecycleAction = 'pause' | 'resume' | 'end' | 'cancel';

const statusLabel: Record<Session['status'], string> = {
  active: '进行中',
  paused: '已暂停',
  ended: '已结束',
  cancelled: '已取消',
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
  const remainingSeconds = safeSeconds % 60;
  return hours > 0
    ? `${hours} 小时 ${minutes} 分钟`
    : minutes > 0
      ? `${minutes} 分钟 ${remainingSeconds} 秒`
      : `${remainingSeconds} 秒`;
}

export function LearningSpace({ userId }: { userId: string }) {
  const client = useQueryClient();
  const [draft] = useState(() => learningDraftFor(userId));
  const [goal, updateGoal] = useState(draft.goal);
  const [subject, updateSubject] = useState(draft.subject);
  const [timingEnabled, updateTimingEnabled] = useState(draft.timingEnabled);
  const [now, setNow] = useState(() => Date.now());
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [, setContextRevision] = useState(0);
  const cancelTrigger = useRef<HTMLButtonElement>(null);
  const cancelDialog = useRef<HTMLDialogElement>(null);
  const [lastEnded, setLastEnded] = useState(false);
  const [feedbackSessionId, setFeedbackSessionId] = useState<string | null>(draft.feedbackSessionId);
  const [feedbackSubjectId, setFeedbackSubjectId] = useState<string | null>(draft.feedbackSubjectId);

  const setGoal = (value: string) => {
    draft.goal = value;
    updateGoal(value);
  };
  const setSubject = (value: string) => {
    const previous = draft.subject;
    draft.subject = value;
    if (draft.knowledgePointId && value !== previous) {
      draft.knowledgePointId = null;
      draft.knowledgePointName = null;
    }
    updateSubject(value);
  };

  const subjects = useQuery({
    queryKey: ['subjects'],
    queryFn: ({ signal }) => request<SubjectsResponse>('/subjects', { signal }),
  });
  const current = useQuery({
    queryKey: currentKey,
    queryFn: ({ signal }) => request<CurrentSessionResponse>('/learning-sessions/current', { signal }),
    refetchInterval: 15_000,
  });
  const knowledgePointId = current.data?.data?.knowledge_point_id ?? draft.knowledgePointId;
  const knowledgePoint = useQuery({
    queryKey: ['knowledge-point', knowledgePointId],
    queryFn: ({ signal }) => request<KnowledgePointResponse>(`/knowledge-points/${knowledgePointId}`, { signal }),
    enabled: Boolean(knowledgePointId),
  });
  const methods = useQuery({
    queryKey: ['learning-methods'],
    queryFn: ({ signal }) => request<LearningMethodsResponse>('/learning-methods', { signal }),
    enabled: Boolean(current.data?.data?.method_id ?? draft.methodId),
  });
  const situations = useQuery({
    queryKey: ['learning-situations'],
    queryFn: ({ signal }) => request<LearningSituationsResponse>('/learning-situations', { signal }),
    enabled: Boolean(draft.situationId),
  });
  const session = current.data?.data;
  useEffect(() => {
    if (!session?.timing_enabled || session.status !== 'active') return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [session?.id, session?.status, session?.timing_enabled]);
  useEffect(() => {
    if (confirmCancel) {
      cancelDialog.current?.querySelector('button')?.focus();
    } else if (session) {
      cancelTrigger.current?.focus();
    }
  }, [confirmCancel, session?.id]);

  const onLifecycleError = (error: Error) => {
    if (error instanceof ApiError && error.status === 409) {
      draft.endOperation = null;
      draft.lifecycleOperation = null;
      void client.invalidateQueries({ queryKey: currentKey });
      void client.invalidateQueries({ queryKey: historyKey });
    }
  };

  const onStartError = (error: Error) => {
    if (error instanceof ApiError && error.status === 409) {
      draft.startOperation = null;
      void client.invalidateQueries({ queryKey: currentKey });
    }
  };

  const start = useMutation({
    mutationFn: async () => {
      const command = {
        goal: goal.trim() || null,
        subject_id: subject || null,
        knowledge_point_id: draft.knowledgePointId,
        timing_enabled: timingEnabled,
        method_id: draft.methodId,
        previous_session_id: draft.previousSessionId,
        resume_note: draft.resumeNote,
      };
      const payload = JSON.stringify(command);
      if (draft.startOperation?.payload !== payload) {
        draft.startOperation = { payload, id: crypto.randomUUID() };
      }
      const id = draft.startOperation.id;
      return request<SessionResponse>('/learning-sessions', {
        method: 'POST',
        headers: { 'Idempotency-Key': id },
        body: JSON.stringify({ ...command, operation_id: id }),
      });
    },
    onSuccess: (response) => {
      client.setQueryData(currentKey, response);
      draft.startOperation = null;
      draft.feedbackSessionId = null;
      draft.feedbackSubjectId = null;
      setFeedbackSessionId(null);
      setFeedbackSubjectId(null);
      draft.methodId = null;
      draft.situationId = null;
      draft.previousSessionId = null;
      draft.resumeNote = null;
      setLastEnded(false);
      void client.invalidateQueries({ queryKey: historyKey });
    },
    onError: onStartError,
  });

  const lifecycle = useMutation({
    mutationFn: async (action: LifecycleAction) => {
      const session = current.data?.data;
      if (!session) throw new Error('学习现场已变化，请刷新后重试。');
      const payload = `${action}:${session.id}:${session.version}`;
      if (action === 'end') {
        if (draft.endOperation?.payload !== payload) {
          draft.endOperation = { payload, id: crypto.randomUUID() };
        }
      } else if (draft.lifecycleOperation?.payload !== payload) {
        draft.lifecycleOperation = { payload, id: crypto.randomUUID() };
      }
      const operation = action === 'end' ? draft.endOperation : draft.lifecycleOperation;
      if (!operation) throw new Error('无法创建操作编号，请重试。');
      const pathAction = action === 'end' ? 'end' : action;
      return request<SessionResponse>(`/learning-sessions/${session.id}/${pathAction}`, {
        method: 'POST',
        headers: {
          'Idempotency-Key': operation.id,
          'If-Match': `"${session.version}"`,
        },
        body: JSON.stringify({ operation_id: operation.id }),
      });
    },
    onSuccess: (response, action) => {
      draft.endOperation = null;
      draft.lifecycleOperation = null;
      if (action === 'end' || action === 'cancel') {
        client.setQueryData(currentKey, { data: null });
        setLastEnded(action === 'end');
        const endedSessionId = action === 'end' ? response.data.id : null;
        const endedSubjectId = action === 'end' ? response.data.subject_id : null;
        draft.feedbackSessionId = endedSessionId;
        draft.feedbackSubjectId = endedSubjectId;
        setFeedbackSessionId(endedSessionId);
        setFeedbackSubjectId(endedSubjectId);
        if (action === 'end') { setGoal(''); draft.knowledgePointId = null; draft.knowledgePointName = null; }
        setConfirmCancel(false);
      } else {
        client.setQueryData(currentKey, response);
      }
      void client.invalidateQueries({ queryKey: historyKey });
    },
    onError: onLifecycleError,
  });

  const subjectName =
    subjects.data?.data.items.find((item) => item.id === session?.subject_id)?.name ?? '自由学习';
  const activeMethodId = session?.method_id ?? draft.methodId;
  const methodName = methods.data?.data.items.find((item) => item.id === activeMethodId)?.title;
  const situationName = situations.data?.data.items.find((item) => item.id === draft.situationId)?.label;
  const busy = start.isPending || lifecycle.isPending;

  return (
    <section className="workspace learning-space" aria-labelledby="workspace-title">
      {/* 参考图的 hero 是学科名 + 章节面包屑 + 一张实景照片；照片资产本批不可得，
          按船长裁决不伪造占位图，改用令牌化的暖米色带承载层级。 */}
      <header className="page-hero learning-hero">
        <span className="eyebrow">ONE STEP AT A TIME</span>
        <h1 id="workspace-title">把注意力留给学习。</h1>
        <p className="muted">从一个小目标开始，让每一段投入都留下记录。</p>
      </header>

      <div className="panel learning-panel">
        <div className="section-label">
          <span className="dot" />{session ? '学习现场' : '你的下一步'}
        </div>
        {(session?.previous_session_id ?? draft.previousSessionId) && <ContinuationContext
          userId={userId}
          previousSessionId={(session?.previous_session_id ?? draft.previousSessionId)!}
          resumeNote={(session ? session.resume_note : draft.resumeNote) ?? null}
        />}
        {current.isPending ? (
          <p role="status">正在恢复学习现场…</p>
        ) : current.isError ? (
          <>
            <Feedback error={current.error} />
            <button className="secondary" onClick={() => void current.refetch()}>重新连接</button>
          </>
        ) : session ? (
          <>
            <p className="subject-caption">{subjectName}{session.knowledge_point_id && ` · ${knowledgePoint.data?.data.name ?? '知识点'}`} · {statusLabel[session.status]}</p>
            <h2>{session.goal || '专注于此刻的一段学习'}</h2>
            {(session.method_id || draft.situationId) && (
              <p className="method-context">
                {session.method_id && <>学习方法：{methodName ?? '此方法已记录'}</>}
                {session.method_id && draft.situationId && ' · '}
                {draft.situationId && <>所选情境：{situationName ?? '情境已选择'}</>}
              </p>
            )}
            <p className="muted">
              开始于 {formatTime(session.started_at, session.day_timezone)} ·
              {' '}现场已保存，可在另一台设备继续。
            </p>
            {session.timing_enabled && (
              <p className="session-duration" role="timer" aria-label="本段有效计时">
                本段有效计时：{formatDuration(
                  (session.effective_duration_seconds ?? 0) +
                    (session.status === 'active' && current.dataUpdatedAt
                      ? Math.max(0, Math.floor((now - current.dataUpdatedAt) / 1000))
                      : 0),
                )}
                <span> · 暂停时间不计入</span>
              </p>
            )}
            {session.timing_enabled && (
              <p className="time-limitation">
                计时可能包含设备休眠或断线时间；异常跨度会标出来，可在「学习记录」里按实际情况校正。时长不代表学习成果或掌握。
              </p>
            )}
            {session.timing_review_required && (
              <p className="time-limitation" role="status">
                这段计时里有跨度看起来不合理，请在「学习记录」中确认后再决定是否计入。
              </p>
            )}
            <Feedback error={lifecycle.error} />
            <div className="session-actions">
              {session.status === 'active' ? (
                <button className="secondary" disabled={busy} onClick={() => lifecycle.mutate('pause')}>
                  {lifecycle.isPending && lifecycle.variables === 'pause' ? '正在暂停…' : '暂停学习'}
                </button>
              ) : (
                <button className="secondary" disabled={busy} onClick={() => lifecycle.mutate('resume')}>
                  {lifecycle.isPending && lifecycle.variables === 'resume' ? '正在恢复…' : '继续学习'}
                </button>
              )}
              <button disabled={busy} onClick={() => lifecycle.mutate('end')}>
                {lifecycle.isPending && lifecycle.variables === 'end' ? '正在保存…' : '结束并保存这一段'}
              </button>
              <button
                ref={cancelTrigger}
                className="text-button cancel-session"
                disabled={busy}
                onClick={() => setConfirmCancel(true)}
              >
                取消本段
              </button>
            </div>
            {confirmCancel && (
              <dialog
                ref={cancelDialog}
                className="cancel-confirm"
                open
                aria-labelledby="cancel-title"
                aria-describedby="cancel-description"
                onCancel={(event) => {
                  event.preventDefault();
                  setConfirmCancel(false);
                }}
              >
                <h3 id="cancel-title">取消这段学习？</h3>
                <p id="cancel-description">
                  这会停止当前现场，不会删除已经保存的记录。尚未提交的学习内容不会作为完成记录。
                </p>
                <div className="session-actions">
                  <button className="secondary" onClick={() => setConfirmCancel(false)}>返回继续</button>
                  <button className="danger-button" disabled={busy} onClick={() => lifecycle.mutate('cancel')}>
                    {lifecycle.isPending && lifecycle.variables === 'cancel' ? '正在取消…' : '确认取消本段'}
                  </button>
                </div>
              </dialog>
            )}
          </>
        ) : (
          <form onSubmit={(event) => { event.preventDefault(); if (!busy) start.mutate(); }}>
            {lastEnded && <p className="success-text" role="status">这一段学习已保存，尚未记录掌握情况。</p>}
            {lastEnded && <Lulu context="complete" userId={userId} />}
            {draft.knowledgePointId && <p className="method-context">知识点：{draft.knowledgePointName ?? knowledgePoint.data?.data.name ?? '正在读取知识点…'} <button type="button" className="text-button" onClick={() => { draft.knowledgePointId = null; draft.knowledgePointName = null; setContextRevision((revision) => revision + 1); }}>移除此关联</button></p>}
            {(draft.methodId || draft.situationId) && (
              <div className="method-context" aria-live="polite">
                {draft.methodId && <span>学习方法：{methodName ?? '正在读取方法信息…'}</span>}
                {situationName && <span> · 情境：{situationName}</span>}
                <button
                  type="button"
                  className="text-button"
                  onClick={() => {
                    draft.methodId = null;
                    draft.situationId = null;
                    setContextRevision((revision) => revision + 1);
                  }}
                >
                  清除方法
                </button>
              </div>
            )}
            <div className="learning-goal-card">
              <label>
                这次想学什么？
                <input
                  placeholder="例如：继续看采样这一节"
                  maxLength={500}
                  value={goal}
                  onChange={(event) => setGoal(event.target.value)}
                  disabled={busy}
                />
              </label>
            </div>
            <div className="learning-setup-row">
              <label>
                学科
                <select
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                  disabled={busy || subjects.isPending || subjects.isError}
                >
                  <option value="">自由学习</option>
                  {subjects.data?.data.items.map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={timingEnabled}
                  onChange={(event) => {
                    draft.timingEnabled = event.target.checked;
                    updateTimingEnabled(event.target.checked);
                  }}
                  disabled={busy}
                />
                <span>记录本次有效计时（可选）</span>
              </label>
            </div>
            <Feedback error={subjects.error} />
            {subjects.isError && (
              <button type="button" className="secondary" onClick={() => void subjects.refetch()}>
                重新加载学科
              </button>
            )}
            <Feedback error={start.error} />
            <button className="learning-start" disabled={busy || subjects.isPending || subjects.isError}>
              {start.isPending ? '正在开始…' : '开始这一段学习 →'}
            </button>
          </form>
        )}
      </div>

      {feedbackSessionId && !session && (
        <SessionFeedback userId={userId} sessionId={feedbackSessionId} subjectId={feedbackSubjectId} />
      )}

      <aside className="quiet-note">
        <span className="eyebrow">HERMES · 学习现场</span>
        <p>学习现场保存在书房服务中。结束只表示这一段已收尾，不代表已经掌握。</p>
      </aside>
    </section>
  );
}
