# 商品搜索工具：支持关键词、品类、价格区间过滤，并在有关键词时接入本地向量/相似度重排。
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
        # 工具持有当前请求的数据库 session。
        self.db = db

    async def execute(self, **kwargs) -> Any:
        # 执行商品搜索，带参数清洗、品类降级搜索和相似度重排。
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
        # 构造 SQLAlchemy 查询，按关键词、品类和价格区间过滤商品。
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
        # 清洗 LLM 可能生成的空值或“不限/全部”等无效文本。
        if value is None:
            return ""
        text = str(value).strip()
        return "" if text.lower() in {"0", "none", "null", "不限", "全部", "任意"} else text

    @classmethod
    def _clean_category(cls, value: Any) -> str | None:
        # 品类清洗并统一常见中文泛品类别名。
        category = cls._clean_text(value)
        if not category:
            return None
        if category in {"电子产品", "数码产品"}:
            return "电子"
        return category

    @staticmethod
    def _clean_price(value: Any) -> float | None:
        # 将价格参数安全转成 float，非法值直接忽略。
        if value in (None, "", "null", "None"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _serialize_product(p: Product) -> dict:
        # 工具结果序列化，控制描述长度并保留 tags/attributes 给推荐和解析链路使用。
        return {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "category": p.category,
            "brand": p.brand,
            "stock": p.stock,
            "image_url": p.image_url,
            "description": (p.description or "")[:200],
            "attributes": p.attributes or {},
            "tags": p.tags or [],
        }
