// 后台仪表盘 / Agent 可观测性：展示 intent、tool、SSE、latency、WebSocket、AI 运营任务
'use client';

import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { api, getWebSocketUrl } from '@/services/api';

type Metrics = {
  uptime_seconds: number;
  intent_counts: Record<string, number>;
  tool_counts: Record<string, number>;
  tool_error_counts: Record<string, number>;
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
  sse_event_counts: {},
  avg_tool_latency_ms: 0,
  recent_events: [],
};

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
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-8">
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <h1 className="text-2xl font-semibold">ShopMind AI 运营仪表盘</h1>
            <p className="mt-2 text-sm text-slate-400">
              Agent 调用、SSE 事件、订单 WebSocket、AI 运营任务统一观测。
            </p>
          </div>
          <button
            className="rounded bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950"
            onClick={loadDashboard}
          >
            刷新
          </button>
        </header>

        {error ? (
          <div className="rounded border border-amber-500/40 bg-amber-500/10 p-3 text-amber-100">
            {error}
          </div>
        ) : null}

        <section className="grid gap-4 md:grid-cols-4">
          <MetricCard label="运行时间" value={`${metrics.uptime_seconds}s`} />
          <MetricCard label="工具调用" value={totalToolCalls.toString()} />
          <MetricCard label="平均延迟" value={`${metrics.avg_tool_latency_ms}ms`} />
          <MetricCard label="订单数量" value={orders.length.toString()} />
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <Panel title="Agent 意图分布">
            <KeyValueList data={metrics.intent_counts} empty="暂无意图数据，先在聊天页发起一次对话。" />
          </Panel>
          <Panel title="MCP 工具调用">
            <KeyValueList data={metrics.tool_counts} empty="暂无工具调用。" />
          </Panel>
          <Panel title="SSE 事件流">
            <KeyValueList data={metrics.sse_event_counts} empty="暂无 SSE 事件。" />
          </Panel>
          <Panel title="订单 WebSocket">
            {wsEvents.length ? (
              <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
                {wsEvents.map((event, index) => (
                  <pre
                    key={`${event}-${index}`}
                    className="whitespace-pre-wrap break-words rounded bg-slate-900 p-3 text-xs text-cyan-100"
                  >
                    {event}
                  </pre>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400">暂无订单快照。创建订单后这里会显示实时状态。</p>
            )}
          </Panel>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <Panel title="商品运营任务">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-slate-400">
                  <tr>
                    <th className="py-2">商品</th>
                    <th>分类</th>
                    <th>价格</th>
                    <th>库存</th>
                    <th>AI 运营任务</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((product) => (
                    <tr key={product.id} className="border-t border-slate-800">
                      <td className="py-3">
                        <div className="font-medium">{product.name}</div>
                        <div className="mt-1 max-w-xs truncate text-xs text-slate-400">
                          {product.description || '暂无描述'}
                        </div>
                        {product.pricing_suggestion ? (
                          <div className="mt-1 max-w-xs truncate text-xs text-emerald-300">
                            定价: {formatPricing(product.pricing_suggestion)}
                          </div>
                        ) : null}
                        {product.marketing_copy ? (
                          <div className="mt-1 max-w-xs truncate text-xs text-fuchsia-300">
                            文案: {product.marketing_copy}
                          </div>
                        ) : null}
                      </td>
                      <td>{product.category || '-'}</td>
                      <td>¥{product.price}</td>
                      <td>{product.stock}</td>
                      <td>
                        <div className="flex flex-wrap gap-2">
                          <button
                            className="rounded border border-cyan-500/50 px-3 py-1 text-xs text-cyan-200"
                            onClick={() => queueDescription(product.id)}
                          >
                            描述
                          </button>
                          <button
                            className="rounded border border-emerald-500/50 px-3 py-1 text-xs text-emerald-200"
                            onClick={() => queuePricing(product.id)}
                          >
                            定价
                          </button>
                          <button
                            className="rounded border border-fuchsia-500/50 px-3 py-1 text-xs text-fuchsia-200"
                            onClick={() => queueMarketing(product.id)}
                          >
                            文案
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button
              className="mt-4 rounded bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950"
              onClick={refreshRecommendations}
            >
              刷新个性化推荐
            </button>
            {taskEvents.length ? (
              <div className="mt-4 max-h-40 space-y-2 overflow-y-auto pr-1">
                {taskEvents.map((event, index) => (
                  <div key={`${event}-${index}`} className="rounded bg-slate-950 px-3 py-2 text-xs text-slate-300">
                    {event}
                  </div>
                ))}
              </div>
            ) : null}
          </Panel>

          <Panel title="最近事件">
            <div className="max-h-96 space-y-2 overflow-y-auto pr-1">
              {metrics.recent_events.length ? (
                metrics.recent_events.slice(0, 8).map((event, index) => (
                  <pre key={index} className="whitespace-pre-wrap break-words rounded bg-slate-900 p-3 text-xs text-slate-300">
                    {JSON.stringify(event, null, 2)}
                  </pre>
                ))
              ) : (
                <p className="text-sm text-slate-400">暂无事件。</p>
              )}
            </div>
          </Panel>
        </section>
      </div>
    </main>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-slate-800 bg-slate-900 p-4">
      <div className="text-sm text-slate-400">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded border border-slate-800 bg-slate-900/70 p-5">
      <h2 className="mb-4 text-base font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function KeyValueList({ data, empty }: { data: Record<string, number>; empty: string }) {
  const entries = Object.entries(data);
  if (!entries.length) return <p className="text-sm text-slate-400">{empty}</p>;
  return (
    <div className="space-y-2">
      {entries.map(([key, value]) => (
        <div key={key} className="flex items-center justify-between rounded bg-slate-950 px-3 py-2 text-sm">
          <span>{key}</span>
          <span className="font-mono text-cyan-200">{value}</span>
        </div>
      ))}
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
