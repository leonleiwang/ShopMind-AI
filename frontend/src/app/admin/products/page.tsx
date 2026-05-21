'use client';

import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import { api } from '@/services/api';
import Link from 'next/link';
import { useEffect, useState } from 'react';

type Product = { id: number; name: string; price: number; category: string; stock: number; pricing_suggestion?: string; marketing_copy?: string };

export default function AdminProductsPage() {
  return (
    <RoleGuard allowed={['merchant', 'admin']}>
      <AdminProductsContent />
    </RoleGuard>
  );
}

function AdminProductsContent() {
  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    void api.get('/products/', { params: { limit: 50 } }).then((response) => setProducts(response.data)).catch(() => setProducts([]));
  }, []);

  return (
    <main className="min-h-screen bg-[#f4f7fb] px-5 py-6 text-slate-900 lg:px-8">
      <RoleNav />
      <div className="mx-auto max-w-7xl">
        <Header title="商品运营" body="商家侧商品列表、库存状态和 AI 运营字段概览。" />
        <section className="mt-5 rounded-lg border border-slate-200 bg-white p-5">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.14em] text-slate-500">
                <tr>
                  <th className="border-b border-slate-200 py-3">商品</th>
                  <th className="border-b border-slate-200 py-3">分类</th>
                  <th className="border-b border-slate-200 py-3">价格</th>
                  <th className="border-b border-slate-200 py-3">库存</th>
                  <th className="border-b border-slate-200 py-3">AI 状态</th>
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id}>
                    <td className="border-b border-slate-100 py-3 font-medium text-slate-900">{product.name}</td>
                    <td className="border-b border-slate-100 py-3 text-slate-600">{product.category || '未分类'}</td>
                    <td className="border-b border-slate-100 py-3 text-slate-600">¥{product.price}</td>
                    <td className="border-b border-slate-100 py-3 text-slate-600">{product.stock}</td>
                    <td className="border-b border-slate-100 py-3 text-slate-600">
                      {product.pricing_suggestion || product.marketing_copy ? '已有 AI 运营内容' : '待生成'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}

function Header({ title, body }: { title: string; body: string }) {
  return (
    <header className="rounded-lg border border-slate-200 bg-white p-5">
      <Link className="text-sm font-semibold text-[#12445f]" href="/admin/dashboard">Admin</Link>
      <h1 className="mt-3 text-3xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm leading-6 text-slate-500">{body}</p>
    </header>
  );
}
