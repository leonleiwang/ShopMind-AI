# app/services/chatbot/tools/caller.py
from time import perf_counter
from typing import Any

from app.services.observability import AgentObservability

from .registry import ToolRegistry


class ToolCaller:
    """[反思1c/2a-并发治理] 请求级工具调用器，隔离 LLM 与具体工具实现。"""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def invoke(self, tool_name: str, **kwargs) -> Any:
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
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters
            }
            for t in self.registry.list_all()
        ]
