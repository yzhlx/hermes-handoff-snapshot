// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import type { ReactNode } from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { clearReviewDrafts } from './draft-store';
import { SuggestionsPage } from './SuggestionsPage';
import { DaySummary } from '../records/DaySummary';
import { RecordsOverview } from '../records/RecordsOverview';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.useRealTimers(); clearReviewDrafts(); });
const envelope = (data: unknown, status = 200) => new Response(JSON.stringify({ data, meta: { request_id: 'QA_TEST_records' } }), { status });
const suggestion = (id = 's1', patch: Record<string, unknown> = {}) => ({ id, version: 1, kind: 'review', status: 'available', subject_id: 'sub1', knowledge_point_id: 'kp1', problem_id: 'p1', reason: `QA_TEST reason ${id}`, source_refs: [{ kind: 'attempt', id: 'a1', version: 3, label: '真实作答', occurred_at: '2026-09-29T08:00:00Z', session_id: 'sess1', problem_id: 'p1' }], source_revision: 'rev1', rule_version: 'suggestions-1', generated_at: '2026-09-30T08:00:00Z', expires_at: null, snoozed_until: null, ...patch });
function mount(node: ReactNode) { const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } }); render(<QueryClientProvider client={client}>{node}</QueryClientProvider>); return client; }

describe('review suggestions and factual records', () => {
  it('shows the snooze deadline in account timezone and prevents queuing handled suggestions', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => envelope({ items: [suggestion('s1', { status: 'snoozed', snoozed_until: '2026-10-08T20:00:00Z' })], next_cursor: null, rule_version: 'suggestions-1' })));
    mount(<SuggestionsPage userId="QA_TEST_user" timezone="Asia/Shanghai" onStart={vi.fn()} onOpenSession={vi.fn()} onOpenProblem={vi.fn()} />);
    expect(await screen.findByText('稍后至 2026年10月9日 04:00 Asia/Shanghai')).toBeInTheDocument();
    expect(screen.getByRole('checkbox')).toBeDisabled();
  });
  it('allows correcting a rejected snooze date with a new command', async () => {
    const commands: Array<{ body: string; key: string | null }> = [];
    vi.stubGlobal('fetch', vi.fn(async (_url: string, init: RequestInit = {}) => {
      if (init.method === 'POST') {
        commands.push({ body: String(init.body), key: new Headers(init.headers).get('Idempotency-Key') });
        return commands.length === 1 ? Response.json({ error: { code: 'VALIDATION_ERROR', message: 'Invalid date' } }, { status: 422 }) : envelope(suggestion('s1', { status: 'snoozed' }));
      }
      return envelope({ items: [suggestion()], next_cursor: null, rule_version: 'suggestions-1' });
    }));
    mount(<SuggestionsPage userId="QA_TEST_user" onStart={vi.fn()} onOpenSession={vi.fn()} onOpenProblem={vi.fn()} />);
    await screen.findByText('QA_TEST reason s1');
    const date = screen.getByLabelText('稍后查看日期（留空为7天后）');
    fireEvent.change(date, { target: { value: '2020-01-01' } });
    await userEvent.setup().click(screen.getByRole('button', { name: '稍后查看' }));
    await screen.findByText(/未通过校验/);
    fireEvent.change(date, { target: { value: '2026-10-03' } });
    await userEvent.setup().click(screen.getByRole('button', { name: '稍后查看' }));
    await waitFor(() => expect(commands).toHaveLength(2));
    expect(commands[1].key).not.toBe(commands[0].key);
    expect(commands[1].body).not.toBe(commands[0].body);
    expect(JSON.parse(commands[1].body).snoozed_until).toContain('2026-10-03');
  });
  it('allows zero, one and multiple local selections, starts only the next chosen item, and opens source records', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => url.endsWith('/suggestions/s1') ? envelope(suggestion('s1')) : envelope({ items: [suggestion('s1'), suggestion('s2', { kind: 'continue' })], next_cursor: null, rule_version: 'suggestions-1' })));
    const onStart = vi.fn(); const onOpenSession = vi.fn(); const onOpenProblem = vi.fn();
    mount(<SuggestionsPage userId="QA_TEST_user" onStart={onStart} onOpenSession={onOpenSession} onOpenProblem={onOpenProblem} />);
    expect(await screen.findByText('QA_TEST reason s1')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /开始队列/ })).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getAllByRole('button', { name: /真实作答/ })[0]); expect(onOpenSession).toHaveBeenCalledWith('sess1');
    const checks = screen.getAllByRole('checkbox'); await userEvent.setup().click(checks[0]); await userEvent.setup().click(checks[1]);
    expect(await screen.findByText(/复习队列（2）/)).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: '开始队列中的第一项' }));
    await waitFor(() => expect(onStart).toHaveBeenCalledTimes(1)); expect(onStart).toHaveBeenCalledWith({ subjectId: 'sub1', knowledgePointId: 'kp1', goal: 'QA_TEST reason s1' });
  });

  it('preserves an uncertain command on transport failure and clears a stale command after 409', async () => {
    const commands: Array<{ key: string | null; body: string | null }> = []; let calls = 0;
    vi.stubGlobal('fetch', vi.fn(async (_url: string, init: RequestInit = {}) => {
      if (init.method === 'POST') { commands.push({ key: new Headers(init.headers).get('Idempotency-Key'), body: String(init.body) }); calls++; return calls === 1 ? new Response(JSON.stringify({ error: { code: 'conflict' } }), { status: 409 }) : envelope(suggestion('s1', { status: 'dismissed' })); }
      return envelope({ items: [suggestion()], next_cursor: null, rule_version: 'suggestions-1' });
    }));
    const props = { userId: 'QA_TEST_user', onStart: vi.fn(), onOpenSession: vi.fn(), onOpenProblem: vi.fn() };
    mount(<SuggestionsPage {...props} />); await screen.findByText('QA_TEST reason s1');
    await userEvent.setup().click(screen.getByRole('button', { name: '忽略' })); await screen.findByRole('status');
    expect(commands).toHaveLength(1); expect(screen.getByText(/来源已更新/)).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: '忽略' })); await waitFor(() => expect(commands).toHaveLength(2));
    expect(commands[1].key).not.toBe(commands[0].key);
  });

  it('replays the exact frozen version, key and body after a network failure', async () => {
    const commands: Array<{ key: string | null; match: string | null; body: string | null }> = []; let writes = 0;
    vi.stubGlobal('fetch', vi.fn(async (_url: string, init: RequestInit = {}) => {
      if (init.method === 'POST') { commands.push({ key: new Headers(init.headers).get('Idempotency-Key'), match: new Headers(init.headers).get('If-Match'), body: String(init.body) }); writes++; if (writes === 1) throw new TypeError('offline'); return envelope(suggestion('s1', { status: 'dismissed' })); }
      return envelope({ items: [suggestion()], next_cursor: null, rule_version: 'suggestions-1' });
    }));
    mount(<SuggestionsPage userId="QA_TEST_user" onStart={vi.fn()} onOpenSession={vi.fn()} onOpenProblem={vi.fn()} />);
    await screen.findByText('QA_TEST reason s1'); await userEvent.setup().click(screen.getByRole('button', { name: '忽略' })); await screen.findByText(/命令已保留/);
    await userEvent.setup().click(screen.getByRole('button', { name: '忽略' })); await waitFor(() => expect(commands).toHaveLength(2));
    expect(commands[1]).toEqual(commands[0]); expect(commands[0].match).toBe('1');
  });

  it('shows honest empty day state while displaying pending counts without treating them as independent correct answers', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => envelope({ date: '2026-09-30', timezone: 'Asia/Shanghai', rule_version: 'records-1', source_revision: 'r1', session_count: 1, effective_record_count: 0, pending_count: 2, checked_count: 0, independent_correct_count: 0, learned: [], changes: [], stuck_points: [], error_categories: [], review_candidates: [], source_refs: [] })));
    mount(<DaySummary userId="QA_TEST_user" onOpenSession={vi.fn()} onOpenProblem={vi.fn()} />);
    expect((await screen.findAllByText('暂无已保存的内容。')).length).toBeGreaterThan(0); expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('独立答对').parentElement).toHaveTextContent('独立答对0');
  });

  it('applies date and subject filters to factual record queries and shows server totals', async () => {
    const calls: string[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string) => { calls.push(url); if (url.includes('/subjects')) return envelope({ items: [{ id: 'sub1', name: '数学' }] }); return envelope({ items: [], next_cursor: null, from_date: '2026-09-24', to_date: '2026-09-30', timezone: 'Asia/Shanghai', rule_version: 'records-1', source_revision: 'r1', totals: { session_count: 4, effective_record_count: 2, pending_count: 1, checked_count: 3, independent_correct_count: 1 } }); }));
    mount(<RecordsOverview userId="QA_TEST_user" onOpenSession={vi.fn()} />);
    await screen.findByText('4'); await userEvent.setup().selectOptions(screen.getByLabelText('学科'), 'sub1'); await waitFor(() => expect(calls.some((url) => url.includes('subject_id=sub1'))).toBe(true));
    expect(screen.getAllByText('1')).toHaveLength(2);
  });

  it('uses account dates from server defaults despite a deliberately wrong browser clock', async () => {
    vi.useFakeTimers({ toFake: ['Date'] }); vi.setSystemTime(new Date('2035-06-01T12:00:00Z'));
    const urls: string[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      urls.push(url);
      if (url.includes('/day-summary')) return envelope({ date: '2026-09-30', timezone: 'Asia/Shanghai', rule_version: 'records-1', source_revision: 'r1', session_count: 0, effective_record_count: 0, pending_count: 0, checked_count: 0, independent_correct_count: 0, learned: [], changes: [], stuck_points: [], error_categories: [], review_candidates: [], source_refs: [] });
      return envelope({ items: [], next_cursor: null, from_date: '2026-09-24', to_date: '2026-09-30', timezone: 'Asia/Shanghai', rule_version: 'records-1', source_revision: 'r1', totals: { session_count: 0, effective_record_count: 0, pending_count: 0, checked_count: 0, independent_correct_count: 0 } });
    }));
    mount(<><DaySummary userId="QA_TEST_user" onOpenSession={vi.fn()} onOpenProblem={vi.fn()} /><RecordsOverview userId="QA_TEST_user" onOpenSession={vi.fn()} /></>);
    await screen.findByText('2026-09-30 · Asia/Shanghai · 规则 records-1');
    await screen.findByText('这个范围内没有匹配的学习记录。');
    expect(urls).toContain('/api/v1/day-summary'); expect(urls.some((url) => url.startsWith('/api/v1/records?limit=100'))).toBe(true);
    expect(urls.some((url) => url.includes('2035'))).toBe(false);
    expect((screen.getByLabelText('日期') as HTMLInputElement).value).toBe('2026-09-30');
    expect(screen.getByLabelText('从')).toHaveValue('2026-09-24');
    expect(screen.getByLabelText('到')).toHaveValue('2026-09-30');
  });
});
