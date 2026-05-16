# app/services/chatbot/tools/registry.py
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MCPTool(Protocol):
    """MCP 工具接口"""
    name: str
    description: str
    parameters: dict[str, Any]
    
    async def execute(self, **kwargs) -> Any:
        ...

class ToolRegistry:
    """[反思1c/2a-并发治理] Request-scoped 工具注册表。

    旧实现把带有 db session / user_id 的工具实例放到全局字典里，并发请求下可能互相覆盖。
    现在每个 ChatService 请求持有自己的 registry，避免用户态工具串线。
    """

    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}

    def register(self, tool: MCPTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> MCPTool | None:
        return self._tools.get(name)

    def list_all(self) -> list[MCPTool]:
        return list(self._tools.values())
