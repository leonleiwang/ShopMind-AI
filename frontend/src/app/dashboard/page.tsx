// 管理员 / 工程师 AgentOps 仪表盘：只展示系统观测与 AI 运营任务，不展示买家私域购物车。
'use client';

import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import { api, getWebSocketUrl } from '@/services/api';
import { useAuthStore } from '@/store/auth';
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

const dashboardCategories = ['Agent 路由', 'MCP 工具', 'LLM 网关', 'SSE 流', '订单 WebSocket', 'AI 运营任务'];
const intentKeys = ['search', 'recommend', 'cart', 'order', 'plan', 'compare'];
const toolKeys = ['search_products', 'compare_products', 'add_to_cart', 'remove_from_cart', 'clear_cart', 'place_order'];

export default function OpsDashboardPage() {
  // 工程观测页仅对 admin 开放。
  return (
    <RoleGuard allowed={['admin']}>
      <OpsDashboardContent />
    </RoleGuard>
  );
}

function OpsDashboardContent() {
  // 聚合 Agent 指标、商品运营任务、订单 WebSocket 和最近事件。
  const [metrics, setMetrics] = useState<Metrics>(emptyMetrics);
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [wsEvents, setWsEvents] = useState<string[]>([]);
  const [taskEvents, setTaskEvents] = useState<string[]>([]);
  const [error, setError] = useState('');
  const token = useAuthStore((s) => s.token);

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
  const latestOrderId = orders[0]?.id ?? null;
  const intentCounts = useMemo(() => withDefaultKeys(metrics.intent_counts, intentKeys), [metrics.intent_counts]);
  const toolCounts = useMemo(() => withDefaultKeys(metrics.tool_counts, toolKeys), [metrics.tool_counts]);

  const loadDashboard = async () => {
    // 周期性加载后端观测快照、商品列表和订单列表。
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
      setError('工程仪表盘数据加载失败：请确认已使用管理员账号登录，并且后端服务可访问。');
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
    if (!latestOrderId || !token || typeof window === 'undefined') return;
    const socket = new WebSocket(getWebSocketUrl(`/orders/ws/${latestOrderId}`, token));

    socket.onopen = () => {
      setWsEvents([]);
    };
    socket.onmessage = (event) => {
      setWsEvents((current) => {
        if (current[0] === event.data) return current;
        return [event.data, ...current].slice(0, 6);
      });
    };
    socket.onerror = () => {
      setWsEvents((current) => {
        const message = '订单 WebSocket 连接失败或暂无可监听订单';
        if (current[0] === message) return current;
        return [message, ...current].slice(0, 6);
      });
    };
    return () => socket.close();
  }, [latestOrderId, token]);

  const runTask = async (task: () => Promise<string>) => {
    // 执行 AI 运营任务并把结果追加到任务事件流。
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
        ? `商品 ${productId} 描述已生成：${description}`
        : `商品 ${productId} 描述生成任务已入队：${response.data.task_id}。Worker 完成后刷新可见。`;
    });

  const queuePricing = (productId: number) =>
    runTask(async () => {
      const response = await api.post(`/products/${productId}/pricing-suggestion`);
      await loadDashboard();
      const result = response.data.result;
      return result?.suggested_price
        ? `商品 ${productId} 建议价 ¥${result.suggested_price}：${result.reason}`
        : `商品 ${productId} 动态定价任务已入队：${response.data.task_id}。Worker 完成后刷新可见。`;
    });

  const queueMarketing = (productId: number) =>
    runTask(async () => {
      const response = await api.post(`/products/${productId}/marketing-copy`);
      await loadDashboard();
      const copy = response.data.result?.marketing_copy;
      return copy
        ? `商品 ${productId} 文案已生成：${copy}`
        : `商品 ${productId} 营销文案任务已入队：${response.data.task_id}。Worker 完成后刷新可见。`;
    });

  const refreshRecommendations = () =>
    runTask(async () => {
      const response = await api.post('/products/recommendations/batch');
      return `个性化推荐刷新任务：${response.data.task_id}`;
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
              <span className="block text-xs text-sky-100/75">管理员 / 工程观测台</span>
            </span>
          </Link>
          <nav className="flex items-center gap-2 text-sm">
            <Link className="hidden rounded-lg px-3 py-2 text-sky-50 hover:bg-white/10 md:inline" href="/admin/dashboard">
              运营后台
            </Link>
            <Link className="hidden rounded-lg px-3 py-2 text-sky-50 hover:bg-white/10 md:inline" href="/governance">
              风控治理
            </Link>
            <button
              className="rounded-lg bg-[#ffca45] px-3 py-2 font-semibold text-[#102033] hover:bg-[#ffd873]"
              onClick={loadDashboard}
            >
              刷新数据
            </button>
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
      <RoleNav />

      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-6 lg:px-8">
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-500">AgentOps cockpit</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">ShopMind AI 工程观测仪表盘</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            这里面向管理员、AgentOps 和开发者，用来观察 Agent 路由、MCP工具调用、LLM 网关、SSE 事件、订单WebSocket状态和 AI 运营任务。
          </p>
        </section>

        {error ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {error}
          </div>
        ) : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard label="运行时长" value={formatUptime(metrics.uptime_seconds)} caption="API 进程" />
          <MetricCard label="工具调用" value={totalToolCalls.toString()} caption={`${totalErrors} 个异常`} />
          <MetricCard label="LLM 事件" value={totalLlmEvents.toString()} caption="成功 / 降级 / 失败" />
          <MetricCard label="平均延迟" value={`${metrics.avg_tool_latency_ms}ms`} caption="工具与 LLM 样本" />
          <MetricCard label="商品样本" value={products.length.toString()} caption="AI 运营任务候选" />
        </section>

        <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
          <Panel title="Order WebSocket" eyebrow="订单实时状态">
            <EventList
              events={wsEvents}
              empty={latestOrderId ? `正在监听订单 #${latestOrderId}。` : '暂无可监听订单。创建订单后这里会显示实时快照。'}
              tone="cyan"
            />
          </Panel>
          <Panel title="最近系统事件" eyebrow="observability">
            <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
              {metrics.recent_events.length ? (
                metrics.recent_events.slice(0, 8).map((event, index) => <EventCard key={index} event={event} />)
              ) : (
                <EmptyBox title="暂无事件" body="进行一次聊天或工具调用后，这里会出现最近事件。" />
              )}
            </div>
          </Panel>
        </section>

        <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
          <Panel title="Agent Routing" eyebrow="intent / evidence">
            <KeyValueList data={intentCounts} empty="暂无意图数据，先在聊天页发起一次对话。" />
          </Panel>
          <Panel title="MCP 工具调用" eyebrow="request-scoped tools">
            <KeyValueList data={toolCounts} empty="暂无工具调用。" />
          </Panel>
        </section>

        <section className="grid gap-5 xl:grid-cols-2">
          <Panel title="LLM 网关" eyebrow="timeout / retry / fallback">
            <KeyValueList data={metrics.llm_counts ?? {}} empty="暂无 LLM 网关事件。" />
          </Panel>
          <Panel title="SSE 事件流" eyebrow="frontend stream">
            <KeyValueList data={metrics.sse_event_counts} empty="暂无 SSE 事件。" />
          </Panel>
        </section>

        <section className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
          <Panel title="AI 商品运营任务" eyebrow="admin tools">
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
              <EmptyBox title="暂无商品" body="先运行 seed 脚本或在后台创建商品，再展示运营任务。" />
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
          </Panel>

          <Panel title="任务回执" eyebrow="latest admin actions">
            <EventList events={taskEvents} empty="暂无任务回执。点击左侧 AI 运营任务后会显示结果。" tone="emerald" />
          </Panel>
        </section>
      </div>
    </main>
  );
}

function MetricCard({ label, value, caption }: { label: string; value: string; caption: string }) {
  // 工程指标卡片。
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">{value}</div>
      <div className="mt-2 text-xs text-slate-500">{caption}</div>
    </article>
  );
}

function Panel({ title, eyebrow, children }: { title: string; eyebrow: string; children: ReactNode }) {
  // 仪表盘通用区块容器。
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="mb-4">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{eyebrow}</p>
        <h2 className="mt-1 text-lg font-semibold text-slate-900">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function KeyValueList({ data, empty }: { data: Record<string, number>; empty: string }) {
  // 计数字典展示组件，用于 intent/tool/LLM 统计。
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(([, value]) => value), 1);

  if (!entries.length) return <EmptyBox title="暂无数据" body={empty} />;
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
  // 商品运营行：触发描述、定价和营销文案 AI 草稿生成。
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
              定价：{formatPricing(product.pricing_suggestion)}
            </span>
          ) : null}
          {product.marketing_copy ? <span className="rounded-lg bg-[#e8f6fa] px-2.5 py-1 text-[#12445f]">文案已生成</span> : null}
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
  // 运营任务按钮。
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
  // WebSocket 与任务执行事件列表。
  if (!events.length) return <EmptyBox title="暂无事件" body={empty} />;
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
  // 最近 AgentOps 事件卡片。
  const type = String(event.type ?? 'event');
  const ok = event.ok;
  return (
    <div className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">{type}</span>
        {typeof ok === 'boolean' ? (
          <span className={ok ? 'text-xs text-emerald-700' : 'text-xs text-amber-700'}>{ok ? '正常' : '注意'}</span>
        ) : null}
      </div>
      <pre className="mt-3 whitespace-pre-wrap break-words text-xs leading-5 text-slate-500">
        {JSON.stringify(event, null, 2)}
      </pre>
    </div>
  );
}

function EmptyBox({ title, body }: { title: string; body: string }) {
  // 空状态提示。
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-[#fbfcfe] p-4">
      <p className="text-sm font-medium text-slate-700">{title}</p>
      <p className="mt-1 text-sm leading-6 text-slate-500">{body}</p>
    </div>
  );
}

function withDefaultKeys(data: Record<string, number>, keys: string[]) {
  // 为关键指标补零，保证图表/列表稳定展示。
  return keys.reduce<Record<string, number>>(
    (result, key) => {
      result[key] = data[key] ?? 0;
      return result;
    },
    { ...data },
  );
}

function formatPricing(value: string) {
  // 定价建议字段格式化。
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
  // 将秒级运行时长格式化为秒/分钟/小时。
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h`;
}
