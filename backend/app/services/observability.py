# AgentOps 轻量观测服务：在进程内记录意图、工具、LLM、SSE 事件、延迟和最近事件流。
from __future__ import annotations

import time
from collections import Counter, deque
from threading import Lock
from typing import Any


class AgentObservability:
    """Small in-process metrics sink for demo and local production deployments."""

    _lock = Lock()
    _started_at = time.time()
    _intents: Counter[str] = Counter()
    _tools: Counter[str] = Counter()
    _tool_errors: Counter[str] = Counter()
    _llm: Counter[str] = Counter()
    _events: Counter[str] = Counter()
    _latency_ms: deque[float] = deque(maxlen=200)
    _recent: deque[dict[str, Any]] = deque(maxlen=50)

    @classmethod
    def record_intent(cls, intent: str, message: str) -> None:
        # 记录意图路由结果和用户消息摘要，用于工程观测 Dashboard。
        with cls._lock:
            cls._intents[intent] += 1
            cls._recent.appendleft(
                {"type": "intent", "intent": intent, "message": message[:160], "ts": time.time()}
            )

    @classmethod
    def record_event(cls, event: str) -> None:
        # 记录 SSE/系统事件计数，例如 intent、action、observation、final。
        with cls._lock:
            cls._events[event] += 1

    @classmethod
    def record_tool(cls, tool_name: str, latency_ms: float, ok: bool = True) -> None:
        # 记录 MCP 工具调用次数、延迟和失败次数。
        with cls._lock:
            cls._tools[tool_name] += 1
            cls._latency_ms.append(latency_ms)
            if not ok:
                cls._tool_errors[tool_name] += 1
            cls._recent.appendleft(
                {
                    "type": "tool",
                    "tool": tool_name,
                    "latency_ms": round(latency_ms, 2),
                    "ok": ok,
                    "ts": time.time(),
                }
            )

    @classmethod
    def record_llm(cls, provider: str, latency_ms: float, ok: bool = True, degraded: bool = False) -> None:
        """[反思2a/2b-韧性降级] 记录 LLM 网关成功、失败和降级事件。"""
        # LLM 网关统一上报成功、失败和 degraded fallback，便于观察模型链路稳定性。
        key = "ok" if ok else "error"
        if degraded:
            key = "degraded"
        with cls._lock:
            cls._llm[f"{provider}:{key}"] += 1
            cls._latency_ms.append(latency_ms)
            cls._recent.appendleft(
                {
                    "type": "llm",
                    "provider": provider,
                    "latency_ms": round(latency_ms, 2),
                    "ok": ok,
                    "degraded": degraded,
                    "ts": time.time(),
                }
            )

    @classmethod
    def snapshot(cls) -> dict[str, Any]:
        # 输出 Dashboard 可直接消费的观测快照。
        with cls._lock:
            latencies = list(cls._latency_ms)
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            return {
                "uptime_seconds": int(time.time() - cls._started_at),
                "intent_counts": dict(cls._intents),
                "tool_counts": dict(cls._tools),
                "tool_error_counts": dict(cls._tool_errors),
                "llm_counts": dict(cls._llm),
                "sse_event_counts": dict(cls._events),
                "avg_tool_latency_ms": round(avg_latency, 2),
                "recent_events": list(cls._recent),
            }
