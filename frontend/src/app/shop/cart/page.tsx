'use client';

import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import { api } from '@/services/api';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';

type CartItem = {
  id: number;
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: number;
};

export default function CartPage() {
  return (
    <RoleGuard allowed={['shopper']}>
      <CartContent />
    </RoleGuard>
  );
}

function CartContent() {
  const [items, setItems] = useState<CartItem[]>([]);
  const [error, setError] = useState('');
  const total = useMemo(() => items.reduce((sum, item) => sum + item.quantity * item.unit_price, 0), [items]);

  const loadCart = useCallback(async () => {
    try {
      const response = await api.get('/orders/cart');
      setItems(response.data);
      setError('');
    } catch {
      setError('购物车加载失败，请确认后端服务和登录状态。');
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadCart();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadCart]);

  return (
    <main className="min-h-screen bg-[#f4f7fb] px-5 py-6 text-slate-900 lg:px-8">
      <RoleNav />
      <div className="mx-auto max-w-5xl">
        <Header title="购物车" subtitle="确认商品、数量和金额，然后回到 Chat 完成订单确认。" />
        {error ? <Notice>{error}</Notice> : null}
        <section className="mt-5 rounded-lg border border-slate-200 bg-white p-5">
          {items.length ? (
            <div className="space-y-3">
              {items.map((item) => (
                <article key={item.id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-[#fbfcfe] p-4">
                  <div>
                    <h2 className="font-semibold text-slate-900">{item.product_name || `商品 ${item.product_id}`}</h2>
                    <p className="mt-1 text-sm text-slate-500">商品 {item.product_id} · 数量 {item.quantity}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-[#12445f]">¥{(item.unit_price * item.quantity).toFixed(2)}</p>
                    <p className="mt-1 text-xs text-slate-500">单价 ¥{item.unit_price}</p>
                  </div>
                </article>
              ))}
              <div className="flex items-center justify-between border-t border-slate-200 pt-4">
                <span className="text-sm font-medium text-slate-600">合计</span>
                <span className="text-2xl font-semibold text-slate-900">¥{total.toFixed(2)}</span>
              </div>
              <Link className="inline-flex rounded-lg bg-[#1d6389] px-4 py-2 text-sm font-semibold text-white hover:bg-[#123b5d]" href="/shop/chat">
                回到 Chat 下单
              </Link>
            </div>
          ) : (
            <Empty title="购物车为空" body="试试在 Chat 里说：把最便宜的一款蓝牙耳机加进购物车。" />
          )}
        </section>
      </div>
    </main>
  );
}

function Header({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="rounded-lg border border-slate-200 bg-white p-5">
      <Link className="text-sm font-semibold text-[#12445f]" href="/">ShopMind AI</Link>
      <h1 className="mt-3 text-3xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm leading-6 text-slate-500">{subtitle}</p>
    </header>
  );
}

function Notice({ children }: { children: string }) {
  return <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{children}</div>;
}

function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-[#fbfcfe] p-5">
      <p className="font-medium text-slate-700">{title}</p>
      <p className="mt-1 text-sm text-slate-500">{body}</p>
    </div>
  );
}
