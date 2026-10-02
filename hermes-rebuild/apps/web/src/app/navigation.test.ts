import { describe, expect, it } from 'vitest';
import { NAV_GROUP_ORDER, NAV_ITEMS, navGroups, navItemFor, pageTitle } from './navigation';

describe('app navigation data', () => {
  /*
   * 入口集合是产品决策，不是实现细节：合并远程功能分支后，
   * 侧栏覆盖全部真实页面（9 项既有 + 卡壳点 / Hermes 顾问 / 账号与数据）。
   * 这里把「哪些入口、以什么顺序出现」显式锁住——顺序变化或入口漏接都会失败，
   * 而不是任由渲染层自行决定。
   */
  it('exposes every real page as a navigation entry, in a fixed order', () => {
    expect(NAV_ITEMS.map((item) => [item.id, item.label])).toEqual([
      ['home', '书房'],
      ['learning', '学习现场'],
      ['subjects', '学科空间'],
      ['methods', '学习方法'],
      ['history', '学习记录'],
      ['stuck-points', '卡壳点'],
      ['review', '可考虑复习'],
      ['summary', '今日收尾'],
      ['comparisons', '题目与对比'],
      ['advisor', 'Hermes 顾问'],
      ['quotes', '我的金句'],
      ['account', '账号与数据'],
    ]);
  });

  it('groups every entry under a declared group, in the declared group order', () => {
    const groups = navGroups(NAV_ITEMS);
    expect(groups.map((group) => group.group)).toEqual([...NAV_GROUP_ORDER]);
    expect(groups.flatMap((group) => group.items).map((item) => item.id))
      .toEqual(NAV_ITEMS.map((item) => item.id));
    expect(groups.every((group) => group.items.length > 0)).toBe(true);
    expect(groups.every((group) => group.label.trim().length > 0)).toBe(true);
  });

  it('uses unique page ids and unique accessible labels', () => {
    const ids = NAV_ITEMS.map((item) => item.id);
    const labels = NAV_ITEMS.map((item) => item.label);
    expect(new Set(ids).size).toBe(ids.length);
    expect(new Set(labels).size).toBe(labels.length);
    expect(labels.every((label) => label.trim().length > 0)).toBe(true);
    expect(NAV_ITEMS.every((item) => typeof item.icon === 'function')).toBe(true);
  });

  it('maps a detail page onto its parent entry, for both selection and title', () => {
    expect(navItemFor('subject-space')?.id).toBe('subjects');
    expect(pageTitle('subject-space')).toBe('学科空间');
  });

  it('derives every page title from the same data as the navigation labels', () => {
    for (const item of NAV_ITEMS) {
      expect(navItemFor(item.id)?.id).toBe(item.id);
      expect(pageTitle(item.id)).toBe(item.label);
    }
  });
});
