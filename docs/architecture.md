# ShopMind AI Architecture

ShopMind AI is organized as a layered AI-native commerce application.

## Runtime Components

| Layer | Responsibility |
| --- | --- |
| Frontend | Next.js App Router UI, login, chat experience, operations dashboard, Zustand state |
| Backend API | FastAPI routes, JWT auth, request validation, SSE streaming, WebSocket order status |
| Service Layer | Product, cart, order, and user business logic |
| Agent Layer | Intent routing, planning, recommendation, comparison, cart/order handling |
| Tool Layer | MCP-style tool registry and tool caller abstraction |
| Async Layer | Celery worker for long-running AI/product operations |
| Data Layer | PostgreSQL models and Alembic migrations |
| Vector Layer | Milvus in production, Chroma as a development fallback, local semantic ranking fallback |

## Agent Flow

1. The frontend posts a user message to `/api/v1/chat/stream`.
2. `ChatService` routes the message through `IntentRouterAgent`.
3. Simple intents call one specialized agent or tool.
4. Multi-step intents use `PlanningAgent`, then execute each step in sequence.
5. Tool calls go through `ToolCaller` and `ToolRegistry`.
6. SSE events stream intent, thought, action, observation, and final answer back to the UI.
7. `AgentObservability` records intents, tool calls, latency, SSE events, and recent activity for `/dashboard`.

## Deployment

| Component | Target |
| --- | --- |
| Frontend | Vercel, with `frontend` as project root |
| Backend | Railway Docker deployment, with `backend` as project root |
| Database | Railway PostgreSQL or self-hosted PostgreSQL |
| Redis | Railway Redis or self-hosted Redis for Celery |
| Vector Store | Zilliz/Milvus Cloud for production, Chroma for lightweight demos |

## Current Scope

The current implementation covers the user-facing shopping assistant loop:
search, recommendation, comparison, cart management, and order placement.

The implementation also includes the production-facing extensions:

- HTTP MCP-style tool discovery and invocation under `/mcp`
- frontend API service layer in `frontend/src/services/api.ts`
- semantic product ranking through `VectorStoreManager`
- WebSocket order-status snapshots and updates
- operations dashboard and Agent observability at `/dashboard`
- pytest coverage for routing, planning, MCP schemas, and semantic ranking
- Celery AI operations for descriptions, pricing suggestions, marketing copy, and recommendation refresh
