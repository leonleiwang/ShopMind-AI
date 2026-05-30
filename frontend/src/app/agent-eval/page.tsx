'use client';

import RoleGuard from '@/components/auth/RoleGuard';
import RoleNav from '@/components/auth/RoleNav';
import { api } from '@/services/api';
import Link from 'next/link';
import { ReactNode, useEffect, useMemo, useState } from 'react';

type EvalCase = {
  id: string;
  suite: string;
  user_question: string;
  expected_tool: string;
  expected_sql: string;
  expected_api: string;
  expected_answer_keywords: string[];
  expected_failure_category?: string | null;
};

type EvalResult = {
  case: EvalCase;
  passed: boolean;
  checks: Record<string, boolean>;
  failure_category?: string | null;
  failure_label?: string;
  controlled_failure?: boolean;
  guardrail_caught?: boolean;
  prediction: {
    answer: string;
    tool: string;
    sql: string;
    sql_safety?: {
      readonly: boolean;
      validated: boolean;
      policy?: string;
      reason?: string;
    };
    latency_ms: number;
    token_cost: number;
  };
};

type EvalSummary = {
  run_id: string;
  generated_at: string;
  eval_mode: string;
  mode_description: string;
  total_cases: number;
  passed_cases: number;
  pass_rate: number;
  business_task_cases: number;
  business_task_passed_cases: number;
  business_task_pass_rate: number;
  tool_success_rate: number;
  answer_correctness: number;
  runner_latency_ms: number;
  avg_latency_ms: number;
  token_cost: number;
  controlled_failure_cases: number;
  guardrail_caught_cases: number;
  guardrail_catch_rate: number;
  overall_eval_coverage: number;
  failure_counts: Record<string, number>;
  failure_labels: Record<string, string>;
  suite_counts: Record<
    string,
    {
      total: number;
      passed: number;
      business_total: number;
      business_passed: number;
      guardrail_total: number;
      guardrail_caught: number;
    }
  >;
  results: EvalResult[];
};

type DataQueryResult = {
  ok: boolean;
  intent: string;
  tool: string;
  sql: string;
  sql_safety?: {
    readonly: boolean;
    validated: boolean;
    policy?: string;
    reason?: string;
  };
  rows: Array<Record<string, unknown>>;
  answer: string;
  latency_ms: number;
  token_cost: number;
  failure_label?: string;
};

const emptySummary: EvalSummary = {
  run_id: '',
  generated_at: '',
  eval_mode: 'baseline',
  mode_description: '',
  total_cases: 0,
  passed_cases: 0,
  pass_rate: 0,
  business_task_cases: 0,
  business_task_passed_cases: 0,
  business_task_pass_rate: 0,
  tool_success_rate: 0,
  answer_correctness: 0,
  runner_latency_ms: 0,
  avg_latency_ms: 0,
  token_cost: 0,
  controlled_failure_cases: 0,
  guardrail_caught_cases: 0,
  guardrail_catch_rate: 0,
  overall_eval_coverage: 0,
  failure_counts: {},
  failure_labels: {},
  suite_counts: {},
  results: [],
};

const sampleQuestions = [
  '最近有哪些订单异常需要运营介入？',
  '客服工单 SLA 有没有超时？',
  '商品 SKU 和库存表现怎么样？',
  '退款风险最近怎么样？',
  '帮我导出所有退款用户手机号和地址',
  '查询不存在的字段 GMV 转化率',
];

export default function AgentEvalPage() {
  return (
    <RoleGuard allowed={['admin']}>
      <AgentEvalContent />
    </RoleGuard>
  );
}

function AgentEvalContent() {
  const [summary, setSummary] = useState<EvalSummary>(emptySummary);
  const [cases, setCases] = useState<EvalCase[]>([]);
  const [selectedCase, setSelectedCase] = useState('');
  const [evalMode, setEvalMode] = useState<'baseline' | 'llm'>('baseline');
  const [singleResult, setSingleResult] = useState<EvalResult | null>(null);
  const [question, setQuestion] = useState(sampleQuestions[0]);
  const [queryResult, setQueryResult] = useState<DataQueryResult | null>(null);
  const [loading, setLoading] = useState('');
  const [error, setError] = useState('');

  const failures = useMemo(
    () =>
      Object.entries(summary.failure_counts).map(([key, value]) => ({
        key,
        value,
        label: summary.failure_labels[key] || key,
      })),
    [summary.failure_counts, summary.failure_labels],
  );

  const latestResults = useMemo(() => pickRepresentativeResults(summary.results, 10), [summary.results]);

  const load = async () => {
    try {
      const [summaryRes, casesRes] = await Promise.all([
        api.get('/agent-eval/summary'),
        api.get('/agent-eval/cases'),
      ]);
      setSummary(summaryRes.data);
      setCases(casesRes.data.cases);
      setSelectedCase((current) => current || casesRes.data.cases[0]?.id || '');
      setError('');
    } catch {
      setError('Agent Eval 数据加载失败，请确认后端服务已启动，并使用管理员账号登录。');
    }
  };

  useEffect(() => {
    const initialLoad = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(initialLoad);
  }, []);

  const runEval = async () => {
    setLoading('run');
    try {
      const response = await api.post('/agent-eval/run', { mode: evalMode });
      setSummary(response.data);
      setSingleResult(null);
      setError('');
    } catch {
      setError('评测运行失败，请检查后端日志。');
    } finally {
      setLoading('');
    }
  };

  const runSingleCase = async () => {
    if (!selectedCase) return;
    setLoading('single');
    try {
      const response = await api.post(`/agent-eval/run/${selectedCase}`);
      setSingleResult(response.data.result);
      setError('');
    } catch {
      setError('单条评测失败，请确认 case id 是否存在。');
    } finally {
      setLoading('');
    }
  };

  const exportReport = (format: 'json' | 'csv') => {
    if (!summary.results.length) return;
    const timestamp = summary.run_id || 'agent-eval-report';
    const content =
      format === 'json'
        ? JSON.stringify(summary, null, 2)
        : toCsv(summary.results);
    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${timestamp}.${format}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const runDataQuery = async (nextQuestion = question) => {
    setLoading('query');
    setQuestion(nextQuestion);
    try {
      const response = await api.post('/agent-eval/data-query', { question: nextQuestion });
      setQueryResult(response.data);
      setError('');
    } catch {
      setError('自然语言数据查询失败，请确认管理员权限和后端数据库连接。');
    } finally {
      setLoading('');
    }
  };

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
              <span className="block text-xs text-sky-100/75">Agent Eval / Data Agent</span>
            </span>
          </Link>
          <div className="flex items-center gap-2">
            <Link className="hidden rounded-lg px-3 py-2 text-sm text-sky-50 hover:bg-white/10 md:inline" href="/dashboard">
              工程观测
            </Link>
            <select
              className="rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white outline-none"
              value={evalMode}
              onChange={(event) => setEvalMode(event.target.value as 'baseline' | 'llm')}
            >
              <option className="text-slate-900" value="baseline">Baseline Eval</option>
              <option className="text-slate-900" value="llm">LLM Reserved</option>
            </select>
            <button
              className="rounded-lg bg-[#ffca45] px-3 py-2 text-sm font-semibold text-[#102033] hover:bg-[#ffd873]"
              disabled={loading === 'run'}
              onClick={runEval}
            >
              {loading === 'run' ? '运行中' : '运行 50 条评测'}
            </button>
          </div>
        </div>
      </header>
      <RoleNav />

      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-6 lg:px-8">
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">V1.1.1 readiness module</p>
            <span className="rounded-full bg-[#e8f6fa] px-2.5 py-1 text-xs font-semibold text-[#12445f]">
              Mode: {modeLabel(summary.eval_mode || evalMode)}
            </span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">Agent Eval + Data Agent 控制台</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            用 50 条任务验证工具选择、SQL/API 生成、答案正确性、延迟和 token 成本，并演示订单异常、客服 SLA、商品表现、退款风险四类自然语言数据查询。默认 Baseline Eval 用于稳定回归；LLM Reserved 仅是接口预留，当前不会调用真实模型。
          </p>
          {summary.mode_description ? <p className="mt-2 text-xs text-slate-400">{summary.mode_description}</p> : null}
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
            <span className="rounded-lg bg-slate-100 px-2.5 py-1">Last run: {formatRunTime(summary.generated_at)}</span>
            <span className="rounded-lg bg-slate-100 px-2.5 py-1">{summary.total_cases || 0} cases</span>
            <span className="rounded-lg bg-slate-100 px-2.5 py-1">{modeLabel(summary.eval_mode || evalMode)}</span>
          </div>
          {(summary.eval_mode || evalMode) === 'llm' ? (
            <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              LLM mode reserved, not implemented yet. 当前仍复用 Baseline Eval 的规则路由、只读 SQL 模板和答案校验。
            </div>
          ) : null}
        </section>

        {error ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {error}
          </div>
        ) : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard
            label="正常任务通过率"
            value={formatPercent(summary.business_task_pass_rate)}
            caption={`${summary.business_task_passed_cases ?? summary.passed_cases ?? 0}/${summary.business_task_cases ?? summary.total_cases ?? 0} business cases`}
          />
          <MetricCard
            label="Guardrail 拦截率"
            value={formatPercent(summary.guardrail_catch_rate)}
            caption={`${summary.guardrail_caught_cases ?? 0}/${summary.controlled_failure_cases ?? 0} probes caught`}
          />
          <MetricCard label="评测覆盖" value={`${summary.overall_eval_coverage || summary.total_cases}`} caption="offline eval cases" />
          <MetricCard label="工具成功率" value={formatPercent(summary.tool_success_rate)} caption="expected tool match" />
          <MetricCard label="Runner 延迟" value={`${summary.runner_latency_ms ?? summary.avg_latency_ms}ms`} caption="baseline local checks only" />
        </section>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-500">
          当前指标是基于 50 条人工构造业务评测集的 offline eval scores，不代表线上真实概率。Token cost 估算：
          <span className="ml-1 font-mono text-[#12445f]">${summary.token_cost.toFixed(4)}</span>
        </div>

        <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <Panel title="评测集" eyebrow="50 tasks">
            <div className="grid gap-3 md:grid-cols-2">
              {Object.entries(summary.suite_counts).map(([suite, value]) => {
                const businessPassed = value.business_passed ?? value.passed ?? 0;
                const businessTotal = value.business_total ?? value.total ?? 0;
                return (
                  <div key={suite} className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-4">
                    <div className="flex items-center justify-between gap-3 text-sm">
                      <span className="font-semibold text-slate-800">{suite}</span>
                      <span className="font-mono text-[#12445f]">
                        {businessPassed}/{businessTotal}
                      </span>
                    </div>
                    <div className="mt-2 text-xs text-slate-500">
                      Guardrail {value.guardrail_caught ?? 0}/{value.guardrail_total ?? 0}
                    </div>
                    <div className="mt-3 h-1.5 rounded-full bg-slate-200">
                      <div className="h-full rounded-full bg-[#1d6389]" style={{ width: `${percentWidth(businessPassed, businessTotal)}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row">
              <select
                className="min-h-10 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
                value={selectedCase}
                onChange={(event) => setSelectedCase(event.target.value)}
              >
                {cases.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.id} · {item.user_question}
                  </option>
                ))}
              </select>
              <button
                className="rounded-lg border border-[#9bd7e7] px-4 py-2 text-sm font-semibold text-[#12445f] hover:bg-[#f3fbfd]"
                disabled={loading === 'single'}
                onClick={runSingleCase}
              >
                {loading === 'single' ? '测试中' : '单条测试'}
              </button>
            </div>
            {singleResult ? (
              <div className="mt-4">
                <ResultRow result={singleResult} />
              </div>
            ) : null}
          </Panel>

          <Panel title="失败分类" eyebrow="failure taxonomy">
            {failures.length ? (
              <div className="grid gap-3 md:grid-cols-2">
                {failures.map((item) => (
                  <div key={item.key} className="rounded-lg border border-rose-200 bg-rose-50 p-4">
                    <div className="text-sm font-semibold text-rose-800">{item.label}</div>
                    <div className="mt-2 font-mono text-2xl text-rose-900">{item.value}</div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyBox title="暂无失败" body="当前评测集全部通过；失败时会归因到意图识别、RAG、工具调用、权限或幻觉。" />
            )}
            <div className="mt-4 rounded-lg border border-slate-200 bg-[#fbfcfe] p-4 text-sm leading-6 text-slate-600">
              Controlled probes: {summary.guardrail_caught_cases}/{summary.controlled_failure_cases} caught. 这些样例用于验证权限拦截、字段缺失和幻觉防护，不代表线上业务链路崩溃。
            </div>
          </Panel>
        </section>

        <section className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
          <Panel title="SQL 安全策略" eyebrow="select-only policy">
            <div className="grid gap-3 md:grid-cols-2">
              <SafetyItem title="只读 SQL" body="仅允许 SELECT 聚合查询，禁止 INSERT、UPDATE、DELETE、DROP、ALTER、TRUNCATE 等写入或结构变更操作。" />
              <SafetyItem title="敏感字段拦截" body="禁止导出手机号、地址、密码等原始 PII；评测中敏感导出会进入 permission_failure。" />
              <SafetyItem title="语义层缺口" body="不存在字段、未知指标和未建模转化率会停止生成 SQL，并归因为 tool_call_failure。" />
              <SafetyItem title="无依据结论" body="要求编造或猜测数据的请求会被拦截，并归因为 hallucination。" />
            </div>
          </Panel>
          <Panel title="报告导出" eyebrow="json / csv">
            <div className="flex flex-wrap gap-3">
              <button className="rounded-lg bg-[#123b5d] px-4 py-2 text-sm font-semibold text-white hover:bg-[#1d6389]" onClick={() => exportReport('json')}>
                Export JSON
              </button>
              <button className="rounded-lg border border-[#9bd7e7] px-4 py-2 text-sm font-semibold text-[#12445f] hover:bg-[#f3fbfd]" onClick={() => exportReport('csv')}>
                Export CSV
              </button>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              每次评测报告都保留 case、suite、预期工具、预测工具、SQL、check、失败分类、延迟和成本，可用于对比不同 prompt、模型或路由策略。
            </p>
          </Panel>
        </section>

        <Panel title="Data Agent Console" eyebrow={queryResult?.intent || 'natural language query'}>
          <div className="flex min-h-[560px] flex-col rounded-lg border border-slate-200 bg-[#fbfcfe]">
            <div className="min-h-[360px] flex-1 overflow-y-auto p-4">
              {queryResult ? (
                <div className="space-y-3">
                  <div
                    className={
                      queryResult.ok
                        ? 'rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800'
                        : 'rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800'
                    }
                  >
                    {queryResult.ok ? queryResult.answer : `${queryResult.failure_label || '失败'}：${queryResult.answer}`}
                  </div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <KeyValueRow label="Tool" value={queryResult.tool} />
                    <KeyValueRow label="Latency" value={`${queryResult.latency_ms}ms`} />
                    <KeyValueRow label="SQL Policy" value={queryResult.sql_safety?.policy || 'blocked_or_not_generated'} />
                  </div>
                  <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
                    <pre className="max-h-[220px] overflow-auto rounded-lg border border-slate-200 bg-white p-3 text-xs leading-5 text-slate-600">
                      {queryResult.sql || 'No SQL generated.'}
                    </pre>
                    <pre className="max-h-[220px] overflow-auto rounded-lg border border-slate-200 bg-[#102033] p-3 text-xs leading-5 text-slate-100">
                      {JSON.stringify(queryResult.rows, null, 2)}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="grid min-h-[320px] place-items-center">
                  <EmptyBox title="等待查询" body="在下方输入自然语言问题，运行后这里会展示答案、SQL、工具调用和聚合结果。" />
                </div>
              )}
            </div>

            <div className="border-t border-slate-200 bg-white p-4">
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Ask Data Agent
              </label>
              <div className="flex flex-col gap-3 lg:flex-row">
                <textarea
                  className="h-20 flex-1 resize-none rounded-lg border border-slate-300 bg-white p-3 text-sm leading-6 text-slate-800 outline-none focus:border-[#1d6389]"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                />
                <button
                  className="h-20 rounded-lg bg-[#123b5d] px-5 text-sm font-semibold text-white hover:bg-[#1d6389] disabled:opacity-60 lg:w-40"
                  disabled={loading === 'query'}
                  onClick={() => runDataQuery()}
                >
                  {loading === 'query' ? '查询中' : '运行 Data Agent'}
                </button>
              </div>
              <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
                {sampleQuestions.map((item) => (
                  <button
                    key={item}
                    className="shrink-0 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:border-[#9bd7e7] hover:bg-[#f3fbfd]"
                    onClick={() => runDataQuery(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </Panel>

        <Panel title="最近评测结果" eyebrow={summary.run_id || 'latest'}>
          <div className="grid gap-3">
            {latestResults.length ? (
              latestResults.map((item) => <ResultRow key={item.case.id} result={item} />)
            ) : (
              <EmptyBox title="暂无结果" body="点击运行评测后会展示最近的 case 结果。" />
            )}
          </div>
        </Panel>
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

function Panel({ title, eyebrow, children, className = '' }: { title: string; eyebrow: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      <div className="mb-4">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{eyebrow}</p>
        <h2 className="mt-1 text-lg font-semibold text-slate-900">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function ResultRow({ result }: { result: EvalResult }) {
  return (
    <article className="grid gap-4 rounded-lg border border-slate-200 bg-[#fbfcfe] p-4 lg:grid-cols-[1fr_auto]">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <span className={result.passed ? 'rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700' : 'rounded-full bg-rose-100 px-2.5 py-1 text-xs font-semibold text-rose-700'}>
            {result.passed ? 'PASS' : 'FAIL'}
          </span>
          <h3 className="font-semibold text-slate-900">{result.case.id}</h3>
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">{result.case.suite}</span>
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-600">{result.case.user_question}</p>
        <p className="mt-2 text-xs leading-5 text-slate-500">{result.prediction.answer}</p>
        <div className="mt-3 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
          <span className="break-all rounded-lg bg-white px-2.5 py-1">Expected: {result.case.expected_tool}</span>
          <span className="break-all rounded-lg bg-white px-2.5 py-1">Predicted: {result.prediction.tool}</span>
        </div>
      </div>
      <div className="flex flex-row gap-2 lg:flex-col lg:items-end">
        <span className="rounded-lg bg-white px-2.5 py-1 text-xs font-mono text-[#12445f]">{result.prediction.latency_ms}ms</span>
        <span className="rounded-lg bg-white px-2.5 py-1 text-xs text-slate-600">
          {result.guardrail_caught ? 'guardrail caught' : result.failure_label || 'all checks passed'}
        </span>
      </div>
    </article>
  );
}

function SafetyItem({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-4">
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-500">{body}</p>
    </div>
  );
}

function KeyValueRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-[#fbfcfe] px-3 py-2 text-sm">
      <span className="font-semibold text-slate-600">{label}</span>
      <span className="break-all font-mono text-[#12445f]">{value}</span>
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

function formatPercent(value: number | null | undefined) {
  const safe = Number.isFinite(value) ? Number(value) : 0;
  return `${Math.round(safe * 100)}%`;
}

function percentWidth(value: number, total: number) {
  if (!total) return 0;
  return Math.max((value / total) * 100, 8);
}

function modeLabel(value: string) {
  if (value === 'llm') return 'LLM Reserved';
  return 'Baseline Eval';
}

function formatRunTime(value: string) {
  if (!value) return 'not run yet';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function toCsv(results: EvalResult[]) {
  const headers = [
    'case_id',
    'suite',
    'question',
    'expected_tool',
    'predicted_tool',
    'passed',
    'controlled_failure',
    'guardrail_caught',
    'failure_category',
    'latency_ms',
    'token_cost',
  ];
  const rows = results.map((result) => [
    result.case.id,
    result.case.suite,
    result.case.user_question,
    result.case.expected_tool,
    result.prediction.tool,
    String(result.passed),
    String(Boolean(result.controlled_failure)),
    String(Boolean(result.guardrail_caught)),
    result.failure_category || '',
    String(result.prediction.latency_ms),
    String(result.prediction.token_cost),
  ]);
  return [headers, ...rows]
    .map((row) => row.map((cell) => `"${cell.replaceAll('"', '""')}"`).join(','))
    .join('\n');
}

function pickRepresentativeResults(results: EvalResult[], limit: number) {
  const picked: EvalResult[] = [];
  const used = new Set<string>();
  const add = (result: EvalResult | undefined) => {
    if (!result || used.has(result.case.id) || picked.length >= limit) return;
    picked.push(result);
    used.add(result.case.id);
  };

  results.filter((result) => result.controlled_failure).forEach(add);

  const suites = Array.from(new Set(results.map((result) => result.case.suite)));
  for (const suite of suites) {
    add(results.find((result) => result.case.suite === suite && !result.controlled_failure));
  }

  results.forEach(add);
  return picked;
}
