'use client';

// 角色路由守卫：校验登录态、加载当前用户，并阻止无权限访问页面。
import { canAccess, roleHome, roleLabels } from '@/services/rbac';
import { UserRole, useAuthStore } from '@/store/auth';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { ReactNode, useEffect } from 'react';

export default function RoleGuard({
  allowed,
  children,
}: {
  allowed?: UserRole[];
  children: ReactNode;
}) {
  // 先恢复 token，再拉取用户信息，最后按 allowed 和路由白名单双重校验。
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const hasHydrated = useAuthStore((s) => s.hasHydrated);
  const hydrate = useAuthStore((s) => s.hydrate);
  const loadUser = useAuthStore((s) => s.loadUser);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!hasHydrated) return;
    if (!token) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    if (!user) {
      void loadUser();
    }
  }, [hasHydrated, loadUser, pathname, router, token, user]);

  if (!hasHydrated || !token || !user) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#f4f7fb] text-slate-700">
        <div className="rounded-lg border border-slate-200 bg-white px-5 py-4 text-sm shadow-sm">正在校验访问权限...</div>
      </main>
    );
  }

  const allowedByProp = allowed ? allowed.includes(user.role) || user.role === 'admin' : true;
  const allowedByRoute = canAccess(user.role, pathname);
  if (!allowedByProp || !allowedByRoute) {
    return <AccessDenied role={user.role} />;
  }

  return <>{children}</>;
}

function AccessDenied({ role }: { role: UserRole }) {
  // 无权限时展示角色友好的返回入口。
  return (
    <main className="grid min-h-screen place-items-center bg-[#f4f7fb] px-5 text-slate-900">
      <section className="max-w-lg rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs uppercase tracking-[0.22em] text-[#1d6389]">访问受限</p>
        <h1 className="mt-2 text-2xl font-semibold">当前页面不对 {roleLabels[role]} 开放。</h1>
        <p className="mt-3 text-sm leading-6 text-slate-500">
          菜单会隐藏无权限模块，同时直接输入 URL 也会被路由守卫拦截。
        </p>
        <Link
          className="mt-5 inline-flex rounded-lg bg-[#1d6389] px-4 py-2 text-sm font-semibold text-white hover:bg-[#123b5d]"
          href={roleHome[role]}
        >
          返回我的工作台
        </Link>
      </section>
    </main>
  );
}
