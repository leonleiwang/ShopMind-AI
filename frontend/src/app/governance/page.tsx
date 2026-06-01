'use client';

// Governance 页面：展示高风险审批队列、AI 草稿审核、人工通过/拒绝和审计日志。
import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import { api } from '@/services/api';
import { useAuthStore } from '@/store/auth';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ReactNode, useCallback, useEffect, useMemo, useState } from 'react';

type Approval = {
  id: number;
  action_type: string;
  status: string;
  risk_level: string;
  risk_reasons: string[];
  summary: string;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  created_at?: string;
};

type AuditLog = {
  id: number;
  approval_id: number;
  event: string;
  details: Record<string, unknown>;
  created_at?: string;
};

export default function GovernancePage() {
  // 风控治理页仅允许 admin 访问。
  return (
    <RoleGuard allowed={['admin']}>
      <GovernanceContent />
    </RoleGuard>
  );
}

function GovernanceContent() {
  // 管理审批列表、审计日志、登录态和审批操作状态。
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState<number | null>(null);
  const token = useAuthStore((s) => s.token);
  const hasHydrated = useAuthStore((s) => s.hasHydrated);
  const hydrate = useAuthStore((s) => s.hydrate);
  const router = useRouter();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (hasHydrated && !token) {
      router.replace('/login');
    }
  }, [hasHydrated, router, token]);

  const pendingCount = useMemo(() => approvals.filter((item) => item.status === 'pending').length, [approvals]);
  const highRiskCount = useMemo(() => approvals.filter((item) => item.risk_level === 'high').length, [approvals]);

  const loadGovernance = useCallback(async () => {
    // 加载治理后台审批队列和审计日志。
    try {
      const [approvalRes, auditRes] = await Promise.all([
        api.get('/approvals/', { params: { limit: 40, scope: 'governance' } }),
        api.get('/approvals/audit', { params: { limit: 60 } }),
      ]);
      setApprovals(approvalRes.data);
      setAuditLogs(auditRes.data);
      setError('');
    } catch {
      setError('风控治理数据加载失败：请确认已登录且后端服务可访问。');
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    const initialTimer = window.setTimeout(() => {
      void loadGovernance();
    }, 0);
    const timer = window.setInterval(() => {
      void loadGovernance();
    }, 7000);
    return () => {
      window.clearTimeout(initialTimer);
      window.clearInterval(timer);
    };
  }, [loadGovernance, token]);

  const review = async (approvalId: number, decision: 'approve' | 'reject') => {
    // 执行通过/拒绝操作，完成后刷新队列和审计信息。
    setBusyId(approvalId);
    try {
      await api.post(`/approvals/${approvalId}/${decision}`, { note: `governance_page_${decision}` });
      await loadGovernance();
      setError('');
    } catch {
      setError('审批操作失败：该审批可能已经被处理，或订单草稿生成后购物车内容发生变化。');
    } finally {
      setBusyId(null);
    }
  };

  if (!hasHydrated || !token) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#f4f7fb] text-slate-700">
        <div className="rounded-lg border border-slate-200 bg-white px-5 py-4 text-sm shadow-sm">正在加载风控治理台...</div>
      </main>
    );
  }

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
              <span className="block text-xs text-sky-100/75">AgentOps 风控治理</span>
            </span>
          </Link>
          <nav className="flex items-center gap-2 text-sm">
            <Link className="hidden rounded-lg px-3 py-2 text-sky-50 hover:bg-white/10 md:inline" href="/chat">
              Chat 主界面
            </Link>
            <Link className="hidden rounded-lg px-3 py-2 text-sky-50 hover:bg-white/10 md:inline" href="/dashboard">
              工程观测
            </Link>
            <button
              className="rounded-lg bg-[#ffca45] px-3 py-2 font-semibold text-[#102033] hover:bg-[#ffd873]"
              onClick={loadGovernance}
            >
              刷新
            </button>
          </nav>
        </div>
      </header>
      <RoleNav />

      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-6 lg:px-8">
        <section className="grid gap-4 md:grid-cols-3">
          <Metric label="待处理审批" value={pendingCount.toString()} caption="需要人工处理" />
          <Metric label="高风险请求" value={highRiskCount.toString()} caption="金额 / 数量 / 异常规则" />
          <Metric label="审计事件" value={auditLogs.length.toString()} caption="审批与拒绝轨迹" />
        </section>

        {error ? <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{error}</div> : null}

        <section className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
          <Panel title="审批队列" eyebrow="关键动作风控">
            <div className="grid gap-3">
              {approvals.length ? (
                approvals.map((approval) => (
                  <ApprovalCard
                    key={approval.id}
                    approval={approval}
                    busy={busyId === approval.id}
                    onApprove={() => review(approval.id, 'approve')}
                    onReject={() => review(approval.id, 'reject')}
                  />
                ))
              ) : (
                <Empty title="暂无审批" body="高风险订单和 AI 运营草稿会出现在这里。" />
              )}
            </div>
          </Panel>

          <Panel title="审计日志" eyebrow="审批 / 拒绝 / 执行历史">
            <div className="max-h-[680px] space-y-2 overflow-y-auto pr-1">
              {auditLogs.length ? (
                auditLogs.map((log) => (
                  <article key={log.id} className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                        {log.event}
                      </span>
                      <span className="text-xs text-slate-500">#{log.approval_id}</span>
                    </div>
                    <pre className="mt-3 whitespace-pre-wrap break-words text-xs leading-5 text-slate-500">
                      {JSON.stringify(log.details, null, 2)}
                    </pre>
                  </article>
                ))
              ) : (
                <Empty title="暂无审计事件" body="审批动作会生成可追踪的审计记录。" />
              )}
            </div>
          </Panel>
        </section>
      </div>
    </main>
  );
}

function ApprovalCard({
  approval,
  busy,
  onApprove,
  onReject,
}: {
  approval: Approval;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  // 单个审批卡片，展示风险、原因、payload/result，并提供通过/拒绝动作。
  const pending = approval.status === 'pending';
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-[#e8f6fa] px-2.5 py-1 text-xs font-semibold text-[#12445f]">
              {approval.action_type}
            </span>
            <StatusBadge status={approval.status} />
            <RiskBadge risk={approval.risk_level} />
          </div>
          <h2 className="mt-3 text-lg font-semibold text-slate-900">审批 #{approval.id}</h2>
          <p className="mt-1 text-sm text-slate-500">{approval.risk_reasons.join(', ') || '标准审核'}</p>
        </div>
        {pending ? (
          <div className="flex gap-2">
            <button
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50"
              disabled={busy}
              onClick={onReject}
            >
              拒绝
            </button>
            <button
              className="rounded-lg bg-[#1d6389] px-3 py-2 text-sm font-semibold text-white hover:bg-[#123b5d] disabled:opacity-50"
              disabled={busy}
              onClick={onApprove}
            >
              通过
            </button>
          </div>
        ) : null}
      </div>
      <pre className="mt-4 whitespace-pre-wrap break-words rounded-lg border border-slate-200 bg-[#fbfcfe] p-3 text-xs leading-5 text-slate-600">
        {approval.summary}
      </pre>
      {Object.keys(approval.result || {}).length ? (
        <pre className="mt-3 whitespace-pre-wrap break-words rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs leading-5 text-emerald-800">
          {JSON.stringify(approval.result, null, 2)}
        </pre>
      ) : null}
    </article>
  );
}

function Metric({ label, value, caption }: { label: string; value: string; caption: string }) {
  // 风控指标卡片。
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">{value}</div>
      <div className="mt-2 text-xs text-slate-500">{caption}</div>
    </article>
  );
}

function Panel({ title, eyebrow, children }: { title: string; eyebrow: string; children: ReactNode }) {
  // Governance 通用区块容器。
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{eyebrow}</p>
      <h1 className="mt-1 mb-4 text-lg font-semibold text-slate-900">{title}</h1>
      {children}
    </section>
  );
}

function StatusBadge({ status }: { status: string }) {
  // 审批状态徽标。
  const color = status === 'pending' ? 'bg-amber-50 text-amber-800' : 'bg-emerald-50 text-emerald-700';
  const label: Record<string, string> = {
    pending: '待处理',
    rejected: '已拒绝',
    executed: '已执行',
    approved: '已通过',
  };
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${color}`}>{label[status] ?? status}</span>;
}

function RiskBadge({ risk }: { risk: string }) {
  // 风险等级徽标。
  const color = risk === 'high' ? 'bg-rose-50 text-rose-700' : risk === 'medium' ? 'bg-sky-50 text-sky-700' : 'bg-slate-100 text-slate-600';
  const label: Record<string, string> = {
    high: '高风险',
    medium: '中风险',
    low: '低风险',
  };
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${color}`}>{label[risk] ?? risk}</span>;
}

function Empty({ title, body }: { title: string; body: string }) {
  // 空状态提示。
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-[#fbfcfe] p-4">
      <p className="text-sm font-medium text-slate-700">{title}</p>
      <p className="mt-1 text-sm leading-6 text-slate-500">{body}</p>
    </div>
  );
}
