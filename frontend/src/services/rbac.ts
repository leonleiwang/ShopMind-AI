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
  if (!role) return false;
  if (role === 'admin') return true;
  return roleRoutes[role].some((route) => path === route || path.startsWith(`${route}/`));
}
