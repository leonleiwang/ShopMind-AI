// src/app/page.tsx # 首页重定向
import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/login');
}