/*
 * 硬门禁：连续追加多条学习记录后，记录列表必须全部自动渲染。
 * 只喂数据、不改渲染代码：
 * - 记录条数从少量追加到多条；
 * - 字段缺失的记录自动少渲染，不出现占位编造的内容；
 * - 计数事实与核对状态全部来自接口字段。
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { RecordData } from '../../shared/api/types';
import { RecordEntry } from './RecordEntry';

function record(id: string, patch: Partial<RecordData> = {}): RecordData {
  return {
    id,
    version: 1,
    goal: `QA_TEST 目标 ${id}`,
    subject_id: 'QA_TEST_subject',
    subject_name: 'QA_TEST 学科',
    status: 'ended',
    learning_date: '2035-04-03',
    day_timezone: 'Asia/Shanghai',
    started_at: '2035-04-03T01:00:00Z',
    ended_at: '2035-04-03T02:00:00Z',
    resume_note: null,
    summary: null,
    recalled_text: null,
    missing_parts: null,
    stuck_note: null,
    attempt_count: 0,
    pending_count: 0,
    checked_count: 0,
    independent_correct_count: 0,
    effective: true,
    source_refs: [],
    ...patch,
  };
}

function mount(records: RecordData[], onOpen = vi.fn()) {
  render(<ol>{records.map((item) => <RecordEntry key={item.id} record={item} onOpen={onOpen} />)}</ol>);
  return { onOpen };
}

function entries(): HTMLElement[] {
  return screen.getAllByRole('listitem');
}

/** 读取某条记录的计数事实（渲染层用 dl 输出；核对状态 chip 用的是同一批词，所以要限定在 dl 内）。 */
function fact(entry: HTMLElement, label: string): string | null | undefined {
  const facts = entry.querySelector('.record-entry__facts');
  if (!facts) throw new Error('记录条目缺少计数事实区域');
  return within(facts as HTMLElement).getByText(label).parentElement?.querySelector('dd')?.textContent;
}

describe('data-driven record entries', () => {
  it('renders every appended record automatically', () => {
    const records = [
      record('QA_TEST_record_1'),
      record('QA_TEST_record_2'),
      record('QA_TEST_record_3'),
      record('QA_TEST_record_4', { goal: 'QA_TEST 追加的第四条' }),
      record('QA_TEST_record_5', { goal: 'QA_TEST 追加的第五条' }),
      record('QA_TEST_record_6', { goal: 'QA_TEST 追加的第六条' }),
    ];
    mount(records);
    expect(entries()).toHaveLength(records.length);
    for (const item of records) expect(screen.getByText(item.goal as string)).toBeInTheDocument();
  });

  it('shows only the facts and notes the interface actually returned', () => {
    mount([record('QA_TEST_full', {
      summary: 'QA_TEST 小结', recalled_text: 'QA_TEST 回忆内容', missing_parts: 'QA_TEST 尚未想起', stuck_note: 'QA_TEST 卡点',
      attempt_count: 4, pending_count: 1, checked_count: 3, independent_correct_count: 2,
    })]);
    const entry = within(entries()[0]!);
    expect(entry.getByText('QA_TEST 小结')).toBeInTheDocument();
    expect(entry.getByText('QA_TEST 回忆内容')).toBeInTheDocument();
    expect(entry.getByText('QA_TEST 尚未想起')).toBeInTheDocument();
    expect(entry.getByText('QA_TEST 卡点')).toBeInTheDocument();
    expect(fact(entries()[0]!, '作答')).toBe('4');
    expect(fact(entries()[0]!, '待核对')).toBe('1');
    expect(fact(entries()[0]!, '已核对')).toBe('3');
    expect(fact(entries()[0]!, '独立答对')).toBe('2');
  });

  it('omits absent text fields instead of inventing placeholder content', () => {
    mount([record('QA_TEST_sparse')]);
    expect(screen.getByText('QA_TEST 目标 QA_TEST_sparse')).toBeInTheDocument();
    expect(screen.queryByText('回忆')).not.toBeInTheDocument();
    expect(screen.queryByText('尚未想起')).not.toBeInTheDocument();
    expect(screen.queryByText('卡点')).not.toBeInTheDocument();
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('derives the check state from the returned counts only', () => {
    mount([
      record('QA_TEST_pending', { attempt_count: 2, pending_count: 2, checked_count: 0 }),
      record('QA_TEST_checked', { attempt_count: 2, pending_count: 0, checked_count: 2 }),
      record('QA_TEST_empty', { attempt_count: 0, pending_count: 0, checked_count: 0 }),
    ]);
    const state = (index: number) => entries()[index]!.querySelector('.record-entry__state')?.getAttribute('data-state');
    expect(state(0)).toBe('pending');
    expect(state(1)).toBe('checked');
    expect(state(2)).toBe('empty');
  });

  it('falls back to the free-learning title and opens the record by id', async () => {
    const { onOpen } = mount([record('QA_TEST_free', { goal: '   ' }), record('QA_TEST_other')]);
    expect(screen.getByText('自由学习')).toBeInTheDocument();
    const buttons = screen.getAllByRole('button', { name: '打开学习现场 →' });
    expect(buttons).toHaveLength(2);
    await userEvent.setup().click(buttons[1]!);
    expect(onOpen).toHaveBeenCalledWith('QA_TEST_other');
  });
});
