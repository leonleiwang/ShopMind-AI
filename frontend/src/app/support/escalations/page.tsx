'use client';

// 异常升级队列页面：聚合高风险、投诉/法务、紧急优先级和 SLA 逾期工单。
import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import { api } from '@/services/api';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

type EscalationTicket = {
  id: number;
  ticket_id: string;
  customer_id: number;
  category: string;
  priority: string;
  status: string;
  summary: string;
  risk_level: string;
  handoff_reason: string;
  sla_deadline?: string | null;
  created_at?: string | null;
};

export default function SupportEscalationsPage() {
  // 升级队列仅允许 support/admin 查看。
  return (
    <RoleGuard allowed={['support', 'admin']}>
      <EscalationsContent />
    </RoleGuard>
  );
}

function EscalationsContent() {
  // 加载全部工单后在前端筛选出需要优先处理的升级事项。
  const [tickets, setTickets] = useState<EscalationTicket[]>([]);
  const [error, setError] = useState('');

  const loadTickets = async () => {
    // 刷新客服工单列表。
    try {
      const response = await api.get('/support/tickets', { params: { limit: 100 } });
      setTickets(response.data);
      setError('');
    } catch {
      setTickets([]);
      setError('升级队列加载失败。请确认 support/admin 权限和后端服务状态。');
    }
  };

  useEffect(() => {
    const initialLoad = window.setTimeout(() => {
      void loadTickets();
    }, 0);
    return () => window.clearTimeout(initialLoad);
  }, []);

  const escalations = useMemo(
    () =>
      tickets.filter(
        (ticket) =>
          ticket.status === 'escalated' ||
          ticket.risk_level === 'high' ||
          ticket.priority === 'urgent' ||
          ticket.category === 'complaint' ||
          ticket.category === 'legal',
      ),
    [tickets],
  );
  const overdue = useMemo(() => escalations.filter((ticket) => isOverdue(ticket.sla_deadline, ticket.status)).length, [escalations]);

  return (
    <main className="min-h-screen bg-[#f4f7fb] text-slate-900">
      <RoleNav />
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-6 lg:px-8">
        <header className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <Link className="text-sm font-semibold text-[#12445f]" href="/support/conversations">
                Contact Center
              </Link>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight">异常升级队列</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
                聚合投诉、法律风险、紧急优先级、SLA 超时和已转人工工单，便于资深客服或管理员快速接管。
              </p>
            </div>
            <button
              className="rounded-lg bg-[#1d6389] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#123b5d]"
              onClick={loadTickets}
            >
              刷新
            </button>
          </div>
        </header>

        {error ? <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{error}</div> : null}

        <section className="grid gap-4 md:grid-cols-3">
          <Metric label="升级工单" value={escalations.length} caption="高风险和人工接管" />
          <Metric label="SLA 超时" value={overdue} caption="需要立即处理" />
          <Metric label="投诉/法律" value={escalations.filter((ticket) => ['complaint', 'legal'].includes(ticket.category)).length} caption="避免过度承诺" />
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">priority queue</p>
              <h2 className="mt-1 text-lg font-semibold">待处理升级事项</h2>
            </div>
            <Link className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:border-[#9bd7e7]" href="/support/conversations">
              返回联络中心
            </Link>
          </div>

          <div className="mt-5 grid gap-3">
            {escalations.length ? (
              escalations.map((ticket) => (
                <Link
                  key={ticket.id}
                  className="grid gap-4 rounded-lg border border-slate-200 bg-[#fbfcfe] p-4 transition hover:border-[#9bd7e7] md:grid-cols-[1fr_auto]"
                  href="/support/conversations"
                >
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold text-[#12445f]">{ticket.ticket_id}</span>
                      <Badge label={ticket.status} />
                      <Badge label={ticket.risk_level} warn={ticket.risk_level === 'high'} />
                      {isOverdue(ticket.sla_deadline, ticket.status) ? <Badge label="SLA overdue" warn /> : null}
                    </div>
                    <p className="mt-2 font-semibold text-slate-900">{ticket.summary}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-500">{ticket.handoff_reason || '暂无升级原因。'}</p>
                  </div>
                  <div className="text-left md:text-right">
                    <p className="text-sm font-semibold text-slate-800">{ticket.category}</p>
                    <p className="mt-1 text-xs text-slate-500">Customer #{ticket.customer_id}</p>
                    <p className="mt-1 text-xs text-slate-500">SLA {formatDate(ticket.sla_deadline)}</p>
                  </div>
                </Link>
              ))
            ) : (
              <EmptyBox title="暂无升级事项" body="当出现投诉、退款风险、法律风险、工具失败或 SLA 超时时，这里会形成集中处理队列。" />
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value, caption }: { label: string; value: number; caption: string }) {
  // 升级队列指标卡片。
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">{value}</p>
      <p className="mt-2 text-xs text-slate-500">{caption}</p>
    </article>
  );
}

function Badge({ label, warn }: { label: string; warn?: boolean }) {
  // 状态/风险徽标。
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${warn ? 'bg-amber-50 text-amber-800' : 'bg-[#e8f6fa] text-[#12445f]'}`}>
      {label}
    </span>
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

function isOverdue(value?: string | null, status?: string) {
  // SLA 是否逾期，resolved 工单不计入。
  if (!value || status === 'resolved') return false;
  return new Date(value).getTime() < Date.now();
}

function formatDate(value?: string | null) {
  // 日期显示统一走中文本地化。
  if (!value) return '暂无';
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}
