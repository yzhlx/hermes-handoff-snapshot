/*
 * AppShell：只负责外壳（顶栏 / 侧边导航 / 内容列），不持有业务状态。
 * 导航项来自 navigation.ts 的数据，AppShell 本身不写死任何入口。
 *
 * 顶栏搜索框是参考图的视觉占位：后端 52 个路径里没有任何 search 端点，
 * 所以这里只有只读外观 + ⌘K 键位提示 + 一句诚实说明（aria-describedby），
 * 不产生请求、不展示伪造结果。
 */
import type { ReactNode } from 'react';
import { NAV_LABEL, navGroups, navItemFor, pageTitle, type AppPage, type NavItem } from './navigation';
import { SearchIcon } from '../shared/ui/icons';

export type ServiceStatus = 'connecting' | 'online' | 'offline';

const serviceStatusText: Record<ServiceStatus, string> = {
  connecting: '正在连接服务…',
  online: '书房服务已连接',
  offline: '书房服务暂不可用',
};

/** 搜索占位框的标识与说明（说明同时是可访问名称之外的第二重信息）。 */
const SEARCH_PLACEHOLDER = '搜索笔记、题目、知识点…';
const SEARCH_LABEL = '搜索笔记、题目、知识点';
const SEARCH_NOTE_ID = 'topbar-search-note';
const SEARCH_NOTE = '搜索需要后端新增 search 接口，本批未实现。';

/**
 * 顶栏能不能承接折叠后的金句，取决于浏览器是否支持原生 scroll-driven animation。
 * 不支持时 hero 不折叠（金句在原位可见），也就**不该**有第二个同文本元素——
 * 既避免读屏念两遍，也让「同一句话只出现一次」这条不变量在测试里成立。
 *
 * 判定用 `window.ScrollTimeline` 而不是 `CSS.supports('animation-timeline','scroll()')`：
 * 实测 jsdom 对后者返回 true（它对该查询过于宽松），而 ScrollTimeline 接口是真浏览器才有的。
 */
export function supportsScrollTimeline(): boolean {
  return typeof window !== 'undefined' && 'ScrollTimeline' in window;
}

export type AppShellProps = {
  /** 当前页面，用于导航选中态与面包屑 */
  page: AppPage;
  /** 数据驱动导航项；未登录时传空数组，外壳显示未登录提示而不是导航。 */
  navItems: readonly NavItem[];
  username?: string | null;
  serviceStatus: ServiceStatus;
  /** 外壳级提示位（例如退出失败信息），在页面内容之前渲染。 */
  banner?: ReactNode;
  logoutPending?: boolean;
  onNavigate: (page: AppPage) => void;
  onLogout: () => void;
  /**
   * 首页金句。hero 折叠后它是那句金句唯一的去处，所以必须在顶栏承接，
   * 否则用户往下滚就再也找不回今天这句话（见 home.css 的 scroll-driven 段）。
   */
  topbarQuote?: string | null;
  children: ReactNode;
};

export function AppShell({
  page,
  navItems,
  username,
  serviceStatus,
  banner,
  logoutPending = false,
  onNavigate,
  onLogout,
  topbarQuote,
  children,
}: AppShellProps) {
  const activeId = navItemFor(page)?.id;
  const groups = navGroups(navItems);
  return <div className="app-shell">
    <header className="app-topbar">
      <a
        className="brand"
        href="/"
        aria-label="Hermes 首页"
        onClick={(event) => { event.preventDefault(); onNavigate('home'); }}
      >
        <span className="brand-mark" aria-hidden="true">h.</span>
        <span className="brand-name">Hermes<small>LEARNING OS</small></span>
      </a>
      <p className="topbar-context">学习 / {pageTitle(page)}</p>
      {/* hero 折叠时淡入的承接位。只在浏览器支持原生 scroll-driven animation 时渲染：
          否则 hero 不折叠、金句在原位，这里再放一份就会让同一句话出现两次。
          aria-hidden：它和 hero 里的金句是同一句话，不该被读屏念第二遍。 */}
      {topbarQuote && supportsScrollTimeline()
        ? <p className="topbar-quote" aria-hidden="true">“{topbarQuote}”</p>
        : null}
      <div className="topbar-search">
        <SearchIcon className="search-icon" />
        <input
          type="search"
          className="search-input"
          placeholder={SEARCH_PLACEHOLDER}
          aria-label={SEARCH_LABEL}
          aria-describedby={SEARCH_NOTE_ID}
          readOnly
          value=""
        />
        <kbd className="search-key" aria-hidden="true">⌘K</kbd>
        <p className="search-note" id={SEARCH_NOTE_ID} role="note">{SEARCH_NOTE}</p>
      </div>
      <div className="topbar-actions">
        <p className="service-status" role="status">
          <span className={`dot ${serviceStatus}`} aria-hidden="true" />
          {serviceStatusText[serviceStatus]}
        </p>
        {username ? <div className="account">
          <span className="account-avatar" aria-hidden="true">{username.slice(0, 1).toUpperCase()}</span>
          <span className="account-name">{username}</span>
          <button type="button" className="text-button" disabled={logoutPending} onClick={onLogout}>退出</button>
        </div> : null}
      </div>
    </header>
    <aside className="sidebar">
      {groups.length > 0
        ? <nav className="primary-nav" aria-label={NAV_LABEL}>
          {groups.map((group) => <div className="nav-group" key={group.group}>
            <p className="nav-group-title">{group.label}</p>
            {group.items.map((item) => {
              const Icon = item.icon;
              const selected = item.id === activeId;
              return <button
                key={item.id}
                type="button"
                className={selected ? 'nav-item selected' : 'nav-item'}
                aria-current={selected ? 'page' : undefined}
                onClick={() => onNavigate(item.id)}
              >
                <Icon className="nav-icon" />
                {item.label}
              </button>;
            })}
          </div>)}
        </nav>
        : <p className="sidebar-hint">我的书房</p>}
      <p className="sidebar-note">慢慢来。<br />每一段学习都有意义。</p>
    </aside>
    <main className="app-main">
      {banner}
      {children}
    </main>
  </div>;
}
