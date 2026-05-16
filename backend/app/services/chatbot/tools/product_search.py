"""
具体工具：商品搜索
"""

# backend/app/services/chatbot/tools/product_search.py
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.services.chatbot.vector_store_manager import vector_store_manager


class ProductSearchTool:
    name = "search_products"
    description = "Search products by keyword and category"
    parameters = {
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "Search keyword"},
            "category": {"type": "string", "description": "Product category"},
            "max_price": {"type": "number", "description": "Maximum price"},
            "min_price": {"type": "number", "description": "Minimum price"}
        },
        "required": ["keyword"]
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, **kwargs) -> Any:
        keyword = self._clean_text(kwargs.get("keyword", ""))
        category = self._clean_category(kwargs.get("category"))
        max_price = self._clean_price(kwargs.get("max_price"))
        min_price = self._clean_price(kwargs.get("min_price"))

        products = await self._run_query(keyword, category, min_price, max_price)
        if not products and category:
            products = await self._run_query(keyword, None, min_price, max_price)
        if not products and keyword and category:
            products = await self._run_query("", category, min_price, max_price)

        serialized = [self._serialize_product(p) for p in products]
        if keyword and serialized:
            return vector_store_manager.rank_products(keyword, serialized)
        return serialized

    async def _run_query(self, keyword: str, category: str | None, min_price: float | None, max_price: float | None):
        query = select(Product)
        if keyword:
            query = query.where(Product.name.ilike(f"%{keyword}%") | Product.description.ilike(f"%{keyword}%"))
        if category:
            query = query.where(Product.category.ilike(f"%{category}%"))
        if max_price is not None:
            query = query.where(Product.price <= max_price)
        if min_price is not None:
            query = query.where(Product.price >= min_price)
        query = query.limit(10)
        result = await self.db.execute(query)
        return result.scalars().all()

    @staticmethod
    def _clean_text(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        return "" if text.lower() in {"0", "none", "null", "不限", "全部", "任意"} else text

    @classmethod
    def _clean_category(cls, value: Any) -> str | None:
        category = cls._clean_text(value)
        if not category:
            return None
        if category in {"电子产品", "数码产品"}:
            return "电子"
        return category

    @staticmethod
    def _clean_price(value: Any) -> float | None:
        if value in (None, "", "null", "None"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _serialize_product(p: Product) -> dict:
        return {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "category": p.category,
            "brand": p.brand,
            "description": (p.description or "")[:200]
        }
