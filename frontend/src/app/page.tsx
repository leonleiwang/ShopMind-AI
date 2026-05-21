'use client';

import { roleHome, roleLabels } from '@/services/rbac';
import { UserRole, useAuthStore } from '@/store/auth';
import Link from 'next/link';
import { useEffect } from 'react';

const demoSurfaces: Array<{
  role: UserRole;
  title: string;
  href: string;
  body: string;
  modules: string[];
}> = [
  {
    role: 'shopper',
    title: '购物者应用',
    href: '/shop/chat',
    body: '对话式购物、自然语言选品、购物车、订单确认和历史订单。',
    modules: ['AI 购物 Chat', '购物车', '历史订单'],
  },
  {
    role: 'merchant',
    title: '商家运营台',
    href: '/admin/dashboard',
    body: '商品运营、订单监控、AI 文案草稿、调价建议和营销任务。',
    modules: ['商品运营', '订单运营', 'AI 草稿'],
  },
  {
    role: 'support',
    title: '客服工作台',
    href: '/support/conversations',
    body: '人工接管会话、异常咨询、售后请求和客服工作流入口。',
    modules: ['客服会话', '异常升级'],
  },
  {
    role: 'admin',
    title: '风控治理台',
    href: '/governance',
    body: '风险分级 HITL、审批队列、审计日志、工具调用轨迹和 Agent 治理。',
    modules: ['审批', '审计日志', '风控规则'],
  },
];

export default function Home() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const hasHydrated = useAuthStore((s) => s.hasHydrated);
  const hydrate = useAuthStore((s) => s.hydrate);
  const loadUser = useAuthStore((s) => s.loadUser);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (hasHydrated && token && !user) {
      void loadUser();
    }
  }, [hasHydrated, loadUser, token, user]);

  return (
    <main className="min-h-screen bg-[#f4f7fb] text-slate-900">
      <header className="bg-[#123b5d] text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-3 lg:px-8">
          <Link className="flex items-center gap-3" href="/">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#ffca45] text-sm font-black text-[#102033]">
              SM
            </span>
            <span>
              <span className="block font-semibold">ShopMind AI</span>
              <span className="block text-xs text-sky-100/75">V1.0 对话式电商 MVP</span>
            </span>
          </Link>
          <nav className="flex items-center gap-2 text-sm">
            {user ? (
              <Link className="rounded-lg bg-[#ffca45] px-4 py-2 font-semibold text-[#102033] hover:bg-[#ffd873]" href={roleHome[user.role]}>
                进入 {roleLabels[user.role]}
              </Link>
            ) : (
              <Link className="rounded-lg bg-[#ffca45] px-4 py-2 font-semibold text-[#102033] hover:bg-[#ffd873]" href="/login">
                登录
              </Link>
            )}
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-5 py-10 lg:px-8">
        <div className="max-w-4xl">
          <p className="text-xs uppercase tracking-[0.28em] text-[#1d6389]">演示入口</p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight text-[#102033] md:text-6xl">
            面向生产化架构的 AI 对话式电商角色入口。
          </h1>
          <p className="mt-5 max-w-3xl text-base leading-8 text-slate-600 md:text-lg">
            ShopMind AI 保留真实 JWT 登录，并将体验拆分为购物者、商家运营、客服和 AgentOps 治理工作台。
            首页用于面试演示快速进入不同角色，具体 URL 也保留给开发调试。
          </p>
        </div>

        {user ? (
          <div className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            当前登录：{user.email}（{roleLabels[user.role]}）。入口卡片和路由守卫都会执行角色访问控制，管理员可访问全部模块。
          </div>
        ) : (
          <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            请先登录。未登录时点击任一入口会先跳转到登录页。
          </div>
        )}

        <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {demoSurfaces.map((surface) => {
            const href = token ? surface.href : `/login?next=${encodeURIComponent(surface.href)}`;
            const isLocked = user && user.role !== 'admin' && user.role !== surface.role;
            return (
              <Link
                key={surface.role}
                className="flex min-h-72 cursor-pointer flex-col justify-between rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-[#9bd7e7] hover:bg-[#fbfcfe]"
                href={href}
              >
                <div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="rounded-full bg-[#e8f6fa] px-2.5 py-1 text-xs font-semibold text-[#12445f]">
                      {roleLabels[surface.role]}
                    </span>
                    {isLocked ? <span className="text-xs font-medium text-amber-700">受限</span> : null}
                  </div>
                  <h2 className="mt-4 text-xl font-semibold text-slate-900">{surface.title}</h2>
                  <p className="mt-3 text-sm leading-6 text-slate-500">{surface.body}</p>
                </div>
                <div className="mt-5 flex flex-wrap gap-2">
                  {surface.modules.map((module) => (
                    <span key={module} className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
                      {module}
                    </span>
                  ))}
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </main>
  );
}
