/*
 * 卡片图标注册表（图标键 → 图形）
 * ------------------------------------------------------------------
 * 1. 这里没有任何来自接口的标题或文案，也没有 id 判断：只有「图标键」到线稿的映射。
 * 2. 元数据层（features/methods/method-meta.ts、features/knowledge/subject-meta.ts）
 *    只保存图标键，渲染层用 CardIcon 解析，因此新增数据条目时本文件与渲染层都不用改。
 * 3. 全部图标 aria-hidden，不参与可访问名称；按钮的可访问名称必须等于它的文字标签。
 * 4. 线稿统一 24 视口、currentColor 1.6px 描边，颜色由 .card-icon 的令牌提供。
 */
import type { ReactNode } from 'react';
import './cards.css';

export type CardIconKey =
  | 'recall'
  | 'practice'
  | 'spaced'
  | 'cycle'
  | 'compare'
  | 'explain'
  | 'question'
  | 'cross'
  | 'face'
  | 'play'
  | 'book'
  | 'sigma'
  | 'language'
  | 'politics'
  | 'signal'
  | 'circuit'
  | 'matrix'
  | 'grid'
  | 'generic';

const GLYPHS: Record<CardIconKey, ReactNode> = {
  recall: <><circle cx="12" cy="9.2" r="3.5" /><path d="M5.9 19.6a6.1 6.1 0 0 1 12.2 0" /><path d="M17.6 5.4l1.3-1.3" /><path d="M18.4 6.6h1.8" /></>,
  practice: <><path d="M6.4 4.8h7l3.8 3.8v10.6H6.4z" /><path d="M13.2 5v3.8h3.8" /><path d="M9.2 14.4l1.8 1.8 3.4-3.4" /></>,
  spaced: <><circle cx="12" cy="12" r="7.2" /><path d="M12 8.4V12l2.8 1.8" /></>,
  cycle: <><path d="M6.6 10.6a5.6 5.6 0 0 1 9.1-2.3l1.7 1.5" /><path d="M18.2 5.9v3.6h-3.6" /><path d="M17.4 13.4a5.6 5.6 0 0 1-9.1 2.3l-1.7-1.5" /><path d="M5.8 18.1v-3.6h3.6" /></>,
  compare: <><circle cx="9.2" cy="12" r="4.4" /><circle cx="14.8" cy="12" r="4.4" /></>,
  explain: <><path d="M3.8 9.4 12 5.2l8.2 4.2-8.2 4.2z" /><path d="M7.6 11.4v4.2c0 1.3 2 2.3 4.4 2.3s4.4-1 4.4-2.3v-4.2" /></>,
  question: <><circle cx="12" cy="12" r="7.2" /><path d="M9.9 10.2a2.2 2.2 0 1 1 3.1 2.1c-.7.4-1 .9-1 1.7v.3" /><path d="M12 17.1h.01" /></>,
  cross: <><circle cx="12" cy="12" r="7.2" /><path d="M9.4 9.4l5.2 5.2" /><path d="M14.6 9.4l-5.2 5.2" /></>,
  face: <><circle cx="12" cy="12" r="7.2" /><path d="M9.6 14.9c.6-.9 1.4-1.3 2.4-1.3s1.8.4 2.4 1.3" /><path d="M9.8 10.2h.01" /><path d="M14.2 10.2h.01" /></>,
  play: <><circle cx="12" cy="12" r="7.2" /><path d="M10.2 8.9 15.4 12l-5.2 3.1z" /></>,
  book: <><path d="M12 6.6C10.8 5.3 8.9 4.5 6.6 4.5H4.8v13h1.8c2.3 0 4.2.8 5.4 2.1" /><path d="M12 6.6c1.2-1.3 3.1-2.1 5.4-2.1h1.8v13h-1.8c-2.3 0-4.2.8-5.4 2.1" /><path d="M12 6.6v13" /></>,
  sigma: <><path d="M16.6 5.9H7.6l4.5 6.1-4.5 6.1h9" /></>,
  language: <><path d="M5.7 18.6 11 5.8l5.3 12.8" /><path d="M7.8 14.2h6.4" /></>,
  politics: <><path d="M4.8 19.4h14.4" /><path d="M6.4 19.4V10.8" /><path d="M10.1 19.4V10.8" /><path d="M13.9 19.4V10.8" /><path d="M17.6 19.4V10.8" /><path d="M12 4.6 19.2 8.9H4.8z" /></>,
  signal: <><path d="M3.8 12h2.9l1.7-4.6 2.5 9.2 2.1-6.4 1.5 3.4h5.7" /></>,
  /* 参考图「电路基础」徽章：带引脚的芯片符号 */
  circuit: <><rect x="7.6" y="7.6" width="8.8" height="8.8" rx="1.6" /><path d="M10.6 4.6v3" /><path d="M13.4 4.6v3" /><path d="M10.6 16.4v3" /><path d="M13.4 16.4v3" /><path d="M4.6 10.6h3" /><path d="M4.6 13.4h3" /><path d="M16.4 10.6h3" /><path d="M16.4 13.4h3" /></>,
  /* 参考图「英语」以外的理数科目：方括号 + 点阵表示矩阵 */
  matrix: <><path d="M8.4 4.8H6.2v14.4h2.2" /><path d="M15.6 4.8h2.2v14.4h-2.2" /><circle cx="10.5" cy="10.5" r="1.05" fill="currentColor" stroke="none" /><circle cx="13.5" cy="10.5" r="1.05" fill="currentColor" stroke="none" /><circle cx="10.5" cy="13.5" r="1.05" fill="currentColor" stroke="none" /><circle cx="13.5" cy="13.5" r="1.05" fill="currentColor" stroke="none" /></>,
  /* 参考图「自由学习」徽章：四个圆角方块 */
  grid: <><rect x="4.6" y="4.6" width="6" height="6" rx="1.6" /><rect x="13.4" y="4.6" width="6" height="6" rx="1.6" /><rect x="4.6" y="13.4" width="6" height="6" rx="1.6" /><rect x="13.4" y="13.4" width="6" height="6" rx="1.6" /></>,
  generic: <><circle cx="12" cy="12" r="7.2" /><path d="M12 8.9v6.2" /><path d="M8.9 12h6.2" /></>,
};

export type CardIconProps = { icon: CardIconKey; className?: string };

export function CardIcon({ icon, className }: CardIconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {GLYPHS[icon] ?? GLYPHS.generic}
    </svg>
  );
}
