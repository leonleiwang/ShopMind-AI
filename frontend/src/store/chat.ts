// src/store/chat.ts 全局状态管理
import { create } from 'zustand';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  steps?: Array<{ type: string; data: string }>;
}

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string;
  addMessage: (msg: ChatMessage) => void;
  updateLastAssistant: (content: string) => void;
  appendStep: (step: { type: string; data: string }) => void;
  setStreaming: (value: boolean) => void;
  setError: (message: string) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  error: '',
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  updateLastAssistant: (content) =>
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant') {
        last.content = content;
      }
      return { messages: msgs };
    }),
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
  clearMessages: () => set({ messages: [], error: '' }),
}));
