// 登录页面
'use client';

import { api } from '@/services/api';
import { useAuthStore } from '@/store/auth';
import { roleHome } from '@/services/rbac';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function LoginPage() {
  const [email, setEmail] = useState('test@shopmind.com');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const setToken = useAuthStore((s) => s.setToken);
  const loadUser = useAuthStore((s) => s.loadUser);
  const router = useRouter();

  const handleLogin = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/auth/login', {
        email,
        password,
      });
      setToken(res.data.access_token);
      const user = await loadUser();
      const next = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('next') : null;
      router.push(next || roleHome[user?.role ?? 'shopper']);
    } catch {
      setError('登录失败，请确认账号、密码和后端服务状态。');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="grid min-h-screen bg-[#f4f7fb] px-5 py-8 text-slate-900 lg:grid-cols-[1fr_440px]">
      <section className="hidden items-center px-8 lg:flex">
        <div className="max-w-2xl">
          <Link className="mb-10 inline-flex items-center gap-3" href="/">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#ffca45] text-sm font-black text-[#102033]">
              SM
            </span>
            <span className="font-semibold">ShopMind AI</span>
          </Link>
          <p className="text-xs uppercase tracking-[0.3em] text-[#1d6389]">Commerce Agent Platform</p>
          <h1 className="mt-4 text-5xl font-semibold leading-tight tracking-tight">
            演示一个可运营、可观测、可降级的 AI 购物助手。
          </h1>
          <p className="mt-5 text-lg leading-8 text-slate-600">
            登录后可以展示多轮澄清、商品推荐、购物车下单、Agent trace 和运营仪表盘。
          </p>
        </div>
      </section>

      <section className="flex items-center justify-center">
        <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/80">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-[#1d6389]">Demo access</p>
            <h1 className="mt-2 text-2xl font-semibold">登录 ShopMind AI</h1>
            <p className="mt-2 text-sm text-slate-500">使用测试账号进入聊天和仪表盘演示。</p>
          </div>

          {error ? (
            <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              {error}
            </div>
          ) : null}

          <div className="mt-6 space-y-3">
            <label className="block">
              <span className="text-xs font-medium text-slate-500">邮箱</span>
              <input
                className="mt-2 h-12 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-[#1d6389] focus:ring-4 focus:ring-[#dff3f8]"
                placeholder="邮箱"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-500">密码</span>
              <input
                className="mt-2 h-12 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-[#1d6389] focus:ring-4 focus:ring-[#dff3f8]"
                type="password"
                placeholder="密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
              />
            </label>
          </div>

          <button
            className="mt-6 h-12 w-full rounded-lg bg-[#ffca45] text-sm font-semibold text-[#102033] transition hover:bg-[#ffd873] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
            disabled={loading || !email || !password}
            onClick={handleLogin}
          >
            {loading ? '登录中...' : '进入演示'}
          </button>
        </div>
      </section>
    </main>
  );
}
