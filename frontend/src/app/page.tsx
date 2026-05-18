import Link from 'next/link';

const capabilities = [
  {
    title: '像购物网站一样自然',
    body: '顶部导航、分类入口和购物车 / 订单入口贴近真实电商用户心智，演示时更容易代入。',
  },
  {
    title: 'Agent 过程可展示',
    body: '路由、工具调用、SSE 事件和最终推荐都能在录屏里看清楚，不只是一个聊天框。',
  },
  {
    title: '运营台可解释',
    body: '面试时能从购物体验顺滑切到 Dashboard，说明工程治理和可观测性能力。',
  },
];

const categories = ['耳机', '手机', '电脑外设', '订单查询', '购物车', 'AI 推荐'];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#f4f7fb] text-slate-900">
      <header className="bg-[#123b5d] text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-3 lg:px-8">
          <Link className="flex items-center gap-3" href="/">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#ffca45] text-sm font-black text-[#102033]">
              SM
            </span>
            <span>
              <span className="block font-semibold">ShopMind AI</span>
              <span className="block text-xs text-sky-100/75">Commerce Agent Platform</span>
            </span>
          </Link>
          <nav className="flex items-center gap-2 text-sm">
            <Link className="hidden rounded-lg px-3 py-2 text-sky-50 hover:bg-white/10 md:inline" href="/dashboard">
              运营台
            </Link>
            <Link className="hidden rounded-lg px-3 py-2 text-sky-50 hover:bg-white/10 md:inline" href="/chat">
              AI 客服
            </Link>
            <Link className="rounded-lg bg-[#ffca45] px-4 py-2 font-semibold text-[#102033] hover:bg-[#ffd873]" href="/login">
              进入演示
            </Link>
          </nav>
        </div>
        <div className="border-t border-white/10 bg-[#1d6389]">
          <div className="mx-auto flex max-w-7xl gap-2 overflow-x-auto px-5 py-2 lg:px-8">
            {categories.map((category) => (
              <span key={category} className="shrink-0 rounded-full bg-[#dff3f8] px-3 py-1.5 text-xs font-medium text-[#12445f]">
                {category}
              </span>
            ))}
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl items-center gap-10 px-5 py-12 lg:grid-cols-[1fr_0.9fr] lg:px-8 lg:py-16">
        <div>
          <div className="mb-5 inline-flex rounded-full border border-[#9bd7e7] bg-[#e8f6fa] px-3 py-1 text-xs font-semibold text-[#12445f]">
            v0.2 Agent Governance & Routing Hardening
          </div>
          <h1 className="max-w-4xl text-5xl font-semibold leading-[1.03] tracking-tight text-[#102033] md:text-6xl">
            更像真实电商的 AI 购物助手。
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
            用接近购物网站的浅色体验承载 Agent 能力：用户可以自然浏览、搜索、推荐和下单，面试官也能清楚看到路由、工具调用、
            LLM 降级和运营仪表盘。
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              className="rounded-lg bg-[#ffca45] px-5 py-3 text-sm font-semibold text-[#102033] shadow-sm transition hover:bg-[#ffd873]"
              href="/login"
            >
              开始购物演示
            </Link>
            <Link
              className="rounded-lg border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-[#123b5d] shadow-sm transition hover:border-[#9bd7e7] hover:bg-[#f3fbfd]"
              href="/dashboard"
            >
              查看运营台
            </Link>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-xl shadow-slate-200/80">
          <div className="rounded-lg border border-slate-200 bg-[#fbfcfe] p-5">
            <div className="flex items-center justify-between border-b border-slate-200 pb-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-[#1d6389]">Shopping session</p>
                <h2 className="mt-2 text-xl font-semibold">低延迟蓝牙耳机推荐</h2>
              </div>
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                healthy
              </span>
            </div>

            <div className="mt-5 space-y-3">
              <div className="ml-auto max-w-[82%] rounded-lg bg-[#ffd66b] px-4 py-3 text-sm font-medium text-slate-900">
                想买 200 元以内、低延迟的蓝牙耳机
              </div>
              <div className="max-w-[88%] rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                为你找到 3 款电子商品，已按价格和语义相关性排序。
              </div>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <ProductPreview name="SoundMax Pro" price="¥199" meta="低延迟 / 通勤" />
              <ProductPreview name="AirBuds Lite" price="¥159" meta="轻量 / 长续航" />
            </div>

            <div className="mt-5 rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-800">Agent trace</span>
                <span className="text-xs text-slate-400">SSE stream</span>
              </div>
              <div className="space-y-2">
                {['intent: recommend', 'tool: search_products', 'observation: 3 products', 'final: 推荐低延迟耳机'].map((step) => (
                  <div key={step} className="flex items-center justify-between rounded-lg bg-[#f3fbfd] px-3 py-2">
                    <span className="text-xs text-slate-700">{step}</span>
                    <span className="h-2 w-2 rounded-full bg-[#1d6389]" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-4 px-5 pb-12 md:grid-cols-3 lg:px-8">
        {capabilities.map((item) => (
          <article key={item.title} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-base font-semibold text-slate-900">{item.title}</h3>
            <p className="mt-3 text-sm leading-6 text-slate-500">{item.body}</p>
          </article>
        ))}
      </section>
    </main>
  );
}

function ProductPreview({ name, price, meta }: { name: string; price: string; meta: string }) {
  return (
    <div className="rounded-lg border border-[#cfe7ef] bg-[#f3fbfd] p-4">
      <div className="h-20 rounded-lg bg-[linear-gradient(135deg,#e8f6fa,#fff7dd)]" />
      <div className="mt-3 flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-slate-900">{name}</p>
          <p className="mt-1 text-xs text-slate-500">{meta}</p>
        </div>
        <span className="text-sm font-semibold text-[#12445f]">{price}</span>
      </div>
    </div>
  );
}
