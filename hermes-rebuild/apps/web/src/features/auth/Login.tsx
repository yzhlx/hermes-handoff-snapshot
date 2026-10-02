import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { request } from '../../shared/api/client';
import type { AuthResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';

export function Login({ onLogin }: { onLogin: (response: AuthResponse) => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const login = useMutation({
    mutationFn: () => request<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
    onSuccess: (response) => { setPassword(''); onLogin(response); },
  });
  return <section className="login panel" aria-labelledby="login-title">
    <span className="eyebrow">YOUR LEARNING SPACE</span>
    <h2 id="login-title">回到你的书房</h2>
    <p className="muted">登录同一个账号，在电脑和平板继续同一段学习。</p>
    <form onSubmit={(event) => { event.preventDefault(); if (!login.isPending) login.mutate(); }}>
      <label>用户名<input required maxLength={64} autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} /></label>
      <label>密码<input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      <Feedback error={login.error} />
      <button disabled={login.isPending}>{login.isPending ? '正在登录…' : '进入书房 →'}</button>
    </form>
  </section>;
}
