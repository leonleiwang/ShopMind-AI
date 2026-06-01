'use client';

// 商家运营仪表盘：聚合商品数量、库存、品类、AI 草稿和运营入口。
import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import { api } from '@/services/api';
import Link from 'next/link';
import { ReactNode, useEffect, useMemo, useState } from 'react';

type Product = {
  id: number;
  name: string;
  description?: string;
  price: number;
  category?: string;
  stock: number;
  pricing_suggestion?: string;
  marketing_copy?: string;
};

const quickLinks = [
  { href: '/admin/products', label: '商品运营', body: '查看商品、库存、AI 描述与价格建议。' },
  { href: '/admin/orders', label: '订单运营', body: '查看订单状态、金额和履约进度。' },
  { href: '/admin/ai-drafts', label: 'AI 草稿', body: '审核 AI 生成的定价、描述和营销文案。' },
];

export default function AdminDashboardPage() {
  // 商家运营页允许 merchant/admin 访问。
  return (
    <RoleGuard allowed={['merchant', 'admin']}>
      <AdminDashboardContent />
    </RoleGuard>
  );
}

function AdminDashboardContent() {
  // 加载商品运营数据并计算库存、品类和 AI 草稿指标。
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    void api
      .get('/products/', { params: { limit: 100 } })
      .then((response) => {
        setProducts(response.data);
        setError('');
      })
      .catch(() => {
        setProducts([]);
        setError('运营数据加载失败，请确认后端服务和登录状态。');
      });
  }, []);

  const totalStock = useMemo(() => products.reduce((sum, product) => sum + Number(product.stock || 0), 0), [products]);
  const lowStock = useMemo(() => products.filter((product) => Number(product.stock || 0) <= 10).length, [products]);
  const categories = useMemo(() => new Set(products.map((product) => product.category || '未分类')).size, [products]);
  const aiDrafts = useMemo(
    () => products.filter((product) => product.pricing_suggestion || product.marketing_copy).length,
    [products],
  );

  return (
    <main className="min-h-screen bg-[#f4f7fb] text-slate-900">
      <RoleNav />
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-6 lg:px-8">
        <header className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Merchant operations</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight">商家运营仪表盘</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
                这里面向商家和运营角色，聚焦商品、库存、订单经营和 AI 运营草稿。买家当前购物车和个人历史订单只在消费者端展示，避免后台越界查看用户私域数据。
              </p>
            </div>
            <Link className="rounded-lg bg-[#1d6389] px-4 py-2 text-sm font-semibold text-white hover:bg-[#123b5d]" href="/admin/products">
              查看商品
            </Link>
          </div>
        </header>

        {error ? <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{error}</div> : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard label="商品数量" value={products.length.toString()} caption="当前演示商品库" />
          <MetricCard label="库存总量" value={totalStock.toString()} caption="所有商品库存合计" />
          <MetricCard label="类目数量" value={categories.toString()} caption="用于自然语言选品" />
          <MetricCard label="低库存" value={lowStock.toString()} caption="库存不高于 10 的商品" />
          <MetricCard label="AI 草稿" value={aiDrafts.toString()} caption="待审核或已生成" />
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {quickLinks.map((item) => (
            <Link key={item.href} className="rounded-lg border border-slate-200 bg-white p-5 transition hover:border-[#9bd7e7] hover:bg-[#fbfcfe]" href={item.href}>
              <p className="text-lg font-semibold text-slate-900">{item.label}</p>
              <p className="mt-2 text-sm leading-6 text-slate-500">{item.body}</p>
            </Link>
          ))}
        </section>

        <section className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
          <Panel title="商品经营概览" eyebrow="catalog health">
            {products.length ? (
              <div className="grid gap-3">
                {products.slice(0, 10).map((product) => (
                  <article key={product.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-[#fbfcfe] p-4">
                    <div>
                      <h2 className="font-semibold text-slate-900">{product.name}</h2>
                      <p className="mt-1 text-sm text-slate-500">
                        {product.category || '未分类'} · 库存 {product.stock}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-[#12445f]">¥{Number(product.price || 0).toFixed(2)}</p>
                      {product.stock <= 10 ? <p className="mt-1 text-xs text-amber-700">低库存</p> : <p className="mt-1 text-xs text-emerald-700">库存正常</p>}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyBox title="暂无商品数据" body="运行 seed 脚本后，这里会显示商品经营样本。" />
            )}
          </Panel>

          <Panel title="运营边界" eyebrow="role boundary">
            <div className="space-y-3 text-sm leading-6 text-slate-600">
              <p>商家后台可以查看商品、库存、订单经营和 AI 草稿。</p>
              <p>消费者的当前购物车、个人历史订单属于用户侧体验，不在商家仪表盘展示。</p>
              <p>客服只处理售后和人工接管；系统级 Agent trace、风控规则和审批日志由管理员在 `/governance` 与 `/dashboard` 查看。</p>
            </div>
          </Panel>
        </section>
      </div>
    </main>
  );
}

function MetricCard({ label, value, caption }: { label: string; value: string; caption: string }) {
  // 商家运营指标卡片。
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">{value}</p>
      <p className="mt-2 text-xs text-slate-500">{caption}</p>
    </article>
  );
}

function Panel({ title, eyebrow, children }: { title: string; eyebrow: string; children: ReactNode }) {
  // 商家运营通用面板。
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{eyebrow}</p>
      <h2 className="mt-1 text-lg font-semibold text-slate-900">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function EmptyBox({ title, body }: { title: string; body: string }) {
  // 空状态提示。
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-[#fbfcfe] p-4">
      <p className="text-sm font-medium text-slate-700">{title}</p>
      <p className="mt-1 text-sm leading-6 text-slate-500">{body}</p>
    </div>
  );
}
