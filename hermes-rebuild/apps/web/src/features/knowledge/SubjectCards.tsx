/*
 * 学科渲染层：学科卡片 / 按 group_label 分组
 * ------------------------------------------------------------------
 * 1. 学科名称与分组全部来自 GET /subjects（或 /home 的 subjects 段落）：
 *    id / name / group_label。
 * 2. 这里不判断具体是哪一个学科：图标键与强调色来自 subject-meta.ts
 *    的元数据映射，未登记的学科按学科身份稳定推导。
 * 3. 卡片形态按 DESIGN.md §2：徽章 44×44 圆角 12 置顶 + 16px 标题 +
 *    12px 次要行；徽章与装饰文字 aria-hidden，按钮可访问名称只由文字构成。
 * 4. 首页 variant='inline' 的可访问名称必须是「学科名 →」（既有测试红线），
 *    因此徽章与次要行都标 aria-hidden；学科空间 variant='card' 保留
 *    「打开章节与知识点 →」这一既有提示作为次要行。
 */
import type { SubjectIdentity } from './subject-meta';
import { subjectMeta } from './subject-meta';
import { CardIcon, type CardIconKey } from '../../shared/ui/card-icons';
import { accentForSeed, type CardAccent } from '../../shared/ui/card-kit';

/** 学科条目：接口字段原样使用，不做重命名或补写。 */
export type SubjectEntry = SubjectIdentity & { id: string; name: string };

export type SubjectGroup = {
  /** 分组键：group_label 原值；没有分组时是渲染层的兜底标签。 */
  key: string;
  label: string;
  items: SubjectEntry[];
};

export type SubjectCardVariant = 'card' | 'inline';

/** 接口没有给 group_label 时的兜底分组名。 */
const UNGROUPED_LABEL = '学科';

/** 按 group_label 分组，保持接口返回的先后顺序（分组顺序 = 首次出现顺序）。 */
export function groupSubjects(items: readonly SubjectEntry[]): SubjectGroup[] {
  const groups = new Map<string, SubjectGroup>();
  for (const subject of items) {
    const label = subject.group_label?.trim() || UNGROUPED_LABEL;
    const group = groups.get(label) ?? { key: label, label, items: [] };
    group.items.push(subject);
    groups.set(label, group);
  }
  return [...groups.values()];
}

function SubjectBadge({ icon, accent, size = 'lg' }: { icon: CardIconKey; accent: CardAccent; size?: 'lg' | 'sm' }) {
  return <span className={`card-icon card-icon--${size} card-accent--${accent}`}><CardIcon icon={icon} /></span>;
}

/**
 * 学科卡：
 * - inline：首页入口（可访问名称 =「学科名 →」，与既有测试一致）；
 * - card：学科空间入口（可访问名称 =「学科名 打开章节与知识点 →」）。
 */
export function SubjectCard({ subject, onOpen, variant = 'card' }: {
  subject: SubjectEntry;
  onOpen: (id: string) => void;
  variant?: SubjectCardVariant;
}) {
  const { icon, accent } = subjectMeta(subject);
  const name = subject.name.trim() || subject.id;
  if (variant === 'inline') {
    return <button type="button" className="subject-card subject-card--inline" onClick={() => onOpen(subject.id)}>
      <SubjectBadge icon={icon} accent={accent} />
      <strong className="subject-card__name">{name} →</strong>
      {/* DESIGN.md §6.2：次要行必须是真实可得的字段；首页数据只有 id/name/group_label，
          而分组名已由区块标题给出（每组一次），因此卡片这里留空、由卡片高度自己收紧。 */}
    </button>;
  }
  return <button type="button" className="subject-card subject-card--entry" onClick={() => onOpen(subject.id)}>
    <SubjectBadge icon={icon} accent={accent} />
    <strong className="subject-card__name">{name}</strong>
    <span className="subject-card__meta">打开章节与知识点 →</span>
  </button>;
}

/**
 * 自由学习入口卡：与学科卡同形，用 ink 强调色 + grid 图标。
 * 文案沿用既有「开始一段学习 →」，不新增入口语义。
 */
export function SubjectActionCard({ label, hint, onOpen, seed = 'free-learning' }: {
  label: string;
  hint?: string;
  onOpen: () => void;
  seed?: string;
}) {
  return <button type="button" className="subject-card subject-card--action" onClick={onOpen}>
    <SubjectBadge icon="grid" accent={accentForSeed(seed)} />
    <strong className="subject-card__name">{label}</strong>
    {hint ? <span className="subject-card__meta">{hint}</span> : null}
  </button>;
}
