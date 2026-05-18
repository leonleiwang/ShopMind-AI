// 后台仪表盘 / Agent 可观测性：展示 intent、tool、SSE、latency、WebSocket、AI 运营任务
'use client';

import { api, getWebSocketUrl } from '@/services/api';
import Link from 'next/link';
import { ReactNode, useEffect, useMemo, useState } from 'react';

type Metrics = {
  uptime_seconds: number;
  intent_counts: Record<string, number>;
  tool_counts: Record<string, number>;
  tool_error_counts: Record<string, number>;
  llm_counts?: Record<string, number>;
  sse_event_counts: Record<string, number>;
  avg_tool_latency_ms: number;
  recent_events: Array<Record<string, unknown>>;
};

type Product = {
  id: number;
  name: string;
  description: string;
  price: number;
  category: string;
  stock: number;
  pricing_suggestion?: string;
  marketing_copy?: string;
};

type Order = {
  id: number;
  status: string;
  total_amount: number;
  created_at?: string;
};

const emptyMetrics: Metrics = {
  uptime_seconds: 0,
  intent_counts: {},
  tool_counts: {},
  tool_error_counts: {},
  llm_counts: {},
  sse_event_counts: {},
  avg_tool_latency_ms: 0,
  recent_events: [],
};

const dashboardCategories = ['Agent 路由', 'MCP 工具', 'LLM 网关', 'SSE', '订单状态', 'AI 运营'];

export default function OpsDashboardPage() {
  const [metrics, setMetrics] = useState<Metrics>(emptyMetrics);
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [wsEvents, setWsEvents] = useState<string[]>([]);
  const [taskEvents, setTaskEvents] = useState<string[]>([]);
  const [error, setError] = useState('');

  const latestOrderId = orders[0]?.id ?? null;
  const totalToolCalls = useMemo(
    () => Object.values(metrics.tool_counts).reduce((sum, value) => sum + value, 0),
    [metrics.tool_counts],
  );
  const totalLlmEvents = useMemo(
    () => Object.values(metrics.llm_counts ?? {}).reduce((sum, value) => sum + value, 0),
    [metrics.llm_counts],
  );
  const totalErrors = useMemo(
    () => Object.values(metrics.tool_error_counts).reduce((sum, value) => sum + value, 0),
    [metrics.tool_error_counts],
  );

  const loadDashboard = async () => {
    try {
      const [metricsRes, productsRes, ordersRes] = await Promise.all([
        api.get('/chat/metrics'),
        api.get('/products/', { params: { limit: 8 } }),
        api.get('/orders/'),
      ]);
      setMetrics(metricsRes.data);
      setProducts(productsRes.data);
      setOrders(ordersRes.data);
      setError('');
    } catch {
      setError('仪表盘数据加载失败：请确认已登录且后端服务可访问。');
    }
  };

  useEffect(() => {
    const initialLoad = window.setTimeout(() => {
      void loadDashboard();
    }, 0);
    const timer = window.setInterval(() => {
      void loadDashboard();
    }, 5000);
    return () => {
      window.clearTimeout(initialLoad);
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!latestOrderId || typeof window === 'undefined') return;
    const token = localStorage.getItem('token');
    const socket = new WebSocket(getWebSocketUrl(`/orders/ws/${latestOrderId}`, token));

    socket.onopen = () => {
      setWsEvents([]);
    };
    socket.onmessage = (event) => {
      setWsEvents((current) => {
        if (current[0] === event.data) return current;
        return [event.data, ...current].slice(0, 5);
      });
    };
    socket.onerror = () => {
      setWsEvents((current) => {
        const message = 'WebSocket 连接失败或无权限';
        if (current[0] === message) return current;
        return [message, ...current].slice(0, 5);
      });
    };
    return () => socket.close();
  }, [latestOrderId]);

  const runTask = async (task: () => Promise<string>) => {
    try {
      const message = await task();
      setTaskEvents((current) => [message, ...current].slice(0, 5));
      setError('');
    } catch {
      setError('AI 运营任务提交失败：请确认后端、Celery/Redis 或 eager 配置正常。');
    }
  };

  const queueDescription = (productId: number) =>
    runTask(async () => {
      const response = await api.post(`/products/${productId}/generate-description`);
      await loadDashboard();
      const description = response.data.result?.description;
      return description
        ? `商品 ${productId} 描述已生成: ${description}`
        : `商品 ${productId} 描述生成任务已入队: ${response.data.task_id}。Worker 完成后刷新可见。`;
    });

  const queuePricing = (productId: number) =>
    runTask(async () => {
      const response = await api.post(`/products/${productId}/pricing-suggestion`);
      await loadDashboard();
      const result = response.data.result;
      return result?.suggested_price
        ? `商品 ${productId} 建议价 ¥${result.suggested_price}: ${result.reason}`
        : `商品 ${productId} 动态定价任务已入队: ${response.data.task_id}。Worker 完成后刷新可见。`;
    });

  const queueMarketing = (productId: number) =>
    runTask(async () => {
      const response = await api.post(`/products/${productId}/marketing-copy`);
      await loadDashboard();
      const copy = response.data.result?.marketing_copy;
      return copy
        ? `商品 ${productId} 文案已生成: ${copy}`
        : `商品 ${productId} 营销文案任务已入队: ${response.data.task_id}。Worker 完成后刷新可见。`;
    });

  const refreshRecommendations = () =>
    runTask(async () => {
      const response = await api.post('/products/recommendations/batch');
      return `个性化推荐刷新任务: ${response.data.task_id}`;
    });

  return (
    <main className="min-h-screen bg-[#f4f7fb] text-slate-900">
      <header className="bg-[#123b5d] text-white shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-3 lg:px-8">
          <Link className="flex items-center gap-3" href="/">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#ffca45] text-sm font-black text-[#102033]">
              SM
            </span>
            <span>
              <span className="block font-semibold">ShopMind AI</span>
              <span className="block text-xs text-sky-100/75">Operations dashboard</span>
            </span>
          </Link>
          <nav className="flex items-center gap-2 text-sm">
            <Link className="hidden rounded-lg px-3 py-2 text-sky-50 hover:bg-white/10 md:inline" href="/chat">
              AI 客服
            </Link>
            <Link className="hidden rounded-lg px-3 py-2 text-sky-50 hover:bg-white/10 md:inline" href="/dashboard">
              我的订单
            </Link>
            <Link className="rounded-lg bg-[#ffca45] px-3 py-2 font-semibold text-[#102033] hover:bg-[#ffd873]" href="/chat">
              返回购物
            </Link>
          </nav>
        </div>
        <div className="border-t border-white/10 bg-[#1d6389]">
          <div className="mx-auto flex max-w-7xl gap-2 overflow-x-auto px-5 py-2 lg:px-8">
            {dashboardCategories.map((category) => (
              <span key={category} className="shrink-0 rounded-full bg-[#dff3f8] px-3 py-1.5 text-xs font-medium text-[#12445f]">
                {category}
              </span>
            ))}
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-6 lg:px-8">
        <header className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Operations cockpit</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight">ShopMind AI 仪表盘</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                统一观察 Agent 路由、MCP 工具、LLM 网关、SSE 事件和订单 WebSocket 状态。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-[#123b5d] transition hover:border-[#9bd7e7] hover:bg-[#f3fbfd]"
                href="/chat"
              >
                Chat
              </Link>
              <button
                className="rounded-lg bg-[#1d6389] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#123b5d]"
                onClick={loadDashboard}
              >
                刷新数据
              </button>
            </div>
          </div>
        </header>

        {error ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {error}
          </div>
        ) : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard label="Uptime" value={formatUptime(metrics.uptime_seconds)} caption="API process" />
          <MetricCard label="Tool calls" value={totalToolCalls.toString()} caption={`${totalErrors} errors`} />
          <MetricCard label="LLM events" value={totalLlmEvents.toString()} caption="ok / error / degraded" />
          <MetricCard label="Avg latency" value={`${metrics.avg_tool_latency_ms}ms`} caption="tool + llm samples" />
          <MetricCard label="Orders" value={orders.length.toString()} caption={latestOrderId ? `watching #${latestOrderId}` : 'no active order'} />
        </section>

        <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
          <Panel title="Agent routing" eyebrow="intent / evidence">
            <KeyValueList data={metrics.intent_counts} empty="暂无意图数据，先在聊天页发起一次对话。" />
          </Panel>
          <Panel title="MCP tools" eyebrow="request-scoped calls">
            <KeyValueList data={metrics.tool_counts} empty="暂无工具调用。" />
          </Panel>
        </section>

        <section className="grid gap-5 xl:grid-cols-3">
          <Panel title="LLM gateway" eyebrow="timeout / retry / fallback">
            <KeyValueList data={metrics.llm_counts ?? {}} empty="暂无 LLM 网关事件。" />
          </Panel>
          <Panel title="SSE stream" eyebrow="frontend process events">
            <KeyValueList data={metrics.sse_event_counts} empty="暂无 SSE 事件。" />
          </Panel>
          <Panel title="Order WebSocket" eyebrow="latest snapshot">
            <EventList
              events={wsEvents}
              empty="暂无订单快照。创建订单后这里会显示实时状态。"
              tone="cyan"
            />
          </Panel>
        </section>

        <section className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
          <Panel title="商品运营任务" eyebrow="AI operations">
            {products.length ? (
              <div className="grid gap-3">
                {products.map((product) => (
                  <ProductOpsRow
                    key={product.id}
                    product={product}
                    onDescription={() => queueDescription(product.id)}
                    onPricing={() => queuePricing(product.id)}
                    onMarketing={() => queueMarketing(product.id)}
                  />
                ))}
              </div>
            ) : (
              <EmptyBox title="暂无商品" body="先在 Swagger 或后台接口创建商品，再展示运营任务。" />
            )}

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                className="rounded-lg bg-[#ffca45] px-4 py-2 text-sm font-semibold text-[#102033] transition hover:bg-[#ffd873]"
                onClick={refreshRecommendations}
              >
                刷新个性化推荐
              </button>
              <span className="text-xs text-slate-500">Celery eager 或 worker 均可演示</span>
            </div>

            {taskEvents.length ? (
              <div className="mt-4">
                <EventList events={taskEvents} empty="" tone="emerald" />
              </div>
            ) : null}
          </Panel>

          <Panel title="最近事件" eyebrow="observability">
            <div className="max-h-[520px] space-y-2 overflow-y-auto pr-1">
              {metrics.recent_events.length ? (
                metrics.recent_events.slice(0, 10).map((event, index) => (
                  <EventCard key={index} event={event} />
                ))
              ) : (
                <EmptyBox title="暂无事件" body="进行一次聊天或工具调用后，这里会出现最近事件。" />
              )}
            </div>
          </Panel>
        </section>
      </div>
    </main>
  );
}

function MetricCard({ label, value, caption }: { label: string; value: string; caption: string }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">{value}</div>
      <div className="mt-2 text-xs text-slate-500">{caption}</div>
    </article>
  );
}

function Panel({ title, eyebrow, children }: { title: string; eyebrow: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{eyebrow}</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">{title}</h2>
        </div>
      </div>
      {children}
    </section>
  );
}

function KeyValueList({ data, empty }: { data: Record<string, number>; empty: string }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(([, value]) => value), 1);

  if (!entries.length) return <EmptyBox title="Empty state" body={empty} />;
  return (
    <div className="space-y-3">
      {entries.map(([key, value]) => (
        <div key={key} className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-3">
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className="font-medium text-slate-700">{key}</span>
            <span className="font-mono text-[#12445f]">{value}</span>
          </div>
          <div className="mt-3 h-1.5 rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-[#1d6389]" style={{ width: `${Math.max((value / max) * 100, 8)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function ProductOpsRow({
  product,
  onDescription,
  onPricing,
  onMarketing,
}: {
  product: Product;
  onDescription: () => void;
  onPricing: () => void;
  onMarketing: () => void;
}) {
  return (
    <article className="grid gap-4 rounded-lg border border-slate-200 bg-[#fbfcfe] p-4 lg:grid-cols-[1fr_auto]">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold text-slate-900">{product.name}</h3>
          <span className="rounded-full bg-[#1d6389]/10 px-2.5 py-1 text-xs font-medium text-[#12445f]">
            {product.category || '未分类'}
          </span>
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">库存 {product.stock}</span>
        </div>
        <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-500">{product.description || '暂无描述'}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="rounded-lg bg-[#fff7dd] px-2.5 py-1 font-semibold text-[#7a4b00]">¥{product.price}</span>
          {product.pricing_suggestion ? (
            <span className="rounded-lg bg-emerald-50 px-2.5 py-1 text-emerald-700">
              定价: {formatPricing(product.pricing_suggestion)}
            </span>
          ) : null}
          {product.marketing_copy ? (
            <span className="rounded-lg bg-[#e8f6fa] px-2.5 py-1 text-[#12445f]">文案已生成</span>
          ) : null}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 lg:justify-end">
        <TaskButton onClick={onDescription}>描述</TaskButton>
        <TaskButton onClick={onPricing}>定价</TaskButton>
        <TaskButton onClick={onMarketing}>文案</TaskButton>
      </div>
    </article>
  );
}

function TaskButton({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <button
      className="rounded-lg border border-[#9bd7e7] px-3 py-2 text-xs font-semibold text-[#12445f] transition hover:border-sky-300/60 hover:bg-[#1d6389]/10"
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function EventList({ events, empty, tone }: { events: string[]; empty: string; tone: 'cyan' | 'emerald' }) {
  if (!events.length) return <EmptyBox title="No events" body={empty} />;
  const color = tone === 'cyan' ? 'text-[#12445f] border-[#cfe7ef]' : 'text-emerald-700 border-emerald-200';
  return (
    <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
      {events.map((event, index) => (
        <pre
          key={`${event}-${index}`}
          className={`whitespace-pre-wrap break-words rounded-lg border bg-[#fbfcfe] p-3 text-xs leading-5 ${color}`}
        >
          {event}
        </pre>
      ))}
    </div>
  );
}

function EventCard({ event }: { event: Record<string, unknown> }) {
  const type = String(event.type ?? 'event');
  const ok = event.ok;
  return (
    <div className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">{type}</span>
        {typeof ok === 'boolean' ? (
          <span className={ok ? 'text-xs text-emerald-700' : 'text-xs text-amber-700'}>{ok ? 'ok' : 'attention'}</span>
        ) : null}
      </div>
      <pre className="mt-3 whitespace-pre-wrap break-words text-xs leading-5 text-slate-500">
        {JSON.stringify(event, null, 2)}
      </pre>
    </div>
  );
}

function EmptyBox({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-[#fbfcfe] p-4">
      <p className="text-sm font-medium text-slate-700">{title}</p>
      <p className="mt-1 text-sm leading-6 text-slate-500">{body}</p>
    </div>
  );
}

function formatPricing(value: string) {
  try {
    const parsed = JSON.parse(value) as { suggested_price?: number; reason?: string };
    if (parsed.suggested_price) {
      return `¥${parsed.suggested_price}，${parsed.reason || ''}`;
    }
  } catch {
    return value;
  }
  return value;
}

function formatUptime(seconds: number) {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h`;
}
