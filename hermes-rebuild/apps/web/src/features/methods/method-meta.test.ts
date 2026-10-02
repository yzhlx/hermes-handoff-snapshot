/*
 * 方法 / 情境元数据映射的门禁测试。
 * 断言把「渲染层不许认识具体数据」变成可执行规则：
 * 1. 元数据映射的值里不能出现任何标题/文案字面量（键是接口 id，跑不掉）；
 * 2. 未登记的 id 必须得到稳定、可复现的外观（新增第 6 种方法零改动）；
 * 3. 入口目标只由 id 元数据决定，缺省是学习现场。
 */
import { describe, expect, it } from 'vitest';
import { DEFAULT_METHOD_START, METHOD_META, SITUATION_META, methodMeta, methodStartTarget, situationIcon } from './method-meta';
import { CARD_ACCENTS } from '../../shared/ui/card-kit';

/** 服务端目录（apps/api/src/hermes_api/catalog.py）里的方法 id。 */
const CATALOG_METHOD_IDS = ['active-recall', 'practice-feedback', 'spaced-review', 'worked-example-compare', 'feynman-check'];
/** 追加的新方法 id：模拟「第 6/7/8 种方法」，不允许需要改代码才能渲染。 */
const APPENDED_METHOD_IDS = ['QA_TEST_method_6', 'QA_TEST_method_7', 'QA_TEST_method_8'];
const CJK = /[\u4e00-\u9fff]/;

describe('method and situation metadata', () => {
  it('keeps presentation metadata free of any catalog copy', () => {
    expect(JSON.stringify(Object.values(METHOD_META))).not.toMatch(CJK);
    expect(JSON.stringify(Object.values(SITUATION_META))).not.toMatch(CJK);
  });

  it('registers the whole server catalog without storing its text', () => {
    for (const id of CATALOG_METHOD_IDS) {
      expect(Object.keys(METHOD_META)).toContain(id);
      expect(METHOD_META[id]?.icon).toBeTruthy();
      expect(CARD_ACCENTS).toContain(METHOD_META[id]?.accent);
    }
  });

  it('gives appended methods a stable appearance without any code change', () => {
    for (const id of APPENDED_METHOD_IDS) {
      const first = methodMeta(id);
      expect(first).toEqual(methodMeta(id));
      expect(CARD_ACCENTS).toContain(first.accent);
      expect(first.icon).toBeTruthy();
    }
    // 追加的方法不会全部落到同一个外观上（否则等于退化成写死一种样式）。
    const icons = new Set([...CATALOG_METHOD_IDS, ...APPENDED_METHOD_IDS].map((id) => methodMeta(id).icon));
    expect(icons.size).toBeGreaterThan(2);
    const accents = new Set([...CATALOG_METHOD_IDS, ...APPENDED_METHOD_IDS].map((id) => methodMeta(id).accent));
    expect(accents.size).toBeGreaterThan(2);
  });

  it('routes every method to the learning scene unless its id is registered otherwise', () => {
    expect(methodStartTarget('worked-example-compare')).toBe('comparison');
    for (const id of [...CATALOG_METHOD_IDS.filter((item) => item !== 'worked-example-compare'), ...APPENDED_METHOD_IDS]) {
      expect(methodStartTarget(id)).toBe(DEFAULT_METHOD_START);
    }
    expect(methodStartTarget(null)).toBe(DEFAULT_METHOD_START);
  });

  it('gives unknown situations a stable icon too', () => {
    expect(situationIcon('QA_TEST_situation_new')).toBe(situationIcon('QA_TEST_situation_new'));
    expect(situationIcon('QA_TEST_situation_new')).toBeTruthy();
  });
});
