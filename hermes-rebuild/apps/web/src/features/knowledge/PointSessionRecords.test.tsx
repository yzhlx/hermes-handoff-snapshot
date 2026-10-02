import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { PointSessionRecords } from './PointSessionRecords';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
describe('knowledge point learning records', () => {
  it('filters saved sessions by point and opens the selected real session', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ data: { items: [
      { id: 'QA_TEST_session', goal: '卷积定理复习', knowledge_point_id: 'QA_TEST_point', status: 'ended' },
      { id: 'QA_TEST_other_session', goal: '其他内容', knowledge_point_id: 'QA_TEST_other', status: 'ended' },
    ], next_cursor: null }, meta: { request_id: 'qa' } }))));
    const client = createQueryClient(); client.setDefaultOptions({ queries: { retry: false } });
    const onOpenSession = vi.fn();
    render(<QueryClientProvider client={client}><PointSessionRecords pointId="QA_TEST_point" onOpenSession={onOpenSession} /></QueryClientProvider>);
    fireEvent.click(await screen.findByRole('button', { name: /卷积定理复习/ }));
    expect(onOpenSession).toHaveBeenCalledWith('QA_TEST_session');
    expect(screen.queryByText('其他内容')).not.toBeInTheDocument();
  });
});
