/*
 * 学习记录条目的元数据与派生事实（按字段名索引，不含文案）
 * ------------------------------------------------------------------
 * 规则：
 * 1. 记录条目的所有文字来自 GET /records 的字段：goal / subject_name /
 *    learning_date / day_timezone / summary / recalled_text / missing_parts /
 *    stuck_note / attempt_count / pending_count / checked_count /
 *    independent_correct_count。本文件只做「字段 → 事实」的规整，
 *    不生成标题、不推断掌握程度（AGENTS.md §24.2：看过答案不等于掌握）。
 * 2. 返回的 key 是机器可读的枚举，中文标签由渲染层决定；
 *    因此这里没有任何文案字面量（有测试守着这一点）。
 * 3. 记录条数增加、字段为 null 都不需要改渲染代码：缺失的字段自动不出现。
 */
import type { RecordData } from '../../shared/api/types';
import { subjectMeta, type SubjectMeta } from '../knowledge/subject-meta';

/** 记录条目里展示的计数事实，顺序固定。 */
export const RECORD_FACT_KEYS = ['attempt', 'pending', 'checked', 'independent'] as const;
export type RecordFactKey = (typeof RECORD_FACT_KEYS)[number];
export type RecordFact = { key: RecordFactKey; value: number };

/** 记录条目里展示的自由文本，顺序固定。 */
export const RECORD_NOTE_KEYS = ['summary', 'recalled', 'missing', 'stuck'] as const;
export type RecordNoteKey = (typeof RECORD_NOTE_KEYS)[number];
export type RecordNote = { key: RecordNoteKey; text: string };

/** 核对状态：只依据接口计数判断，不做任何掌握度推断。 */
export type RecordCheckState = 'checked' | 'pending' | 'empty';

type RecordCounts = Pick<RecordData, 'attempt_count' | 'pending_count' | 'checked_count' | 'independent_correct_count'>;

type RecordNotes = Pick<RecordData, 'summary' | 'recalled_text' | 'missing_parts' | 'stuck_note'>;

const FACT_FIELDS: Record<RecordFactKey, keyof RecordCounts> = {
  attempt: 'attempt_count',
  pending: 'pending_count',
  checked: 'checked_count',
  independent: 'independent_correct_count',
};

const NOTE_FIELDS: Record<RecordNoteKey, keyof RecordNotes> = {
  summary: 'summary',
  recalled: 'recalled_text',
  missing: 'missing_parts',
  stuck: 'stuck_note',
};

function toCount(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
}

function toText(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

/** 计数事实：全部来自接口，未提供的字段计 0。 */
export function recordFacts(record: Partial<RecordCounts>): RecordFact[] {
  return RECORD_FACT_KEYS.map((key) => ({ key, value: toCount(record[FACT_FIELDS[key]]) }));
}

/** 自由文本：按固定顺序输出，空字段直接缺席（数据驱动，不做占位编造）。 */
export function recordNotes(record: Partial<RecordNotes>): RecordNote[] {
  return RECORD_NOTE_KEYS.flatMap((key) => {
    const text = toText(record[NOTE_FIELDS[key]]);
    return text ? [{ key, text }] : [];
  });
}

/** 核对状态：待核对为 0 且有作答记录时才算已核对。 */
export function recordCheckState(record: Partial<RecordCounts>): RecordCheckState {
  const attempts = toCount(record.attempt_count);
  if (attempts === 0) return 'empty';
  return toCount(record.pending_count) === 0 ? 'checked' : 'pending';
}

/** 记录所属学科的外观：有 subject_id 时按学科推导，否则按学科名兜底。
 *  t13：同时把 subject_name 传给 subjectMeta，否则同一学科在学科空间（有名字）
 *  与学习记录（只有 id）会得到不同强调色/图标，破坏「同学科在所有页面同色」。 */
export function recordSubjectMeta(record: Pick<RecordData, 'subject_id' | 'subject_name'>): SubjectMeta & { name: string | null } {
  const name = toText(record.subject_name);
  return { ...subjectMeta({ id: record.subject_id ?? name ?? '', name, group_label: null }), name };
}
