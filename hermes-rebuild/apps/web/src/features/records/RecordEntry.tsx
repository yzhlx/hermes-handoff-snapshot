/*
 * 学习记录条目渲染层
 * ------------------------------------------------------------------
 * 1. 条目的每一个可见字段都来自 GET /records：
 *    goal / subject_name / learning_date / day_timezone / summary /
 *    recalled_text / missing_parts / stuck_note / attempt_count /
 *    pending_count / checked_count / independent_correct_count。
 * 2. 计数与自由文本的规整（哪些字段、什么顺序、空值如何处理）来自
 *    record-meta.ts 的字段索引；这里只负责把 key 翻译成中文标签。
 * 3. 因此新增第 N 条记录、或某条记录缺少某个字段时本文件不需要改动。
 */
import type { RecordData } from '../../shared/api/types';
import { recordCheckState, recordFacts, recordNotes, recordSubjectMeta, type RecordCheckState, type RecordFactKey, type RecordNoteKey } from './record-meta';
import { CardIcon } from '../../shared/ui/card-icons';

const FACT_LABELS: Record<RecordFactKey, string> = { attempt: '作答', pending: '待核对', checked: '已核对', independent: '独立答对' };

/** label 为 null 的字段按原文段落渲染（与既有行为一致，不额外加标签）。 */
const NOTE_LABELS: Record<RecordNoteKey, string | null> = { summary: null, recalled: '回忆', missing: '尚未想起', stuck: '卡点' };

const CHECK_LABELS: Record<RecordCheckState, string> = { checked: '已核对', pending: '待核对', empty: '—' };

/** 目标缺失时的兜底标题，与既有行为一致。 */
const FREE_LEARNING_TITLE = '自由学习';

/** 参考图在左侧留出日期与时刻：时刻来自 started_at，按账号时区格式化。 */
function timeLabel(value: string, timezone: string): string | null {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return null;
  try {
    return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', timeZone: timezone }).format(timestamp);
  } catch {
    return null;
  }
}

export type RecordEntryProps = {
  record: RecordData;
  onOpen: (id: string) => void;
};

export function RecordEntry({ record, onOpen }: RecordEntryProps) {
  const subject = recordSubjectMeta(record);
  const facts = recordFacts(record);
  const notes = recordNotes(record);
  const checkState = recordCheckState(record);
  const goal = record.goal?.trim();
  const time = timeLabel(record.started_at, record.day_timezone);
  return <li className="panel record-entry">
    <p className="record-entry__date">
      <span className="record-entry__day">{record.learning_date}</span>
      {time && <span className="record-entry__time">{time}</span>}
    </p>
    <div className="record-entry__main">
      <div className="record-entry__head">
        <span className={`card-icon card-icon--sm card-accent--${subject.accent}`}><CardIcon icon={subject.icon} /></span>
        <div className="record-entry__heading">
          <strong>{goal || FREE_LEARNING_TITLE}</strong>
          <p className="muted">{subject.name ? `${subject.name} · ` : ''}{record.day_timezone}</p>
        </div>
        <span className="record-entry__state" data-state={checkState}>{CHECK_LABELS[checkState]}</span>
      </div>
      {notes.map((note) => <p className="record-entry__note" key={note.key}>{NOTE_LABELS[note.key] ? <strong>{NOTE_LABELS[note.key]}：</strong> : null}{note.text}</p>)}
      <dl className="record-entry__facts">{facts.map((fact) => <div key={fact.key}><dt>{FACT_LABELS[fact.key]}</dt><dd>{fact.value}</dd></div>)}</dl>
    </div>
    <div className="record-entry__actions">
      <button className="text-button" onClick={() => onOpen(record.id)}>打开学习现场 →</button>
    </div>
  </li>;
}
