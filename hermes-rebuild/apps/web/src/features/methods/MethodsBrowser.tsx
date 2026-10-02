import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { request } from '../../shared/api/client';
import type { LearningMethodsResponse, LearningSituationsResponse } from '../../shared/api/types';
import { MethodCard, MethodDetails, SituationChoice, methodCatalogHeading } from './MethodCards';
import './methods.css';

export type MethodsBrowserProps = {
  onStart: (choice: { methodId: string | null; situationId: string | null }) => void;
};

/**
 * 方法目录：情境与方法条目全部来自 GET /learning-situations 与 GET /learning-methods。
 * 页面不判断具体是哪一种方法，只负责把接口数组交给渲染层；
 * 目录标题里的数量由数据长度推导，新增方法时不需要改这里。
 */
export function MethodsBrowser({ onStart }: MethodsBrowserProps) {
  const [selectedSituationId, setSelectedSituationId] = useState('');
  const [selectedMethodId, setSelectedMethodId] = useState('');
  const methodsQuery = useQuery({ queryKey: ['learning-methods'], queryFn: ({ signal }) => request<LearningMethodsResponse>('/learning-methods', { signal }) });
  const situationsQuery = useQuery({ queryKey: ['learning-situations'], queryFn: ({ signal }) => request<LearningSituationsResponse>('/learning-situations', { signal }) });
  const methods = methodsQuery.data?.data.items ?? [];
  const situations = situationsQuery.data?.data.items ?? [];
  const situation = situations.find((item) => item.id === selectedSituationId);
  const method = methods.find((item) => item.id === selectedMethodId);
  const recommended = situation ? methods.filter((item) => situation.method_ids.includes(item.id)) : methods;

  if (methodsQuery.isPending || situationsQuery.isPending) return <section className="methods-page" aria-live="polite"><p role="status">正在载入学习方法…</p></section>;
  if (methodsQuery.isError || situationsQuery.isError) return <section className="methods-page" aria-labelledby="methods-error-title"><h1 id="methods-error-title">学习方法暂时无法载入</h1><p className="muted">目录没有完整载入，请重试后再选择，避免显示不完整的推荐。</p><button onClick={() => { void methodsQuery.refetch(); void situationsQuery.refetch(); }}>重新加载方法</button></section>;

  if (method) return <section className="methods-page" aria-labelledby="methods-title">
    <button className="methods-back" onClick={() => setSelectedMethodId('')}>← 返回学习方法</button>
    <header className="page-hero methods-hero"><span className="eyebrow">LEARNING METHOD</span><h1 id="methods-title">{method.title}</h1><p>{method.summary}</p></header>
    {situation && <aside className="methods-reason"><span>你选择的情况</span><strong>{situation.label}</strong><p>{situation.reason}</p></aside>}
    <div className="method-detail-grid">
      <MethodDetails method={method} onStart={() => onStart({ methodId: method.id, situationId: situation?.id ?? null })} />
    </div>
  </section>;

  return <section className="methods-page" aria-labelledby="methods-title">
    <header className="page-hero methods-hero">
      <span className="eyebrow">A WAY TO BEGIN</span>
      <h1 id="methods-title">学习方法</h1>
      <p>选一个此刻用得上的办法，也可以换成别的方法。</p>
    </header>
    <section className="panel situation-section" aria-labelledby="situation-title">
      <h2 id="situation-title">我现在是什么情况？</h2>
      <div className="situation-list">{situations.map((item) => <SituationChoice key={item.id} situation={item} selected={selectedSituationId === item.id} onSelect={setSelectedSituationId} />)}</div>
      {situation && <div className="methods-recommendation" aria-live="polite"><p>{situation.reason}</p>{recommended.length ? <p>可以尝试：{recommended.map((item) => item.title).join('、')}</p> : <p>你可以直接开始自由学习。</p>}{situation.allow_free_learning && <button className="secondary" onClick={() => onStart({ methodId: null, situationId: situation.id })}>直接自由学习</button>}</div>}
    </section>
    <section className="methods-catalog" aria-labelledby="catalog-title"><div className="methods-section-heading"><h2 id="catalog-title">{situation ? '可尝试的方法' : methodCatalogHeading(recommended.length)}</h2>{situation && <button className="methods-clear" onClick={() => setSelectedSituationId('')}>查看全部</button>}</div>
      {recommended.length ? <div className="method-cards">{recommended.map((item) => <MethodCard
        key={item.id}
        method={item}
        density="full"
        startLabel="开始使用"
        onOpen={setSelectedMethodId}
        onStart={(id) => onStart({ methodId: id, situationId: situation?.id ?? null })}
      />)}</div> : <p className="methods-empty">这个情况不需要额外方法。你可以按自己的计划开始学习，或重新选择情况。</p>}
    </section>
  </section>;
}
