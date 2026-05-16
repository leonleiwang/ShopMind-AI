"""
商品对比工具
"""

# backend/app/services/chatbot/tools/product_compare.py
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductCompareTool:
    name = "compare_products"
    description = "Compare multiple products by their IDs, returning price, category, and description"
    parameters = {
        "type": "object",
        "properties": {
            "product_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of product IDs to compare"
            }
        },
        "required": ["product_ids"]
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, **kwargs) -> Any:
        product_ids: list[int] = kwargs.get("product_ids", [])
        if not product_ids:
            return []
        result = await self.db.execute(select(Product).where(Product.id.in_(product_ids)))
        products = result.scalars().all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "category": p.category,
                "brand": p.brand,
                "description": p.description[:200]
            }
            for p in products
        ]