/*
 * 方法卡渲染层：一次把 /learning-methods 的全部字段喂进去，确认卡片用的是接口数据。
 * 覆盖：
 * - full 密度渲染 problem / situations / steps / pitfalls 四个字段（步骤是 ol，其余是列表）；
 * - 字段缺失（首页的 methods 段落只有 id/title/summary）时自动变紧凑，不出现空标签；
 * - 标题、摘要、字段文本全部来自传入的数据，卡片里没有任何写死的方法内容。
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import type { LearningMethod } from './catalog';
import { MethodCard, methodCatalogHeading } from './MethodCards';

const full: LearningMethod = {
  id: 'QA_TEST_method_full',
  title: 'QA_TEST 方法标题',
  summary: 'QA_TEST 方法摘要',
  problem: 'QA_TEST 它解决什么问题',
  situations: ['QA_TEST 适用一', 'QA_TEST 适用二'],
  steps: ['QA_TEST 步骤一', 'QA_TEST 步骤二'],
  pitfalls: ['QA_TEST 误区一'],
  content_version: 1,
};

describe('method card', () => {
  it('renders every catalog field the interface returned', () => {
    render(<MethodCard method={full} density="full" onOpen={vi.fn()} />);
    expect(screen.getByRole('heading', { name: full.title })).toBeInTheDocument();
    expect(screen.getByText(full.summary)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '解决什么问题' })).toBeInTheDocument();
    expect(screen.getByText(full.problem)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '适用情况' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '操作步骤' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '常见误区' })).toBeInTheDocument();
    const steps = screen.getByRole('heading', { name: '操作步骤' }).parentElement!;
    expect(within(steps).getByRole('list').tagName).toBe('OL');
    expect(within(steps).getAllByRole('listitem')).toHaveLength(full.steps.length);
    expect(screen.getByRole('button', { name: '查看方法与步骤' })).toBeInTheDocument();
  });

  it('stays compact when the interface only provides id, title and summary', () => {
    const summaryOnly = { id: 'QA_TEST_method_compact', title: 'QA_TEST 精简标题', summary: 'QA_TEST 精简摘要' };
    render(<MethodCard method={summaryOnly} density="full" onStart={vi.fn()} />);
    expect(screen.getByRole('heading', { name: summaryOnly.title })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '解决什么问题' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '适用情况' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '操作步骤' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '常见误区' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '用这个方法开始 →' })).toBeInTheDocument();
  });

  it('skips empty lists instead of rendering an empty field', () => {
    render(<MethodCard method={{ id: 'QA_TEST_method_empty', title: 'QA_TEST 空字段', summary: 'QA_TEST 摘要', problem: '   ', situations: [], steps: [], pitfalls: [] }} density="full" />);
    expect(screen.queryByRole('heading', { name: '解决什么问题' })).not.toBeInTheDocument();
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
  });

  it('builds the catalog heading from the number of entries it rendered', () => {
    expect([1, 5, 6, 8, 10].map(methodCatalogHeading)).toEqual(['一种学习方法', '五大学习方法', '六大学习方法', '八大学习方法', '十大学习方法']);
    expect(methodCatalogHeading(12)).toBe('共 12 种学习方法');
    expect(methodCatalogHeading(0)).toBe('学习方法');
  });
});
