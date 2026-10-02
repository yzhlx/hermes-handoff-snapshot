/*
 * 学习方法 / 学习情境元数据（按 id 索引）
 * ------------------------------------------------------------------
 * 这是「前端唯一可以出现方法 id 字面量」的地方，而且只保存表现元数据：
 * 图标键、强调色、以及每个方法对应的入口目标（学习现场 / 题目与对比）。
 *
 * 规则：
 * 1. 不复制接口内容：标题、摘要、适用情况、步骤、常见误区一律来自
 *    GET /learning-methods（服务端目录见 apps/api/src/hermes_api/catalog.py）。
 *    本文件里没有任何标题或文案字面量（有测试守着这一点）。
 * 2. 渲染层只调用 methodMeta(id) / situationMeta(id)，不写
 *    `item.id === '...'` 这类分支，因此新增第 6 种学习方法时渲染代码零改动：
 *    未登记的 id 会得到由 id 稳定推导出的图标键与强调色。
 * 3. start 只描述「这个方法的入口去哪」；缺省入口是学习现场，
 *    因此第 6 种方法不需要在这里登记也能正常工作。
 */
import type { LearningMethod } from './catalog';
import { accentForSeed, iconForSeed, type CardAccent } from '../../shared/ui/card-kit';
import type { CardIconKey } from '../../shared/ui/card-icons';

/** 方法入口目标：学习现场，或题目与对比编辑器。 */
export type MethodStartTarget = 'learning' | 'comparison';

export type MethodMeta = {
  icon: CardIconKey;
  accent: CardAccent;
  /** 缺省为 learning。 */
  start?: MethodStartTarget;
};

/** 入口目标的缺省值：目录里没有登记 start 的方法都进学习现场。 */
export const DEFAULT_METHOD_START: MethodStartTarget = 'learning';

/**
 * 从「题目与对比」开始一段学习时挂上的方法 id。
 * 这是选题入口的既有行为，只是从渲染路径搬进了元数据模块：
 * 渲染层引用名字，不出现方法 id 字面量。
 */
export const PROBLEM_START_METHOD_ID = 'practice-feedback';

/** 未登记方法可用的图标池（按 id 稳定取一个）。 */
const METHOD_ICON_POOL: readonly CardIconKey[] = ['recall', 'practice', 'spaced', 'compare', 'explain', 'book', 'question', 'play'];

/**
 * 已登记的方法元数据。键 = 服务端方法 id。
 * 只登记「表现」与「入口」；目录内容仍然完全由接口决定。
 */
export const METHOD_META: Readonly<Record<string, MethodMeta>> = {
  'active-recall': { icon: 'recall', accent: 'sage' },
  'practice-feedback': { icon: 'practice', accent: 'warm' },
  'spaced-review': { icon: 'spaced', accent: 'lime' },
  'worked-example-compare': { icon: 'compare', accent: 'indigo', start: 'comparison' },
  'feynman-check': { icon: 'explain', accent: 'clay' },
};

/** 学习情境的图标元数据。键 = 服务端情境 id；情境文字来自接口的 label。 */
export const SITUATION_META: Readonly<Record<string, { icon: CardIconKey }>> = {
  'just-finished-class': { icon: 'explain' },
  'no-entry-point': { icon: 'question' },
  'answer-looks-clear': { icon: 'practice' },
  'similar-problems': { icon: 'compare' },
  'confusable-formulas': { icon: 'sigma' },
  'forgotten-content': { icon: 'cycle' },
  'repeated-mistake': { icon: 'cross' },
  'low-energy': { icon: 'face' },
  'know-what-to-do': { icon: 'play' },
};

const SITUATION_ICON_POOL: readonly CardIconKey[] = ['question', 'cross', 'face', 'play', 'cycle', 'explain'];

/** 取方法元数据：登记过就用登记的，没登记过就按 id 稳定推导。 */
export function methodMeta(id: string | null | undefined): MethodMeta {
  const seed = id ?? '';
  const known = id ? METHOD_META[id] : undefined;
  if (known) return known;
  return { icon: iconForSeed(seed, METHOD_ICON_POOL), accent: accentForSeed(seed) };
}

/** 方法入口目标：缺省 learning；注册表里的条目决定特例。 */
export function methodStartTarget(id: string | null | undefined): MethodStartTarget {
  return (id ? METHOD_META[id]?.start : undefined) ?? DEFAULT_METHOD_START;
}

/** 取情境图标键：登记过就用登记的，没登记过就按 id 稳定推导。 */
export function situationIcon(id: string | null | undefined): CardIconKey {
  const seed = id ?? '';
  const known = id ? SITUATION_META[id]?.icon : undefined;
  return known ?? iconForSeed(seed, SITUATION_ICON_POOL);
}

/** 方法卡片的外观（图标键 + 强调色令牌名），供渲染层直接透传到 class。 */
export function methodAppearance(method: Pick<LearningMethod, 'id'>): { icon: CardIconKey; accent: CardAccent } {
  const meta = methodMeta(method.id);
  return { icon: meta.icon, accent: meta.accent };
}
