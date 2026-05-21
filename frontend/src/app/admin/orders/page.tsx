'use client';

import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import { api } from '@/services/api';
import Link from 'next/link';
import { useEffect, useState } from 'react';

type Order = { id: number; status: string; total_amount: number; created_at?: string };

export default function AdminOrdersPage() {
  return (
    <RoleGuard allowed={['merchant', 'admin']}>
      <AdminOrdersContent />
    </RoleGuard>
  );
}

function AdminOrdersContent() {
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    void api.get('/orders/').then((response) => setOrders(response.data)).catch(() => setOrders([]));
  }, []);

  return (
    <main className="min-h-screen bg-[#f4f7fb] px-5 py-6 text-slate-900 lg:px-8">
      <RoleNav />
      <div className="mx-auto max-w-6xl">
        <header className="rounded-lg border border-slate-200 bg-white p-5">
          <Link className="text-sm font-semibold text-[#12445f]" href="/admin/dashboard">Admin</Link>
          <h1 className="mt-3 text-3xl font-semibold">订单运营</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">商家视角订单列表，用于监控订单状态和金额。</p>
        </header>
        <section className="mt-5 grid gap-3">
          {orders.map((order) => (
            <article key={order.id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-4">
              <div>
                <h2 className="font-semibold text-slate-900">订单 #{order.id}</h2>
                <p className="mt-1 text-sm text-slate-500">{order.created_at || '暂无时间'}</p>
              </div>
              <div className="text-right">
                <p className="font-semibold text-[#12445f]">¥{order.total_amount}</p>
                <p className="mt-1 text-xs text-slate-500">{order.status}</p>
              </div>
            </article>
          ))}
          {!orders.length ? <div className="rounded-lg border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500">暂无订单。</div> : null}
        </section>
      </div>
    </main>
  );
}
