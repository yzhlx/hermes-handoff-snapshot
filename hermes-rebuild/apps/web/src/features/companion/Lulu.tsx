import { useEffect, useState } from 'react';
import './lulu.css';

const PREFERENCE_KEY = 'hermes:lulu:hidden';
const SYNC_EVENT = 'hermes:lulu-display-preference';

export type LuluContext = 'home' | 'empty' | 'complete' | 'summary';

export type LuluProps = {
  context?: LuluContext;
  /** Reserved for callers that already have an account in scope; display preference is global. */
  userId?: string;
};

const contextCopy: Record<LuluContext, string> = {
  home: '噜噜在这里陪你慢慢开始。',
  empty: '暂时没有记录也没关系，想好时再开始。',
  complete: '这一段先告一段落，噜噜陪你歇一会儿。',
  summary: '谢谢你留下今天的学习片段。',
};

function readHiddenPreference() {
  try {
    return window.localStorage.getItem(PREFERENCE_KEY) === 'true';
  } catch {
    return false;
  }
}

function writeHiddenPreference(hidden: boolean) {
  try {
    window.localStorage.setItem(PREFERENCE_KEY, String(hidden));
  } catch {
    // The in-memory state and same-page companions still work when storage is blocked.
  }
  window.dispatchEvent(new CustomEvent(SYNC_EVENT, { detail: hidden }));
}

export function Lulu({ context = 'home' }: LuluProps) {
  const [hidden, setHidden] = useState(readHiddenPreference);

  useEffect(() => {
    const onPreferenceChange = (event: Event) => {
      const preferenceEvent = event as CustomEvent<unknown>;
      setHidden(typeof preferenceEvent.detail === 'boolean' ? preferenceEvent.detail : readHiddenPreference());
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key === PREFERENCE_KEY || event.key === null) setHidden(readHiddenPreference());
    };
    window.addEventListener(SYNC_EVENT, onPreferenceChange);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(SYNC_EVENT, onPreferenceChange);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  if (hidden) {
    return <div className="lulu-restore"><button type="button" onClick={() => writeHiddenPreference(false)}>显示噜噜</button></div>;
  }

  return (
    <aside className={`lulu lulu--${context}`} aria-label="噜噜陪伴">
      <svg className="lulu__art" viewBox="0 0 136 104" aria-hidden="true" focusable="false">
        <ellipse cx="68" cy="88" rx="48" ry="7" fill="#d9d0c3" opacity=".48" />
        <path d="M24 61c0-18 14-31 34-33l4-13c1-4 7-5 9-1l8 14c20 2 34 14 34 32 0 17-16 27-42 27H62C39 87 24 77 24 61Z" fill="#b99d7d" />
        <path d="M35 38 31 23c-1-4 4-7 7-4l13 11M97 35l11-13c3-3 8-1 7 3l-3 17" fill="#b99d7d" />
        <path d="M36 41 34 29l10 8M98 39l9-11-2 15" fill="#d9c6ad" />
        <ellipse cx="48" cy="56" rx="2.1" ry="2.6" fill="#51473b" />
        <ellipse cx="91" cy="56" rx="2.1" ry="2.6" fill="#51473b" />
        <path d="M63 65c2-2 6-2 8 0l-4 4-4-4Z" fill="#51473b" />
        <path d="M67 69c-2 4-6 5-9 3m9-3c2 4 6 5 9 3" fill="none" stroke="#51473b" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M41 68c3 4 8 4 11 1m31 0c3 3 8 3 11-1" fill="none" stroke="#d6baa0" strokeWidth="2" strokeLinecap="round" />
        <path d="M20 71c-5 0-8-4-7-8 1-5 7-6 11-3m94 11c5 0 8-4 7-8-1-5-7-6-11-3" fill="none" stroke="#a98d6f" strokeWidth="7" strokeLinecap="round" />
      </svg>
      <p className="lulu__copy">{contextCopy[context]}</p>
      <button className="lulu__hide" type="button" onClick={() => writeHiddenPreference(true)}>隐藏噜噜</button>
    </aside>
  );
}
