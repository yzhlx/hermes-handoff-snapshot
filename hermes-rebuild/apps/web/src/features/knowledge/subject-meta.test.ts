/*
 * 学科元数据映射的门禁测试。
 * 学科 id 由数据库生成（用户自建学科），所以外观只能按 id 稳定推导 + 按 group 登记：
 * 1. 元数据的值里不能出现学科名一类的文案字面量；
 * 2. 未登记的 id / group 必须得到稳定、可复现的外观（新增第 7 个学科零改动）。
 */
import { describe, expect, it } from 'vitest';
import { SUBJECT_GROUP_ACCENTS, subjectGroupAccent, subjectMeta } from './subject-meta';
import { accentForSeed, CARD_ACCENTS } from '../../shared/ui/card-kit';

/** 服务端 catalog.subject_group_label 目前产生的两个分组。 */
const CATALOG_GROUPS = ['上海大学829', '公共课'];
/** 追加的新分组：模拟后端新增分组，不允许需要改前端代码才能渲染。 */
const APPENDED_GROUPS = ['QA_TEST_新分组一', 'QA_TEST_新分组二'];
const CJK = /[\u4e00-\u9fff]/;

describe('subject metadata', () => {
  it('stores only accent tokens, never subject copy', () => {
    expect(JSON.stringify(Object.values(SUBJECT_GROUP_ACCENTS))).not.toMatch(CJK);
    for (const value of Object.values(SUBJECT_GROUP_ACCENTS)) expect(CARD_ACCENTS).toContain(value);
  });

  it('falls back to a stable accent for catalog and appended groups alike', () => {
    for (const group of CATALOG_GROUPS) expect(CARD_ACCENTS).toContain(subjectGroupAccent(group));
    for (const group of APPENDED_GROUPS) expect(subjectGroupAccent(group)).toBe(subjectGroupAccent(group));
    expect(subjectGroupAccent(null)).toBeTruthy();
    expect(subjectGroupAccent('   ')).toBeTruthy();
  });

  it('derives a stable icon per subject id and colors by subject identity, not by group', () => {
    const identity = { id: 'QA_TEST_subject_1', name: 'QA_TEST 学科一', group_label: 'QA_TEST_新分组一' };
    expect(subjectMeta(identity)).toEqual(subjectMeta(identity));
    // t13 规则修正：强调色按学科身份取。分组只用于分组标题与排序，不再决定颜色，
    // 所以换一个分组标签不会改变同一个学科的颜色（旧规则下这里相等的是分组色）。
    expect(subjectMeta(identity).accent).toBe(accentForSeed(identity.id));
    expect(subjectMeta({ ...identity, group_label: 'QA_TEST_另一个分组' }).accent).toBe(subjectMeta(identity).accent);
    expect(subjectMeta({ ...identity, group_label: null }).accent).toBe(subjectMeta(identity).accent);
    const icons = new Set(Array.from({ length: 7 }, (_, index) => subjectMeta({ id: `QA_TEST_subject_${index}` }).icon));
    expect(icons.size).toBeGreaterThan(1);
  });

  it('gives the six reference subjects six distinct accents and matching icons', () => {
    // 参考图首页「我的学科」六张卡：高数 / 信号 / 电路 / 英语 / 政治 / 自由学习。
    const reference: { id: string; name: string }[] = [
      { id: 'QA_TEST_ref_1', name: '高等数学' },
      { id: 'QA_TEST_ref_2', name: '信号与系统' },
      { id: 'QA_TEST_ref_3', name: '电路基础' },
      { id: 'QA_TEST_ref_4', name: '英语' },
      { id: 'QA_TEST_ref_5', name: '政治' },
      { id: 'QA_TEST_ref_6', name: '自由学习' },
    ];
    const metas = reference.map((subject) => subjectMeta(subject));
    expect(metas.map((meta) => meta.accent)).toEqual(['sage', 'indigo', 'warm', 'plum', 'clay', 'ink']);
    expect(new Set(metas.map((meta) => meta.accent)).size).toBe(reference.length);
    expect(metas.map((meta) => meta.icon)).toEqual(['sigma', 'signal', 'circuit', 'language', 'politics', 'grid']);
    // 同一分组的学科不再同色：公共课下的数学 / 英语 / 政治必须两两不同。
    const sameGroup = reference.filter((subject) => subject.name !== '信号与系统' && subject.name !== '电路基础')
      .map((subject) => subjectMeta({ ...subject, group_label: '公共课' }));
    expect(new Set(sameGroup.map((meta) => meta.accent)).size).toBe(sameGroup.length);
  });

  it('colors subjects without a group by their own id (the /records shape)', () => {
    // /records 只返回 subject_id 与 subject_name，没有 group_label。
    const recordShape = Array.from({ length: 7 }, (_, index) => subjectMeta({ id: `QA_TEST_subject_${index}` }));
    expect(new Set(recordShape.map((meta) => meta.accent)).size).toBeGreaterThan(1);
    expect(subjectMeta({ id: 'QA_TEST_subject_0' })).toEqual(subjectMeta({ id: 'QA_TEST_subject_0', group_label: null }));
  });
});
