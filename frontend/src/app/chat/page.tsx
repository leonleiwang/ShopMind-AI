// Chat 主页面：电商浅色购物体验 + SSE 过程可视化
'use client';

import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import ChatMessageBubble from '@/components/chat/ChatMessageBubble';
import { useChatStream } from '@/hooks/useChatStream';
import { useAuthStore } from '@/store/auth';
import { useChatStore } from '@/store/chat';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

const quickPrompts = [
  '这个功能不好用，应该怎么操作？',
  '有没有 200 元以内的低延迟耳机？',
  '推荐一款蓝牙耳机，但先别下单',
  '帮我清空购物车，然后重新把商品 1 加进去，再下单',
];

const categories = ['低延迟耳机', '手机数码', '电脑外设', '订单售后', '购物车', 'AI 推荐'];

export default function ChatPage() {
  return (
    <RoleGuard allowed={['shopper']}>
      <ChatContent />
    </RoleGuard>
  );
}

function ChatContent() {
  const [input, setInput] = useState('');
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const error = useChatStore((s) => s.error);
  const clearMessages = useChatStore((s) => s.clearMessages);
  const { sendMessage } = useChatStream();
  const token = useAuthStore((s) => s.token);
  const hasHydrated = useAuthStore((s) => s.hasHydrated);
  const hydrate = useAuthStore((s) => s.hydrate);
  const router = useRouter();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (hasHydrated && !token) {
      router.replace('/login');
    }
  }, [hasHydrated, router, token]);

  const handleSend = (message = input) => {
    if (!message.trim() || !token || isStreaming) return;
    sendMessage(message, token);
    setInput('');
  };

  if (!hasHydrated) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#f4f7fb] text-slate-700">
        <div className="rounded-lg border border-slate-200 bg-white px-5 py-4 text-sm shadow-sm">
          正在恢复会话...
        </div>
      </main>
    );
  }

  if (!token) {
    return null;
  }

  return (
    <main className="flex h-screen flex-col overflow-hidden bg-[#f4f7fb] text-slate-900">
      <header className="shrink-0 bg-[#123b5d] text-white shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 lg:px-6">
          <Link className="flex items-center gap-3" href="/">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#ffca45] text-sm font-black text-[#102033]">
              SM
            </span>
            <span>
              <span className="block font-semibold">ShopMind AI</span>
              <span className="block text-xs text-sky-100/75">AI shopping assistant</span>
            </span>
          </Link>
          <nav className="flex items-center gap-2 text-sm">
            <Link className="hidden rounded-lg px-3 py-2 text-sky-50 hover:bg-white/10 md:inline" href="/shop/products">
              商品
            </Link>
            <Link className="hidden rounded-lg px-3 py-2 text-sky-50 hover:bg-white/10 md:inline" href="/shop/cart">
              购物车
            </Link>
            <Link className="hidden rounded-lg px-3 py-2 text-sky-50 hover:bg-white/10 md:inline" href="/shop/orders">
              我的订单
            </Link>
            <Link className="rounded-lg bg-[#ffca45] px-3 py-2 font-semibold text-[#102033] hover:bg-[#ffd873]" href="/shop/cart">
              购物车 / 订单
            </Link>
          </nav>
        </div>
        <div className="border-t border-white/10 bg-[#1d6389]">
          <div className="mx-auto flex max-w-7xl gap-2 overflow-x-auto px-4 py-2 lg:px-6">
            {categories.map((category) => (
              <button
                key={category}
                className="shrink-0 rounded-full bg-[#dff3f8] px-3 py-1.5 text-xs font-medium text-[#12445f] hover:bg-white"
                onClick={() => handleSend(`帮我看看${category}`)}
                disabled={isStreaming}
              >
                {category}
              </button>
            ))}
          </div>
        </div>
      </header>
      <div className="shrink-0">
        <RoleNav />
      </div>

      <div className="mx-auto grid min-h-0 w-full max-w-7xl flex-1 gap-4 px-4 py-3 lg:grid-cols-[292px_1fr] lg:px-6">
        <aside className="hidden overflow-y-auto rounded-lg border border-slate-200 bg-white p-5 shadow-sm lg:block">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#1d6389]">Demo flow</p>
          <h2 className="mt-2 text-lg font-semibold">购物者视角演示</h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            浅色主界面更接近真实电商场景；顶部保留购物导航，中间分类条用于快速发起任务。
          </p>

          <div className="mt-5 space-y-2">
            {quickPrompts.map((prompt) => (
              <button
                key={prompt}
                className="w-full rounded-lg border border-slate-200 bg-[#f8fafc] px-3 py-3 text-left text-xs leading-5 text-slate-700 transition hover:border-[#9bd7e7] hover:bg-[#eef9fc] disabled:opacity-50"
                disabled={isStreaming}
                onClick={() => handleSend(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        </aside>

        <section className="flex min-h-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <header className="shrink-0 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-5 py-3">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-[#1d6389]">Shop assistant</p>
              <h1 className="mt-1 text-xl font-semibold">对话式购物助手</h1>
            </div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                SSE ready
              </span>
              <button
                className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:border-[#9bd7e7] hover:bg-[#eef9fc]"
                onClick={clearMessages}
              >
                清空
              </button>
            </div>
          </header>

          {error ? (
            <div className="mx-5 mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              {error}
            </div>
          ) : null}

          <div className="min-h-0 flex-1 overflow-y-auto bg-[#fbfcfe] px-5 py-4">
            {messages.length ? (
              <div className="space-y-4">
                {messages.map((msg, i) => (
                  <ChatMessageBubble key={i} message={msg} />
                ))}
              </div>
            ) : (
              <EmptyState onPick={(prompt) => handleSend(prompt)} disabled={isStreaming} />
            )}
          </div>

          <footer className="shrink-0 border-t border-slate-200 bg-white p-3">
            <div className="flex flex-col gap-3 md:flex-row">
              <input
                className="min-h-12 flex-1 rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-[#1d6389] focus:ring-4 focus:ring-[#dff3f8]"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="描述你的购物需求、预算或想办理的业务..."
              />
              <button
                className="rounded-lg bg-[#ffca45] px-6 py-3 text-sm font-semibold text-[#102033] transition hover:bg-[#ffd873] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
                disabled={isStreaming || !input.trim()}
                onClick={() => handleSend()}
              >
                {isStreaming ? '处理中...' : '发送'}
              </button>
            </div>
          </footer>
        </section>
      </div>
    </main>
  );
}

function EmptyState({ onPick, disabled }: { onPick: (prompt: string) => void; disabled: boolean }) {
  return (
    <div className="grid min-h-full place-items-center">
      <div className="max-w-2xl text-center">
        <div className="mx-auto grid h-16 w-16 place-items-center rounded-lg bg-[#dff3f8] text-lg font-black text-[#123b5d]">
          AI
        </div>
        <h2 className="mt-5 text-2xl font-semibold">今天想买点什么？</h2>
        <p className="mt-3 text-sm leading-6 text-slate-500">
          可以像购物网站一样从品类开始，也可以直接说预算、场景和偏好。Agent 会展示路由、工具调用和最终结果。
        </p>
        <div className="mt-6 grid gap-2 sm:grid-cols-2">
          {quickPrompts.map((prompt) => (
            <button
              key={prompt}
              className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-left text-sm text-slate-700 shadow-sm transition hover:border-[#9bd7e7] hover:bg-[#f3fbfd] disabled:opacity-50"
              disabled={disabled}
              onClick={() => onPick(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
