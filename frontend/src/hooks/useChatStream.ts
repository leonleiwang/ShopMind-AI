// src/hooks/useChatStream.ts SSE 连接 Hook
import { SSE } from 'sse.js';
import { useChatStore } from '@/store/chat';
import { API_BASE_URL } from '@/services/api';

function toDisplayText(value: unknown): string {
  if (typeof value === 'string') return value;
  if (value && typeof value === 'object' && 'text' in value) {
    const text = (value as { text?: unknown }).text;
    if (typeof text === 'string') return text;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function parseEventData(event: MessageEvent<string>): Record<string, unknown> {
  return JSON.parse(event.data) as Record<string, unknown>;
}

export function useChatStream() {
  const addMessage = useChatStore((s) => s.addMessage);
  const updateLastAssistant = useChatStore((s) => s.updateLastAssistant);
  const appendStep = useChatStore((s) => s.appendStep);

  const sendMessage = (message: string, token: string) => {
    addMessage({ role: 'user', content: message });
    addMessage({ role: 'assistant', content: '', steps: [] });

    const source = new SSE(`${API_BASE_URL}/chat/stream`, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      method: 'POST',
      payload: JSON.stringify({ message }),
    });

    source.addEventListener('intent', (e: MessageEvent<string>) => {
      const data = parseEventData(e);
      appendStep({ type: 'intent', data: `意图: ${data.intent}` });
    });

    source.addEventListener('thought', (e: MessageEvent<string>) => {
      const data = parseEventData(e);
      appendStep({ type: 'thought', data: toDisplayText(data.content) });
    });

    source.addEventListener('action', (e: MessageEvent<string>) => {
      const data = parseEventData(e);
      appendStep({ type: 'action', data: `工具: ${data.tool} ${JSON.stringify(data.input)}` });
    });

    source.addEventListener('observation', (e: MessageEvent<string>) => {
      const data = parseEventData(e);
      appendStep({ type: 'observation', data: toDisplayText(data.content) });
    });

    source.addEventListener('final', (e: MessageEvent<string>) => {
      const data = parseEventData(e);
      updateLastAssistant(toDisplayText(data.content));
      source.close();
    });

    source.onerror = () => {
      updateLastAssistant('连接错误，请重试。');
      source.close();
    };
  };

  return { sendMessage };
}
