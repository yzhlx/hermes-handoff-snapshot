import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { KnowledgeHome } from './KnowledgeHome';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const envelope = (data: unknown) => new Response(JSON.stringify({ data, meta: { request_id: 'qa' } }));

describe('knowledge home subject entries', () => {
  it('renders the five equal subjects with the backend group and a separate free-learning entry', async () => {
    const names = ['信号与系统', '电路基础', '高等数学', '英语', '政治'];
    vi.stubGlobal('fetch', vi.fn(async () => envelope({ items: names.map((name, index) => ({ id: `QA_TEST_subject_${index}`, name, group_label: index < 2 ? '上海大学 829' : '公共课' })) })));
    const client = createQueryClient();
    client.setDefaultOptions({ queries: { retry: false } });
    const onOpenSubject = vi.fn();
    const onStartFree = vi.fn();
    render(<QueryClientProvider client={client}><KnowledgeHome onOpenSubject={onOpenSubject} onStartFree={onStartFree} /></QueryClientProvider>);
    for (const name of names) expect(await screen.findByRole('button', { name: new RegExp(name) })).toBeInTheDocument();
    expect(screen.getByText('上海大学 829')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /自由学习/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /信号与系统/ }));
    fireEvent.click(screen.getByRole('button', { name: /自由学习/ }));
    expect(onOpenSubject).toHaveBeenCalledWith('QA_TEST_subject_0');
    expect(onStartFree).toHaveBeenCalledOnce();
  });
});
