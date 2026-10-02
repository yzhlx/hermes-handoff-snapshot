/*
 * 卡片渲染层的公共工具（元数据解析用）
 * ------------------------------------------------------------------
 * 目的：让「同类数据的重复形态」只由接口数据决定。
 *
 * 1. 强调色只有下面这一组令牌名，具体颜色值全部来自 tokens.css 的
 *    --accent-<name>-soft / --accent-<name>-ink，不在组件里写颜色。
 * 2. 未在后端目录里登记过的 id（例如将来新增的第 6 种学习方法、第 7 个学科）
 *    会由 id 稳定推导出图标键与强调色：同一个 id 每次得到同样的结果，
 *    因此新增数据条目时渲染代码零改动。
 * 3. 本文件不含任何标题或文案字面量，只有令牌名与推导规则。
 */
import type { CardIconKey } from './card-icons';

export const CARD_ACCENTS = ['sage', 'lime', 'warm', 'clay', 'indigo', 'plum', 'ink'] as const;

export type CardAccent = (typeof CARD_ACCENTS)[number];

/** 默认强调色：未登记且无法推导时使用（正常路径不会走到）。 */
export const DEFAULT_CARD_ACCENT: CardAccent = 'sage';

/** 默认图标键：图标注册表里必须存在 'generic'。 */
export const DEFAULT_CARD_ICON: CardIconKey = 'generic';

/**
 * FNV-1a 32 位散列，按 Unicode 码点推进。
 * 只要求「同一字符串稳定得到同一结果」，不用于任何安全用途。
 */
export function stableIndex(seed: string, modulo: number): number {
  if (modulo <= 1) return 0;
  let hash = 0x811c9dc5;
  for (const character of seed) {
    hash ^= character.codePointAt(0) ?? 0;
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash % modulo;
}

/** 由 id 稳定推导强调色：没登记的 id 也有稳定、可复现的外观。 */
export function accentForSeed(seed: string): CardAccent {
  return CARD_ACCENTS[stableIndex(seed, CARD_ACCENTS.length)] ?? DEFAULT_CARD_ACCENT;
}

/** 由 id 稳定推导图标键：从给定的候选池里取一个。 */
export function iconForSeed(seed: string, pool: readonly CardIconKey[]): CardIconKey {
  if (!pool.length) return DEFAULT_CARD_ICON;
  return pool[stableIndex(seed, pool.length)] ?? DEFAULT_CARD_ICON;
}
