// 前端 RBAC 配置：定义角色首页、显示名称、可访问路由和路由守卫判断。
import { UserRole } from '@/store/auth';

export const roleHome: Record<UserRole, string> = {
  shopper: '/shop/chat',
  merchant: '/admin/dashboard',
  support: '/support/conversations',
  admin: '/admin/dashboard',
};

export const roleLabels: Record<UserRole, string> = {
  shopper: '购物者',
  merchant: '商家 / 运营',
  support: '客服',
  admin: '管理员 / AgentOps',
};

export const roleRoutes: Record<UserRole, string[]> = {
  shopper: ['/chat', '/shop', '/shop/chat', '/shop/products', '/shop/cart', '/shop/orders'],
  merchant: ['/admin', '/admin/dashboard', '/admin/products', '/admin/orders', '/admin/ai-drafts'],
  support: ['/support', '/support/conversations', '/support/escalations'],
  admin: ['/shop', '/admin', '/support', '/governance', '/dashboard', '/chat'],
};

export function canAccess(role: UserRole | undefined, path: string) {
  // admin 可访问全部；其他角色按路由前缀白名单判断。
  if (!role) return false;
  if (role === 'admin') return true;
  return roleRoutes[role].some((route) => path === route || path.startsWith(`${route}/`));
}
