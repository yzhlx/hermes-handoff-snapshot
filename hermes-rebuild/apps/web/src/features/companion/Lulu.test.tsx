import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Lulu } from './Lulu';

const PREFERENCE_KEY = 'hermes:lulu:hidden';

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe('Lulu companion', () => {
  it('hides explicitly, restores from the compact control, and remembers the preference after remount', async () => {
    const user = userEvent.setup();
    const first = render(<Lulu />);
    expect(screen.getByText('噜噜在这里陪你慢慢开始。')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '隐藏噜噜' }));
    expect(screen.queryByLabelText('噜噜陪伴')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '显示噜噜' })).toBeInTheDocument();
    expect(window.localStorage.getItem(PREFERENCE_KEY)).toBe('true');

    first.unmount();
    render(<Lulu context="summary" />);
    expect(screen.getByRole('button', { name: '显示噜噜' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '显示噜噜' }));
    expect(screen.getByText('谢谢你留下今天的学习片段。')).toBeInTheDocument();
    expect(window.localStorage.getItem(PREFERENCE_KEY)).toBe('false');
  });

  it('keeps multiple mounted companions synchronized', async () => {
    const user = userEvent.setup();
    render(<><Lulu /><Lulu context="empty" /></>);
    await user.click(screen.getAllByRole('button', { name: '隐藏噜噜' })[0]);
    expect(screen.getAllByRole('button', { name: '显示噜噜' })).toHaveLength(2);
    await user.click(screen.getAllByRole('button', { name: '显示噜噜' })[1]);
    expect(screen.getAllByLabelText('噜噜陪伴')).toHaveLength(2);
  });

  it('continues working when local storage access fails', async () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new DOMException('blocked', 'SecurityError'); });
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new DOMException('blocked', 'SecurityError'); });
    const user = userEvent.setup();
    render(<><Lulu /><Lulu context="complete" /></>);
    await user.click(screen.getAllByRole('button', { name: '隐藏噜噜' })[0]);
    expect(screen.getAllByRole('button', { name: '显示噜噜' })).toHaveLength(2);
    await user.click(screen.getAllByRole('button', { name: '显示噜噜' })[0]);
    expect(screen.getAllByLabelText('噜噜陪伴')).toHaveLength(2);
  });

  it('keeps the static illustration motion-free and decorative under reduced motion', () => {
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true, media: '(prefers-reduced-motion: reduce)' }));
    const { container } = render(<Lulu />);
    const illustration = container.querySelector('svg');
    expect(illustration).toHaveAttribute('aria-hidden', 'true');
    expect(illustration?.querySelector('animate, animateMotion, animateTransform')).toBeNull();
    expect(container.querySelector('.lulu')).toBeInTheDocument();
  });

  it.each([
    ['home', '噜噜在这里陪你慢慢开始。'],
    ['empty', '暂时没有记录也没关系，想好时再开始。'],
    ['complete', '这一段先告一段落，噜噜陪你歇一会儿。'],
    ['summary', '谢谢你留下今天的学习片段。'],
  ] as const)('shows friendly %s copy without an alert or overlay', (context, copy) => {
    const { container } = render(<Lulu context={context} />);
    expect(screen.getByText(copy)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(container.querySelector('[role="dialog"], [aria-modal="true"]')).toBeNull();
  });
});
