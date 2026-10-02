import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppShell, type AppShellProps } from './AppShell';
import { NAV_ITEMS } from './navigation';

function renderShell(overrides: Partial<AppShellProps> = {}) {
  const onNavigate = vi.fn();
  const onLogout = vi.fn();
  const props: AppShellProps = {
    page: 'home',
    navItems: NAV_ITEMS,
    username: 'QA_TEST_user',
    serviceStatus: 'online',
    onNavigate,
    onLogout,
    children: <p>页面内容</p>,
    ...overrides,
  };
  render(<AppShell {...props} />);
  return { onNavigate, onLogout };
}

describe('AppShell', () => {
  it('renders every navigation entry from the data with its label as the accessible name', () => {
    renderShell();
    const nav = screen.getByRole('navigation', { name: '书房导航' });
    const buttons = within(nav).getAllByRole('button');
    expect(buttons.map((button) => button.textContent)).toEqual(NAV_ITEMS.map((item) => item.label));
    // 图标只做装饰：aria-hidden，且不贡献可访问名称
    expect(nav.querySelectorAll('svg[aria-hidden="true"]')).toHaveLength(NAV_ITEMS.length);
    for (const item of NAV_ITEMS) expect(within(nav).getByRole('button', { name: item.label })).toBeInTheDocument();
  });

  it('marks only the current page and keeps a detail page on its parent entry', () => {
    renderShell({ page: 'subject-space' });
    const nav = screen.getByRole('navigation', { name: '书房导航' });
    expect(within(nav).getByRole('button', { name: '学科空间' })).toHaveAttribute('aria-current', 'page');
    expect(nav.querySelectorAll('[aria-current="page"]')).toHaveLength(1);
    expect(screen.getByText('学习 / 学科空间')).toBeInTheDocument();
  });

  it('navigates with the page id stored in the navigation data', async () => {
    const { onNavigate } = renderShell();
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: '学习记录' }));
    expect(onNavigate).toHaveBeenCalledWith('history');
    await user.click(screen.getByRole('link', { name: 'Hermes 首页' }));
    expect(onNavigate).toHaveBeenLastCalledWith('home');
    await user.click(screen.getByRole('button', { name: '可考虑复习' }));
    expect(onNavigate).toHaveBeenLastCalledWith('review');
  });

  it('shows a signed-out hint instead of navigation when there are no entries', () => {
    renderShell({ navItems: [], username: null });
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.getByText('我的书房')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '退出' })).not.toBeInTheDocument();
  });

  it('reports the service status and the signed-in account', () => {
    const { rerender } = render(<AppShell page="home" navItems={NAV_ITEMS} username="QA_TEST_user" serviceStatus="connecting" onNavigate={vi.fn()} onLogout={vi.fn()}><p>页面内容</p></AppShell>);
    expect(screen.getByRole('status')).toHaveTextContent('正在连接服务…');
    rerender(<AppShell page="home" navItems={NAV_ITEMS} username="QA_TEST_user" serviceStatus="offline" onNavigate={vi.fn()} onLogout={vi.fn()}><p>页面内容</p></AppShell>);
    expect(screen.getByRole('status')).toHaveTextContent('书房服务暂不可用');
    expect(screen.getByText('QA_TEST_user')).toBeInTheDocument();
  });

  it('logs out once and blocks repeat clicks while the request is pending', async () => {
    const { onLogout } = renderShell({ logoutPending: false });
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: '退出' }));
    expect(onLogout).toHaveBeenCalledTimes(1);
    renderShell({ logoutPending: true });
    const pending = screen.getAllByRole('button', { name: '退出' }).at(-1);
    expect(pending).toBeDisabled();
  });

  it('renders the shell-level banner before the page content', () => {
    renderShell({ banner: <p role="alert">QA_TEST_退出失败</p> });
    expect(screen.getByRole('alert')).toHaveTextContent('QA_TEST_退出失败');
    expect(screen.getByText('页面内容')).toBeInTheDocument();
  });
});
