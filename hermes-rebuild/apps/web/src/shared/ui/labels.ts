import type { components } from '../../../../../packages/contracts/src/schema';

export type ErrorCategory = components['schemas']['ErrorCategory'];

export const errorCategoryLabels: Record<ErrorCategory, string> = {
  concept: '概念',
  modeling: '思路 / 建模',
  condition: '条件判断',
  formula: '公式',
  derivation: '推导',
  calculation: '计算',
  sign: '符号 / 正负 / 方向',
  unit: '单位',
  reading: '审题',
  other: '其他',
};
