# app/services/chatbot/tools/registry.py
from typing import Dict, Any, Protocol, runtime_checkable

@runtime_checkable
class MCPTool(Protocol):
    """MCP 工具接口"""
    name: str
    description: str
    parameters: Dict[str, Any]
    
    async def execute(self, **kwargs) -> Any:
        ...

class ToolRegistry:
    """全局工具注册表"""
    _tools: Dict[str, MCPTool] = {}
    
    @classmethod
    def register(cls, tool: MCPTool):
        cls._tools[tool.name] = tool
    
    @classmethod
    def get(cls, name: str) -> MCPTool:
        return cls._tools.get(name)
    
    @classmethod
    def list_all(cls) -> list:
        return list(cls._tools.values())