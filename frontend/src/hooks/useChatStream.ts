// SSE 对话 Hook：负责连接 Chat API、消费 Agent 事件流，并把步骤/结果写入 Zustand 状态。
// src/hooks/useChatStream.ts SSE 连接 Hook
import { SSE } from 'sse.js';
import { ChatApproval, ChatProduct, useChatStore } from '@/store/chat';
import { API_BASE_URL } from '@/services/api';

function toDisplayText(value: unknown): string {
  // 将 SSE payload 中的任意内容转换成可展示文本。
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
  // 统一解析服务端 SSE data JSON。
  return JSON.parse(event.data) as Record<string, unknown>;
}

export function useChatStream() {
  // 暴露 sendMessage，内部处理用户消息、assistant 占位、SSE 事件和错误降级。
  const addMessage = useChatStore((s) => s.addMessage);
  const updateLastAssistant = useChatStore((s) => s.updateLastAssistant);
  const appendStep = useChatStore((s) => s.appendStep);
  const setStreaming = useChatStore((s) => s.setStreaming);
  const setError = useChatStore((s) => s.setError);
  const lastAddedProduct = useChatStore((s) => s.lastAddedProduct);

  const sendMessage = (message: string, token: string) => {
    // 发送消息并监听 intent/thought/action/observation/final 五类事件。
    setError('');
    setStreaming(true);
    addMessage({ role: 'user', content: message });
    addMessage({ role: 'assistant', content: '', steps: [] });
    const shouldAttachLastAdded =
      Boolean(lastAddedProduct) &&
      /刚刚|刚才|已加入购物车|已经加入购物车|加入购物车的|这个|这款/.test(message) &&
      /下单|结算|购买|加入购物车|加购/.test(message);
    const requestMessage =
      shouldAttachLastAdded && lastAddedProduct
        ? `${message}\n[上下文：用户刚才通过商品卡片加入购物车的是商品 ${lastAddedProduct.id}：${lastAddedProduct.name}]`
        : message;

    const source = new SSE(`${API_BASE_URL}/chat/stream`, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      method: 'POST',
      payload: JSON.stringify({ message: requestMessage }),
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
      updateLastAssistant(
        toDisplayText(data.content),
        data.approval as ChatApproval | undefined,
        data.products as ChatProduct[] | undefined,
      );
      setStreaming(false);
      source.close();
    });

    source.onerror = () => {
      const message = '连接错误，请确认后端服务可访问后重试。';
      updateLastAssistant(message);
      setError(message);
      setStreaming(false);
      source.close();
    };
  };

  return { sendMessage };
}
