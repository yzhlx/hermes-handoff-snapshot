/*
 * 侧栏导航的状态清理回归测试（T5-F1）。
 * ------------------------------------------------------------------
 * 既有行为：从侧栏进入「题目与对比」等价于旧的 openComparison(null)——
 * 必须同时关闭题目详情面板（sourceProblemId）并清空对比预填（comparisonProblemId）。
 * 重构后 navigate() 只 setPage，两个 state 会留着：面板不消失、对比页仍带着预填。
 * 这里锁住修复后的行为：面板消失 + 对比页以「无预填」的状态重新挂载。
 * 本文件为新增测试，不修改任何既有测试。
 */
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App } from './App';
import { homeFixture } from './test-home-fixture';
import { clearLearningDraft } from '../features/learning/draft-store';
import { clearComparisonDrafts } from '../features/comparisons';
import { setCsrfToken, setUnauthorizedHandler } from '../shared/api/client';

const problem = {
  id: 'QA_TEST_nav_problem',
  subject_id: 'QA_TEST_nav_subject',
  title: 'QA_TEST 导航用例题目',
  statement: 'QA_TEST 题干',
  correct_answer: null,
  source_note: null,
  archived: false,
  is_representative: false,
  knowledge_point_ids: [],
  attempts: [],
  version: 1,
};

const quoteData = { daily_quote: { local_date: '2026-10-01', day_timezone: 'Asia/Shanghai', quote: null, reason: 'no_eligible_quotes', preference: null } };

function homeWithProblemSuggestion() {
  const home = homeFixture();
  home.sections.suggestions = {
    status: 'ready',
    source_revision: 'QA_TEST_nav',
    error: null,
    data: {
      has_more: false,
      items: [{
        id: 'QA_TEST_nav_suggestion',
        kind: 'unverified',
        status: 'available',
        generated_at: '2026-10-01T08:00:00Z',
        rule_version: 'nav-test',
        source_revision: 'QA_TEST_nav',
        version: 1,
        reason: 'QA_TEST 这道题还没有核对。',
        source_refs: [{ kind: 'problem', id: problem.id, problem_id: problem.id, label: 'QA_TEST 题目来源', version: 1, occurred_at: '2026-10-01T08:00:00Z' }],
      }],
    },
  } as never;
  return home;
}

beforeEach(() => { clearComparisonDrafts(); clearLearningDraft(); });
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  clearComparisonDrafts();
  clearLearningDraft();
  setCsrfToken(undefined);
  setUnauthorizedHandler(undefined);
});

function mount() {
  const envelope = (data: unknown) => Response.json({ data, meta: { request_id: 'QA_TEST_nav' } });
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    if (path.endsWith('/auth/session')) return envelope({ user: { id: 'QA_TEST_owner', username: 'QA_TEST_owner', timezone: 'Asia/Shanghai' }, csrf_token: 'QA_TEST_csrf' });
    if (path.endsWith('/health/ready')) return envelope({ status: 'ok' });
    if (path.endsWith('/home')) return envelope(homeWithProblemSuggestion());
    if (path.endsWith('/learning-sessions/current')) return envelope(null);
    if (path.includes('/learning-sessions?')) return envelope({ items: [], next_cursor: null });
    if (path.endsWith('/subjects')) return envelope({ items: [{ id: problem.subject_id, name: 'QA_TEST 学科' }] });
    if (path.endsWith(`/problems/${problem.id}`)) return envelope(problem);
    if (path.includes('/problems?')) return envelope({ items: [problem], next_cursor: null });
    if (path.includes('/problem-comparisons?')) return envelope({ items: [], next_cursor: null });
    if (path.endsWith('/quotes/today')) return envelope(quoteData);
    if (path.includes('/quotes/favorites')) return envelope({ items: [], disliked: [], next_cursor: null });
    throw new Error(`Unexpected test request: ${path}`);
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
  return userEvent.setup();
}

describe('sidebar navigation resets page-scoped state', () => {
  it('closes the problem detail panel when entering 题目与对比 from the sidebar', async () => {
    const user = mount();
    await user.click(await screen.findByRole('button', { name: /QA_TEST 题目来源 · v1/ }));
    expect(await screen.findByRole('heading', { name: '题目记录详情' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '题目与对比' }));

    expect(await screen.findByRole('heading', { name: '双例对比' })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('heading', { name: '题目记录详情' })).not.toBeInTheDocument());
  });

  it('drops the preselected comparison problem when entering 题目与对比 from the sidebar', async () => {
    const user = mount();
    await user.click(await screen.findByRole('button', { name: /QA_TEST 题目来源 · v1/ }));
    await user.click(await screen.findByRole('button', { name: '选择另一题对比 →' }));
    expect(await screen.findByText(`左例：${problem.title}`)).toBeInTheDocument();

    // 页面内部的筛选状态（不写入 draft-store）：只有重新挂载才会被重置，
    // 而重新挂载只发生在 comparisonProblemId 被清空导致 key 变化时。
    const archivedFilter = screen.getByLabelText('查看归档题目');
    await user.click(archivedFilter);
    expect(archivedFilter).toBeChecked();

    await user.click(screen.getByRole('button', { name: '题目与对比' }));

    await waitFor(() => expect(screen.getByLabelText('查看归档题目')).not.toBeChecked());
    expect(screen.queryByRole('heading', { name: '题目记录详情' })).not.toBeInTheDocument();
  });
});
