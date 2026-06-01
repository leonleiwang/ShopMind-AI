'use client';

// AI 草稿页：展示商品描述、定价建议、营销文案等 AI 运营草稿审批记录。
import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import { api } from '@/services/api';
import Link from 'next/link';
import { useEffect, useState } from 'react';

type Approval = { id: number; action_type: string; status: string; summary: string; created_at?: string };

export default function AiDraftsPage() {
  // AI 草稿页允许 merchant/admin 访问。
  return (
    <RoleGuard allowed={['merchant', 'admin']}>
      <AiDraftsContent />
    </RoleGuard>
  );
}

function AiDraftsContent() {
  // 加载 governance 队列中的非下单类审批，作为 AI 运营草稿列表。
  const [drafts, setDrafts] = useState<Approval[]>([]);

  useEffect(() => {
    void api.get('/approvals/', { params: { scope: 'governance', limit: 50 } }).then((response) => {
      setDrafts(response.data.filter((item: Approval) => item.action_type !== 'place_order'));
    }).catch(() => setDrafts([]));
  }, []);

  return (
    <main className="min-h-screen bg-[#f4f7fb] px-5 py-6 text-slate-900 lg:px-8">
      <RoleNav />
      <div className="mx-auto max-w-5xl">
        <header className="rounded-lg border border-slate-200 bg-white p-5">
          <Link className="text-sm font-semibold text-[#12445f]" href="/admin/dashboard">Admin</Link>
          <h1 className="mt-3 text-3xl font-semibold">AI 运营草稿</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">商品描述、调价建议和营销文案进入风控治理审核前后的草稿视图。</p>
        </header>
        <section className="mt-5 space-y-3">
          {drafts.map((draft) => (
            <article key={draft.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="rounded-full bg-[#e8f6fa] px-2.5 py-1 text-xs font-semibold text-[#12445f]">{draft.action_type}</span>
                <span className="text-xs text-slate-500">{draft.status}</span>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-600">{draft.summary}</p>
            </article>
          ))}
          {!drafts.length ? <div className="rounded-lg border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500">暂无 AI 草稿。</div> : null}
        </section>
      </div>
    </main>
  );
}
