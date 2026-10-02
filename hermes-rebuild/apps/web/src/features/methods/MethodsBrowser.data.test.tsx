/*
 * 硬门禁：连续追加多个学习方法后，目录必须全部自动渲染。
 * 本文件只喂数据、不改渲染代码：
 * - 服务端目录 5 种方法 → 追加到 8 种；
 * - 服务端目录 9 个情境 → 追加到 11 个；
 * - 目录标题里的数量由数据长度推导（五大 → 八大），不是写死的文案。
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { request } from '../../shared/api/client';
import type { LearningMethod, LearningSituation } from './catalog';
import { MethodsBrowser } from './MethodsBrowser';

vi.mock('../../shared/api/client', () => ({ request: vi.fn() }));

function method(id: string): LearningMethod {
  return { id, title: `QA_TEST 方法 ${id}`, summary: `${id} 摘要`, problem: `${id} 问题`, situations: [`${id} 适用`], steps: [`${id} 第一步`], pitfalls: [`${id} 误区`], content_version: 1 };
}

/** 服务端目录的 5 种方法，加 3 种将来会追加的方法。 */
const baseMethods = ['active-recall', 'practice-feedback', 'spaced-review', 'worked-example-compare', 'feynman-check'].map(method);
const appendedMethods = ['QA_TEST_method_6', 'QA_TEST_method_7', 'QA_TEST_method_8'].map(method);

function situation(id: string, methodIds: string[] = []): LearningSituation {
  return { id, label: `QA_TEST 情境 ${id}`, method_ids: methodIds, reason: `${id} 的理由`, allow_free_learning: true };
}

const baseSituations = ['s1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9'].map((id) => situation(id));
const appendedSituations = [situation('QA_TEST_situation_10', ['QA_TEST_method_8']), situation('QA_TEST_situation_11', ['QA_TEST_method_6', 'QA_TEST_method_7'])];

function mount(methods: LearningMethod[], situations: LearningSituation[], onStart = vi.fn()) {
  vi.mocked(request).mockImplementation(async (path) => ({ data: { items: path === '/learning-methods' ? methods : situations } }) as never);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MethodsBrowser onStart={onStart} /></QueryClientProvider>);
  return { onStart };
}

describe('data-driven method catalog', () => {
  beforeEach(() => vi.mocked(request).mockReset());

  it('renders every appended method automatically and derives the catalog count from data', async () => {
    mount([...baseMethods, ...appendedMethods], baseSituations);
    const cards = await screen.findAllByRole('button', { name: '查看方法与步骤' });
    expect(cards).toHaveLength(baseMethods.length + appendedMethods.length);
    for (const item of appendedMethods) expect(screen.getByRole('heading', { name: item.title })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '八大学习方法' })).toBeInTheDocument();
  });

  it('derives the five-method heading from the unmodified server catalog', async () => {
    mount(baseMethods, baseSituations);
    expect(await screen.findByRole('heading', { name: '五大学习方法' })).toBeInTheDocument();
  });

  it('grows the heading to six as soon as a sixth method is appended', async () => {
    mount([...baseMethods, method('QA_TEST_method_6')], baseSituations);
    expect(await screen.findByRole('heading', { name: '六大学习方法' })).toBeInTheDocument();
  });

  it('renders every appended situation and maps it to appended methods by id only', async () => {
    const { onStart } = mount([...baseMethods, ...appendedMethods], [...baseSituations, ...appendedSituations]);
    expect(await screen.findAllByRole('button', { name: /^QA_TEST 情境/ })).toHaveLength(baseSituations.length + appendedSituations.length);

    fireEvent.click(screen.getByRole('button', { name: appendedSituations[0]!.label }));
    expect(screen.getByText(`可以尝试：QA_TEST 方法 QA_TEST_method_8`)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: appendedSituations[1]!.label }));
    expect(screen.getByText('可以尝试：QA_TEST 方法 QA_TEST_method_6、QA_TEST 方法 QA_TEST_method_7')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '查看方法与步骤' })).toHaveLength(2);

    fireEvent.click(screen.getAllByRole('button', { name: '查看方法与步骤' })[1]!);
    fireEvent.click(screen.getByRole('button', { name: '用「QA_TEST 方法 QA_TEST_method_7」开始' }));
    expect(onStart).toHaveBeenCalledWith({ methodId: 'QA_TEST_method_7', situationId: 'QA_TEST_situation_11' });
  });

  it('opens any method detail, including a newly appended one, with all server fields', async () => {
    mount([...baseMethods, ...appendedMethods], baseSituations);
    const cards = await screen.findAllByRole('button', { name: '查看方法与步骤' });
    fireEvent.click(cards[cards.length - 1]!);
    expect(screen.getByRole('heading', { name: 'QA_TEST 方法 QA_TEST_method_8' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '它解决什么问题' })).toBeInTheDocument();
    expect(screen.getByText('QA_TEST_method_8 问题')).toBeInTheDocument();
    expect(screen.getByText('QA_TEST_method_8 适用')).toBeInTheDocument();
    expect(screen.getByText('QA_TEST_method_8 第一步')).toBeInTheDocument();
    expect(screen.getByText('QA_TEST_method_8 误区')).toBeInTheDocument();
  });
});
