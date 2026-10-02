import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { request } from '../../shared/api/client';
import type { HomeData, HomeResponse, RecordData, SuggestionData } from '../../shared/api/types';
import { DailyQuote } from '../quotes/Quotes';
import { Lulu } from '../companion';
import { Feedback } from '../../shared/ui/Feedback';
import { SubjectCard, groupSubjects } from '../knowledge/SubjectCards';
import { MethodCard } from '../methods/MethodCards';
import './home.css';

export type HomePageProps = {
  userId: string;
  onOpenSubject: (id: string) => void;
  onStartFree: () => void;
  onContinue: (last: RecordData | null) => void;
  onOpenMethods: () => void;
  onStartMethod: (id: string) => void;
  onOpenReview: () => void;
  onOpenSession: (id: string) => void;
  onOpenProblem: (id: string) => void;
  onOpenSummary: () => void;
  onOpenMyQuotes: () => void;
  /**
   * 打开完整学科空间（参考图里「学科」分区右侧的入口）。
   * 可选：不传时不渲染该入口，既有调用方的行为不变。
   */
  onOpenSubjects?: () => void;
};

type SectionName = keyof HomeData['sections'];
type SectionData<K extends SectionName> = NonNullable<HomeData['sections'][K]>['data'];
type SourceRef = SuggestionData['source_refs'][number];

/** 首页只展示前几条方法作为入口预览；完整目录在「学习方法」页。 */
const HOME_METHOD_PREVIEW = 3;

const sectionLabels: Record<SectionName, string> = {
  quote: '今日金句', subjects: '学科', continue_learning: '继续学习', suggestions: '学习线索',
  methods: '学习方法', changes: '近七日记录', review: '可以回顾',
};

function retryPath(section: SectionName) { return `/home?section=${encodeURIComponent(section)}`; }

const sectionNames: SectionName[] = ['quote', 'subjects', 'continue_learning', 'suggestions', 'methods', 'changes', 'review'];
function isObject(value: unknown): value is Record<string, unknown> { return Boolean(value) && typeof value === 'object' && !Array.isArray(value); }
function validRefs(value: unknown) {
  return Array.isArray(value) && value.every((ref) => isObject(ref) && typeof ref.id === 'string' && typeof ref.kind === 'string' && typeof ref.label === 'string' && typeof ref.version === 'number' && typeof ref.occurred_at === 'string' && Number.isFinite(Date.parse(ref.occurred_at)));
}
function validTextItems(value: unknown) {
  return Array.isArray(value) && value.every((item) => isObject(item) && typeof item.text === 'string' && validRefs(item.source_refs));
}
function validSuggestions(value: unknown) {
  return Array.isArray(value) && value.every((item) => isObject(item) && typeof item.id === 'string' && typeof item.reason === 'string' && validRefs(item.source_refs));
}
function validSectionData(name: SectionName, value: unknown) {
  if (!isObject(value)) return false;
  if (name === 'quote') return isObject(value.daily_quote) && typeof value.daily_quote.local_date === 'string' && typeof value.daily_quote.day_timezone === 'string' && (value.daily_quote.quote === null || (isObject(value.daily_quote.quote) && typeof value.daily_quote.quote.id === 'string' && typeof value.daily_quote.quote.text === 'string'));
  if (name === 'subjects') return Array.isArray(value.items) && value.items.every((item) => isObject(item) && typeof item.id === 'string' && typeof item.name === 'string' && (item.group_label === undefined || item.group_label === null || typeof item.group_label === 'string'));
  if (name === 'continue_learning') return (value.current === null || (isObject(value.current) && typeof value.current.id === 'string' && ['active', 'paused', 'ended', 'cancelled'].includes(String(value.current.status)) && typeof value.current.effective_duration_seconds === 'number')) && (value.last === null || (isObject(value.last) && typeof value.last.id === 'string' && typeof value.last.learning_date === 'string'));
  if (name === 'suggestions' || name === 'review') return validSuggestions(value.items);
  if (name === 'methods') return Array.isArray(value.items) && value.items.every((item) => isObject(item) && typeof item.id === 'string' && typeof item.title === 'string' && typeof item.summary === 'string');
  return validTextItems(value.items) && typeof value.effective_learning_days === 'number' && typeof value.from_date === 'string' && typeof value.to_date === 'string';
}
function parseHomeResponse(value: unknown): HomeResponse {
  if (!isObject(value) || !isObject(value.data) || typeof value.data.date !== 'string' || typeof value.data.timezone !== 'string' || typeof value.data.rule_version !== 'string' || !isObject(value.data.sections)) {
    throw new Error('首页响应格式不正确，请重试读取。');
  }
  const sections = { ...value.data.sections };
  for (const name of sectionNames) {
    const sectionValue = value.data.sections[name];
    if (sectionValue === undefined || sectionValue === null) {
      sections[name] = { status: 'unavailable', data: null, source_revision: null, error: { code: 'missing_home_section', message: `${sectionLabels[name]}暂时无法读取，请重试。` } };
      continue;
    }
    if (!isObject(sectionValue) || !['ready', 'empty', 'unavailable'].includes(String(sectionValue.status)) || (sectionValue.status !== 'unavailable' && !validSectionData(name, sectionValue.data))) {
      sections[name] = { status: 'unavailable', data: null, source_revision: null, error: { code: 'invalid_home_section', message: `${sectionLabels[name]}暂时无法读取，请重试。` } };
    }
  }
  return { ...value, data: { ...value.data, sections } } as unknown as HomeResponse;
}

function Section<K extends SectionName>({
  name, section, retry, retryError, action, hideHeading, children,
}: {
  name: K;
  section: NonNullable<HomeData['sections'][K]>;
  retry: () => void;
  retryError?: string;
  /** 分区标题右侧的入口（参考图里各分区的「查看全部」位置）。 */
  action?: React.ReactNode;
  /**
   * 标题只留给读屏，不在屏幕上显示。
   * 用于「今日金句」这类区块：参考图里金句没有可见的小标题，但 section 仍需要
   * 一个可访问名称（aria-labelledby 指向它），直接删掉会削弱无障碍语义。
   */
  hideHeading?: boolean;
  children: (data: NonNullable<SectionData<K>>) => React.ReactNode;
}) {
  return <section className="home-section" aria-labelledby={`home-${name}-title`}>
    <div className="home-section-heading">
      <h2 id={`home-${name}-title`} className={hideHeading ? 'visually-hidden' : undefined}>{sectionLabels[name]}</h2>
      {action}
    </div>
    {section.status === 'unavailable' ? <div className="home-section-error" role="status">
      <span>{section.error?.message || '这部分暂时无法读取。'}</span>
      <button type="button" className="secondary" onClick={retry}>重试</button>
      {retryError && <p role="alert">{retryError}</p>}
    </div> : section.data ? children(section.data as NonNullable<SectionData<K>>) : <p className="home-empty">这里暂时没有可显示的内容。</p>}
  </section>;
}

function refDate(value: string, timezone: string) {
  return `${new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short', timeZone: timezone }).format(new Date(value))} · ${timezone}`;
}

function SourceButton({ ref, timezone, onOpenSession, onOpenProblem }: {
  ref: SourceRef;
  timezone: string;
  onOpenSession: (id: string) => void;
  onOpenProblem: (id: string) => void;
}) {
  const open = () => {
    if (ref.session_id || ref.kind === 'session') onOpenSession(ref.session_id ?? ref.id);
    else if (ref.problem_id || ref.kind === 'problem') onOpenProblem(ref.problem_id ?? ref.id);
  };
  const canOpen = Boolean(ref.session_id || ref.kind === 'session' || ref.problem_id || ref.kind === 'problem');
  return <li className="home-evidence-meta">{canOpen
    ? <button type="button" className="home-source-button" onClick={open}>{ref.label} · v{ref.version} · {refDate(ref.occurred_at, timezone)} →</button>
    : <span>{ref.label} · v{ref.version} · {refDate(ref.occurred_at, timezone)}</span>}
  </li>;
}

function evidenceList(items: { text: string; source_refs: SourceRef[] }[], timezone: string, onOpenSession: (id: string) => void, onOpenProblem: (id: string) => void) {
  if (!items.length) return <p className="home-empty">近七个账号自然日还没有留下这类记录。</p>;
  return <ul className="home-evidence-list">{items.map((item, index) => <li key={`${item.text}:${index}`}>
    <p>{item.text}</p><ul>{item.source_refs.map((ref) => <SourceButton key={`${ref.kind}:${ref.id}:${ref.version}`} ref={ref} timezone={timezone} onOpenSession={onOpenSession} onOpenProblem={onOpenProblem} />)}</ul>
  </li>)}</ul>;
}

function suggestionItems(items: SuggestionData[], timezone: string, onOpenSession: (id: string) => void, onOpenProblem: (id: string) => void) {
  if (!items.length) return <p className="home-empty">目前没有待核对或反复出现的错误线索。</p>;
  return <ul className="home-evidence-list">{items.map((item) => <li key={item.id}>
    <p>{item.reason}</p><ul>{item.source_refs.map((ref) => <SourceButton key={`${ref.kind}:${ref.id}:${ref.version}`} ref={ref} timezone={timezone} onOpenSession={onOpenSession} onOpenProblem={onOpenProblem} />)}</ul>
  </li>)}</ul>;
}

export function HomePage({
  userId, onOpenSubject, onStartFree, onContinue, onOpenMethods, onStartMethod,
  onOpenReview, onOpenSession, onOpenProblem, onOpenSummary, onOpenMyQuotes, onOpenSubjects,
}: HomePageProps) {
  const client = useQueryClient();
  const [retryErrors, setRetryErrors] = useState<Partial<Record<SectionName, string>>>({});
  const queryKey = ['home', userId] as const;
  const home = useQuery({ queryKey, queryFn: async ({ signal }) => parseHomeResponse(await request<unknown>('/home', { signal })), retry: false });
  const data = home.data?.data;
  const section = <K extends SectionName>(name: K) => data?.sections[name] as NonNullable<HomeData['sections'][K]> | undefined;
  const retry = async (name: SectionName) => {
    setRetryErrors((current) => ({ ...current, [name]: undefined }));
    try {
      const fresh = parseHomeResponse(await request<unknown>(retryPath(name)));
      const refreshedSection = fresh.data.sections[name];
      if (!refreshedSection) throw new Error('服务没有返回刚才请求的这一部分。');
      const previous = client.getQueryData<HomeResponse>(queryKey);
      let refreshQuoteCache = name === 'quote';
      if (previous && (fresh.data.date !== previous.data.date || fresh.data.timezone !== previous.data.timezone || fresh.data.rule_version !== previous.data.rule_version)) {
        const fullRefresh = await home.refetch();
        if (fullRefresh.isError) throw fullRefresh.error;
        refreshQuoteCache = true;
      } else client.setQueryData<HomeResponse>(queryKey, (cached) => cached ? {
        ...cached,
        data: { ...cached.data, sections: { ...cached.data.sections, [name]: refreshedSection } },
      } : fresh);
      if (refreshQuoteCache) await client.invalidateQueries({ queryKey: ['quotes', userId, 'today'] });
    } catch (error) {
      setRetryErrors((current) => ({ ...current, [name]: error instanceof Error ? error.message : '重试没有完成，请稍后再试。' }));
    }
  };

  if (home.isPending) return <section className="workspace home-page" aria-live="polite"><p role="status" className="muted">正在整理今天的书房…</p></section>;
  if (!data) return <section className="workspace home-page" aria-labelledby="home-error-title">
    <h1 id="home-error-title">书房暂时无法载入</h1><p className="muted">没有读取到首页数据，请连接服务后重试。你也可以先进入自由学习。</p>
    <Feedback error={home.error} /><div className="home-primary-actions"><button className="secondary" onClick={() => void home.refetch()}>重试读取首页</button><button onClick={onStartFree}>开始一段学习 →</button><button className="secondary" onClick={onOpenMethods}>浏览学习方法 →</button></div>
  </section>;

  const subjects = section('subjects');
  const subjectItems = subjects?.status !== 'unavailable' ? subjects?.data?.items ?? [] : [];
  return <section className="workspace home-page" aria-labelledby="home-title">
    <header className="home-heading"><div><span className="eyebrow">YOUR STUDY ROOM</span><h1 id="home-title">今天的书房</h1></div><span className="home-date">{data.date} · {data.timezone}</span></header>
    {/* 参考图的 hero 是一张实景照片（窗边绿植 + 书堆 + 马克杯）；该素材本批不可得，
        按 DESIGN.md §5 用令牌化手法做出体积：三层米色带 + 极淡纹理 + 内描边 +
        右侧线性母题（纯 SVG，aria-hidden），不用灰色渐变冒充照片。 */}
    <div className="page-hero home-hero">
      <div className="home-hero__motif" aria-hidden="true">
        {/* 学习角落的线性母题：一摞书 + 马克杯 + 一盆绿植。纯装饰（aria-hidden）、纯 SVG、
            由 currentColor 驱动（容器给 --accent-warm-ink），只有两处 fill-opacity 淡填充，
            不引入位图、不使用灰色渐变。stroke-width 2.5 + CSS 的 vector-effect: non-scaling-stroke
            ⇒ 无论 hero 高度如何缩放（stub 284 / 真实 219），描边恒为 2.5px，不会再变淡。 */}
        <svg viewBox="2 34 296 98" width="296" height="98" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          {/* 一摞横放的书（书脊 + 书名线） */}
          <rect x="14" y="112" width="112" height="16" rx="3" />
          <rect x="21" y="94" width="98" height="16" rx="3" />
          <rect x="30" y="76" width="80" height="16" rx="3" />
          <path d="M26 120h26M33 102h26M42 84h26" />
          {/* 立着的书 */}
          <rect x="132" y="96" width="18" height="32" rx="2" />
          <rect x="152" y="88" width="16" height="40" rx="2" />
          {/* 马克杯 */}
          <path d="M178 128v-32h36v24a8 8 0 0 1-8 8h-20a8 8 0 0 1-8-8z" />
          <path d="M214 106h8a7 7 0 0 1 0 14h-8" />
          <path d="M188 88c0-4 4-4 4-9M202 88c0-4 4-4 4-9" />
          {/* 盆栽：花盆（淡填充）+ 三片叶 */}
          <path d="M234 128h50l-7-26h-36z" fill="currentColor" fillOpacity="0.14" />
          <path d="M230 102h58" />
          <path d="M259 102c-2-18-8-30-19-38" />
          <path d="M259 102c2-20 8-32 20-40" />
          <path d="M240 70c8-10 19-11 27-3-8 9-19 10-27 3z" fill="currentColor" fillOpacity="0.10" />
          <path d="M277 62c-7-10-2-20 9-24 5 11 0 20-9 24z" fill="currentColor" fillOpacity="0.10" />
          <path d="M258 96c-10-7-21-4-28 4 10 6 21 4 28-4z" fill="currentColor" fillOpacity="0.10" />
          {/* 桌面 */}
          <path d="M6 128h288" />
        </svg>
      </div>
      {section('quote') && <Section name="quote" section={section('quote')!} retry={() => void retry('quote')} retryError={retryErrors.quote} hideHeading>
        {(quoteData) => <DailyQuote userId={userId} onOpenMyQuotes={onOpenMyQuotes} hero initialData={{ data: quoteData, meta: { request_id: 'home-seed' } }} />}
      </Section>}
    </div>
    <div className="home-row">
      {section('subjects') && <Section
        name="subjects"
        section={section('subjects')!}
        retry={() => void retry('subjects')}
        retryError={retryErrors.subjects}
        action={<div className="home-heading-actions">
          {/* 自由学习入口是一个动作，不是学科：不占学科网格的格子（保留既有可访问名称）。 */}
          <button type="button" className="secondary" onClick={onStartFree}>开始一段学习 →</button>
          {onOpenSubjects && <button type="button" className="home-inline-link" onClick={onOpenSubjects}>查看全部学科 →</button>}
        </div>}
      >
        {(value) => {
          const data = value as NonNullable<SectionData<'subjects'>>;
          const items = data?.items ?? [];
          const groups = groupSubjects(items);
          return <>
            {/* DESIGN.md §2：参考图是 6 列徽章卡一行（184×129，gap 12）。
                我们的学科来自接口且带分组：分组名保留为仅供读屏的标题（每组恰好一次），
                卡片与「开始一段学习」入口排成同一行网格。 */}
            <div className="home-subject-grid">
              {groups.map((group) => <h3 className="visually-hidden" key={group.key}>{group.label}</h3>)}
              {items.map((subject) => <SubjectCard key={subject.id} subject={subject} onOpen={onOpenSubject} variant="inline" />)}
            </div>
            {!items.length && <p className="home-empty">添加学科后，这里会出现你的学习入口。</p>}
          </>;
        }}
      </Section>}
    </div>
    <div className="home-grid">
      <div className="home-column">
        {section('continue_learning') && <Section name="continue_learning" section={section('continue_learning')!} retry={() => void retry('continue_learning')} retryError={retryErrors.continue_learning}>
          {(value) => {
            const continuation = value as NonNullable<SectionData<'continue_learning'>>;
            const active = continuation.current?.status === 'active' || continuation.current?.status === 'paused' ? continuation.current : null;
            const record = continuation.last;
            if (!active && !record) return <p className="home-empty">还没有可以继续的学习现场。</p>;
            const currentSubject = active?.subject_id ? subjectItems.find((item) => item.id === active.subject_id)?.name : null;
            return <div className="home-continue"><div><h3>{active?.goal || record?.goal || record?.resume_note?.trim() || record?.summary || '自由学习'}</h3><p>{active ? `${currentSubject ?? '自由学习'} · ${active.status === 'paused' ? '已暂停' : '进行中'} · ${active.effective_duration_seconds} 秒` : `${record?.learning_date} · ${record?.subject_name ?? '自由学习'}`}</p>
              {!active && record?.resume_note?.trim() && <p><strong>继续位置：</strong>{record.resume_note}</p>}
              {!active && record?.stuck_note?.trim() && <p><strong>上次卡点：</strong>{record.stuck_note}</p>}
            </div>
              <button type="button" onClick={active ? () => onContinue(null) : () => record && onContinue(record)}>{active ? '继续当前现场 →' : '继续上次 →'}</button></div>;
          }}
        </Section>}
      </div>
      <div className="home-column">
        {section('suggestions') && <Section name="suggestions" section={section('suggestions')!} retry={() => void retry('suggestions')} retryError={retryErrors.suggestions}>
          {(value) => {
            const suggestionData = value as NonNullable<SectionData<'suggestions'>>;
            return <>{suggestionItems(suggestionData.items, data.timezone, onOpenSession, onOpenProblem)}
              <button type="button" className="home-inline-link" onClick={onOpenReview}>查看全部学习建议 →</button>
            </>;
          }}
        </Section>}
      </div>
    </div>
    <div className="home-row">
      {section('methods') && <Section name="methods" section={section('methods')!} retry={() => void retry('methods')} retryError={retryErrors.methods}>
        {(value) => {
          const methodData = value as NonNullable<SectionData<'methods'>>;
          return <><div className="home-methods">{methodData.items.slice(0, HOME_METHOD_PREVIEW).map((method) => <MethodCard key={method.id} method={method} className="home-method" onStart={onStartMethod} />)}</div>
            {!methodData.items.length && <p className="home-empty">方法目录暂时没有可展示的条目。</p>}
            <button type="button" className="home-inline-link" onClick={onOpenMethods}>打开完整方法目录 →</button>
          </>;
        }}
      </Section>}
    </div>
    <div className="home-grid">
      <div className="home-column">
        {section('changes') && <Section name="changes" section={section('changes')!} retry={() => void retry('changes')} retryError={retryErrors.changes}>
          {(value) => {
            const changeData = value as NonNullable<SectionData<'changes'>>;
            return <><p className="home-changes-summary"><strong>{changeData.effective_learning_days}</strong> 个有效学习日 <span>· {changeData.from_date} 至 {changeData.to_date}</span></p>
              {evidenceList(changeData.items, data.timezone, onOpenSession, onOpenProblem)}
              <button type="button" className="home-inline-link" onClick={onOpenSummary}>查看今日收尾 →</button>
            </>;
          }}
        </Section>}
      </div>
      <div className="home-column">
        {section('review') && <Section name="review" section={section('review')!} retry={() => void retry('review')} retryError={retryErrors.review}>
          {(value) => {
            const reviewData = value as NonNullable<SectionData<'review'>>;
            return <>{reviewData.items.length ? <ul className="home-evidence-list">{reviewData.items.map((item) => <li key={item.id}><p>{item.reason}</p><ul>{item.source_refs.map((ref) => <SourceButton key={`${ref.kind}:${ref.id}:${ref.version}`} ref={ref} timezone={data.timezone} onOpenSession={onOpenSession} onOpenProblem={onOpenProblem} />)}</ul></li>)}</ul> : <p className="home-empty">当前没有可以回顾的建议。无需补做任何内容。</p>}
              <button type="button" className="home-inline-link" onClick={onOpenReview}>打开复习建议列表 →</button>
            </>;
          }}
        </Section>}
      </div>
    </div>
    <div className="home-lulu-slot"><Lulu context="home" userId={userId} /></div>
  </section>;
}
