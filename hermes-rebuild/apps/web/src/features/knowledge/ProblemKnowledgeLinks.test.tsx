import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { ProblemKnowledgeLinks } from './ProblemKnowledgeLinks';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const envelope = (data: unknown) => new Response(JSON.stringify({ data, meta: { request_id: 'qa' } }));
const problem = { id: 'QA_TEST_problem', title: 'QA_TEST 原题', statement: '题干', subject_id: 'QA_TEST_subject', archived: false, correct_answer: null, source_note: null, is_representative: false, knowledge_point_ids: ['QA_TEST_other_point'], version: 7, created_at: '2026-09-01T10:00:00Z', updated_at: '2026-09-01T10:00:00Z' };
function mount(fetchMock: ReturnType<typeof vi.fn>, canAssociate = true) { vi.stubGlobal('fetch', fetchMock); const client = createQueryClient(); client.setDefaultOptions({ queries: { retry: false }, mutations: { retry: false } }); render(<QueryClientProvider client={client}><ProblemKnowledgeLinks userId="QA_TEST_user" subjectId="QA_TEST_subject" pointId="QA_TEST_point" canAssociate={canAssociate} /></QueryClientProvider>); }

describe('problem and knowledge point links', () => {
  it('replaces links without dropping existing points and sends the frozen problem version', async () => {
    let submitted: Record<string, unknown> | undefined;
    let match: string | null = null;
    const fetchMock = vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url.includes('/problems?')) return envelope({ items: [problem], next_cursor: null });
      if (url.endsWith('/knowledge-links')) { submitted = JSON.parse(String(init.body)) as Record<string, unknown>; match = new Headers(init.headers).get('If-Match'); return envelope({ problem: { ...problem, knowledge_point_ids: ['QA_TEST_other_point', 'QA_TEST_point'], version: 8 }, knowledge_point_ids: ['QA_TEST_other_point', 'QA_TEST_point'] }); }
      throw new Error(`Unexpected URL ${url}`);
    });
    mount(fetchMock);
    fireEvent.click(await screen.findByLabelText(/QA_TEST 原题/));
    fireEvent.click(screen.getByRole('button', { name: '关联到此知识点' }));
    await waitFor(() => expect(submitted).toBeDefined());
    expect(submitted?.knowledge_point_ids).toEqual(['QA_TEST_other_point', 'QA_TEST_point']);
    expect(match).toBe('"7"');
  });

  it('blocks creating a new link when the point or parent chapter is archived', async () => {
    const fetchMock = vi.fn(async (url: string) => { if (url.includes('/problems?')) return envelope({ items: [problem], next_cursor: null }); throw new Error(`Unexpected write or URL ${url}`); });
    mount(fetchMock, false);
    expect(await screen.findByText(/已归档/)).toBeInTheDocument();
    expect(await screen.findByLabelText(/QA_TEST 原题/)).toBeDisabled();
    expect(screen.queryByRole('button', { name: '关联到此知识点' })).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
