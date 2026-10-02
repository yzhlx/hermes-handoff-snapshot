// Business payload types are generated from the backend OpenAPI document.
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly requestId?: string,
  ) { super(message); this.name = 'ApiError'; }
}

let csrfToken: string | undefined;
let onUnauthorized: (() => void) | undefined;
export function setCsrfToken(token: string | undefined) { csrfToken = token; }
export function setUnauthorizedHandler(handler: (() => void) | undefined) { onUnauthorized = handler; }

function commandHeaders(method: string, initial?: HeadersInit, accept = 'application/json') {
  const headers = new Headers(initial);
  headers.set('Accept', accept);
  if (method !== 'GET' && method !== 'HEAD' && csrfToken) headers.set('X-CSRF-Token', csrfToken);
  return headers;
}

async function responseError(response: Response, path: string): Promise<ApiError> {
  if (response.status === 401 && path !== '/auth/login') {
    csrfToken = undefined;
    onUnauthorized?.();
  }
  const body: unknown = await response.json().catch(() => null);
  const error = body && typeof body === 'object' && 'error' in body ? body.error : null;
  const fields = error && typeof error === 'object' ? error : {};
  const code = 'code' in fields && typeof fields.code === 'string' ? fields.code : 'http_error';
  const message = response.status === 401 ? (path === '/auth/login' ? '用户名或密码不正确，请重新输入。' : '登录已过期，请重新登录。')
    : response.status === 409 ? '这条记录已在另一台设备更新。请重新读取最新内容后再保存；你的输入仍保留。'
    : response.status === 422 ? '内容格式不正确，请检查后再试。'
    : response.status === 413 ? '文件超过允许大小，请选择较小的文件。'
    : response.status === 415 ? '服务端检测到文件类型不受支持或与声明不符，请重新选择文件。'
    : response.status === 429 ? '操作较频繁，请稍后再试。'
    : '操作未完成。输入已保留，请稍后重试。';
  const requestId = 'request_id' in fields && typeof fields.request_id === 'string' ? fields.request_id : response.headers.get('X-Request-ID') ?? undefined;
  return new ApiError(response.status, code, message, requestId);
}

/** Uploads a private file as raw bytes. No JSON content-type is added. */
export function uploadBinary<T>(path: string, file: Blob, contentType: string, idempotencyKey: string, onProgress?: (percent: number) => void, signal?: AbortSignal): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', `/api/v1${path}`);
    xhr.withCredentials = true;
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.setRequestHeader('Content-Type', contentType);
    xhr.setRequestHeader('Idempotency-Key', idempotencyKey);
    if (csrfToken) xhr.setRequestHeader('X-CSRF-Token', csrfToken);
    xhr.upload.onprogress = (event) => { if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100)); };
    xhr.onerror = () => reject(new ApiError(0, 'network_error', '暂时无法连接书房。输入已保留，请检查网络后重试。'));
    const abort = () => xhr.abort();
    if (signal?.aborted) { abort(); reject(new DOMException('aborted', 'AbortError')); return; }
    signal?.addEventListener('abort', abort, { once: true });
    const cleanup = () => signal?.removeEventListener('abort', abort);
    xhr.onabort = () => { cleanup(); reject(new DOMException('aborted', 'AbortError')); };
    xhr.onload = async () => {
      cleanup();
      const response = new Response(xhr.responseText, { status: xhr.status, headers: { 'X-Request-ID': xhr.getResponseHeader('X-Request-ID') ?? '' } });
      if (xhr.status < 200 || xhr.status >= 300) { reject(await responseError(response, path)); return; }
      try { resolve(JSON.parse(xhr.responseText) as T); }
      catch { reject(new ApiError(xhr.status, 'invalid_response', '服务响应无法读取，请稍后重试。', xhr.getResponseHeader('X-Request-ID') ?? undefined)); }
    };
    xhr.onloadend = cleanup;
    xhr.send(file);
  });
}

/** Fetches an authorized attachment or safe page preview as a Blob. */
export async function requestBlob(path: string, init: RequestInit = {}): Promise<Blob> {
  const method = init.method ?? 'GET';
  const headers = commandHeaders(method, init.headers, 'application/octet-stream, image/png');
  try {
    const response = await fetch(`/api/v1${path}`, { ...init, headers, credentials: 'include' });
    if (!response.ok) throw await responseError(response, path);
    return await response.blob();
  } catch (error) {
    if (error instanceof ApiError || (error && typeof error === 'object' && 'name' in error && error.name === 'AbortError')) throw error;
    throw new ApiError(0, 'network_error', '暂时无法连接书房。请检查网络后重试。');
  }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method ?? 'GET';
  const headers = commandHeaders(method, init.headers);
  if (init.body) headers.set('Content-Type', 'application/json');
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { ...init, headers, credentials: 'include' });
  } catch (error) {
    if (error && typeof error === 'object' && 'name' in error && error.name === 'AbortError') throw error;
    throw new ApiError(0, 'network_error', '暂时无法连接书房。输入已保留，请检查网络后重试。');
  }
  if (!response.ok) {
    throw await responseError(response, path);
  }
  if (response.status === 204) return undefined as T;
  try { return await response.json() as T; }
  catch { throw new ApiError(response.status, 'invalid_response', '服务响应无法读取，请稍后重试。', response.headers.get('X-Request-ID') ?? undefined); }
}
