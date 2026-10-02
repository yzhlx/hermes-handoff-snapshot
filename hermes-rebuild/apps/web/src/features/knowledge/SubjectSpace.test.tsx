import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { SubjectSpace } from './SubjectSpace';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const wrap = (data: unknown) => new Response(JSON.stringify({ data, meta: { request_id: 'QA_TEST' } }));

describe('subject space source records', () => {
  it('opens the saved session and fetches full problem detail from recent records', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/subjects/QA_TEST_subject/space')) return wrap({ subject: { id: 'QA_TEST_subject', name: '信号与系统', group_label: '829' }, chapters: [], recent_sessions: [{ id: 'QA_TEST_session', goal: '卷积复习', status: 'ended' }], recent_problems: [{ id: 'QA_TEST_problem', title: '卷积题', statement: '从题目列表摘要来的题干' }] });
      if (url.includes('/chapters?')) return wrap({ items: [], next_cursor: null });
      if (url.includes('/problems/QA_TEST_problem')) return wrap({ id: 'QA_TEST_problem', title: '卷积题', statement: '完整题干：求两个信号的卷积。', correct_answer: '完整答案：分段积分。', source_note: null, subject_id: 'QA_TEST_subject', archived: false, is_representative: false, knowledge_point_ids: [], attempts: [{ id: 'QA_TEST_attempt', problem_id: 'QA_TEST_problem', session_id: 'QA_TEST_session', occurred_at: '2026-09-01T10:00:00Z', answer_check: 'checked', result: 'incorrect', independence: 'independent', attempt_text: '交换积分次序时漏项', stuck_note: '边界范围', other_error_note: null, error_categories: ['derivation'], verified_at: '2026-09-01T10:10:00Z', evidence_eligibility: { eligible: true }, version: 2, created_at: '2026-09-01T10:00:00Z', updated_at: '2026-09-01T10:10:00Z' }], version: 1, created_at: '2026-09-01T10:00:00Z', updated_at: '2026-09-01T10:10:00Z' });
      throw new Error(`Unexpected URL ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    const client = createQueryClient();
    client.setDefaultOptions({ queries: { retry: false } });
    const onOpenSession = vi.fn();
    render(<QueryClientProvider client={client}><SubjectSpace userId="QA_TEST_user" subjectId="QA_TEST_subject" onBack={vi.fn()} onOpenSession={onOpenSession} onStartPoint={vi.fn()} /></QueryClientProvider>);

    fireEvent.click(await screen.findByRole('button', { name: /卷积复习 · 已结束/ }));
    expect(onOpenSession).toHaveBeenCalledWith('QA_TEST_session');
    fireEvent.click(screen.getByRole('button', { name: /卷积题/ }));
    expect(await screen.findByText('完整题干：求两个信号的卷积。')).toBeInTheDocument();
    expect(screen.getByText('交换积分次序时漏项')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/problems/QA_TEST_problem'), expect.anything());
  });
});
