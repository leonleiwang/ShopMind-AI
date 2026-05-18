// 消息气泡组件
'use client';

import { ChatMessage } from '@/store/chat';

const stepTone: Record<string, string> = {
  intent: 'border-[#9bd7e7] bg-[#e8f6fa] text-[#0f4d68]',
  thought: 'border-slate-200 bg-slate-50 text-slate-600',
  action: 'border-[#b9d7ff] bg-[#edf5ff] text-[#164a82]',
  observation: 'border-emerald-200 bg-emerald-50 text-emerald-700',
};

export default function ChatMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  const isPendingAssistant = !isUser && !message.content && message.steps?.length;

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <article
        className={[
          'max-w-[90%] rounded-lg border px-4 py-3 shadow-sm md:max-w-[76%]',
          isUser
            ? 'border-[#c68a00] bg-[#ffd66b] text-[#1f2933]'
            : 'border-slate-200 bg-white text-slate-800',
        ].join(' ')}
      >
        {message.steps?.length ? (
          <div className="mb-3 space-y-2">
            {message.steps.map((step, i) => (
              <div
                key={`${step.type}-${i}`}
                className={`rounded-lg border px-3 py-2 text-xs ${stepTone[step.type] ?? stepTone.thought}`}
              >
                <span className="mr-2 font-semibold uppercase tracking-[0.14em]">{step.type}</span>
                <span className="text-current/80">{step.data}</span>
              </div>
            ))}
          </div>
        ) : null}

        {isPendingAssistant ? (
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <span className="h-2 w-2 rounded-full bg-[#1d7fa8]" />
            Agent 正在检索商品和调用工具...
          </div>
        ) : (
          <div className="whitespace-pre-wrap text-sm leading-7">{formatMessage(message.content)}</div>
        )}
      </article>
    </div>
  );
}

function formatMessage(content: string) {
  if (!content) return '';

  const lines = content.split('\n');
  return lines.map((line, index) => {
    const isProductLine = line.trim().startsWith('- ') && (line.includes('商品') || line.includes('¥'));
    if (!isProductLine) {
      return (
        <span key={`${line}-${index}`}>
          {line}
          {index < lines.length - 1 ? '\n' : ''}
        </span>
      );
    }

    return (
      <span
        key={`${line}-${index}`}
        className="my-2 block rounded-lg border border-[#cfe7ef] bg-[#f3fbfd] px-3 py-2 text-slate-800"
      >
        {line.replace(/^- /, '')}
      </span>
    );
  });
}
