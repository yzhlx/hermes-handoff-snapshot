import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { request } from '../../shared/api/client';
import type { LearningMethod, LearningSituation } from './catalog';
import { MethodsBrowser } from './MethodsBrowser';

vi.mock('../../shared/api/client', () => ({ request: vi.fn() }));

const methods: LearningMethod[] = ['active-recall', 'practice-feedback', 'spaced-review', 'worked-example-compare', 'feynman-check'].map((id) => ({
  id, title: id, summary: `${id} summary`, problem: `${id} problem`, situations: ['case'], steps: ['step one', 'step two'], pitfalls: ['pitfall'], content_version: 1,
}));
const situations: LearningSituation[] = [
  { id: 'similar', label: '两道题很像但做法不同', method_ids: ['worked-example-compare'], reason: '比较条件。', allow_free_learning: false },
  { id: 'low-energy', label: '状态差，只想先开始一下', method_ids: ['active-recall'], reason: '可以只做一次。', allow_free_learning: true },
  { id: 'know-what-to-do', label: '知道要干什么', method_ids: [], reason: '直接自由学习。', allow_free_learning: true },
];

function mount(onStart = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return { client, onStart, ...render(<QueryClientProvider client={client}><MethodsBrowser onStart={onStart} /></QueryClientProvider>) };
}

describe('MethodsBrowser', () => {
  beforeEach(() => vi.mocked(request).mockReset());

  it('renders the server catalog and emits the chosen method and situation from the detail start action', async () => {
    vi.mocked(request).mockImplementation(async (path) => ({ data: { items: path === '/learning-methods' ? methods : situations } }) as never);
    const onStart = vi.fn();
    mount(onStart);
    expect(await screen.findAllByRole('button', { name: '查看方法与步骤' })).toHaveLength(5);
    fireEvent.click(screen.getAllByRole('button', { name: '查看方法与步骤' })[0]);
    expect(screen.getByRole('heading', { name: '它解决什么问题' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '什么情况适合用' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '怎么使用' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '常见误区' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '开始使用' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '用「active-recall」开始' }));
    expect(onStart).toHaveBeenCalledWith({ methodId: 'active-recall', situationId: null });
  });

  it('maps a selected situation to methods and preserves the direct free-learning choice', async () => {
    vi.mocked(request).mockImplementation(async (path) => ({ data: { items: path === '/learning-methods' ? methods : situations } }) as never);
    const onStart = vi.fn();
    mount(onStart);
    fireEvent.click(await screen.findByRole('button', { name: '两道题很像但做法不同' }));
    expect(screen.getByText('可以尝试：worked-example-compare')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '查看方法与步骤' })).toHaveLength(1);
    fireEvent.click(screen.getByRole('button', { name: '状态差，只想先开始一下' }));
    fireEvent.click(screen.getByRole('button', { name: '直接自由学习' }));
    expect(onStart).toHaveBeenCalledWith({ methodId: null, situationId: 'low-energy' });
    fireEvent.click(screen.getByRole('button', { name: '知道要干什么' }));
    expect(screen.getByText('直接自由学习。')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '直接自由学习' }));
    expect(onStart).toHaveBeenLastCalledWith({ methodId: null, situationId: 'know-what-to-do' });
  });

  it('shows no partial catalog on load failure and retries both catalog endpoints', async () => {
    vi.mocked(request).mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ data: { items: methods } } as never);
    mount();
    fireEvent.click(await screen.findByRole('button', { name: '重新加载方法' }));
    await waitFor(() => expect(screen.getAllByRole('button', { name: '查看方法与步骤' })).toHaveLength(5));
    expect(request).toHaveBeenCalledWith('/learning-methods', expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(request).toHaveBeenCalledWith('/learning-situations', expect.objectContaining({ signal: expect.any(AbortSignal) }));
  });
});
