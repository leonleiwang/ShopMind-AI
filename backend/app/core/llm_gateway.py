from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter, time
from typing import Any

from app.core.config import settings
from app.core.llm import get_llm
from app.services.observability import AgentObservability


@dataclass
class LLMGatewayMessage:
    content: str
    degraded: bool = False
    error: str | None = None


class LLMGateway:
    """[反思2a/2b-韧性降级] LLM 调用网关。

    集中处理 timeout、retry、熔断和纯逻辑 fallback，并且避免测试/CI 在 import 阶段
    强制初始化真实模型客户端。
    """

    def __init__(self) -> None:
        self.llm: Any | None = None
        self.provider = settings.OPENAI_MODEL_NAME
        self._failure_count = 0
        self._circuit_open_until = 0.0

    async def ainvoke(self, prompt: str, fallback_content: str = "") -> LLMGatewayMessage:
        llm = self._get_llm()
        if llm is None:
            return self._degraded(fallback_content, "llm credentials are not configured", 0)

        if self._is_circuit_open():
            return self._degraded(fallback_content, "llm circuit breaker is open", 0)

        last_error: Exception | None = None
        for attempt in range(settings.LLM_MAX_RETRIES + 1):
            start = perf_counter()
            try:
                response = await asyncio.wait_for(
                    llm.ainvoke(prompt),
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
                latency = (perf_counter() - start) * 1000
                self._failure_count = 0
                AgentObservability.record_llm(self.provider, latency, ok=True)
                return LLMGatewayMessage(content=response.content)
            except Exception as exc:
                last_error = exc
                latency = (perf_counter() - start) * 1000
                AgentObservability.record_llm(self.provider, latency, ok=False)
                if attempt < settings.LLM_MAX_RETRIES:
                    await asyncio.sleep(min(0.2 * (attempt + 1), 1.0))

        self._failure_count += 1
        if self._failure_count >= settings.LLM_CIRCUIT_BREAKER_THRESHOLD:
            self._circuit_open_until = time() + settings.LLM_CIRCUIT_BREAKER_RESET_SECONDS
        return self._degraded(fallback_content, str(last_error), 0)

    def invoke(self, prompt: str, fallback_content: str = "") -> LLMGatewayMessage:
        llm = self._get_llm()
        if llm is None:
            return self._degraded(fallback_content, "llm credentials are not configured", 0)

        if self._is_circuit_open():
            return self._degraded(fallback_content, "llm circuit breaker is open", 0)

        last_error: Exception | None = None
        for attempt in range(settings.LLM_MAX_RETRIES + 1):
            start = perf_counter()
            try:
                response = llm.invoke(prompt)
                latency = (perf_counter() - start) * 1000
                self._failure_count = 0
                AgentObservability.record_llm(self.provider, latency, ok=True)
                return LLMGatewayMessage(content=response.content)
            except Exception as exc:
                last_error = exc
                latency = (perf_counter() - start) * 1000
                AgentObservability.record_llm(self.provider, latency, ok=False)
                if attempt < settings.LLM_MAX_RETRIES:
                    continue

        self._failure_count += 1
        if self._failure_count >= settings.LLM_CIRCUIT_BREAKER_THRESHOLD:
            self._circuit_open_until = time() + settings.LLM_CIRCUIT_BREAKER_RESET_SECONDS
        return self._degraded(fallback_content, str(last_error), 0)

    def _get_llm(self) -> Any | None:
        if not settings.OPENAI_API_KEY:
            return None
        if self.llm is None:
            self.llm = get_llm()
        return self.llm

    def _is_circuit_open(self) -> bool:
        return time() < self._circuit_open_until

    def _degraded(self, content: str, error: str, latency_ms: float) -> LLMGatewayMessage:
        AgentObservability.record_llm(self.provider, latency_ms, ok=False, degraded=True)
        return LLMGatewayMessage(content=content, degraded=True, error=error)


llm_gateway = LLMGateway()
