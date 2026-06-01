'use client';

// 客服联络中心页面：展示工单队列、SLA、风险等级、事件日志和 AI 坐席辅助。
import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import { api } from '@/services/api';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

type TicketStatus = 'open' | 'pending' | 'resolved' | 'escalated';

type SupportTicket = {
  id: number;
  ticket_id: string;
  customer_id: number;
  conversation_id: string;
  category: string;
  priority: string;
  status: TicketStatus;
  assigned_agent: string;
  summary: string;
  channel: string;
  order_id?: number | null;
  risk_level: string;
  handoff_reason: string;
  resolution: string;
  sla_deadline?: string | null;
  closed_at?: string | null;
  created_at?: string | null;
};

type TicketEvent = {
  id: number;
  event_type: string;
  from_status: string;
  to_status: string;
  details: Record<string, unknown>;
  created_at?: string | null;
};

type AgentAssist = {
  intent: string;
  user_intent: string;
  recommended_reply: string;
  knowledge_refs: Array<{ title?: string; source?: string; section?: string }>;
  order_snapshot: Record<string, unknown>;
  risk_level: string;
  next_best_action: string;
  ai_confidence: number;
  routing_strategy: string;
};

const statuses: Array<TicketStatus | 'all'> = ['all', 'open', 'pending', 'escalated', 'resolved'];
const riskLevels = ['all', 'low', 'medium', 'high'];

export default function SupportConversationsPage() {
  // 客服控制台允许 support 和 admin 访问。
  return (
    <RoleGuard allowed={['support', 'admin']}>
      <SupportContactCenter />
    </RoleGuard>
  );
}

function SupportContactCenter() {
  // 管理工单列表、筛选器、选中工单、事件时间线和 AI Assist 状态。
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [events, setEvents] = useState<TicketEvent[]>([]);
  const [assist, setAssist] = useState<AgentAssist | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<TicketStatus | 'all'>('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isGeneratingAssist, setIsGeneratingAssist] = useState(false);

  const selectedTicket = useMemo(
    () => tickets.find((ticket) => ticket.id === selectedId) ?? tickets[0] ?? null,
    [selectedId, tickets],
  );

  const visibleTickets = useMemo(
    () =>
      tickets.filter((ticket) => {
        const statusMatches = statusFilter === 'all' || ticket.status === statusFilter;
        const riskMatches = riskFilter === 'all' || ticket.risk_level === riskFilter;
        return statusMatches && riskMatches;
      }),
    [riskFilter, statusFilter, tickets],
  );

  const metrics = useMemo(() => {
    const open = tickets.filter((ticket) => ticket.status === 'open').length;
    const escalated = tickets.filter((ticket) => ticket.status === 'escalated').length;
    const overdue = tickets.filter((ticket) => isOverdue(ticket.sla_deadline, ticket.status)).length;
    const highRisk = tickets.filter((ticket) => ticket.risk_level === 'high').length;
    return { open, escalated, overdue, highRisk };
  }, [tickets]);

  const loadTickets = async () => {
    // 加载客服工单列表，并自动选择当前工单。
    setIsLoading(true);
    try {
      const response = await api.get('/support/tickets', { params: { limit: 80 } });
      setTickets(response.data);
      setSelectedId((current) => current ?? response.data[0]?.id ?? null);
      setError('');
    } catch {
      setTickets([]);
      setError('客服工单加载失败。请确认已使用 support/admin 账号登录，并且后端服务可访问。');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const initialLoad = window.setTimeout(() => {
      void loadTickets();
    }, 0);
    return () => window.clearTimeout(initialLoad);
  }, []);

  useEffect(() => {
    if (!selectedTicket) {
      const resetTimer = window.setTimeout(() => {
        setEvents([]);
        setAssist(null);
      }, 0);
      return () => window.clearTimeout(resetTimer);
    }
    let ignore = false;
    api
      .get(`/support/tickets/${selectedTicket.id}/events`)
      .then((response) => {
        if (!ignore) setEvents(response.data);
      })
      .catch(() => {
        if (!ignore) setEvents([]);
      });
    if (selectedTicket.conversation_id) {
      api
        .get(`/support/conversations/${selectedTicket.conversation_id}/agent-assist`)
        .then((response) => {
          if (!ignore) setAssist(response.data);
        })
        .catch(() => {
          if (!ignore) setAssist(null);
        });
    } else {
      const resetAssistTimer = window.setTimeout(() => {
        if (!ignore) setAssist(null);
      }, 0);
      return () => {
        ignore = true;
        window.clearTimeout(resetAssistTimer);
      };
    }
    return () => {
      ignore = true;
    };
  }, [selectedTicket]);

  useEffect(() => {
    if (selectedId || !tickets[0]) {
      return;
    }
    const selectTimer = window.setTimeout(() => setSelectedId(tickets[0].id), 0);
    return () => window.clearTimeout(selectTimer);
  }, [selectedId, tickets]);

  const updateStatus = async (status: TicketStatus) => {
    // 更新工单状态，resolved 时自动补默认 resolution。
    if (!selectedTicket) return;
    try {
      const payload = status === 'resolved' ? { status, resolution: selectedTicket.resolution || 'Resolved by support.' } : { status };
      const response = await api.patch(`/support/tickets/${selectedTicket.id}`, payload);
      setTickets((current) => current.map((ticket) => (ticket.id === selectedTicket.id ? response.data : ticket)));
      setError('');
    } catch {
      setError('工单状态更新失败。请确认当前账号有客服权限。');
    }
  };

  const generateAssist = async () => {
    // 为当前工单生成 AI Assist，并刷新事件时间线。
    if (!selectedTicket) return;
    setIsGeneratingAssist(true);
    try {
      const response = await api.post(`/support/tickets/${selectedTicket.id}/ai-assists/generate`);
      setAssist(response.data);
      const eventsResponse = await api.get(`/support/tickets/${selectedTicket.id}/events`);
      setEvents(eventsResponse.data);
      setError('');
    } catch {
      setError('AI Assist generation failed. Please confirm support/admin permission and backend availability.');
    } finally {
      setIsGeneratingAssist(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#f4f7fb] text-slate-900">
      <RoleNav />
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-6 lg:px-8">
        <header className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <Link className="text-sm font-semibold text-[#12445f]" href="/">
                ShopMind AI
              </Link>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight">AI 客服联络中心</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
                面向售后、退款、投诉、物流异常和转人工场景，统一处理工单队列、SLA、状态流转与 AI 坐席辅助。
              </p>
            </div>
            <button
              className="rounded-lg bg-[#1d6389] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#123b5d]"
              onClick={loadTickets}
            >
              刷新队列
            </button>
          </div>
        </header>

        {error ? <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{error}</div> : null}

        <section className="grid gap-4 md:grid-cols-4">
          <MetricCard label="Open" value={metrics.open} caption="待首次处理" />
          <MetricCard label="Escalated" value={metrics.escalated} caption="已转人工/升级" />
          <MetricCard label="SLA Risk" value={metrics.overdue} caption="已超过响应窗口" />
          <MetricCard label="High Risk" value={metrics.highRisk} caption="投诉/法律/高风险" />
        </section>

        <section className="grid gap-5 xl:grid-cols-[340px_1fr_360px]">
          <aside className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">ticket queue</p>
                <h2 className="mt-1 text-lg font-semibold">工单队列</h2>
              </div>
              <span className="rounded-lg bg-[#e8f6fa] px-2.5 py-1 text-xs font-semibold text-[#12445f]">
                {visibleTickets.length}
              </span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <Select label="状态" value={statusFilter} values={statuses} onChange={(value) => setStatusFilter(value as TicketStatus | 'all')} />
              <Select label="风险" value={riskFilter} values={riskLevels} onChange={setRiskFilter} />
            </div>
            <div className="mt-4 max-h-[690px] space-y-2 overflow-y-auto pr-1">
              {isLoading ? <EmptyBox title="正在加载" body="正在同步客服工单队列。" /> : null}
              {!isLoading && visibleTickets.length === 0 ? <EmptyBox title="暂无工单" body="符合当前筛选条件的工单会显示在这里。" /> : null}
              {visibleTickets.map((ticket) => (
                <button
                  key={ticket.id}
                  className={`w-full rounded-lg border p-3 text-left transition ${
                    selectedTicket?.id === ticket.id
                      ? 'border-[#1d6389] bg-[#f3fbfd]'
                      : 'border-slate-200 bg-[#fbfcfe] hover:border-[#9bd7e7]'
                  }`}
                  onClick={() => setSelectedId(ticket.id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-[#12445f]">{ticket.ticket_id}</span>
                    <StatusBadge status={ticket.status} />
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm font-semibold leading-5 text-slate-900">{ticket.summary}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                    <span>{ticket.category}</span>
                    <span>{ticket.priority}</span>
                    <span>{ticket.channel}</span>
                  </div>
                </button>
              ))}
            </div>
          </aside>

          <section className="rounded-lg border border-slate-200 bg-white p-5">
            {selectedTicket ? (
              <>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{selectedTicket.ticket_id}</p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight">{selectedTicket.summary}</h2>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <StatusBadge status={selectedTicket.status} />
                      <ToneBadge label={selectedTicket.risk_level} tone={riskTone(selectedTicket.risk_level)} />
                      <ToneBadge label={selectedTicket.priority} tone={priorityTone(selectedTicket.priority)} />
                      {isOverdue(selectedTicket.sla_deadline, selectedTicket.status) ? <ToneBadge label="SLA overdue" tone="amber" /> : null}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <ActionButton onClick={() => updateStatus('pending')}>标记待处理</ActionButton>
                    <ActionButton onClick={() => updateStatus('escalated')}>升级</ActionButton>
                    <ActionButton primary onClick={() => updateStatus('resolved')}>
                      解决
                    </ActionButton>
                  </div>
                </div>

                <div className="mt-5 grid gap-3 md:grid-cols-3">
                  <InfoCell label="客户 ID" value={`#${selectedTicket.customer_id}`} />
                  <InfoCell label="订单" value={selectedTicket.order_id ? `#${selectedTicket.order_id}` : '未绑定'} />
                  <InfoCell label="SLA" value={formatDate(selectedTicket.sla_deadline)} />
                  <InfoCell label="SLA remaining" value={slaRemaining(selectedTicket.sla_deadline, selectedTicket.status)} />
                  <InfoCell label="Assigned agent" value={selectedTicket.assigned_agent || 'Unassigned'} />
                  <InfoCell label="Channel" value={selectedTicket.channel || 'web'} />
                </div>

                <div className="mt-5 rounded-lg border border-slate-200 bg-[#fbfcfe] p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">handoff reason</p>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{selectedTicket.handoff_reason || '暂无转人工原因。'}</p>
                </div>

                <div className="mt-5">
                  <h3 className="text-lg font-semibold">处理时间线</h3>
                  <div className="mt-3 space-y-2">
                    {events.length ? (
                      events.map((event) => <EventRow key={event.id} event={event} />)
                    ) : (
                      <EmptyBox title="暂无事件" body="创建、分派、状态变化和 AI 辅助记录会显示在这里。" />
                    )}
                  </div>
                </div>
              </>
            ) : (
              <EmptyBox title="选择一个工单" body="客服队列加载完成后，点击左侧工单查看详情。" />
            )}
          </section>

          <aside className="rounded-lg border border-slate-200 bg-white p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">agent assist</p>
                <h2 className="mt-1 text-lg font-semibold">AI 坐席辅助</h2>
              </div>
              <button
                className="rounded-lg border border-[#9bd7e7] px-3 py-2 text-xs font-semibold text-[#12445f] transition hover:bg-[#f3fbfd] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={!selectedTicket || isGeneratingAssist}
                onClick={generateAssist}
              >
                {isGeneratingAssist ? '生成中' : '生成辅助'}
              </button>
            </div>
            {assist ? (
              <div className="mt-4 space-y-4">
                <InfoCell label="用户意图" value={assist.intent || assist.user_intent || '未识别'} />
                <InfoCell label="成本路由" value={assist.routing_strategy} />
                <InfoCell label="置信度" value={`${Math.round((assist.ai_confidence || 0) * 100)}%`} />
                <InfoCell label="风险解释" value={riskExplanation(assist.risk_level, assist.routing_strategy)} />
                <div className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">推荐回复</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{assist.recommended_reply || '暂无推荐回复。'}</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">下一步建议</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{assist.next_best_action || '请先查看会话摘要和订单信息。'}</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">订单快照</p>
                  <p className="mt-2 break-words font-mono text-xs leading-5 text-slate-600">{formatOrderSnapshot(assist.order_snapshot)}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold">知识库引用</p>
                  <div className="mt-2 space-y-2">
                    {assist.knowledge_refs.length ? (
                      assist.knowledge_refs.map((ref, index) => (
                        <div key={`${ref.section}-${index}`} className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-3 text-sm">
                          <p className="font-medium text-slate-800">{ref.title || 'Support reference'}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {ref.source || 'knowledge'} / {ref.section || 'general'}
                          </p>
                        </div>
                      ))
                    ) : (
                      <EmptyBox title="暂无引用" body="RAG 或政策命中后会在这里展示来源。" />
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-4">
                <EmptyBox title="暂无 AI 辅助" body="点击“生成辅助”后，会基于工单摘要、订单快照、风险等级和成本路由生成推荐回复。" />
              </div>
            )}
          </aside>
        </section>
      </div>
    </main>
  );
}

function Select({ label, value, values, onChange }: { label: string; value: string; values: string[]; onChange: (value: string) => void }) {
  // 筛选下拉控件。
  return (
    <label className="text-xs font-medium text-slate-500">
      {label}
      <select
        className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm font-semibold text-slate-700"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {values.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
    </label>
  );
}

function MetricCard({ label, value, caption }: { label: string; value: number; caption: string }) {
  // 客服指标卡片。
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">{value}</p>
      <p className="mt-2 text-xs text-slate-500">{caption}</p>
    </article>
  );
}

function StatusBadge({ status }: { status: TicketStatus }) {
  // 工单状态徽标。
  const tone = status === 'resolved' ? 'emerald' : status === 'escalated' ? 'amber' : status === 'pending' ? 'cyan' : 'slate';
  return <ToneBadge label={status} tone={tone} />;
}

function ToneBadge({ label, tone }: { label: string; tone: 'slate' | 'cyan' | 'amber' | 'emerald' }) {
  // 通用色彩徽标。
  const classes = {
    slate: 'bg-slate-100 text-slate-700',
    cyan: 'bg-[#e8f6fa] text-[#12445f]',
    amber: 'bg-amber-50 text-amber-800',
    emerald: 'bg-emerald-50 text-emerald-700',
  };
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${classes[tone]}`}>{label}</span>;
}

function InfoCell({ label, value }: { label: string; value: string }) {
  // 工单详情信息块。
  return (
    <div className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 break-words text-sm font-semibold text-slate-800">{value}</p>
    </div>
  );
}

function ActionButton({ children, primary, onClick }: { children: React.ReactNode; primary?: boolean; onClick: () => void }) {
  // 工单状态操作按钮。
  return (
    <button
      className={
        primary
          ? 'rounded-lg bg-[#1d6389] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[#123b5d]'
          : 'rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[#9bd7e7] hover:bg-[#f3fbfd]'
      }
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function EventRow({ event }: { event: TicketEvent }) {
  // 工单事件时间线行。
  return (
    <div className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-slate-800">{event.event_type}</p>
        <p className="text-xs text-slate-500">{formatDate(event.created_at)}</p>
      </div>
      {event.from_status || event.to_status ? (
        <p className="mt-1 text-xs text-slate-500">
          {event.from_status || 'new'} → {event.to_status || 'updated'}
        </p>
      ) : null}
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

function riskTone(risk: string) {
  // 风险等级到徽标色彩的映射。
  if (risk === 'high') return 'amber';
  if (risk === 'medium') return 'cyan';
  return 'slate';
}

function priorityTone(priority: string) {
  // 优先级到徽标色彩的映射。
  if (priority === 'urgent' || priority === 'high') return 'amber';
  if (priority === 'normal') return 'cyan';
  return 'slate';
}

function isOverdue(value?: string | null, status?: string) {
  // SLA 是否逾期，resolved 工单不再计入逾期。
  if (!value || status === 'resolved') return false;
  return new Date(value).getTime() < Date.now();
}

function slaRemaining(value?: string | null, status?: string) {
  // SLA 剩余/逾期时间格式化。
  if (!value) return 'No SLA';
  if (status === 'resolved') return 'Closed';
  const delta = new Date(value).getTime() - Date.now();
  const abs = Math.abs(delta);
  const hours = Math.floor(abs / 36e5);
  const minutes = Math.floor((abs % 36e5) / 6e4);
  const label = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
  return delta < 0 ? `Overdue ${label}` : `${label} left`;
}

function riskExplanation(riskLevel: string, routingStrategy: string) {
  // 用简短说明解释 AI Assist 的风险和路由策略。
  if (riskLevel === 'high') return 'High risk: keep human ownership and avoid refund/legal commitments.';
  if (routingStrategy === 'agent_workflow') return 'Complex after-sales case: combine order lookup, policy RAG, and support review.';
  if (routingStrategy === 'sql_cache') return 'Low-cost path: answer from database or cache before invoking an LLM.';
  if (routingStrategy === 'rag') return 'Policy path: answer from knowledge references with limited generation.';
  return 'Standard support path.';
}

function formatOrderSnapshot(snapshot: Record<string, unknown>) {
  // 订单快照格式化，空快照用占位说明。
  if (!snapshot || Object.keys(snapshot).length === 0) return 'No linked order snapshot';
  return JSON.stringify(snapshot);
}

function formatDate(value?: string | null) {
  // 日期显示统一走中文本地化。
  if (!value) return '暂无';
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}
