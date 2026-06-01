// 前端 API 客户端：统一配置 REST baseURL、JWT 注入和 WebSocket URL 构造。
import axios from 'axios';

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  // 浏览器端自动从 localStorage 注入 Bearer token。
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export function getWebSocketUrl(path: string, token?: string | null) {
  // 根据 API baseURL 推导 ws/wss 地址，并把 token 放到 query 参数。
  const apiUrl = new URL(API_BASE_URL);
  apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  apiUrl.pathname = `${apiUrl.pathname.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
  if (token) {
    apiUrl.searchParams.set('token', token);
  }
  return apiUrl.toString();
}
