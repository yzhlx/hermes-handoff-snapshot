import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, request, setCsrfToken, setUnauthorizedHandler } from '../shared/api/client';
import type { AuthResponse, CurrentSessionResponse, HealthResponse, HomeResponse } from '../shared/api/types';
import { Login } from '../features/auth/Login';
import { LearningSpace } from '../features/learning/LearningSpace';
import { SessionHistory } from '../features/learning/SessionHistory';
import { clearLearningDraft, learningDraftFor } from '../features/learning/draft-store';
import { MethodsBrowser } from '../features/methods/MethodsBrowser';
import { methodStartTarget, PROBLEM_START_METHOD_ID, type MethodStartTarget } from '../features/methods/method-meta';
import { Feedback } from '../shared/ui/Feedback';
import { clearFeedbackDrafts } from '../features/feedback';
import { clearAttachmentDrafts, selectAttachmentOwner } from '../features/attachments';
import { clearKnowledgeDrafts, KnowledgeHome, SubjectSpace } from '../features/knowledge';
import { MyQuotes, clearQuotePendingOperations } from '../features/quotes/Quotes';
import { HomePage } from '../features/home';
import { SuggestionsPage, clearReviewDrafts, selectReviewOwner } from '../features/review';
import { RecordsOverview, DaySummary } from '../features/records';
import { ProblemRecordDetail } from '../features/knowledge/ProblemRecordDetail';
import { ComparisonsPage, clearComparisonDrafts, selectComparisonOwner } from '../features/comparisons';
import { AppShell, type ServiceStatus } from './AppShell';
import { NAV_ITEMS, NAV_RESET_ACTIONS, type AppPage, type NavItem, type NavResetAction } from './navigation';
import { AdvisorPage } from '../features/advisor';
import { StuckPointsPage, clearStuckPointDrafts, selectStuckPointOwner } from '../features/stuck-points';
import { AccountDataPage } from '../features/account';

/** 未登录时不渲染导航项（外壳显示未登录提示）。保持模块级常量，避免每次渲染产生新数组。 */
const SIGNED_OUT_NAV: readonly NavItem[] = [];

export function App() {
  const client = useQueryClient();
  const [page, setPage] = useState<AppPage>('home');
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [historySessionId, setHistorySessionId] = useState<string | null>(null);
  const [sourceProblemId, setSourceProblemId] = useState<string | null>(null);
  const [comparisonProblemId, setComparisonProblemId] = useState<string | null>(null);
  const openComparison = (id: string | null) => { setComparisonProblemId(id); setSourceProblemId(null); setPage('comparisons'); };
  const openSession = (id: string) => { setHistorySessionId(id); setSourceProblemId(null); setPage('history'); };
  /**
   * 导航入口统一走这里：按 navigation.ts 的 NAV_RESET_ACTIONS 查表做状态清理。
   * 进入学习记录要清空待查看的记录；进入题目与对比要关闭题目详情面板并清空对比预填
   * （等价于旧的 openComparison(null)），否则面板与预填会留在新页面上（T5-F1）。
   * 渲染路径里没有页面 id 字面量分支：新增页面只改 navigation.ts 的映射。
   */
  const navigate = (next: AppPage) => {
    const resets: Record<NavResetAction, () => void> = {
      'clear-history-selection': () => setHistorySessionId(null),
      'close-comparison': () => { setComparisonProblemId(null); setSourceProblemId(null); },
    };
    const reset = NAV_RESET_ACTIONS[next];
    if (reset) resets[reset]();
    setPage(next);
  };
  const auth = useQuery({ queryKey: ['auth'], queryFn: ({ signal }) => request<AuthResponse>('/auth/session', { signal }), retry: false });
  const health = useQuery({ queryKey: ['health'], queryFn: ({ signal }) => request<HealthResponse>('/health/ready', { signal }), refetchInterval: 30_000 });
  /**
   * 金句的顶栏承接位（hero 折叠后它是那句金句唯一的去处）。
   * 与 HomePage 用**同一个 query key**，TanStack Query 会去重——不会多发一次请求，
   * 也避免了把 HomePage 的状态往上提到 App（那会让 App 重渲染、连累整个外壳）。
   */
  const homeQuote = useQuery({
    queryKey: ['home', auth.data?.data.user.id],
    queryFn: ({ signal }) => request<HomeResponse>('/home', { signal }),
    enabled: Boolean(auth.data) && page === 'home',
    retry: false,
  });
  const currentLearning = useQuery({
    queryKey: ['learning', 'current'],
    queryFn: ({ signal }) => request<CurrentSessionResponse>('/learning-sessions/current', { signal }),
    enabled: Boolean(auth.data),
    refetchInterval: 15_000,
  });
  const prepareLearning = (configure: (draft: ReturnType<typeof learningDraftFor>) => void) => {
    if (auth.data && currentLearning.isSuccess && !currentLearning.data.data) {
      const draft = learningDraftFor(auth.data.data.user.id);
      if (!draft.startOperation) {
        draft.previousSessionId = null;
        draft.resumeNote = null;
        configure(draft);
      }
    }
    setSourceProblemId(null);
    setPage('learning');
  };
  /**
   * 方法入口分派：入口目标来自 id 元数据映射（features/methods/method-meta.ts），
   * 这里按目标查表执行，渲染路径里没有 `id === '...'` 分支，
   * 因此新增学习方法时本文件不需要改动。
   */
  const startMethods = (choice: { methodId: string | null; situationId: string | null }) => {
    const handlers: Record<MethodStartTarget, () => void> = {
      comparison: () => openComparison(null),
      learning: () => prepareLearning((draft) => {
        draft.methodId = choice.methodId;
        draft.situationId = choice.situationId;
      }),
    };
    handlers[methodStartTarget(choice.methodId)]();
  };
  const clearPrivateQueries = () => {
    const predicate = (query: { queryKey: readonly unknown[] }) => query.queryKey[0] !== 'auth' && query.queryKey[0] !== 'health';
    void client.cancelQueries({ predicate });
    client.removeQueries({ predicate });
  };
  useEffect(() => { setCsrfToken(auth.data?.data.csrf_token); }, [auth.data]);
  useEffect(() => {
    if (auth.data) { selectAttachmentOwner(auth.data.data.user.id); selectReviewOwner(auth.data.data.user.id); selectComparisonOwner(auth.data.data.user.id); selectStuckPointOwner(auth.data.data.user.id); setSourceProblemId(null); }
  }, [auth.data?.data.user.id]);
  useEffect(() => {
    setUnauthorizedHandler(() => {
      const predicate = (query: { queryKey: readonly unknown[] }) => query.queryKey[0] !== 'auth' && query.queryKey[0] !== 'health';
      void client.cancelQueries({ predicate });
      client.removeQueries({ predicate });
      client.setQueryData(['auth'], null);
    });
    return () => setUnauthorizedHandler(undefined);
  }, [client]);
  const logout = useMutation({ mutationFn: () => request<void>('/auth/logout', { method: 'POST' }), onMutate: () => { clearQuotePendingOperations(); clearKnowledgeDrafts(); clearAttachmentDrafts(); clearReviewDrafts(); clearComparisonDrafts(); clearStuckPointDrafts(); }, onSuccess: () => { clearLearningDraft(); clearFeedbackDrafts(); setCsrfToken(undefined); clearPrivateQueries(); client.setQueryData(['auth'], null); setPage('home'); } });
  const signedOut = auth.error instanceof ApiError && auth.error.status === 401 || auth.data === null;
  const serviceStatus: ServiceStatus = health.isSuccess ? 'online' : health.isError ? 'offline' : 'connecting';
  const topbarQuote = homeQuote.data?.data.sections.quote?.data?.daily_quote.quote?.text ?? null;
  return <AppShell
    topbarQuote={topbarQuote}
    page={page}
    navItems={auth.data ? NAV_ITEMS : SIGNED_OUT_NAV}
    username={auth.data?.data.user.username ?? null}
    serviceStatus={serviceStatus}
    banner={<Feedback error={logout.error} />}
    logoutPending={logout.isPending}
    onNavigate={navigate}
    onLogout={() => logout.mutate()}
  >
    {auth.isPending ? <p className="loading" role="status">正在打开书房…</p>
      : signedOut ? <Login onLogin={(response) => { clearPrivateQueries(); learningDraftFor(response.data.user.id); setCsrfToken(response.data.csrf_token); client.setQueryData(['auth'], response); }} />
        : auth.isError ? <div className="panel login"><Feedback error={auth.error} /><button onClick={() => void auth.refetch()}>重新连接</button></div>
          : auth.data && page === 'methods' ? <MethodsBrowser onStart={startMethods} />
            : auth.data && page === 'comparisons' ? <ComparisonsPage key={`${auth.data.data.user.id}:${comparisonProblemId ?? 'all'}`} userId={auth.data.data.user.id} initialProblemId={comparisonProblemId} onOpenProblem={setSourceProblemId} onStartProblem={(choice) => { prepareLearning((draft) => { draft.subject = choice.subjectId ?? ''; draft.knowledgePointId = null; draft.knowledgePointName = null; draft.goal = choice.goal; draft.methodId = PROBLEM_START_METHOD_ID; draft.situationId = null; }); setSourceProblemId(choice.problemId); }} />
            : auth.data && page === 'review' ? <SuggestionsPage userId={auth.data.data.user.id} timezone={auth.data.data.user.timezone} onOpenSession={openSession} onOpenProblem={setSourceProblemId} onStart={(choice) => prepareLearning((draft) => { draft.subject = choice.subjectId ?? ''; draft.knowledgePointId = choice.knowledgePointId; draft.knowledgePointName = null; draft.goal = choice.goal; })} />
            : auth.data && page === 'advisor' ? <AdvisorPage key={auth.data.data.user.id} userId={auth.data.data.user.id} />
              : auth.data && page === 'stuck-points' ? <StuckPointsPage key={auth.data.data.user.id} userId={auth.data.data.user.id} timezone={auth.data.data.user.timezone} onOpenSession={openSession} />
                : auth.data && page === 'account' ? <AccountDataPage onDataRemoved={() => { clearPrivateQueries(); client.setQueryData(['auth'], null); setPage('home'); }} />
                  : auth.data && page === 'summary' ? <DaySummary userId={auth.data.data.user.id} onOpenSession={openSession} onOpenProblem={setSourceProblemId} />
            : auth.data && page === 'history' ? <><RecordsOverview userId={auth.data.data.user.id} onOpenSession={openSession} />{historySessionId && <SessionHistory key={`${auth.data.data.user.id}:${historySessionId}`} userId={auth.data.data.user.id} initialSelectedSessionId={historySessionId} detailOnly />}</>
              : auth.data && page === 'quotes' ? <MyQuotes userId={auth.data.data.user.id} />
                : auth.data && page === 'subjects' ? <KnowledgeHome onOpenSubject={(id) => { setSelectedSubjectId(id); setPage('subject-space'); }} onStartFree={() => prepareLearning((draft) => { draft.subject = ''; draft.knowledgePointId = null; draft.knowledgePointName = null; })} />
                  : auth.data && page === 'subject-space' && selectedSubjectId ? <SubjectSpace userId={auth.data.data.user.id} subjectId={selectedSubjectId} onCompareProblem={openComparison} onBack={() => setPage('subjects')} onOpenSession={(id) => { setHistorySessionId(id); setPage('history'); }} onStartPoint={(context) => prepareLearning((draft) => { draft.subject = context.subjectId; draft.knowledgePointId = context.pointId; draft.knowledgePointName = context.pointName; if (!draft.goal.trim()) draft.goal = context.pointName; })} />
                : auth.data && page === 'learning' ? <LearningSpace userId={auth.data.data.user.id} />
                  : auth.data ? <HomePage userId={auth.data.data.user.id}
                    onOpenSubject={(id) => { setSourceProblemId(null); setSelectedSubjectId(id); setPage('subject-space'); }}
                    onStartFree={() => prepareLearning(() => {})}
                    onContinue={(last) => prepareLearning((draft) => {
                      if (!last) return;
                      draft.subject = last.subject_id ?? '';
                      draft.goal = last.goal || last.resume_note?.trim() || last.summary || '';
                      draft.previousSessionId = last.id;
                      draft.resumeNote = last.resume_note;
                      draft.knowledgePointId = null;
                      draft.knowledgePointName = null;
                      draft.methodId = null;
                      draft.situationId = null;
                    })}
                    onOpenMethods={() => setPage('methods')}
                    onOpenSubjects={() => setPage('subjects')}
                    onOpenMyQuotes={() => setPage('quotes')}
                    onStartMethod={(id) => prepareLearning((draft) => { draft.methodId = id; draft.situationId = null; })}
                    onOpenReview={() => setPage('review')} onOpenSession={openSession}
                    onOpenProblem={setSourceProblemId} onOpenSummary={() => setPage('summary')}
                  /> : null}
    {auth.data && sourceProblemId && <div className="workspace"><ProblemRecordDetail key={`${auth.data.data.user.id}:${sourceProblemId}`} userId={auth.data.data.user.id} problemId={sourceProblemId} onClose={() => setSourceProblemId(null)} onCompare={() => openComparison(sourceProblemId)} concealAnswer={page === 'learning'} /></div>}
  </AppShell>;
}
