/*
 * 硬门禁：首页的学科入口与方法预览同样必须由接口数据驱动。
 * 覆盖点（既有 HomePage.test.tsx 关注交互，这里关注数据结构）：
 * - 学科按 group_label 真正分组（不是每个学科各占一个分组），分组标题各出现一次；
 * - 追加学科后首页自动多出入口，可访问名称保持「学科名 →」；
 * - 方法预览的标题与「用这个方法开始 →」都来自 home 段落的 items。
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { HomeResponse } from '../../shared/api/types';
import { HomePage, type HomePageProps } from './HomePage';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const quoteData = { daily_quote: { local_date: '2035-04-03', day_timezone: 'Asia/Shanghai', quote: null, reason: 'no_eligible_quotes', preference: null } };
const section = <T,>(data: T, status: 'ready' | 'empty' = 'ready') => ({ status, data, source_revision: 'QA_TEST_home_v1', error: null });

function payload() {
  return {
    data: {
      date: '2035-04-03', timezone: 'Asia/Shanghai', rule_version: 'QA_TEST_home_rule',
      sections: {
        quote: section(quoteData),
        subjects: section({ items: [
          { id: 'QA_TEST_subject_1', name: 'QA_TEST 学科一', group_label: 'QA_TEST 分组甲' },
          { id: 'QA_TEST_subject_2', name: 'QA_TEST 学科二', group_label: 'QA_TEST 分组甲' },
          { id: 'QA_TEST_subject_3', name: 'QA_TEST 学科三', group_label: 'QA_TEST 分组乙' },
          { id: 'QA_TEST_subject_4', name: 'QA_TEST 学科四', group_label: 'QA_TEST 分组乙' },
          { id: 'QA_TEST_subject_5', name: 'QA_TEST 学科五', group_label: 'QA_TEST 分组乙' },
          { id: 'QA_TEST_subject_6', name: 'QA_TEST 学科六', group_label: 'QA_TEST 分组丙' },
          { id: 'QA_TEST_subject_7', name: 'QA_TEST 学科七', group_label: 'QA_TEST 分组丙' },
        ] }),
        methods: section({ items: [
          { id: 'QA_TEST_method_a', title: 'QA_TEST 方法甲', summary: 'QA_TEST 摘要甲', content_version: 1 },
          { id: 'QA_TEST_method_b', title: 'QA_TEST 方法乙', summary: 'QA_TEST 摘要乙', content_version: 1 },
          { id: 'QA_TEST_method_c', title: 'QA_TEST 方法丙', summary: 'QA_TEST 摘要丙', content_version: 1 },
          { id: 'QA_TEST_method_d', title: 'QA_TEST 方法丁', summary: 'QA_TEST 摘要丁', content_version: 1 },
        ] }),
      },
    },
    meta: { request_id: 'QA_TEST_home' },
  } as unknown as HomeResponse;
}

function mount() {
  const callbacks = {
    onOpenSubject: vi.fn(), onStartFree: vi.fn(), onContinue: vi.fn(), onOpenMethods: vi.fn(),
    onStartMethod: vi.fn(), onOpenReview: vi.fn(), onOpenSession: vi.fn(), onOpenProblem: vi.fn(),
    onOpenSummary: vi.fn(), onOpenMyQuotes: vi.fn(),
  } satisfies Omit<HomePageProps, 'userId'>;
  vi.stubGlobal('fetch', vi.fn(async (url: string) => new Response(JSON.stringify(url.endsWith('/home') ? payload() : { data: quoteData, meta: { request_id: 'QA_TEST' } }))));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><HomePage userId="QA_TEST_user" {...callbacks} /></QueryClientProvider>);
  return callbacks;
}

describe('data-driven home entries', () => {
  it('groups the server subjects and renders every appended subject entry', async () => {
    const callbacks = mount();
    for (const index of [1, 2, 3, 4, 5, 6, 7]) {
      expect(await screen.findByRole('button', { name: `QA_TEST 学科${'一二三四五六七'[index - 1]} →` })).toBeInTheDocument();
    }
    for (const label of ['QA_TEST 分组甲', 'QA_TEST 分组乙', 'QA_TEST 分组丙']) {
      expect(screen.getAllByText(label)).toHaveLength(1);
    }
    await userEvent.setup().click(screen.getByRole('button', { name: 'QA_TEST 学科七 →' }));
    expect(callbacks.onOpenSubject).toHaveBeenCalledWith('QA_TEST_subject_7');
  });

  it('renders the method preview from the home section and starts the clicked method', async () => {
    const callbacks = mount();
    for (const title of ['QA_TEST 方法甲', 'QA_TEST 方法乙', 'QA_TEST 方法丙']) {
      expect(await screen.findByRole('heading', { name: title })).toBeInTheDocument();
    }
    // 首页只是预览：第 4 条不展示，完整目录在「学习方法」页。
    expect(screen.queryByRole('heading', { name: 'QA_TEST 方法丁' })).not.toBeInTheDocument();
    const starts = screen.getAllByRole('button', { name: '用这个方法开始 →' });
    expect(starts).toHaveLength(3);
    await userEvent.setup().click(starts[2]!);
    expect(callbacks.onStartMethod).toHaveBeenCalledWith('QA_TEST_method_c');
  });

  it('keeps the icon out of the accessible name of every data-driven entry', async () => {
    mount();
    const subject = await screen.findByRole('button', { name: 'QA_TEST 学科一 →' });
    expect(subject.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true');
    const start = screen.getAllByRole('button', { name: '用这个方法开始 →' })[0]!;
    expect(start.closest('.home-method')?.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true');
  });
});
