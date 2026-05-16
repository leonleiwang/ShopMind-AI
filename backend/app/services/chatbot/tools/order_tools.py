"""
订单工具
"""

# backend/app/services/chatbot/tools/order_tools.py
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.order_service import OrderService


class PlaceOrderTool:
    name = "place_order"
    description = "Create an order from the current user's shopping cart"
    parameters = {"type": "object", "properties": {}}

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def execute(self, **kwargs) -> Any:
        try:
            order = await OrderService.create_order(self.db, self.user_id)
            return {"order_id": order.id, "total_amount": order.total_amount}
        except ValueError as e:
            return {"error": str(e)}

class CheckOrderTool:
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