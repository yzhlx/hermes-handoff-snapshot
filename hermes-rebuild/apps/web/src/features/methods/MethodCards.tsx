/*
 * 学习方法渲染层：方法卡 / 方法详情 / 情境选项
 * ------------------------------------------------------------------
 * 1. 所有文字来自 GET /learning-methods 与 /learning-situations：
 *    title / summary / problem / situations / steps / pitfalls / label / reason。
 * 2. 这里不判断具体是哪一种方法，只用「字段名 + 密度」索引自己的标签与结构；
 *    图标键与强调色来自 method-meta.ts 的 id 元数据映射。
 * 3. 因此新增第 6 种学习方法时，本文件与页面都不需要改动：
 *    新方法会自动出现在目录里，字段按接口提供的部分渲染（缺失字段不出现）。
 */
import type { LearningMethod, LearningSituation } from './catalog';
import { methodMeta, situationIcon } from './method-meta';
import { CardIcon } from '../../shared/ui/card-icons';
import './methods.css';

/** 方法卡需要的最小字段集合；详情字段按接口实际提供情况渲染。 */
export type MethodSummary = Pick<LearningMethod, 'id' | 'title' | 'summary'> &
  Partial<Pick<LearningMethod, 'problem' | 'situations' | 'steps' | 'pitfalls'>>;

/** 卡片密度：summary 只渲染标题与摘要，full 额外渲染四个详情字段。 */
export type MethodDensity = 'summary' | 'full';

/** 字段展示版式：card 是目录卡内的紧凑行，detail 是方法详情页的面板。 */
export type MethodLayout = 'card' | 'detail';

const METHOD_FIELD_KEYS = ['problem', 'situations', 'steps', 'pitfalls'] as const;
type MethodFieldKey = (typeof METHOD_FIELD_KEYS)[number];

/** 同一条数据的两种版式各自使用什么标签（短标签给卡片，长标签给详情）。 */
const FIELD_LABELS: Record<MethodFieldKey, Record<MethodLayout, string>> = {
  problem: { card: '解决什么问题', detail: '它解决什么问题' },
  situations: { card: '适用情况', detail: '什么情况适合用' },
  steps: { card: '操作步骤', detail: '怎么使用' },
  pitfalls: { card: '常见误区', detail: '常见误区' },
};

/** 字段形状：正文还是列表；列表用 ul 还是 ol。 */
const FIELD_SHAPES: Record<MethodFieldKey, { kind: 'text' | 'list'; listTag: 'ul' | 'ol' }> = {
  problem: { kind: 'text', listTag: 'ul' },
  situations: { kind: 'list', listTag: 'ul' },
  steps: { kind: 'list', listTag: 'ol' },
  pitfalls: { kind: 'list', listTag: 'ul' },
};

/** 标签在两种版式下的标题层级：详情是 h2，卡片内是 h4。 */
const FIELD_HEADINGS: Record<MethodLayout, 'h2' | 'h4'> = { card: 'h4', detail: 'h2' };

/** 字段容器的样式钩子：详情沿用既有 method-detail 面板，卡片内用紧凑行。 */
const FIELD_CLASSES: Record<MethodLayout, string> = { card: 'method-field', detail: 'panel method-detail' };

const CATALOG_NUMERALS = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十'] as const;

/**
 * 目录标题由数据数量推导，而不是写死「五种学习方法」：
 * 服务端新增第 6 种方法时标题自动变成「六大学习方法」，渲染代码零改动。
 */
export function methodCatalogHeading(count: number): string {
  if (!Number.isFinite(count) || count <= 0) return '学习方法';
  if (count === 1) return '一种学习方法';
  const numeral = CATALOG_NUMERALS[count];
  return numeral ? `${numeral}大学习方法` : `共 ${count} 种学习方法`;
}

function fieldValue(method: MethodSummary, field: MethodFieldKey): unknown {
  return method[field];
}

function MethodField({ field, method, layout }: { field: MethodFieldKey; method: MethodSummary; layout: MethodLayout }) {
  const shape = FIELD_SHAPES[field];
  const value = fieldValue(method, field);
  const label = FIELD_LABELS[field][layout];
  const Heading = FIELD_HEADINGS[layout];
  const className = FIELD_CLASSES[layout];
  if (shape.kind === 'text') {
    const text = typeof value === 'string' ? value.trim() : '';
    return text ? <section className={className}><Heading>{label}</Heading><p>{text}</p></section> : null;
  }
  const items = Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0) : [];
  if (!items.length) return null;
  const List = shape.listTag;
  return <section className={className}><Heading>{label}</Heading><List>{items.map((item) => <li key={item}>{item}</li>)}</List></section>;
}

/** 一条方法的全部字段：版式决定标签与标题层级，字段缺失就自动不渲染。 */
export function MethodFields({ method, layout }: { method: MethodSummary; layout: MethodLayout }) {
  return <>{METHOD_FIELD_KEYS.map((field) => <MethodField key={field} field={field} method={method} layout={layout} />)}</>;
}

/**
 * 方法卡：标题、摘要永远来自接口；problem/situations/steps/pitfalls
 * 只有在接口真的返回时才渲染（首页的 methods 段落是精简结构，卡片自动变紧凑）。
 */
export function MethodCard({ method, onOpen, onStart, density = 'summary', className = 'panel method-card', startLabel = '用这个方法开始 →' }: {
  method: MethodSummary;
  onOpen?: (id: string) => void;
  onStart?: (id: string) => void;
  density?: MethodDensity;
  /** 页面级样式钩子；默认是方法目录的卡片样式。 */
  className?: string;
  /** 开始按钮文案：目录用参考图的「开始使用」，首页保持原有文案。 */
  startLabel?: string;
}) {
  const meta = methodMeta(method.id);
  return <article className={className}>
    <span className={`card-icon method-card__icon card-accent--${meta.accent}`}><CardIcon icon={meta.icon} /></span>
    <h3>{method.title}</h3>
    <p>{method.summary}</p>
    {density === 'full' && <MethodFields method={method} layout="card" />}
    {(onOpen || onStart) && <div className="method-card__actions">
      {/* DESIGN.md §3.3：同屏 ≤1 个实心绿主操作。方法卡是「每个方法一张卡」的列表，
          实心绿会在一屏里出现多次，因此方法卡内的开始按钮统一用软绿次级样式；
          实心绿留给页面级主操作。 */}
      {onStart && <button type="button" className="secondary" onClick={() => onStart(method.id)}>{startLabel}</button>}
      {onOpen && <button type="button" className="secondary" onClick={() => onOpen(method.id)}>查看方法与步骤</button>}
    </div>}
  </article>;
}

/** 方法详情：四个字段区 + 开始使用。字段顺序与接口字段一一对应。 */
export function MethodDetails({ method, onStart }: { method: LearningMethod; onStart: () => void }) {
  return <>
    <MethodFields method={method} layout="detail" />
    <section className="panel method-detail method-start"><h2>开始使用</h2><p>用这个方法开始一段学习。目标仍由你决定，方法也可以随时更换。</p><button onClick={onStart}>用「{method.title}」开始</button></section>
  </>;
}

/** 情境选项：文字与理由来自接口，图标键来自情境元数据映射。 */
export function SituationChoice({ situation, selected, onSelect }: {
  situation: LearningSituation;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return <button
    className={selected ? 'situation-choice selected' : 'situation-choice'}
    aria-pressed={selected}
    onClick={() => onSelect(situation.id)}
  >
    <span className="card-icon card-icon--sm card-accent--ink"><CardIcon icon={situationIcon(situation.id)} /></span>
    {situation.label}
  </button>;
}
