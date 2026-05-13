// src/store/auth.ts 更新用户认证 Store
import { create } from 'zustand';

type AuthUser = { email: string; full_name: string };

interface AuthState {
  token: string | null;
  hasHydrated: boolean;
  user: AuthUser | null;
  hydrate: () => void;
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
