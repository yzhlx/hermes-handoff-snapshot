/*
 * 数据驱动导航：外壳只渲染这里的数据，页面不再各自硬编码入口。
 * 新增入口 = 在这里加一条记录；无需改 AppShell 的 JSX。
 *
 * 约束：
 * - label 同时是按钮的可访问名称与顶栏面包屑标题，改动会影响导航测试。
 * - 不新增页面：id 必须是 App 中真实存在的渲染分支。
 */
import type { ComponentType } from 'react';
import {
  AccountIcon,
  CompareIcon,
  HomeIcon,
  LearningIcon,
  MethodIcon,
  PinIcon,
  QuoteIcon,
  RecordIcon,
  ReviewIcon,
  SparkIcon,
  SubjectIcon,
  SummaryIcon,
  type IconProps,
} from '../shared/ui/icons';

export type AppPage =
  | 'home'
  | 'learning'
  | 'methods'
  | 'history'
  | 'quotes'
  | 'subjects'
  | 'subject-space'
  | 'review'
  | 'summary'
  | 'comparisons'
  | 'advisor'
  | 'stuck-points'
  | 'account';

export type NavItem = {
  /** 导航目标页面，必须与 App 的渲染分支一致 */
  id: AppPage;
  /** 可访问名称与面包屑标题 */
  label: string;
  icon: ComponentType<IconProps>;
  /** 侧边栏分组：只影响视觉分组与顺序，不改变入口本身 */
  group: NavGroup;
  /** 额外算作该项选中的页面（如学科详情仍属于“学科空间”） */
  alsoActiveOn?: readonly AppPage[];
};

/**
 * 侧边导航分组：参考图用「图标 + 标签 + 分组小标题」组织导航。
 * 分组只做视觉组织——入口集合与标签集保持真实页面集合，不新增也不隐藏。
 * 账户单独成组，因为参考图把「设置」放在侧栏底部、与学习类入口分开。
 */
export type NavGroup = 'study' | 'review' | 'mine' | 'account';

export const NAV_GROUP_ORDER: readonly NavGroup[] = ['study', 'review', 'mine', 'account'];

export const NAV_GROUP_LABELS: Readonly<Record<NavGroup, string>> = {
  study: '学习',
  review: '记录与复习',
  mine: '我的',
  account: '账户',
};

export const NAV_LABEL = '书房导航';

export const FALLBACK_PAGE_TITLE = '书房';

export const NAV_ITEMS: readonly NavItem[] = [
  { id: 'home', label: '书房', icon: HomeIcon, group: 'study' },
  { id: 'learning', label: '学习现场', icon: LearningIcon, group: 'study' },
  { id: 'subjects', label: '学科空间', icon: SubjectIcon, group: 'study', alsoActiveOn: ['subject-space'] },
  { id: 'methods', label: '学习方法', icon: MethodIcon, group: 'study' },
  { id: 'history', label: '学习记录', icon: RecordIcon, group: 'review' },
  { id: 'stuck-points', label: '卡壳点', icon: PinIcon, group: 'review' },
  { id: 'review', label: '可考虑复习', icon: ReviewIcon, group: 'review' },
  { id: 'summary', label: '今日收尾', icon: SummaryIcon, group: 'review' },
  { id: 'comparisons', label: '题目与对比', icon: CompareIcon, group: 'mine' },
  { id: 'advisor', label: 'Hermes 顾问', icon: SparkIcon, group: 'mine' },
  { id: 'quotes', label: '我的金句', icon: QuoteIcon, group: 'mine' },
  { id: 'account', label: '账号与数据', icon: AccountIcon, group: 'account' },
];

/** 按分组切分导航项，保持 NAV_ITEMS 的原有顺序（分组内顺序 = 数组顺序）。 */
export function navGroups(items: readonly NavItem[]): { group: NavGroup; label: string; items: NavItem[] }[] {
  return NAV_GROUP_ORDER.flatMap((group) => {
    const groupItems = items.filter((item) => item.group === group);
    return groupItems.length ? [{ group, label: NAV_GROUP_LABELS[group], items: groupItems }] : [];
  });
}

/** 把当前页面映射到导航项（含 alsoActiveOn），用于选中态与标题。 */
export function navItemFor(page: AppPage): NavItem | undefined {
  return NAV_ITEMS.find((item) => item.id === page || item.alsoActiveOn?.includes(page) === true);
}

export function pageTitle(page: AppPage): string {
  return navItemFor(page)?.label ?? FALLBACK_PAGE_TITLE;
}

/**
 * 进入某个页面时需要先执行的状态清理（按页面 id 索引）。
 * 与 App 的渲染分支解耦：App 只按名字查表执行，不写 `page === 'history'` 这类分支。
 * 修复 T5-F1：从侧栏进入「题目与对比」以前只 setPage，题目详情面板
 * （sourceProblemId）与对比预填（comparisonProblemId）会留在原地；
 * 旧的入口函数 openComparison(null) 正是清这两个 state。
 */
export type NavResetAction = 'clear-history-selection' | 'close-comparison';

export const NAV_RESET_ACTIONS: Readonly<Partial<Record<AppPage, NavResetAction>>> = {
  history: 'clear-history-selection',
  comparisons: 'close-comparison',
};
