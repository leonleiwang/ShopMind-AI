'use client';

import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import Link from 'next/link';

export default function SupportEscalationsPage() {
  return (
    <RoleGuard allowed={['support', 'admin']}>
      <main className="min-h-screen bg-[#f4f7fb] px-5 py-6 text-slate-900">
        <RoleNav />
        <section className="max-w-2xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <Link className="text-sm font-semibold text-[#12445f]" href="/support/conversations">Support</Link>
          <h1 className="mt-3 text-3xl font-semibold">异常升级队列</h1>
          <p className="mt-3 text-sm leading-7 text-slate-500">
            这里预留给退款、售后、异常订单和人工接管工作流。V1.0 保留轻量入口，避免为了演示引入过重客服坐席系统。
          </p>
        </section>
      </main>
    </RoleGuard>
  );
}
