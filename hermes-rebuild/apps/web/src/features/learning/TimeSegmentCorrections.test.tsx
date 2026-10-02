import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { TimeSegmentCorrections } from './TimeSegmentCorrections';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const envelope = (data: unknown, status = 200) =>
  new Response(JSON.stringify({ data, meta: { request_id: 'qa' } }), { status });
const failure = (status: number, code: string) =>
  new Response(JSON.stringify({ error: { code, message: 'QA test failure' }, meta: { request_id: 'qa' } }), { status });

// 2026-09-30T12:00Z == 20:00 in Shanghai; +9h crosses the local day.
const START = '2026-09-30T12:00:00+00:00';
const OVERNIGHT_END = '2026-09-30T21:00:00+00:00';

const session = (extras: Record<string, unknown> = {}, segment: Record<string, unknown> = {}) => ({
  id: 'QA_TEST_session', goal: 'QA_TEST 隔夜计时', subject_id: null, status: 'ended', version: 4,
  started_at: START, ended_at: OVERNIGHT_END, day_timezone: 'Asia/Shanghai', learning_date: '2026-09-30',
  method_id: null, timing_enabled: true, kind: 'reading', previous_session_id: null, resume_note: null,
  knowledge_point_id: null,
  effective_duration_seconds: 9 * 3600,
  timing_review_required: true,
  time_segments: [{
    id: 'QA_TEST_segment', started_at: START, ended_at: OVERNIGHT_END, duration_seconds: 9 * 3600,
    excluded: false, excluded_at: null, original_ended_at: null, correction_note: null,
    anomalies: ['excessive_span', 'crosses_local_day'], review_required: true,
    ...segment,
  }],
  ...extras,
});

function setup(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal('fetch', fetchMock);
  const onCorrected = vi.fn();
  render(<TimeSegmentCorrections session={session() as never} onCorrected={onCorrected} />);
  return { onCorrected };
}

describe('timer span corrections', () => {
  it('explains an implausible span instead of counting it silently', () => {
    setup(vi.fn());
    expect(screen.getByText(/有 1 段计时看起来不合理/)).toBeInTheDocument();
    expect(screen.getByText('这一段跨度很长，可能是设备休眠或忘记停止计时。')).toBeInTheDocument();
    expect(screen.getByText('这一段跨越了本地学习日，可能把隔夜时间算了进来。')).toBeInTheDocument();
    expect(screen.getByText(/时长不代表学习成果或掌握/)).toBeInTheDocument();
  });

  it('excludes a span with If-Match and a matching idempotency key', async () => {
    const calls: Array<{ url: string; headers: Headers; body: string }> = [];
    const fetchMock = vi.fn(async (url: string, init: RequestInit = {}) => {
      calls.push({ url, headers: new Headers(init.headers), body: String(init.body) });
      return envelope(session({ version: 5 }, { excluded: true, duration_seconds: 0 }));
    });
    const { onCorrected } = setup(fetchMock);
    fireEvent.click(screen.getByRole('button', { name: '不把这段计入' }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].url).toContain('/learning-sessions/QA_TEST_session/time-segments/QA_TEST_segment');
    expect(calls[0].headers.get('If-Match')).toBe('4');
    const body = JSON.parse(calls[0].body);
    expect(body.operation_id).toBe(calls[0].headers.get('Idempotency-Key'));
    expect(body).toMatchObject({ exclude: true });
    await waitFor(() => expect(onCorrected).toHaveBeenCalled());
  });

  it('prefills the real end time in the session timezone and converts it back', async () => {
    const calls: Array<{ headers: Headers; body: string }> = [];
    const fetchMock = vi.fn(async (_url: string, init: RequestInit = {}) => {
      calls.push({ headers: new Headers(init.headers), body: String(init.body) });
      return envelope(session({ version: 5 }));
    });
    setup(fetchMock);
    fireEvent.click(screen.getByRole('button', { name: '修正结束时间' }));
    const input = screen.getByLabelText(/实际结束时间/) as HTMLInputElement;
    // 21:00 UTC is 05:00 the next day in Shanghai.
    expect(input.value).toBe('2026-10-01T05:00');
    fireEvent.change(input, { target: { value: '2026-09-30T20:30' } });
    fireEvent.change(screen.getByLabelText(/一句话说明/), { target: { value: 'QA_TEST 中途睡着了' } });
    fireEvent.click(screen.getByRole('button', { name: '保存校正' }));
    await waitFor(() => expect(calls).toHaveLength(1));
    const body = JSON.parse(calls[0].body);
    // 20:30 in Shanghai is 12:30 UTC.
    expect(body.ended_at).toBe('2026-09-30T12:30:00.000Z');
    expect(body.correction_note).toBe('QA_TEST 中途睡着了');
    expect(body.operation_id).toBe(calls[0].headers.get('Idempotency-Key'));
  });

  it('keeps the typed correction when the server refuses to extend a span', async () => {
    const fetchMock = vi.fn(async () => failure(422, 'VALIDATION_ERROR'));
    setup(fetchMock);
    fireEvent.click(screen.getByRole('button', { name: '修正结束时间' }));
    const input = screen.getByLabelText(/实际结束时间/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: '2026-09-30T21:30' } });
    fireEvent.click(screen.getByRole('button', { name: '保存校正' }));
    expect(await screen.findByText(/校正只能把这段改短/)).toBeInTheDocument();
    expect(input.value).toBe('2026-09-30T21:30');
  });

  it('re-reads on a version conflict and says so', async () => {
    const fetchMock = vi.fn(async () => failure(409, 'VERSION_CONFLICT'));
    const { onCorrected } = setup(fetchMock);
    fireEvent.click(screen.getByRole('button', { name: '不把这段计入' }));
    expect(await screen.findByText(/已重新读取；你的输入仍保留/)).toBeInTheDocument();
    await waitFor(() => expect(onCorrected).toHaveBeenCalled());
  });

  it('does not warn about a plausible span and offers to exclude it', () => {
    const plausible = session(
      { timing_review_required: false, effective_duration_seconds: 1800 },
      { ended_at: '2026-09-30T12:30:00+00:00', duration_seconds: 1800, anomalies: [], review_required: false },
    );
    vi.stubGlobal('fetch', vi.fn());
    render(<TimeSegmentCorrections session={plausible as never} onCorrected={vi.fn()} />);
    expect(screen.queryByText(/看起来不合理/)).toBeNull();
    expect(screen.getByRole('button', { name: '不把这段计入' })).toBeEnabled();
  });
});
