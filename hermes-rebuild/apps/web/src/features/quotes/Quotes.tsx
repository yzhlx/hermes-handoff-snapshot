import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, request } from '../../shared/api/client';
import type { components, paths } from '../../../../../packages/contracts/src/schema';
import { Feedback } from '../../shared/ui/Feedback';
import './quotes.css';

type TodayResponse = paths['/api/v1/quotes/today']['get']['responses'][200]['content']['application/json'];
type FavoritesResponse = paths['/api/v1/quotes/favorites']['get']['responses'][200]['content']['application/json'];
type PreferenceResponse = paths['/api/v1/quotes/{quote_id}/preference']['put']['responses'][200]['content']['application/json'];
type QuotePreference = components['schemas']['QuotePreferenceData'];
type PreferenceInput = components['schemas']['QuotePreferenceInput'];

type PendingPreference = {
  userId: string;
  quoteId: string;
  text: string;
  key: string;
  body: PreferenceInput;
  ifMatch?: string;
  ifNoneMatch?: string;
};

// Idempotency keys stay in memory across a 401/unmount so the same owner can safely retry.
// Explicit logout clears this volatile state. No quote content or command is stored in browser storage.
const pendingByOwner = new Map<string, Map<string, PendingPreference>>();

export function clearQuotePendingOperations() {
  pendingByOwner.clear();
}

function pendingFor(userId: string, quoteId: string) {
  return pendingByOwner.get(userId)?.get(quoteId);
}

function pendingForOwner(userId: string) {
  return [...(pendingByOwner.get(userId)?.values() ?? [])];
}

function remember(command: PendingPreference) {
  const commands = pendingByOwner.get(command.userId) ?? new Map<string, PendingPreference>();
  commands.set(command.quoteId, command);
  pendingByOwner.set(command.userId, commands);
}

function forget(command: PendingPreference) {
  const commands = pendingByOwner.get(command.userId);
  if (commands?.get(command.quoteId)?.key === command.key) commands.delete(command.quoteId);
  if (commands?.size === 0) pendingByOwner.delete(command.userId);
}

function operationKey() {
  return globalThis.crypto?.randomUUID?.() ?? `quote-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function newPreferenceCommand(
  userId: string,
  preference: QuotePreference | null | undefined,
  quoteId: string,
  text: string,
  body: PreferenceInput,
): PendingPreference {
  return {
    userId,
    quoteId,
    text,
    key: operationKey(),
    body,
    ...(preference ? { ifMatch: `"${preference.version}"` } : { ifNoneMatch: '*' }),
  };
}

function usePreferenceMutation(userId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (command: PendingPreference) => {
      const headers = new Headers({ 'Idempotency-Key': command.key });
      if (command.ifMatch) headers.set('If-Match', command.ifMatch);
      if (command.ifNoneMatch) headers.set('If-None-Match', command.ifNoneMatch);
      return request<PreferenceResponse>(`/quotes/${encodeURIComponent(command.quoteId)}/preference`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(command.body),
      });
    },
    onSuccess: (_response, command) => {
      forget(command);
      void client.invalidateQueries({ queryKey: ['quotes', userId] });
      void client.invalidateQueries({ queryKey: ['home', userId] });
    },
    onError: (error, command) => {
      // Network loss, expired sign-in, and service failures may happen after commit.
      // Retain the original key and body for a safe same-owner retry.
      if (!(error instanceof ApiError) || (error.status !== 401 && error.status !== 0 && error.status < 500)) {
        forget(command);
      }
      if (error instanceof ApiError && (error.status === 404 || error.status === 409)) {
        void client.invalidateQueries({ queryKey: ['quotes', userId] });
      }
    },
  });
}

function executePreference(
  userId: string,
  preference: QuotePreference | null | undefined,
  quoteId: string,
  text: string,
  body: PreferenceInput,
  mutation: ReturnType<typeof usePreferenceMutation>,
) {
  const pending = pendingFor(userId, quoteId);
  const command = pending ?? newPreferenceCommand(userId, preference, quoteId, text, body);
  if (!pending) remember(command);
  mutation.reset();
  mutation.mutate(command);
}

export type DailyQuoteProps = {
  userId: string;
  onOpenMyQuotes: () => void;
  initialData?: TodayResponse;
  /**
   * 首页 hero 用法：参考图的金句区没有可见的「我的金句」入口文字，
   * 且 hero 右侧要让位给母题。入口本身仍然可达（侧栏「我的金句」），
   * 所以这里只把链接文字视觉隐藏，保留给读屏，不改变可访问名称。
   */
  hero?: boolean;
};

export function DailyQuote({ userId, onOpenMyQuotes, initialData, hero }: DailyQuoteProps) {
  const query = useQuery({
    queryKey: ['quotes', userId, 'today'],
    queryFn: ({ signal }) => request<TodayResponse>('/quotes/today', { signal }),
    retry: false,
    initialData,
  });
  const mutation = usePreferenceMutation(userId);
  const daily = query.data?.data.daily_quote;
  const quote = daily?.quote;
  const preference = daily?.preference;
  const pending = quote ? pendingFor(userId, quote.id) : undefined;

  if (query.isPending) return <section className="daily-quote panel" aria-labelledby="daily-quote-title" aria-live="polite"><span className="eyebrow">TODAY</span><p id="daily-quote-title" role="status">正在取出今天的一句话…</p></section>;
  if (query.isError) return <section className="daily-quote panel" aria-labelledby="daily-quote-title"><span className="eyebrow">TODAY</span><h2 id="daily-quote-title">今日金句暂时无法载入</h2><Feedback error={query.error} /><button className="secondary" onClick={() => void query.refetch()}>重试</button></section>;

  return <section className="daily-quote panel" aria-labelledby="daily-quote-title">
    <div className="daily-quote-heading"><span className="eyebrow">TODAY · {daily?.local_date}</span><button className={hero ? 'quote-library-link visually-hidden' : 'quote-library-link'} onClick={onOpenMyQuotes}>我的金句</button></div>
    {quote ? <>
      <h2 id="daily-quote-title" className="daily-quote-text">“{quote.text}”</h2>
      {quote.author && <cite className="daily-quote-author">{quote.author}</cite>}
      <div className="quote-actions" aria-label="金句操作">
        <button
          className={preference?.favorited ? 'secondary quote-action selected' : 'secondary quote-action'}
          aria-pressed={preference?.favorited ?? false}
          disabled={mutation.isPending || Boolean(pending)}
          onClick={() => executePreference(
            userId, preference, quote.id, quote.text,
            { favorited: !preference?.favorited, disliked: preference?.disliked ?? false }, mutation,
          )}
        >{pending ? '等待重试' : preference?.favorited ? '已收藏' : '收藏'}</button>
        {!preference?.disliked && <button
          className="secondary quote-action"
          disabled={mutation.isPending || Boolean(pending)}
          onClick={() => executePreference(
            userId, preference, quote.id, quote.text,
            { favorited: preference?.favorited ?? false, disliked: true }, mutation,
          )}
        >不喜欢</button>}
      </div>
      {pending && <div className="quote-pending" role="status"><p>这次偏好操作尚未确认，重试会使用同一个请求编号。</p><button className="secondary" onClick={() => mutation.mutate(pending)} disabled={mutation.isPending}>重试保存</button></div>}
    </> : <>
      <h2 id="daily-quote-title" className="daily-quote-empty">{daily?.reason === 'disliked_today' ? '今天这句话已收起。' : '暂时没有可展示的金句。'}</h2>
      <p className="muted">{daily?.reason === 'disliked_today' ? '你可以在“我的金句”中撤销不喜欢。' : '所有金句都已暂时屏蔽，可以在“我的金句”中调整。'}</p>
      <button className="secondary quote-library-link-bottom" onClick={onOpenMyQuotes}>打开我的金句</button>
    </>}
    <Feedback error={mutation.error} />
  </section>;
}

export type MyQuotesProps = { userId: string };

function QuotePreferenceCard({
  userId,
  preference,
  action,
  mutation,
}: {
  userId: string;
  preference: QuotePreference;
  action: 'favorite' | 'dislike';
  mutation: ReturnType<typeof usePreferenceMutation>;
}) {
  const pending = pendingFor(userId, preference.quote_id);
  const body: PreferenceInput = action === 'favorite'
    ? { favorited: false, disliked: preference.disliked }
    : { favorited: preference.favorited, disliked: false };
  return <article className="quote-library-item">
    <p>“{preference.text}”</p>
    <div className="quote-library-item-actions">
      <span className="muted">{action === 'favorite' ? '已收藏' : '不再每日展示'}</span>
      <button className="secondary quote-action" disabled={mutation.isPending || Boolean(pending)} onClick={() => executePreference(
        userId, preference, preference.quote_id, preference.text, body, mutation,
      )}>{pending ? '等待重试' : action === 'favorite' ? '取消收藏' : '撤销不喜欢'}</button>
    </div>
  </article>;
}

export function MyQuotes({ userId }: MyQuotesProps) {
  const query = useQuery({
    queryKey: ['quotes', userId, 'favorites'],
    queryFn: ({ signal }) => request<FavoritesResponse>('/quotes/favorites', { signal }),
    retry: false,
  });
  const mutation = usePreferenceMutation(userId);
  const library = query.data?.data;
  const pending = pendingForOwner(userId);

  if (query.isPending) return <section className="my-quotes-page" aria-live="polite"><p role="status">正在载入收藏的金句…</p></section>;
  if (query.isError) return <section className="my-quotes-page" aria-labelledby="my-quotes-title"><h1 id="my-quotes-title">我的金句</h1><p className="muted">暂时无法读取收藏和屏蔽状态。</p><Feedback error={query.error} /><button className="secondary" onClick={() => void query.refetch()}>重试</button></section>;

  return <section className="my-quotes-page" aria-labelledby="my-quotes-title">
    <header className="my-quotes-heading page-head"><span className="eyebrow">YOUR LIBRARY</span><h1 id="my-quotes-title">我的金句</h1><p>收藏与不喜欢分别保存，可以随时调整。</p></header>
    {pending.length > 0 && <section className="quote-library-section" aria-labelledby="quote-pending-title">
      <h2 id="quote-pending-title">待确认的操作</h2>
      <p className="muted">如果刚才遇到断网或登录过期，重试会继续使用原请求编号。</p>
      {pending.map((command) => <article className="quote-library-item" key={command.key}>
        <p>“{command.text}”</p>
        <button className="secondary quote-action" disabled={mutation.isPending} onClick={() => mutation.mutate(command)}>重试保存</button>
      </article>)}
    </section>}
    <Feedback error={mutation.error} />
    <section className="quote-library-section" aria-labelledby="favorites-title">
      <h2 id="favorites-title">收藏</h2>
      {library?.items.length ? <div className="quote-library-list">{library.items.map((item) => <QuotePreferenceCard key={item.quote_id} userId={userId} preference={item} action="favorite" mutation={mutation} />)}</div> : <p className="quote-library-empty">这里还没有收藏的句子。</p>}
    </section>
    <section className="quote-library-section" aria-labelledby="disliked-title">
      <h2 id="disliked-title">不喜欢的句子</h2>
      {library?.disliked.length ? <div className="quote-library-list">{library.disliked.map((item) => <QuotePreferenceCard key={item.quote_id} userId={userId} preference={item} action="dislike" mutation={mutation} />)}</div> : <p className="quote-library-empty">没有屏蔽的句子。</p>}
    </section>
  </section>;
}
