import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, request } from '../../shared/api/client';
import type {
  AccountExportDownloadResponse,
  AccountExportPageResponse,
  AccountExportResponse,
  AccountStatusResponse,
} from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import './account.css';

const CONFIRMATION = 'DELETE MY ACCOUNT';

/**
 * Data sovereignty (03 §9): take your records out, or ask for them to be
 * erased. Deletion is deliberately two-step and revocable until it is not.
 */
export function AccountDataPage({ onDataRemoved }: { onDataRemoved: () => void }) {
  const client = useQueryClient();
  const [confirmation, setConfirmation] = useState('');
  const [purgeConfirmation, setPurgeConfirmation] = useState('');
  const [message, setMessage] = useState('');
  const status = useQuery({
    queryKey: ['account'],
    queryFn: ({ signal }) => request<AccountStatusResponse>('/account', { signal }),
  });
  const exports = useQuery({
    queryKey: ['account-exports'],
    queryFn: ({ signal }) => request<AccountExportPageResponse>('/account/exports?limit=20', { signal }),
  });
  useEffect(() => setMessage(''), [status.data?.data.status]);
  const createExport = useMutation({
    mutationFn: () => {
      const operationId = crypto.randomUUID();
      return request<AccountExportResponse>('/account/exports', {
        method: 'POST',
        headers: { 'Idempotency-Key': operationId },
        body: JSON.stringify({ operation_id: operationId }),
      });
    },
    onSuccess: () => void client.invalidateQueries({ queryKey: ['account-exports'] }),
    onError: () => setMessage('导出未完成，可以重试。'),
  });
  const download = async (id: string) => {
    try {
      const response = await request<AccountExportDownloadResponse>(`/account/exports/${encodeURIComponent(id)}/download`);
      const blob = new Blob([JSON.stringify(response.data.document, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `hermes-export-${id}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage('导出已下载。这个包包含你本人的记录、附件清单与数据字典。');
    } catch (error) {
      setMessage(error instanceof ApiError && error.status === 410
        ? '这个导出包已过期，请重新生成一份。'
        : '暂时无法下载导出包，请稍后重试。');
    }
  };
  const deletion = status.data?.data.deletion ?? null;
  const pending = deletion?.status === 'pending';
  const requestDeletion = useMutation({
    mutationFn: () => {
      const operationId = crypto.randomUUID();
      return request('/account/deletion', {
        method: 'POST',
        headers: { 'Idempotency-Key': operationId },
        body: JSON.stringify({ operation_id: operationId, confirmation }),
      });
    },
    onSuccess: () => { setConfirmation(''); setMessage('删除请求已登记。在此之前你仍然可以选择取消。'); void client.invalidateQueries({ queryKey: ['account'] }); },
    onError: (error) => setMessage(error instanceof ApiError && error.status === 422
      ? `请逐字输入 ${CONFIRMATION} 以确认。`
      : error instanceof ApiError && error.status === 409 ? '已经有一个待处理的删除请求。' : '请求未提交，可以稍后重试。'),
  });
  const cancelDeletion = useMutation({
    mutationFn: () => {
      const operationId = crypto.randomUUID();
      return request('/account/deletion/cancel', {
        method: 'POST',
        headers: { 'Idempotency-Key': operationId, 'If-Match': String(deletion?.version ?? 1) },
        body: JSON.stringify({ operation_id: operationId }),
      });
    },
    onSuccess: () => { setMessage('删除请求已撤销，账号恢复可用。'); void client.invalidateQueries({ queryKey: ['account'] }); },
    onError: () => setMessage('撤销未完成，请重新读取后重试。'),
  });
  const purge = useMutation({
    mutationFn: () => {
      const operationId = crypto.randomUUID();
      return request('/account/deletion/purge', {
        method: 'POST',
        headers: { 'Idempotency-Key': operationId, 'If-Match': String(deletion?.version ?? 1) },
        body: JSON.stringify({ operation_id: operationId, confirmation: purgeConfirmation }),
      });
    },
    onSuccess: () => { setPurgeConfirmation(''); onDataRemoved(); },
    onError: (error) => setMessage(error instanceof ApiError && error.status === 422
      ? `请逐字输入 ${CONFIRMATION} 以最终确认。`
      : '最终删除未执行，请重新读取后重试。'),
  });

  if (status.isPending) return <section className="workspace"><p role="status" className="muted">正在读取账号状态…</p></section>;
  if (status.isError) return <section className="workspace"><Feedback error={status.error} /><button className="secondary" onClick={() => void status.refetch()}>重试</button></section>;
  const data = status.data.data;
  return <section className="workspace account-page" aria-labelledby="account-title">
    <header className="history-heading page-head"><div><span className="eyebrow">YOUR DATA, YOUR CALL</span><h1 id="account-title">账号与数据</h1><p className="muted">你可以随时导出自己的记录，也可以要求删除。删除是两段式：先登记，再确认执行，中间可以撤销。</p></div></header>
    <dl className="history-detail-list">
      <div><dt>账号</dt><dd>{data.username}（{data.timezone}）</dd></div>
      <div><dt>状态</dt><dd>{data.status === 'active' ? '正常使用' : data.status === 'deletion_pending' ? '待删除（写入已暂停）' : '已删除'}</dd></div>
      <div><dt>记录数</dt><dd>{data.record_count}</dd></div>
    </dl>

    <section className="panel account-block" aria-labelledby="export-title">
      <h2 id="export-title">导出我的数据</h2>
      <p className="muted">导出包包含你本人各表的记录、附件清单（含校验值）与数据字典；不包含密码、登录凭据或存储内部标识，也不会包含别人的记录。导出包有有效期。</p>
      <div className="account-actions"><button disabled={createExport.isPending} onClick={() => createExport.mutate()}>{createExport.isPending ? '正在生成…' : '生成导出包'}</button><button className="secondary" onClick={() => void exports.refetch()}>刷新列表</button></div>
      {exports.isError && <Feedback error={exports.error} />}
      {exports.data?.data.items.length ? <ul className="account-export-list">{exports.data.data.items.map((item) => <li key={item.id}><span>{(item.created_at ?? '').slice(0, 16).replace('T', ' ')} · {item.status === 'ready' ? `${Math.ceil((item.byte_size ?? 0) / 1024)} KB` : item.status === 'expired' ? '已过期' : '生成失败'}</span>{item.status === 'ready' && <button className="text-button" onClick={() => void download(item.id)}>下载</button>}</li>)}</ul> : <p className="muted">还没有导出包。</p>}
    </section>

    <section className="panel account-block" aria-labelledby="delete-title">
      <h2 id="delete-title">删除账号与学习内容</h2>
      {!pending ? <><p className="muted">登记后写入会暂停，你仍可以导出与撤销。请逐字输入 <code>{CONFIRMATION}</code> 后提交。</p>
        <label>确认文字<input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} placeholder={CONFIRMATION} /></label>
        <div className="account-actions"><button disabled={requestDeletion.isPending} onClick={() => requestDeletion.mutate()}>登记删除请求</button></div></> : <>
        <p className="account-warning" role="status">删除请求已登记。在最终确认之前，学习写入已暂停，你可以随时撤销。</p>
        <dl className="history-detail-list"><div><dt>影响范围</dt><dd>{String((deletion?.impact as Record<string, unknown> | undefined)?.total_records ?? 0)} 条记录、私有附件与导出包</dd></div><div><dt>登记时间</dt><dd>{(deletion?.created_at ?? '').slice(0, 16).replace('T', ' ')}</dd></div></dl>
        <div className="account-actions"><button className="secondary" disabled={cancelDeletion.isPending} onClick={() => cancelDeletion.mutate()}>撤销删除请求</button></div>
        <details className="account-final"><summary>我确认要永久删除</summary><p className="muted">这一步会清除你的学习内容、私有附件与导出包，服务端不再保留。删除后无法从这里恢复。请再次逐字输入 <code>{CONFIRMATION}</code>。</p>
          <label>最终确认<input value={purgeConfirmation} onChange={(event) => setPurgeConfirmation(event.target.value)} placeholder={CONFIRMATION} /></label>
          <div className="account-actions"><button className="danger-button" disabled={purge.isPending} onClick={() => purge.mutate()}>永久删除我的内容</button></div>
        </details></>}
    </section>
    {message && <p role="status" className="muted">{message}</p>}
  </section>;
}
