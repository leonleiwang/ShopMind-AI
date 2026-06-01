# Tool Caller：统一执行 MCP 风格工具，并记录工具调用延迟、成功率和失败事件。
# app/services/chatbot/tools/caller.py
from time import perf_counter
from typing import Any

from app.services.observability import AgentObservability

from .registry import ToolRegistry


class ToolCaller:
    """[反思1c/2a-并发治理] 请求级工具调用器，隔离 LLM 与具体工具实现。"""

    def __init__(self, registry: ToolRegistry):
        # 绑定请求级工具注册表。
        self.registry = registry

    async def invoke(self, tool_name: str, **kwargs) -> Any:
        # 调用指定工具并把成功/失败与耗时写入 AgentOps 观测。
        tool = self.registry.get(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found in registry")
        start = perf_counter()
        try:
            result = await tool.execute(**kwargs)
            AgentObservability.record_tool(tool_name, (perf_counter() - start) * 1000, ok=True)
            return result
        except Exception:
            AgentObservability.record_tool(tool_name, (perf_counter() - start) * 1000, ok=False)
            raise

    def get_tool_schemas(self) -> list[dict]:
        """返回 JSON Schema 格式的工具列表，供 LLM function calling"""
        # 将已注册工具暴露为 LLM 可理解的 function schema。
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters
            }
            for t in self.registry.list_all()
        ]
