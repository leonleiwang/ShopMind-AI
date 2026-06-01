'use client';

// 历史订单页：展示购物者已确认订单和订单项明细。
import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import { api } from '@/services/api';
import Link from 'next/link';
import { useEffect, useState } from 'react';

type Order = {
  id: number;
  status: string;
  total_amount: number;
  created_at?: string;
  items: Array<{ product_id: number; product_name?: string; quantity: number; unit_price: number }>;
};

export default function OrdersPage() {
  // 历史订单页仅允许 shopper 访问。
  return (
    <RoleGuard allowed={['shopper']}>
      <OrdersContent />
    </RoleGuard>
  );
}

function OrdersContent() {
  // 加载当前用户订单列表。
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    void api.get('/orders/').then((response) => setOrders(response.data)).catch(() => setOrders([]));
  }, []);

  return (
    <main className="min-h-screen bg-[#f4f7fb] px-5 py-6 text-slate-900 lg:px-8">
      <RoleNav />
      <div className="mx-auto max-w-5xl">
        <header className="rounded-lg border border-slate-200 bg-white p-5">
          <Link className="text-sm font-semibold text-[#12445f]" href="/">ShopMind AI</Link>
          <h1 className="mt-3 text-3xl font-semibold">历史订单</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">查看已确认下单的订单和商品明细。</p>
        </header>
        <section className="mt-5 space-y-3">
          {orders.length ? (
            orders.map((order) => (
              <article key={order.id} className="rounded-lg border border-slate-200 bg-white p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="font-semibold text-slate-900">订单 #{order.id}</h2>
                    <p className="mt-1 text-sm text-slate-500">{formatDate(order.created_at)}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-[#12445f]">¥{order.total_amount}</p>
                    <p className="mt-1 text-xs text-slate-500">{order.status}</p>
                  </div>
                </div>
                <div className="mt-4 space-y-2 border-t border-slate-200 pt-3">
                  {order.items.map((item, index) => (
                    <p key={`${order.id}-${item.product_id}-${index}`} className="text-sm text-slate-600">
                      {item.product_name || `商品 ${item.product_id}`} x {item.quantity} · ¥{item.unit_price}
                    </p>
                  ))}
                </div>
              </article>
            ))
          ) : (
            <div className="rounded-lg border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500">
              暂无历史订单。完成一次 Chat 订单确认后会显示在这里。
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function formatDate(value?: string) {
  // 订单时间格式化。
  if (!value) return '暂无时间';
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}
