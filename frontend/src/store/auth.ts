// src/store/auth.ts 更新用户认证 Store
import { create } from 'zustand';
import { api } from '@/services/api';

export type UserRole = 'shopper' | 'merchant' | 'support' | 'admin';
type AuthUser = { email: string; full_name: string; role: UserRole; is_superuser?: boolean };

interface AuthState {
  token: string | null;
  hasHydrated: boolean;
  user: AuthUser | null;
  hydrate: () => void;
  loadUser: () => Promise<AuthUser | null>;
  setToken: (token: string) => void;
  setUser: (user: AuthUser | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  hasHydrated: false,
  user: null,
  hydrate: () => {
    if (typeof window === 'undefined') return;
    set({ token: localStorage.getItem('token'), hasHydrated: true });
  },
  loadUser: async () => {
    try {
      const response = await api.get('/auth/me');
      const role = normalizeRole(response.data.role, response.data.is_superuser);
      const user = { ...response.data, role };
      set({ user });
      return user;
    } catch {
      set({ user: null });
      return null;
    }
  },
  setToken: (token) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token);
    }
    set({ token });
  },
  setUser: (user) => set({ user }),
  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
    set({ token: null, user: null });
  },
}));

function normalizeRole(role: string | undefined, isSuperuser?: boolean): UserRole {
  if (isSuperuser) return 'admin';
  if (role === 'merchant' || role === 'support' || role === 'admin') return role;
  return 'shopper';
}
