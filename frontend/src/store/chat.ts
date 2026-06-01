// Chat 状态 Store：保存消息流、Agent 步骤、审批卡片、推荐商品和最近加购商品。
// src/store/chat.ts 全局状态管理
import { create } from 'zustand';

export interface ChatApproval {
  id: number;
  action_type: string;
  status: string;
  risk_level: string;
  risk_reasons: string[];
  approval_channel?: 'chat' | 'governance';
  confirmation_level?: 'standard' | 'double_confirm' | 'strong_confirm' | 'manual_review';
  summary: string;
  payload?: Record<string, unknown>;
  result?: Record<string, unknown>;
}

export interface ChatProduct {
  id: number;
  name: string;
  price: number;
  category?: string;
  brand?: string;
  stock?: number;
  image_url?: string;
  description?: string;
  attributes?: Record<string, unknown>;
  tags?: string[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  steps?: Array<{ type: string; data: string }>;
  approval?: ChatApproval;
  products?: ChatProduct[];
}

interface ChatState {
  messages: ChatMessage[];
  lastAddedProduct?: ChatProduct;
  isStreaming: boolean;
  error: string;
  addMessage: (msg: ChatMessage) => void;
  setLastAddedProduct: (product: ChatProduct) => void;
  updateLastAssistant: (content: string, approval?: ChatApproval, products?: ChatProduct[]) => void;
  updateApprovalResult: (approvalId: number, status: string, result: Record<string, unknown>, content: string) => void;
  appendStep: (step: { type: string; data: string }) => void;
  setStreaming: (value: boolean) => void;
  setError: (message: string) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  lastAddedProduct: undefined,
  isStreaming: false,
  error: '',
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  setLastAddedProduct: (product) => set({ lastAddedProduct: product }),
  updateLastAssistant: (content, approval, products) =>
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant') {
        last.content = content;
        last.approval = approval;
        last.products = products;
      }
      return { messages: msgs };
    }),
  updateApprovalResult: (approvalId, status, result, content) =>
    set((state) => ({
      messages: state.messages.map((message) =>
        message.approval?.id === approvalId
          ? {
              ...message,
              content,
              approval: {
                ...message.approval,
                status,
                result,
              },
            }
          : message,
      ),
    })),
  appendStep: (step) =>
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant') {
        if (!last.steps) last.steps = [];
        last.steps.push(step);
      }
      return { messages: msgs };
    }),
  setStreaming: (value) => set({ isStreaming: value }),
  setError: (message) => set({ error: message }),
  clearMessages: () => set({ messages: [], error: '', lastAddedProduct: undefined }),
}));
