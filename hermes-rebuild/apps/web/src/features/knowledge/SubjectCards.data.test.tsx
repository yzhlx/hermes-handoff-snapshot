/*
 * 硬门禁：连续追加多个学科后，学科空间必须全部自动渲染。
 * 只喂数据、不改渲染代码：
 * - 服务端目录 5 个学科（两个分组）→ 追加到 7 个学科（三个分组）；
 * - 分组与分组顺序完全按接口的 group_label 走，没有分组时落到兜底分组。
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '../../app/query-client';
import { KnowledgeHome } from './KnowledgeHome';
import { groupSubjects } from './SubjectCards';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const envelope = (data: unknown) => new Response(JSON.stringify({ data, meta: { request_id: 'QA_TEST' } }));

const baseSubjects = [
  { id: 'QA_TEST_subject_1', name: 'QA_TEST 学科一', group_label: '上海大学829' },
  { id: 'QA_TEST_subject_2', name: 'QA_TEST 学科二', group_label: '上海大学829' },
  { id: 'QA_TEST_subject_3', name: 'QA_TEST 学科三', group_label: '公共课' },
  { id: 'QA_TEST_subject_4', name: 'QA_TEST 学科四', group_label: '公共课' },
  { id: 'QA_TEST_subject_5', name: 'QA_TEST 学科五', group_label: '公共课' },
];
const appendedSubjects = [
  { id: 'QA_TEST_subject_6', name: 'QA_TEST 学科六', group_label: 'QA_TEST_新分组' },
  { id: 'QA_TEST_subject_7', name: 'QA_TEST 学科七', group_label: 'QA_TEST_新分组' },
];

function mount(subjects: unknown[], onOpenSubject = vi.fn()) {
  vi.stubGlobal('fetch', vi.fn(async () => envelope({ items: subjects })));
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false } });
  render(<QueryClientProvider client={client}><KnowledgeHome onOpenSubject={onOpenSubject} onStartFree={vi.fn()} /></QueryClientProvider>);
  return { onOpenSubject };
}

describe('data-driven subject entries', () => {
  it('groups by the server group_label in first-seen order', () => {
    const groups = groupSubjects([...baseSubjects, ...appendedSubjects]);
    expect(groups.map((group) => group.label)).toEqual(['上海大学829', '公共课', 'QA_TEST_新分组']);
    expect(groups.map((group) => group.items.length)).toEqual([2, 3, 2]);
  });

  it('uses a fallback group when the interface provides no group_label', () => {
    const groups = groupSubjects([{ id: 'QA_TEST_subject_alone', name: 'QA_TEST 无分组学科', group_label: null }, { id: 'QA_TEST_subject_blank', name: 'QA_TEST 空分组学科', group_label: '   ' }]);
    expect(groups).toHaveLength(1);
    expect(groups[0]?.items).toHaveLength(2);
  });

  it('renders every appended subject and the appended group without any render change', async () => {
    const { onOpenSubject } = mount([...baseSubjects, ...appendedSubjects]);
    for (const subject of [...baseSubjects, ...appendedSubjects]) {
      expect(await screen.findByRole('button', { name: new RegExp(subject.name) })).toBeInTheDocument();
    }
    expect(screen.getByText('QA_TEST_新分组')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /QA_TEST 学科七/ }));
    expect(onOpenSubject).toHaveBeenCalledWith('QA_TEST_subject_7');
  });
});
