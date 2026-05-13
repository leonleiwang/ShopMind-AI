// 聊天主页面
'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/auth';
import { useChatStore } from '@/store/chat';
import { useChatStream } from '@/hooks/useChatStream';
import ChatMessageBubble from '@/components/chat/ChatMessageBubble';

export default function ChatPage() {
  const [input, setInput] = useState('');
  const messages = useChatStore((s) => s.messages);
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

  const handleSend = () => {
    if (!input.trim()) return;
    if (!token) return;
    sendMessage(input, token);
    setInput('');
  };

  if (!hasHydrated) {
    return <div className="flex items-center justify-center h-screen">加载中...</div>;
  }

  if (!token) {
    return null;
  }

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-4">
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.map((msg, i) => (
          <ChatMessageBubble key={i} message={msg} />
        ))}
      </div>
      <div className="flex gap-2">
        <input
          className="flex-1 border rounded px-4 py-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="描述你的购物需求..."
        />
        <button className="bg-blue-600 text-white px-6 py-2 rounded" onClick={handleSend}>
          发送
        </button>
      </div>
    </div>
  );
}
