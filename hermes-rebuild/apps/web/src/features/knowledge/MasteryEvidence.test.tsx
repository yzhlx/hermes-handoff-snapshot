import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { MasteryEvidence } from './MasteryEvidence';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const source = { attempt_id: 'QA_TEST_attempt', attempt_version: 3, problem_id: 'QA_TEST_problem', problem_version: 2 };
const emptyErrorCategories = ['concept', 'modeling', 'condition', 'formula', 'derivation', 'calculation', 'sign', 'unit', 'reading', 'other'].map((category) => ({ category, attempt_count: 0, source_refs: [] }));
const assessment = (evidence_status: 'unsupported' | 'current' | 'stale') => ({ id: 'QA_TEST_assessment', level: 'independent', reason: '阶段性自评', variant_note: null, version: 1, knowledge_point_version: 5, created_at: '2026-09-01T10:00:00Z', evidence_status, evidence_message: evidence_status === 'unsupported' ? '自评，暂无已核证据' : evidence_status === 'stale' ? '来源记录已变化' : '来源仍匹配', source_refs: evidence_status === 'unsupported' ? [] : [source] });
const evidence = (status: 'unsupported' | 'current' | 'stale') => ({ knowledge_point_id: 'QA_TEST_point', knowledge_point_version: 5, rule_version: '1', source_revision: 'rev', counts: { attempt_count: 1, pending_count: 0, checked_count: 1, checked_correct_count: 1, checked_correct_rate: 1, independent_correct_count: 1 }, recent_checked_streak: { count: 1, label: '最近 1 个已核对记录', pending_count: 0, source_refs: [source] }, error_categories: [], source_refs: [source], assessments: [assessment(status)] });
const envelope = (data: unknown) => new Response(JSON.stringify({ data, meta: { request_id: 'qa' } }));
const setup = (fetchMock: ReturnType<typeof vi.fn>) => { vi.stubGlobal('fetch', fetchMock); const client = createQueryClient(); client.setDefaultOptions({ queries: { retry: false } }); render(<QueryClientProvider client={client}><MasteryEvidence userId="QA_TEST_user" pointId="QA_TEST_point" pointVersion={5} /></QueryClientProvider>); };

describe('mastery evidence interaction', () => {
  it('uses Chinese labels, collapses remaining error categories, and keeps empty metrics compact', async () => {
    const empty = { ...evidence('unsupported'), counts: { attempt_count: 0, pending_count: 0, checked_count: 0, checked_correct_count: 0, checked_correct_rate: null, independent_correct_count: 0 }, source_refs: [], assessments: [], error_categories: [
      { category: 'concept', attempt_count: 2, source_refs: [] }, { category: 'modeling', attempt_count: 1, source_refs: [] }, { category: 'condition', attempt_count: 1, source_refs: [] }, { category: 'other', attempt_count: 1, source_refs: [] },
    ] };
    const fetchMock = vi.fn(async () => envelope(empty));
    setup(fetchMock);
    expect(await screen.findByText('概念：2 次')).toBeInTheDocument();
    expect(screen.getByText('思路 / 建模：1 次')).toBeInTheDocument();
    expect(screen.getByText('条件判断：1 次')).toBeInTheDocument();
    expect(screen.getByText(/查看其余 1 类/)).toBeInTheDocument();
    expect(screen.queryByText('other')).not.toBeInTheDocument();
    expect(screen.queryByText('关联作答')).not.toBeInTheDocument();
  });

  it('shows a quiet empty error-category state when none are recorded', async () => {
    const empty = { ...evidence('unsupported'), counts: { attempt_count: 0, pending_count: 0, checked_count: 0, checked_correct_count: 0, checked_correct_rate: null, independent_correct_count: 0 }, source_refs: [], assessments: [], error_categories: emptyErrorCategories };
    vi.stubGlobal('fetch', vi.fn(async () => envelope(empty)));
    const client = createQueryClient(); client.setDefaultOptions({ queries: { retry: false } });
    render(<QueryClientProvider client={client}><MasteryEvidence userId="QA_TEST_user" pointId="QA_TEST_point" pointVersion={5} /></QueryClientProvider>);
    expect(await screen.findByText('暂无已记录的错误原因。')).toBeInTheDocument();
    expect(screen.queryByText('关联作答')).not.toBeInTheDocument();
  });

  it.each(['unsupported', 'current', 'stale'] as const)('shows the backend %s evidence status without upgrading it', async (status) => {
    const fetchMock = vi.fn(async () => envelope(evidence(status)));
    setup(fetchMock);
    expect(await screen.findAllByText(status === 'unsupported' ? '暂无已核证据' : status === 'current' ? '来源仍匹配' : '来源后来有变化')).not.toHaveLength(0);
    expect(screen.getByText(/自评说明：阶段性自评/)).toBeInTheDocument();
  });

  it('opens source records and preserves a self-assessment after a version conflict', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/evidence')) return envelope(evidence('current'));
      if (url.endsWith('/problem-attempts/QA_TEST_attempt')) return envelope({ id: source.attempt_id, problem_id: source.problem_id, session_id: 'QA_TEST_session', occurred_at: '2026-09-01T10:00:00Z', answer_check: 'checked', result: 'correct', independence: 'independent', attempt_text: '按定义展开', stuck_note: null, error_categories: [], verified_at: '2026-09-01T10:01:00Z', evidence_eligibility: { eligible: true, reason: '可用' }, version: 3, created_at: '2026-09-01T10:00:00Z', updated_at: '2026-09-01T10:01:00Z' });
      if (url.endsWith('/problems/QA_TEST_problem')) return envelope({ id: source.problem_id, title: '实际题目', statement: '实际题干内容', correct_answer: null, source_note: null, subject_id: 'QA_TEST_subject', archived: false, is_representative: false, knowledge_point_ids: ['QA_TEST_point'], version: 2, created_at: '2026-09-01T10:00:00Z', updated_at: '2026-09-01T10:01:00Z' });
      if (url.endsWith('/mastery-assessments')) {
        expect(new Headers(init?.headers).get('If-Match')).toBe('"5"');
        const body = JSON.parse(String(init?.body)) as { level: string; reason: string; operation_id: string };
        expect(body).toMatchObject({ level: 'typical', reason: '可以完成常见题' });
        return new Response(JSON.stringify({ error: { code: 'VERSION_CONFLICT', message: '版本冲突' }, meta: { request_id: 'qa' } }), { status: 409 });
      }
      throw new Error(`Unexpected URL ${url}`);
    });
    setup(fetchMock);
    fireEvent.click(await screen.findByRole('button', { name: /打开原题与这次作答/ }));
    expect(await screen.findByText('实际题干内容')).toBeInTheDocument();
    expect(screen.getByText(/作答过程：按定义展开/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('掌握参考状态'), { target: { value: 'typical' } });
    fireEvent.change(screen.getByLabelText('自评理由（可选）'), { target: { value: '可以完成常见题' } });
    fireEvent.click(screen.getByRole('button', { name: '保存这条自评' }));
    expect(await screen.findByText(/知识点已在其他窗口更新/)).toBeInTheDocument();
    expect(screen.getByLabelText('掌握参考状态')).toHaveValue('typical');
    expect(screen.getByLabelText('自评理由（可选）')).toHaveValue('可以完成常见题');
    expect(await screen.findAllByText('来源仍匹配')).not.toHaveLength(0);
  });
});
