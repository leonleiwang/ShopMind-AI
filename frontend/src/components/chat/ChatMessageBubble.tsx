// 消息气泡组件
'use client';

import { api } from '@/services/api';
import { useAuthStore } from '@/store/auth';
import { ChatApproval, ChatMessage, ChatProduct, useChatStore } from '@/store/chat';
import { useState } from 'react';

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
          <>
            <div className="whitespace-pre-wrap text-sm leading-7">{formatMessage(message.content)}</div>
            {message.products?.length ? <ProductCards products={message.products} /> : null}
            {message.approval ? <ApprovalCard approval={message.approval} /> : null}
          </>
        )}
      </article>
    </div>
  );
}

function ProductCards({ products }: { products: ChatProduct[] }) {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [notice, setNotice] = useState('');
  const token = useAuthStore((s) => s.token);
  const setLastAddedProduct = useChatStore((s) => s.setLastAddedProduct);

  const addToCart = async (product: ChatProduct) => {
    if (!token || busyId) return;
    setBusyId(product.id);
    setNotice('');
    try {
      await api.post('/orders/cart', { product_id: product.id, quantity: 1 });
      setLastAddedProduct(product);
      setNotice(`已将 ${product.name} 加入购物车。`);
    } catch {
      setNotice('加入购物车失败，请稍后重试。');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="mt-3 space-y-2">
      {products.slice(0, 4).map((product, index) => {
        const expanded = expandedId === product.id;
        return (
          <div key={product.id} className="rounded-lg border border-[#cfe7ef] bg-[#f8fcfd] p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[11px] font-semibold text-[#1d6389]">推荐 {index + 1}</div>
                <h3 className="mt-1 text-sm font-semibold leading-5 text-slate-900">{product.name}</h3>
                <p className="mt-1 text-xs text-slate-500">
                  {product.brand ? `${product.brand} · ` : ''}
                  {product.category ?? '商品'} · 库存 {product.stock ?? '未知'}
                </p>
              </div>
              <div className="shrink-0 text-right text-sm font-semibold text-[#9a5a00]">
                ¥{Number(product.price ?? 0).toFixed(2)}
              </div>
            </div>

            {expanded ? (
              <div className="mt-3 rounded-md bg-white p-2 text-xs leading-6 text-slate-600">
                {product.description ? <p>{product.description}</p> : null}
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {formatAttributes(product.attributes).map((item) => (
                    <span key={item} className="rounded-full bg-slate-100 px-2 py-1 text-slate-600">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="mt-3 flex flex-wrap gap-2">
              <button
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
                onClick={() => setExpandedId(expanded ? null : product.id)}
              >
                {expanded ? '收起参数' : '展开参数'}
              </button>
              <button
                className="rounded-lg bg-[#1d6389] px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-[#123b5d] disabled:opacity-50"
                disabled={!token || busyId === product.id}
                onClick={() => addToCart(product)}
              >
                {busyId === product.id ? '加入中...' : '加入购物车'}
              </button>
            </div>
          </div>
        );
      })}
      {notice ? <p className="text-xs text-[#1d6389]">{notice}</p> : null}
    </div>
  );
}

function formatAttributes(attributes?: Record<string, unknown>) {
  if (!attributes) return [];
  const labelMap: Record<string, string> = {
    latency: '延迟',
    sound_quality: '音质',
    use_cases: '用途',
    noise_cancellation: '降噪',
    bluetooth_version: '蓝牙版本',
    performance_tier: '性能定位',
    camera_tier: '影像定位',
    screen_refresh_rate: '刷新率',
    energy_rating: '能效',
    capacity_liters: '容量',
    resolution: '分辨率',
    refresh_rate: '刷新率',
  };
  return Object.entries(attributes)
    .slice(0, 6)
    .map(([key, value]) => `${labelMap[key] ?? key}：${formatAttributeValue(value)}`);
}

function formatAttributeValue(value: unknown) {
  if (Array.isArray(value)) return value.join(' / ');
  if (typeof value === 'boolean') return value ? '是' : '否';
  return String(value);
}

function ApprovalCard({ approval }: { approval: ChatApproval }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const token = useAuthStore((s) => s.token);
  const updateApprovalResult = useChatStore((s) => s.updateApprovalResult);
  const pending = approval.status === 'pending';
  const isChatApproval = approval.approval_channel === 'chat';

  const review = async (decision: 'approve' | 'reject') => {
    if (!token || busy) return;
    setBusy(true);
    setError('');
    try {
      const response = await api.post(`/approvals/${approval.id}/${decision}`, {
        note: `chat_${decision}`,
      });
      const result = response.data.result ?? {};
      const content =
        decision === 'approve'
          ? `下单成功！订单号 ${result.order_id}，总金额 ¥${result.total_amount}。`
          : '已取消本次订单草稿，购物车不会被结算。';
      updateApprovalResult(approval.id, response.data.status, result, content);
    } catch {
      setError('处理失败：订单可能已处理，或购物车内容已变化。');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-3 rounded-lg border border-[#cfe7ef] bg-[#f3fbfd] p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-[#12445f]">
          {approval.risk_level} risk
        </span>
        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-600">
          {approval.confirmation_level ?? 'confirmation'}
        </span>
      </div>

      {isChatApproval && pending ? (
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
            disabled={busy}
            onClick={() => review('reject')}
          >
            取消
          </button>
          <button
            className="rounded-lg bg-[#1d6389] px-3 py-2 text-xs font-semibold text-white transition hover:bg-[#123b5d] disabled:opacity-50"
            disabled={busy}
            onClick={() => review('approve')}
          >
            {approval.confirmation_level === 'strong_confirm'
              ? '我已核对并确认购买'
              : approval.confirmation_level === 'double_confirm'
                ? '我确认购买'
                : '确认下单'}
          </button>
        </div>
      ) : null}

      {!isChatApproval && pending ? (
        <p className="mt-3 text-xs leading-5 text-slate-600">该订单已进入后台人工审核队列。</p>
      ) : null}

      {error ? <p className="mt-2 text-xs text-amber-700">{error}</p> : null}
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
