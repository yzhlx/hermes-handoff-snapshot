import { afterEach, describe, expect, it, vi } from 'vitest';
import { request, requestBlob, setCsrfToken, setUnauthorizedHandler, uploadBinary } from './client';

afterEach(() => { vi.unstubAllGlobals(); setCsrfToken(undefined); setUnauthorizedHandler(undefined); });
describe('API transport', () => {
  it('uploads a Blob as raw bytes with its declared MIME, auth, CSRF, idempotency and progress', async () => {
    let lastXhr: MockXHR | undefined;
    class MockXHR {
      upload: { onprogress: ((event: ProgressEvent) => void) | null } = { onprogress: null };
      headers = new Map<string, string>(); status = 200; responseText = JSON.stringify({ data: { id: 'QA_TEST_attachment' } });
      method = ''; url = ''; body: BodyInit | null = null; withCredentials = false;
      onload: (() => void) | null = null; onloadend: (() => void) | null = null; onerror: (() => void) | null = null; onabort: (() => void) | null = null;
      constructor() { lastXhr = this; }
      open(method: string, url: string) { this.method = method; this.url = url; }
      setRequestHeader(name: string, value: string) { this.headers.set(name.toLowerCase(), value); }
      getResponseHeader() { return 'qa-request'; }
      send(body: BodyInit | null) { this.body = body; this.upload.onprogress?.({ lengthComputable: true, loaded: 4, total: 4 } as ProgressEvent); this.onload?.(); this.onloadend?.(); }
      abort() { this.onabort?.(); }
    }
    const progress: number[] = [];
    vi.stubGlobal('XMLHttpRequest', MockXHR);
    setCsrfToken('qa-csrf');
    const file = new Blob(['PNG!'], { type: 'image/png' });
    expect(await uploadBinary<{ data: { id: string } }>('/attachments/QA_TEST_attachment/content', file, 'image/png', 'QA_TEST_put', (percent) => progress.push(percent))).toEqual({ data: { id: 'QA_TEST_attachment' } });
    expect(progress).toEqual([100]);
    expect(lastXhr?.method).toBe('PUT');
    expect(lastXhr?.url).toBe('/api/v1/attachments/QA_TEST_attachment/content');
    expect(lastXhr?.withCredentials).toBe(true);
    expect(lastXhr?.body).toBe(file);
    expect(lastXhr?.headers.get('content-type')).toBe('image/png');
    expect(lastXhr?.headers.get('content-type')).not.toBe('application/json');
    expect(lastXhr?.headers.get('idempotency-key')).toBe('QA_TEST_put');
    expect(lastXhr?.headers.get('x-csrf-token')).toBe('qa-csrf');
  });

  it('uses an authorized binary response path without forcing JSON headers', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(new Blob(['safe-png'], { type: 'image/png' }), { headers: { 'Content-Type': 'image/png' } }));
    vi.stubGlobal('fetch', fetcher);
    const blob = await requestBlob('/attachments/QA_TEST_attachment/preview?page=1');
    expect(blob.type).toBe('image/png');
    const [path, init] = fetcher.mock.calls[0];
    expect(path).toBe('/api/v1/attachments/QA_TEST_attachment/preview?page=1');
    expect(init.credentials).toBe('include');
    expect(init.headers.get('Accept')).toContain('image/png');
    expect(init.headers.get('Content-Type')).toBeNull();
  });

  it('includes cookies, CSRF, idempotency and cancellation on commands', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: { id: 'test' } })));
    vi.stubGlobal('fetch', fetcher);
    setCsrfToken('test-csrf');
    const signal = new AbortController().signal;
    expect(await request('/learning-sessions', { method: 'POST', body: '{}', headers: { 'Idempotency-Key': 'op-1' }, signal })).toEqual({ data: { id: 'test' } });
    const [path, init] = fetcher.mock.calls[0];
    expect(path).toBe('/api/v1/learning-sessions');
    expect(init.credentials).toBe('include');
    expect(init.signal).toBe(signal);
    expect(init.headers.get('X-CSRF-Token')).toBe('test-csrf');
    expect(init.headers.get('Idempotency-Key')).toBe('op-1');
  });
  it('clears session state on unauthorized protected requests without exposing server content', async () => {
    const unauthorized = vi.fn();
    setUnauthorizedHandler(unauthorized);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: 'unauthorized', message: 'private backend detail', request_id: 'r-1' } }), { status: 401 })));
    await expect(request('/subjects')).rejects.toMatchObject({ status: 401, code: 'unauthorized', requestId: 'r-1', message: '登录已过期，请重新登录。' });
    expect(unauthorized).toHaveBeenCalledOnce();
  });
  it('returns an actionable conflict and request id', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: 'version_conflict', request_id: 'r-2' } }), { status: 409 })));
    await expect(request('/learning-sessions/1/end')).rejects.toMatchObject({ status: 409, code: 'version_conflict', requestId: 'r-2' });
  });
  it('preserves cancellation and distinguishes unreadable success responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new DOMException('aborted', 'AbortError')));
    await expect(request('/subjects')).rejects.toMatchObject({ name: 'AbortError' });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('bad json')));
    await expect(request('/subjects')).rejects.toMatchObject({ code: 'invalid_response' });
  });
  it('accepts logout with no JSON and does not clear auth on a rejected login', async () => {
    const unauthorized = vi.fn(); setUnauthorizedHandler(unauthorized);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    expect(await request('/auth/logout', { method: 'POST' })).toBeUndefined();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 401 })));
    await expect(request('/auth/login')).rejects.toMatchObject({ status: 401 });
    expect(unauthorized).not.toHaveBeenCalled();
  });
});
