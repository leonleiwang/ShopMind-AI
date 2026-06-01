# 订单工具集：把下单审批和订单查询能力暴露给 Agent，并确保下单先进入 HITL 审批。
"""
订单工具
"""

# backend/app/services/chatbot/tools/order_tools.py
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.hitl_service import ApprovalService
from app.services.order_service import OrderService


class PlaceOrderTool:
    # 下单工具：不直接创建订单，而是生成可审批的 checkout request。
    name = "place_order"
    description = "Create an order from the current user's shopping cart"
    parameters = {
        "type": "object",
        "properties": {
            "product_id": {"type": "integer", "description": "Only checkout this product from the cart"},
            "keyword": {"type": "string", "description": "Only checkout cart items matching this product keyword/category"},
        },
    }

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def execute(self, **kwargs) -> Any:
        # 生成订单审批并返回前端可渲染的审批卡片字段。
        try:
            product_id = kwargs.get("product_id")
            approval = await ApprovalService.create_order_approval(
                self.db,
                self.user_id,
                product_ids=[int(product_id)] if product_id else None,
                keyword=kwargs.get("keyword"),
            )
            return {
                "approval_required": True,    # [HITL轻量级更新] 生成审批请求；确认后才执行真实下单
                "approval_id": approval.id,
                "status": approval.status,
                "risk_level": approval.risk_level,
                "risk_reasons": approval.risk_reasons,
                "approval_channel": (approval.payload or {}).get("approval_channel"),
                "confirmation_level": (approval.payload or {}).get("confirmation_level"),
                "summary": approval.summary,
                "payload": approval.payload or {},
                "total_amount": (approval.payload or {}).get("total_amount"),
            }
        except ValueError as e:
            return {"error": str(e)}

class CheckOrderTool:
    # 订单查询工具：按订单 id 返回状态、金额和订单项。
    name = "check_order"
    description = "Check the status of an order by ID"
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {"type": "integer", "description": "Order ID"}
        },
        "required": ["order_id"]
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, **kwargs) -> Any:
        # 查询订单详情，未找到时返回工具错误结果。
        order_id = kwargs.get("order_id")
        order = await OrderService.get_order(self.db, order_id)
        if not order:
            return {"error": "Order not found"}
        return {
            "order_id": order.id,
            "status": order.status,
            "total_amount": order.total_amount,
            "items": [{"product_id": item.product_id, "quantity": item.quantity, "price": item.unit_price} for item in order.items]
        }
