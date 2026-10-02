import { ApiError } from '../api/client';

export function Feedback({ error }: { error: Error | null }) {
  if (!error) return null;
  return <div className="feedback" role="alert">
    <p>{error.message}</p>
    {error instanceof ApiError && error.requestId && <small>请求编号：{error.requestId}</small>}
  </div>;
}
