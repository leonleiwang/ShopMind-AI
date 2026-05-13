// 消息气泡组件
'use client';
import { ChatMessage } from '@/store/chat';

export default function ChatMessageBubble({ message }: { message: ChatMessage }) {
  return (
    <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[70%] p-3 rounded-xl ${message.role === 'user' ? 'bg-blue-100' : 'bg-gray-100'}`}>
        {message.steps?.map((step, i) => (
          <div key={i} className="text-sm text-gray-600 mb-1">
            <span className="font-bold">{step.type}</span>: {step.data}
          </div>
        ))}
        <div className="text-gray-900 whitespace-pre-wrap">{message.content}</div>
      </div>
    </div>
  );
}