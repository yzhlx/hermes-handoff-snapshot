/*
 * 学科元数据（强调色与图标按学科身份取，不按分组取）
 * ------------------------------------------------------------------
 * 规则（t13 修正「同一分组内所有学科同色」的根因）：
 * 1. 强调色与图标都按「学科身份」取，因此同一个学科在首页 / 学科空间 /
 *    学习记录 / 复盘拿到同一套外观，而同一分组内的不同学科颜色不同。
 * 2. 取法分两层：
 *    a. 语义层：学科名命中 SUBJECT_SEMANTICS 时用登记的外观
 *       （参考图首页六个学科各占一色一形，见下）；
 *    b. 兜底层：没命中时按 id 稳定散列，新增学科零改动、外观可复现。
 * 3. 分组（group_label）只用于分组标题与排序（见 SubjectCards.groupSubjects），
 *    不再参与外观计算；SUBJECT_GROUP_ACCENTS / subjectGroupAccent 为兼容保留，
 *    只有「分组本身要一个颜色」的场合才用（当前没有消费者）。
 * 4. 学科名与分组名都是接口数据，本文件只保存关键词 → 外观的映射，
 *    不复制任何学科的展示文案。
 */
import { accentForSeed, iconForSeed, type CardAccent } from '../../shared/ui/card-kit';
import type { CardIconKey } from '../../shared/ui/card-icons';

export type SubjectIdentity = {
  id: string;
  name?: string | null;
  group_label?: string | null;
};

export type SubjectMeta = { icon: CardIconKey; accent: CardAccent };

/** 学科图标兜底池：没命中语义表时按 id 稳定取一个，保证同学科每次渲染一致。 */
const SUBJECT_ICON_POOL: readonly CardIconKey[] = ['book', 'sigma', 'language', 'politics', 'signal', 'circuit', 'grid', 'matrix'];

/**
 * 语义外观表：关键词 → 图标 + 强调色。
 * 前六条与参考图首页「我的学科」六张卡一一对应（徽章底色实测见 DESIGN.md §3）：
 *   高等数学 = Σ 绿、信号与系统 = 波形 蓝、电路基础 = 芯片 琥珀、
 *   英语 = A 紫、政治 = 柱式建筑 红、自由学习 = 四格 石板灰。
 * 关键词只做「包含」匹配，命中优先级 = 数组顺序。
 */
export const SUBJECT_SEMANTICS: readonly { readonly match: readonly string[]; readonly icon: CardIconKey; readonly accent: CardAccent }[] = [
  { match: ['电路', '模电', '数电', '电子'], icon: 'circuit', accent: 'warm' },
  { match: ['信号', '通信', '微波', '电磁'], icon: 'signal', accent: 'indigo' },
  { match: ['线性代数', '矩阵'], icon: 'matrix', accent: 'lime' },
  { match: ['数学', '代数', '高数', '统计', '概率'], icon: 'sigma', accent: 'sage' },
  { match: ['英语', '英文', '语言', '词汇', '阅读'], icon: 'language', accent: 'plum' },
  { match: ['政治', '时政', '马原', '思修'], icon: 'politics', accent: 'clay' },
  { match: ['自由学习', '自定义', '其他'], icon: 'grid', accent: 'ink' },
];

/** 已登记分组的强调色。键 = 接口返回的 group_label 原值；仅用于「分组自己要有颜色」的场合。 */
export const SUBJECT_GROUP_ACCENTS: Readonly<Record<string, CardAccent>> = {
  '上海大学829': 'indigo',
  '公共课': 'sage',
};

/** 分组强调色：登记过的分组用登记的，没登记过按分组标签稳定推导。 */
export function subjectGroupAccent(groupLabel: string | null | undefined): CardAccent {
  const label = groupLabel?.trim() ?? '';
  return SUBJECT_GROUP_ACCENTS[label] ?? accentForSeed(label);
}

/** 语义层：按学科名命中登记的外观；没有名字或没命中时返回 undefined。 */
export function subjectSemantic(name: string | null | undefined) {
  const text = name?.trim();
  if (!text) return undefined;
  return SUBJECT_SEMANTICS.find((entry) => entry.match.some((keyword) => text.includes(keyword)));
}

/**
 * 学科外观（强调色 + 图标）：
 * - 命中语义表 → 用登记的外观；
 * - 否则按学科 id 稳定推导，保证「同学科在任何页面同色、同形」。
 * 分组不再是外观的输入：同一分组内的不同学科会得到不同颜色。
 */
export function subjectMeta(subject: SubjectIdentity): SubjectMeta {
  const semantic = subjectSemantic(subject.name);
  return {
    icon: semantic?.icon ?? iconForSeed(subject.id, SUBJECT_ICON_POOL),
    accent: semantic?.accent ?? accentForSeed(subject.id),
  };
}
