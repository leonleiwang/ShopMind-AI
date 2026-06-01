"""
HTTP MCP-style tool server.

This is a lightweight Model Context Protocol adapter for the project's tools:
clients can discover available tools and invoke them through a stable JSON API.
It shares the same tool implementations used by the chat Agent runtime.
"""
# HTTP MCP 适配层：让外部客户端发现并调用 ShopMind 的搜索、购物车、下单和对比工具。

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.chatbot.tools.cart_tools import AddToCartTool, ClearCartTool, ViewCartTool
from app.services.chatbot.tools.order_tools import CheckOrderTool, PlaceOrderTool
from app.services.chatbot.tools.product_compare import ProductCompareTool
from app.services.chatbot.tools.product_search import ProductSearchTool

router = APIRouter()


class ToolCallRequest(BaseModel):
    # 工具调用入参，arguments 会原样传给具体工具 execute。
    arguments: dict[str, Any] = Field(default_factory=dict)


def _tool_schemas() -> list[dict[str, Any]]:
    # 暴露工具 JSON schema，供 MCP/Function Calling 客户端发现能力。
    tool_classes = [
        ProductSearchTool,
        ProductCompareTool,
        AddToCartTool,
        ViewCartTool,
        ClearCartTool,
        PlaceOrderTool,
        CheckOrderTool,
    ]
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        }
        for tool in tool_classes
    ]


def _build_tool(tool_name: str, db: AsyncSession, user_id: int):
    # 按工具名创建带当前 db/user 上下文的工具实例。
    factories = {
        "search_products": lambda: ProductSearchTool(db),
        "compare_products": lambda: ProductCompareTool(db),
        "add_to_cart": lambda: AddToCartTool(db, user_id),
        "view_cart": lambda: ViewCartTool(db, user_id),
        "clear_cart": lambda: ClearCartTool(db, user_id),
        "place_order": lambda: PlaceOrderTool(db, user_id),
        "check_order": lambda: CheckOrderTool(db),
    }
    if tool_name not in factories:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
    return factories[tool_name]()


@router.get("/tools")
async def list_tools():
    # 工具发现接口。
    return {"protocol": "shopmind-mcp-http", "tools": _tool_schemas()}


@router.post("/tools/{tool_name}/call")
async def call_tool(
    tool_name: str,
    request: ToolCallRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 工具调用接口，复用 Chat Agent 的同一套工具实现。
    tool = _build_tool(tool_name, db, current_user.id)
    result = await tool.execute(**request.arguments)
    return {"tool": tool_name, "result": result}
