ShopMind AI 面试演示指南
本文档演示如何从 G:\MyProjects\ShopMind AI 运行并展示 ShopMind AI。

1. 项目展示要点

ShopMind AI 是一个全栈 AI Agent 电商系统：

- 基于 Next.js 的前端，包含登录、聊天界面和运营仪表盘
- 基于 FastAPI 的后端，集成 JWT 鉴权、商品接口、购物车/订单接口、SSE 及 WebSocket
- 多智能体购物助手，具备意图路由、规划、推荐、对比、购物车和下单等能力
- 基于 MCP 风格的工具服务器，用于工具发现与调用
- 以 PostgreSQL 持久化数据，并通过 Alembic 管理数据库迁移
- 使用 Celery 处理 AI 运营任务，如生成商品描述、动态定价、营销文案和推荐刷新
- 采用 Milvus/Chroma 向量存储抽象层，在商品搜索中集成语义排序
- 提供可观测性仪表盘，用于监控 Agent 意图、工具调用、SSE 事件、延迟及 WebSocket 订单状态快照

2. 新 Windows 机器环境准备

需安装：

- Git
- Node.js 20 LTS
- Python 3.11
- Docker Desktop
- 若未使用 Docker Compose，需单独安装 PostgreSQL 15
- 若未使用 Docker Compose，需单独安装 Redis

可选云服务：

- 用于 Qwen/OpenAI 兼容 LLM 的 DashScope API 密钥
- 用于生产环境向量存储的 Zilliz Cloud 或 Milvus
- 用于前端部署的 Vercel 账户
- 用于后端、PostgreSQL、Redis 部署的 Railway 账户

3. 使用 Docker Compose 的本地搭建

打开 PowerShell：
cd "G:\MyProjects\ShopMind AI"
Copy-Item backend\.env.example backend\.env -Force
Copy-Item frontend\.env.local.example frontend\.env.local -Force

编辑 backend\.env 并设置：
notepad backend\.env

推荐的演示环境变量值：
SECRET_KEY=replace-with-a-long-random-string
CELERY_TASK_ALWAYS_EAGER=True
VECTOR_STORE_TYPE=chroma
OPENAI_API_KEY=<你的 DashScope API 密钥>
DASHSCOPE_API_KEY=<你的 DashScope API 密钥>

启动整个技术栈：
docker compose up --build

在另一个 PowerShell 窗口中运行数据库迁移：
cd "G:\MyProjects\ShopMind AI\backend"
docker compose exec backend alembic upgrade head

打开以下页面：
- 前端：http://localhost:3000
- 后端 OpenAPI 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/v1/health
- MCP 工具列表：http://localhost:8000/mcp/tools

4. 不使用 Docker 的本地搭建

后端：
cd "G:\MyProjects\ShopMind AI\backend"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env -Force
notepad .env
alembic upgrade head
uvicorn main:app --reload

前端：
cd "G:\MyProjects\ShopMind AI\frontend"
npm install
Copy-Item .env.local.example .env.local -Force
npm run dev

可选启动 Celery worker：
cd "G:\MyProjects\ShopMind AI\backend"
.\.venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

为简化演示，可将 CELERY_TASK_ALWAYS_EAGER=True，这样 AI 任务会同步执行，无需单独启动 worker。

5. 演示数据准备

  1. 在 Swagger 中通过 POST /api/v1/auth/register 注册一个用户，或者如果你已初始化用户，直接使用前端登录流程。

  2. 登录，并从 POST /api/v1/auth/login 的响应中复制 Bearer 令牌。

  3. 在 Swagger 中点击 Authorize，并填入：
  Bearer <你的访问令牌>

  通过 POST /api/v1/products/ 创建一些商品，例如：
  {
    "name": "低延迟蓝牙耳机 Pro",
    "description": "适合游戏和通勤，蓝牙 5.3，低延迟模式",
    "price": 199,
    "category": "电子",
    "brand": "SoundMax",
    "image_url": "",
    "stock": 50
  }

  {
    "name": "机械键盘 K87",
    "description": "热插拔轴体，办公游戏两用",
    "price": 299,
    "category": "电子",
    "brand": "KeyLab",
    "image_url": "",
    "stock": 20
  }

6. 面试演示流程

 1. 登录 http://localhost:3000/login。

 2. 打开聊天界面 http://localhost:3000/chat。

 3. 测试纯搜索：
  帮我找一下有哪些电子产品

 4. 测试筛选搜索：
  有没有200元以下的耳机？

 5. 测试对比：
  帮我对比一下商品2和商品4

 6. 测试购物车和下单：
  帮我清空购物车，然后重新把商品1加进去，再下单

 7. 打开仪表盘：
  http://localhost:3000/dashboard

  展示：
  - 意图分布
  - MCP 工具调用计数
  - SSE 事件计数
  - 平均工具延迟
  - 最近的 Agent/工具事件
  - WebSocket 订单状态快照
  - AI 生成商品描述的任务按钮
  - 动态定价和营销文案的任务按钮

  8. 展示 MCP 工具发现：
  Invoke-RestMethod http://localhost:8000/mcp/tools

  9. 展示 API 契约：
  http://localhost:8000/docs

7. 部署演示

前端部署至 Vercel：
- 根目录：frontend
- 构建命令：npm run build
- 输出目录：.next
- 环境变量：
NEXT_PUBLIC_API_BASE_URL=https://<railway-后端域名>/api/v1

后端部署至 Railway：
- 根目录：backend
- Railway 使用 railway.json 和 Dockerfile
- 添加 PostgreSQL 和 Redis 插件
- 环境变量：
SECRET_KEY=<一个较长的随机字符串>
OPENAI_API_KEY=<DashScope 密钥>
DASHSCOPE_API_KEY=<DashScope 密钥>
BACKEND_CORS_ORIGINS=["https://<vercel-域名>"]
DATABASE_URL=<Railway 提供的 PostgreSQL URL>
REDIS_URL=<Railway 提供的 Redis URL>
VECTOR_STORE_TYPE=milvus
MILVUS_URI=<Zilliz 或 Milvus 的 URI>
MILVUS_TOKEN=<对应的令牌>

8. 面试官可能的提问及回答要点
问：为什么选择多智能体而不是一个提示词？

答： 系统将路由、规划、推荐、对比和购物车/订单执行分离。这使得每种行为都可测试、可替换，并且规划器能够组合多步骤工作流，例如“清空购物车，添加商品，然后下单”，而无需为每一句话硬编码。

问：MCP 在哪里体现？

答： 工具通过共享模式注册，并通过 ToolCaller 调用。/mcp/tools 和 /mcp/tools/{tool_name}/call 端点通过稳定的 HTTP MCP 风格接口暴露相同工具，这样未来的外部智能体无需耦合内部服务即可发现和调用电商功能。

问：搜索是如何工作的？

答： PostgreSQL 按关键词、类别和价格进行结构化筛选。向量存储管理器提供语义排序阶段。在生产环境中，它可以使用 Milvus/Zilliz；在本地演示中，它会回退到确定性的语义评分，以保证系统在没有外部向量基础设施的情况下依然稳定可靠。

问：如何观察 Agent 的行为？

答： AgentObservability 会记录每个意图、SSE 事件和工具调用。仪表盘轮询 /api/v1/chat/metrics 并展示意图计数、工具调用计数、错误计数、延迟、最近事件以及 WebSocket 订单状态流。

问：最大的工程权衡是什么？

答： 在保持演示可靠性的同时保留生产级架构。像 LLM、Redis 和 Milvus 这样的外部服务很有价值，但项目必须能优雅降级。Celery 支持同步执行以便演示，向量排序有本地回退方案，前端所有服务 URL 都从环境变量读取。

问：下一步如何改进？

答：添加持久化可观测性存储、OpenTelemetry 链路追踪、将真实嵌入数据注入 Milvus、为管理端添加更严格的 RBAC，并为智能体规划提供更丰富的评估测试。

9. 最终验证命令

前端：
cd "G:\MyProjects\ShopMind AI\frontend"
npm.cmd run lint
npm.cmd run build

验证后端：
cd "G:\MyProjects\ShopMind AI\backend"
.\.venv\Scripts\Activate.ps1
python -m compileall app
python -m pytest

Docker 环境验证：
cd "G:\MyProjects\ShopMind AI"
docker compose config
docker compose up --build

--
# ShopMind AI Interview Demo Guide

This guide shows how to run and present ShopMind AI from `G:\MyProjects\ShopMind AI`.

## 1. What This Project Demonstrates

ShopMind AI is a full-stack AI Agent commerce system:

- Next.js frontend with login, chat, and operations dashboard
- FastAPI backend with JWT, product APIs, cart/order APIs, SSE, and WebSocket
- Multi-agent shopping assistant with intent routing, planning, recommendation, comparison, cart, and order agents
- MCP-style tool server for tool discovery and invocation
- PostgreSQL persistence with Alembic migrations
- Celery AI operations tasks for product description generation, dynamic pricing, marketing copy, and recommendation refresh
- Milvus/Chroma vector-store abstraction with semantic ranking integrated into product search
- Observability dashboard for Agent intents, tool calls, SSE events, latency, and order WebSocket snapshots

## 2. Prerequisites On A New Windows Machine

Install:

- Git
- Node.js 20 LTS
- Python 3.11
- Docker Desktop
- PostgreSQL 15 if you do not use Docker Compose
- Redis if you do not use Docker Compose

Optional cloud services:

- DashScope API key for Qwen/OpenAI-compatible LLM
- Zilliz Cloud or Milvus for production vector store
- Vercel account for frontend deployment
- Railway account for backend, PostgreSQL, Redis deployment

## 3. Local Setup With Docker Compose

Open PowerShell:

```powershell
cd "G:\MyProjects\ShopMind AI"
Copy-Item backend\.env.example backend\.env -Force
Copy-Item frontend\.env.local.example frontend\.env.local -Force
```

Edit `backend\.env` and set:

```powershell
notepad backend\.env
```

Recommended demo values:

```text
SECRET_KEY=replace-with-a-long-random-string
CELERY_TASK_ALWAYS_EAGER=True
VECTOR_STORE_TYPE=chroma
OPENAI_API_KEY=<your DashScope API key>
DASHSCOPE_API_KEY=<your DashScope API key>
```

Start the stack:

```powershell
docker compose up --build
```

Run database migrations in another PowerShell window:

```powershell
cd "G:\MyProjects\ShopMind AI\backend"
docker compose exec backend alembic upgrade head
```

Open:

- Frontend: `http://localhost:3000`
- Backend OpenAPI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/v1/health`
- MCP tools: `http://localhost:8000/mcp/tools`

## 4. Local Setup Without Docker

Backend:

```powershell
cd "G:\MyProjects\ShopMind AI\backend"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env -Force
notepad .env
alembic upgrade head
uvicorn main:app --reload
```

Frontend:

```powershell
cd "G:\MyProjects\ShopMind AI\frontend"
npm install
Copy-Item .env.local.example .env.local -Force
npm run dev
```

Optional Celery worker:

```powershell
cd "G:\MyProjects\ShopMind AI\backend"
.\.venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app worker --loglevel=info
```

For simple demos, set `CELERY_TASK_ALWAYS_EAGER=True` so AI operations run synchronously without a worker.

## 5. Demo Data Setup

1. Register a user through `POST /api/v1/auth/register` in Swagger, or use the frontend login flow if you already seeded a user.
2. Login and copy the Bearer token from `POST /api/v1/auth/login`.
3. In Swagger, click Authorize and paste:

```text
Bearer <access_token>
```

Create several products through `POST /api/v1/products/`, for example:

```json
{
  "name": "低延迟蓝牙耳机 Pro",
  "description": "适合游戏和通勤，蓝牙 5.3，低延迟模式",
  "price": 199,
  "category": "电子",
  "brand": "SoundMax",
  "image_url": "",
  "stock": 50
}
```

```json
{
  "name": "机械键盘 K87",
  "description": "热插拔轴体，办公游戏两用",
  "price": 299,
  "category": "电子",
  "brand": "KeyLab",
  "image_url": "",
  "stock": 20
}
```

## 6. Interview Demo Flow

1. Login at `http://localhost:3000/login`.
2. Open chat at `http://localhost:3000/chat`.
3. Test pure search:

```text
帮我找一下有哪些电子产品
```

4. Test filtered search:

```text
有没有200元以下的耳机？
```

5. Test comparison:

```text
帮我对比一下商品1和商品2
```

6. Test cart and order:

```text
帮我清空购物车，然后重新把商品1加进去，再下单
```

7. Open dashboard:

```text
http://localhost:3000/dashboard
```

Show:

- intent distribution
- MCP tool call counts
- SSE event counts
- average tool latency
- recent Agent/tool events
- WebSocket order snapshot
- AI product description task button
- dynamic pricing and marketing copy task buttons

8. Show MCP tool discovery:

```powershell
Invoke-RestMethod http://localhost:8000/mcp/tools
```

9. Show API contracts:

```text
http://localhost:8000/docs
```

## 7. Deployment Demo

Frontend on Vercel:

- Root Directory: `frontend`
- Build Command: `npm run build`
- Output Directory: `.next`
- Environment:

```text
NEXT_PUBLIC_API_BASE_URL=https://<railway-backend-domain>/api/v1
```

Backend on Railway:

- Root Directory: `backend`
- Railway uses `railway.json` and `Dockerfile`
- Add PostgreSQL and Redis plugins
- Environment:

```text
SECRET_KEY=<long random string>
OPENAI_API_KEY=<DashScope key>
DASHSCOPE_API_KEY=<DashScope key>
BACKEND_CORS_ORIGINS=["https://<vercel-domain>"]
DATABASE_URL=<Railway PostgreSQL URL>
REDIS_URL=<Railway Redis URL>
VECTOR_STORE_TYPE=milvus
MILVUS_URI=<Zilliz or Milvus URI>
MILVUS_TOKEN=<token>
```

## 8. Talking Points For Interviewers

Question: Why multi-agent instead of one prompt?

Answer: The system separates routing, planning, recommendation, comparison, and cart/order execution. That makes each behavior testable and replaceable, and it lets the planner compose multi-step workflows such as "clear cart, add product, then order" without hardcoding every sentence pattern.

Question: Where is MCP used?

Answer: Tools are registered behind a shared schema and invoked through `ToolCaller`. The `/mcp/tools` and `/mcp/tools/{tool_name}/call` endpoints expose the same tools through a stable HTTP MCP-style interface, so future external agents can discover and call commerce capabilities without coupling to internal services.

Question: How does search work?

Answer: PostgreSQL performs structured filtering by keyword, category, and price. The vector-store manager provides a semantic ranking stage. In production it can use Milvus/Zilliz, and in local demos it falls back to deterministic semantic scoring so the system stays reliable without external vector infrastructure.

Question: How do you observe Agent behavior?

Answer: Every intent, SSE event, and tool call is recorded by `AgentObservability`. The dashboard polls `/api/v1/chat/metrics` and shows intent counts, tool counts, error counts, latency, recent events, and a WebSocket order-status stream.

Question: What was the hardest engineering tradeoff?

Answer: Keeping the demo reliable while preserving production architecture. External services like LLMs, Redis, and Milvus are valuable, but the project must degrade gracefully. Celery supports eager execution for demos, vector ranking has a local fallback, and the frontend reads all service URLs from environment variables.

Question: How would you improve this next?

Answer: Add persistent observability storage, OpenTelemetry traces, real embedding ingestion into Milvus, stricter RBAC for admin endpoints, and richer evaluation tests for agent planning.

## 9. Final Verification Commands

Frontend:

```powershell
cd "G:\MyProjects\ShopMind AI\frontend"
npm.cmd run lint
npm.cmd run build
```

Backend on a machine with Python:

```powershell
cd "G:\MyProjects\ShopMind AI\backend"
.\.venv\Scripts\Activate.ps1
python -m compileall app
python -m pytest
```

Docker:

```powershell
cd "G:\MyProjects\ShopMind AI"
docker compose config
docker compose up --build
```
