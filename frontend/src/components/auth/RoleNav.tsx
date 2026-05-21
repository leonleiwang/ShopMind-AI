'use client';

import { canAccess, roleLabels } from '@/services/rbac';
import { useAuthStore } from '@/store/auth';
import Link from 'next/link';

const navGroups = [
  {
    label: '购物者侧',
    links: [
      { href: '/shop/chat', label: 'Chat 主界面' },
      { href: '/shop/products', label: '商品浏览' },
      { href: '/shop/cart', label: '购物车' },
      { href: '/shop/orders', label: '历史订单' },
    ],
  },
  {
    label: '商家运营侧',
    links: [
      { href: '/admin/dashboard', label: '运营仪表盘' },
      { href: '/admin/products', label: '商品运营' },
      { href: '/admin/orders', label: '订单运营' },
      { href: '/admin/ai-drafts', label: 'AI 草稿' },
    ],
  },
  {
    label: '客服侧',
    links: [
      { href: '/support/conversations', label: '客服会话台' },
      { href: '/support/escalations', label: '异常升级队列' },
    ],
  },
  {
    label: '管理员 / AgentOps',
    links: [
      { href: '/governance', label: '风控治理' },
      { href: '/dashboard', label: '工程观测' },
    ],
  },
];

export default function RoleNav() {
  const user = useAuthStore((s) => s.user);
  if (!user) return null;

  return (
    <div className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-3 lg:px-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">当前角色：{roleLabels[user.role]}</p>
          <Link className="text-xs font-semibold text-[#12445f] hover:text-[#1d6389]" href="/">
            返回演示入口
          </Link>
        </div>
        <div className="flex gap-3 overflow-x-auto pb-1">
          {navGroups.map((group) => {
            const links = group.links.filter((link) => canAccess(user.role, link.href));
            if (!links.length) return null;
            return (
              <div key={group.label} className="flex shrink-0 items-center gap-2">
                <span className="text-xs font-medium text-slate-400">{group.label}</span>
                {links.map((link) => (
                  <Link
                    key={link.href}
                    className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-[#9bd7e7] hover:bg-[#f3fbfd]"
                    href={link.href}
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
