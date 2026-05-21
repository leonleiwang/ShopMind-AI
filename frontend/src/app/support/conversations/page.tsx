'use client';

import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import Link from 'next/link';

const conversations = [
  { id: 'handoff-001', title: '低置信度购物意图澄清', status: 'triage', detail: '用户需求含糊且涉及下单，建议客服确认预算和品类。' },
  { id: 'handoff-002', title: '订单确认失败后人工接管', status: 'open', detail: '购物车在确认后发生变化，需要引导用户重新生成订单草稿。' },
];

export default function SupportConversationsPage() {
  return (
    <RoleGuard allowed={['support', 'admin']}>
      <main className="min-h-screen bg-[#f4f7fb] px-5 py-6 text-slate-900 lg:px-8">
        <RoleNav />
        <div className="mx-auto max-w-5xl">
          <header className="rounded-lg border border-slate-200 bg-white p-5">
            <Link className="text-sm font-semibold text-[#12445f]" href="/">ShopMind AI</Link>
            <h1 className="mt-3 text-3xl font-semibold">客服会话台</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500">轻量展示人工接管、异常会话和售后入口，后续可接入真实工单系统。</p>
          </header>
          <section className="mt-5 grid gap-3">
            {conversations.map((item) => (
              <article key={item.id} className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="font-semibold text-slate-900">{item.title}</h2>
                  <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800">{item.status}</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-500">{item.detail}</p>
              </article>
            ))}
          </section>
        </div>
      </main>
    </RoleGuard>
  );
}
