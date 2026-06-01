'use client';

// 商品浏览页：购物者侧商品列表、关键词搜索、品类筛选和分页展示。
import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import { api } from '@/services/api';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

type Product = {
  id: number;
  name: string;
  description: string;
  price: number;
  category: string;
  brand: string;
  stock: number;
  attributes?: Record<string, unknown>;
  tags?: string[];
};

const PAGE_SIZE = 12;

export default function ProductsPage() {
  // 商品浏览允许 shopper/admin 查看。
  return (
    <RoleGuard allowed={['shopper', 'admin']}>
      <ProductsContent />
    </RoleGuard>
  );
}

function ProductsContent() {
  // 维护商品列表、搜索关键词、品类筛选和分页状态。
  const [products, setProducts] = useState<Product[]>([]);
  const [keyword, setKeyword] = useState('');
  const [category, setCategory] = useState('全部');
  const [page, setPage] = useState(1);

  useEffect(() => {
    void api
      .get('/products/', { params: { limit: 100 } })
      .then((response) => setProducts(response.data))
      .catch(() => setProducts([]));
  }, []);

  const categories = useMemo(
    () => ['全部', ...Array.from(new Set(products.map((product) => product.category).filter(Boolean)))],
    [products],
  );

  const filtered = useMemo(() => {
    const text = keyword.trim().toLowerCase();
    return products.filter((product) => {
      const matchesCategory = category === '全部' || product.category === category;
      const matchesKeyword =
        !text ||
        [product.name, product.description, product.brand, product.category, ...(product.tags ?? [])]
          .join(' ')
          .toLowerCase()
          .includes(text);
      return matchesCategory && matchesKeyword;
    });
  }, [products, keyword, category]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const visibleProducts = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const selectCategory = (nextCategory: string) => {
    // 切换品类时重置分页，避免空页。
    setCategory(nextCategory);
    setPage(1);
  };

  return (
    <main className="min-h-screen bg-[#f4f7fb] px-5 py-6 text-slate-900 lg:px-8">
      <RoleNav />
      <div className="mx-auto max-w-7xl">
        <header className="rounded-lg border border-slate-200 bg-white p-5">
          <Link className="text-sm font-semibold text-[#12445f]" href="/">
            ShopMind AI
          </Link>
          <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl font-semibold">商品浏览</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                用于消费者快速扫一眼当前样例商品库。深度选品仍建议在 Chat 中用自然语言完成。
              </p>
            </div>
            <Link className="rounded-lg bg-[#1d6389] px-4 py-2 text-sm font-semibold text-white" href="/shop/chat">
              去对话选品
            </Link>
          </div>
        </header>

        <section className="mt-5 rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap gap-2">
              {categories.map((item) => (
                <button
                  key={item}
                  className={[
                    'rounded-full border px-3 py-1.5 text-xs font-semibold transition',
                    category === item
                      ? 'border-[#1d6389] bg-[#e8f6fa] text-[#12445f]'
                      : 'border-slate-200 bg-white text-slate-600 hover:border-[#9bd7e7]',
                  ].join(' ')}
                  onClick={() => selectCategory(item)}
                >
                  {item}
                </button>
              ))}
            </div>
            <input
              className="h-10 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-[#1d6389] lg:w-72"
              placeholder="搜索商品、品牌或标签"
              value={keyword}
              onChange={(event) => {
                setKeyword(event.target.value);
                setPage(1);
              }}
            />
          </div>
        </section>

        <section className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {visibleProducts.map((product) => (
            <article key={product.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="rounded-full bg-[#e8f6fa] px-2.5 py-1 text-xs font-semibold text-[#12445f]">
                  {product.category || '未分类'}
                </span>
                <span className="text-xs text-slate-500">库存 {product.stock}</span>
              </div>
              <h2 className="mt-3 min-h-12 font-semibold leading-6 text-slate-900">{product.name}</h2>
              <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-500">{product.description || '暂无描述'}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {(product.tags ?? []).slice(0, 4).map((tag) => (
                  <span key={tag} className="rounded-full bg-slate-100 px-2 py-1 text-[11px] text-slate-600">
                    {tag}
                  </span>
                ))}
              </div>
              <p className="mt-4 text-lg font-semibold text-[#12445f]">¥{Number(product.price).toFixed(2)}</p>
            </article>
          ))}
        </section>

        <footer className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">
          <span>
            共 {filtered.length} 件商品，第 {currentPage} / {totalPages} 页
          </span>
          <div className="flex gap-2">
            <button
              className="rounded-lg border border-slate-200 px-3 py-2 font-semibold disabled:opacity-40"
              disabled={currentPage <= 1}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
            >
              上一页
            </button>
            <button
              className="rounded-lg border border-slate-200 px-3 py-2 font-semibold disabled:opacity-40"
              disabled={currentPage >= totalPages}
              onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
            >
              下一页
            </button>
          </div>
        </footer>
      </div>
    </main>
  );
}
