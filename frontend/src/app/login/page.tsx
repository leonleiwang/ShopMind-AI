// src/app/login/page.tsx 登录页面
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/auth';
import { api } from '@/services/api';

export default function LoginPage() {
  const [email, setEmail] = useState('test@shopmind.com');
  const [password, setPassword] = useState('');
  const setToken = useAuthStore((s) => s.setToken);
  const router = useRouter();

  const handleLogin = async () => {
    const res = await api.post('/auth/login', {
      email,
      password,
    });
    setToken(res.data.access_token);
    router.push('/chat');
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen">
      <div className="border p-6 rounded-lg w-80">
        <h1 className="text-xl font-bold mb-4">ShopMind AI 登录</h1>
        <input
          className="border w-full px-3 py-2 mb-2"
          placeholder="邮箱"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="border w-full px-3 py-2 mb-4"
          type="password"
          placeholder="密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button
          className="w-full bg-blue-600 text-white py-2 rounded"
          onClick={handleLogin}
        >
          登录
        </button>
      </div>
    </div>
  );
}
