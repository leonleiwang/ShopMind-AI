# app/services/chatbot/tools/caller.py
from typing import Any
from time import perf_counter
from app.services.observability import AgentObservability
from .registry import ToolRegistry

class ToolCaller:
    """工具调用抽象，隔离 LLM 与具体工具实现"""
    
    @staticmethod
    async def invoke(tool_name: str, **kwargs) -> Any:
        tool = ToolRegistry.get(tool_name)
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
    
    @staticmethod
    def get_tool_schemas() -> list[dict]:
        """返回 JSON Schema 格式的工具列表，供 LLM function calling"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters
            }
            for t in ToolRegistry.list_all()
        ]
