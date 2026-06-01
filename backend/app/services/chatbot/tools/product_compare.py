# 商品对比工具：按商品 id 批量读取关键字段，供 ComparisonAgent 生成对比回复。
"""
商品对比工具
"""

# backend/app/services/chatbot/tools/product_compare.py
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductCompareTool:
    # 对比工具元数据会暴露给 function calling schema。
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
        # 执行批量查询并返回轻量商品对比字段。
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
