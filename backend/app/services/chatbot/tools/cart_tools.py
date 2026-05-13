"""
购物车工具
"""

# backend/app/services/chatbot/tools/cart_tools.py
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.order_service import CartService

class AddToCartTool:
    name = "add_to_cart"
    description = "Add a product to the user's shopping cart"
    parameters = {
        "type": "object",
        "properties": {
            "product_id": {"type": "integer", "description": "ID of the product to add"},
            "quantity": {"type": "integer", "description": "Quantity to add", "default": 1}
        },
        "required": ["product_id"]
    }

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def execute(self, **kwargs) -> Any:
        product_id = kwargs.get("product_id")
        quantity = kwargs.get("quantity", 1)
        try:
            cart_item = await CartService.add_to_cart(self.db, self.user_id, product_id, quantity)
            return {"message": "Added to cart", "cart_item_id": cart_item.id}
        except ValueError as e:
            return {"error": str(e)}

class ViewCartTool:
    name = "view_cart"
    description = "View the current user's shopping cart"
    parameters = {"type": "object", "properties": {}}

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def execute(self, **kwargs) -> Any:
        items = await CartService.get_cart(self.db, self.user_id)
        return items

class ClearCartTool:
    name = "clear_cart"
    description = "Clear all items from the user's shopping cart"
    parameters = {"type": "object", "properties": {}}

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def execute(self, **kwargs) -> Any:
        await CartService.clear_cart(self.db, self.user_id)
        return {"message": "Cart cleared"}
