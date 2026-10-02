/*
 * 图标：只包含导航与外壳需要的最少集合。
 * 约定：使用 currentColor 1.6px 描边；始终 aria-hidden，
 * 图标不参与可访问名称计算（按钮的可访问名称必须等于它的文字标签）。
 */
import type { ReactNode } from 'react';

export type IconProps = { className?: string };

function Glyph({ className, children }: IconProps & { children: ReactNode }) {
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
      {children}
    </svg>
  );
}

/** 书房（首页） */
export function HomeIcon(props: IconProps) {
  return <Glyph {...props}><path d="M4 11.2 12 4.6l8 6.6" /><path d="M6.4 10.4V19.4h11.2v-9" /><path d="M10.2 19.4v-4.2h3.6v4.2" /></Glyph>;
}

/** 学习现场 */
export function LearningIcon(props: IconProps) {
  return <Glyph {...props}><path d="M6.5 4.5h11a1.5 1.5 0 0 1 1.5 1.5v12a1.5 1.5 0 0 1-1.5 1.5h-11" /><path d="M6.5 4.5A2 2 0 0 0 4.5 6.5v11a2 2 0 0 0 2 2" /><path d="M9 9h6.5" /><path d="M9 12.6h4.5" /></Glyph>;
}

/** 学科空间 */
export function SubjectIcon(props: IconProps) {
  return <Glyph {...props}><path d="M12 6.6C10.8 5.3 8.9 4.5 6.6 4.5H4.8v13h1.8c2.3 0 4.2.8 5.4 2.1" /><path d="M12 6.6c1.2-1.3 3.1-2.1 5.4-2.1h1.8v13h-1.8c-2.3 0-4.2.8-5.4 2.1" /><path d="M12 6.6v13" /></Glyph>;
}

/** 学习方法 */
export function MethodIcon(props: IconProps) {
  return <Glyph {...props}><path d="M12 3.6a5.4 5.4 0 0 0-3.1 9.8c.5.4.7.9.7 1.5v.7h4.8v-.7c0-.6.2-1.1.7-1.5A5.4 5.4 0 0 0 12 3.6z" /><path d="M9.9 18.4h4.2" /><path d="M10.6 20.7h2.8" /></Glyph>;
}

/** 学习记录 */
export function RecordIcon(props: IconProps) {
  return <Glyph {...props}><path d="M5.5 19.5V12" /><path d="M10 19.5V5.5" /><path d="M14.5 19.5v-5" /><path d="M19 19.5V8.5" /></Glyph>;
}

/** 可考虑复习 */
export function ReviewIcon(props: IconProps) {
  return <Glyph {...props}><path d="M6.8 4.5h10.4a1.3 1.3 0 0 1 1.3 1.3v12.4a1.3 1.3 0 0 1-1.3 1.3H6.8a1.3 1.3 0 0 1-1.3-1.3V5.8a1.3 1.3 0 0 1 1.3-1.3z" /><path d="M9 9.4h6" /><path d="M9 12.7h6" /><path d="M9 16h3.4" /></Glyph>;
}

/** 今日收尾 */
export function SummaryIcon(props: IconProps) {
  return <Glyph {...props}><path d="M5.5 7.4h13v11.2h-13z" /><path d="M5.5 11h13" /><path d="M9 4.8v3.4" /><path d="M15 4.8v3.4" /><path d="M9.8 15.1l1.7 1.7 3-3" /></Glyph>;
}

/** 题目与对比 */
export function CompareIcon(props: IconProps) {
  return <Glyph {...props}><circle cx="9" cy="12" r="4.4" /><circle cx="15" cy="12" r="4.4" /></Glyph>;
}

/** 我的金句 */
export function QuoteIcon(props: IconProps) {
  return <Glyph {...props}><path d="M9.6 7.6C7.4 8.3 6.2 10.1 6.2 12.7v3.7h4.2v-4.2H8.1" /><path d="M18 7.6c-2.2.7-3.4 2.5-3.4 5.1v3.7h4.2v-4.2h-2.3" /></Glyph>;
}

/** 搜索（顶栏占位框的装饰图标，不参与可访问名称） */
export function SearchIcon(props: IconProps) {
  return <Glyph {...props}><circle cx="11" cy="11" r="5.6" /><path d="M15.2 15.2 19 19" /></Glyph>;
}

/** 卡壳点：一枚定位针，表示“卡在这里”的位置 */
export function PinIcon(props: IconProps) {
  return <Glyph {...props}><path d="M12 20.4s5.8-5.3 5.8-9.6a5.8 5.8 0 1 0-11.6 0c0 4.3 5.8 9.6 5.8 9.6z" /><circle cx="12" cy="10.6" r="2.1" /></Glyph>;
}

/** Hermes 顾问：星芒，保留 AI 语义但用线条而不是发光球 */
export function SparkIcon(props: IconProps) {
  return <Glyph {...props}><path d="M12 4.4l1.8 4.6 4.6 1.8-4.6 1.8L12 17.2l-1.8-4.6L5.6 10.8l4.6-1.8z" /><path d="M18.4 16.6l.7 1.7 1.7.7-1.7.7-.7 1.7-.7-1.7-1.7-.7 1.7-.7z" /></Glyph>;
}

/** 账号与数据：齿轮 */
export function AccountIcon(props: IconProps) {
  return <Glyph {...props}><circle cx="12" cy="12" r="2.7" /><path d="M12 3.8v2.1" /><path d="M12 18.1v2.1" /><path d="M20.2 12h-2.1" /><path d="M5.9 12H3.8" /><path d="M17.8 6.2l-1.5 1.5" /><path d="M7.7 16.3l-1.5 1.5" /><path d="M17.8 17.8l-1.5-1.5" /><path d="M7.7 7.7 6.2 6.2" /></Glyph>;
}
