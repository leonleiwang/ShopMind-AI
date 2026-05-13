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
    _events: Counter[str] = Counter()
    _latency_ms: deque[float] = deque(maxlen=200)
    _recent: deque[dict[str, Any]] = deque(maxlen=50)

    @classmethod
    def record_intent(cls, intent: str, message: str) -> None:
        with cls._lock:
            cls._intents[intent] += 1
            cls._recent.appendleft(
                {"type": "intent", "intent": intent, "message": message[:160], "ts": time.time()}
            )

    @classmethod
    def record_event(cls, event: str) -> None:
        with cls._lock:
            cls._events[event] += 1

    @classmethod
    def record_tool(cls, tool_name: str, latency_ms: float, ok: bool = True) -> None:
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
    def snapshot(cls) -> dict[str, Any]:
        with cls._lock:
            latencies = list(cls._latency_ms)
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            return {
                "uptime_seconds": int(time.time() - cls._started_at),
                "intent_counts": dict(cls._intents),
                "tool_counts": dict(cls._tools),
                "tool_error_counts": dict(cls._tool_errors),
                "sse_event_counts": dict(cls._events),
                "avg_tool_latency_ms": round(avg_latency, 2),
                "recent_events": list(cls._recent),
            }
