import asyncio
import json
from collections.abc import Awaitable
from typing import TypeVar

from sqlalchemy import select

from app.core.config import settings
from app.core.llm_gateway import llm_gateway
from app.db.session import AsyncSessionLocal, engine
from app.models.order import Order, OrderItem
from app.models.product import Product

from .celery_app import celery_app

T = TypeVar("T")


async def _run_with_engine_cleanup(awaitable: Awaitable[T]) -> T:
    try:
        return await awaitable
    finally:
        # Celery sync tasks call async code via asyncio.run(). If pooled asyncpg
        # connections survive that loop, the next task may reuse a closed-loop connection.
        await engine.dispose()


def _run_async_task(awaitable: Awaitable[T]) -> T:
    return asyncio.run(_run_with_engine_cleanup(awaitable))


@celery_app.task(bind=True, max_retries=3)
def generate_product_description(self, product_id: int):
    """AI 生成商品描述（异步任务）。"""
    return _run_async_task(_generate_product_description(product_id))


@celery_app.task(bind=True, max_retries=3)
def batch_update_recommendations(self, user_id: int):
    """批量刷新商品推荐（异步任务）。"""
    return _run_async_task(_batch_update_recommendations(user_id))


@celery_app.task(bind=True, max_retries=3)
def generate_pricing_suggestion(self, product_id: int):
    """AI 动态定价建议（异步任务）。"""
    return _run_async_task(_generate_pricing_suggestion(product_id))


@celery_app.task(bind=True, max_retries=3)
def generate_marketing_copy(self, product_id: int):
    """AI 个性化营销文案（异步任务）。"""
    return _run_async_task(_generate_marketing_copy(product_id))


async def _generate_product_description(product_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        product = await db.get(Product, product_id)
        if not product:
            return {"product_id": product_id, "error": "Product not found"}

        fallback = (
            f"{product.name} 是一款来自 {product.brand or '优选品牌'} 的{product.category or '商品'}，"
            f"价格为 {product.price} 元，适合希望快速完成智能购物决策的用户。"
        )

        description = fallback
        if settings.OPENAI_API_KEY:
            prompt = f"""为电商商品生成一段中文卖点描述，80 字以内，语气专业可信。
商品名：{product.name}
品牌：{product.brand}
分类：{product.category}
价格：{product.price}
原描述：{product.description}
"""
            try:
                response = llm_gateway.invoke(prompt, fallback_content=fallback)
                description = response.content.strip() or fallback
            except Exception:
                description = fallback

        product.description = description
        await db.commit()
        return {"product_id": product.id, "description": description}


async def _batch_update_recommendations(user_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        bought = await db.execute(
            select(Product.category)
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.user_id == user_id)
        )
        categories = sorted({row[0] for row in bought.all() if row[0]})

        query = select(Product).order_by(Product.stock.desc(), Product.price.asc()).limit(5)
        if categories:
            query = (
                select(Product)
                .where(Product.category.in_(categories))
                .order_by(Product.stock.desc(), Product.price.asc())
                .limit(5)
            )

        result = await db.execute(query)
        recommendations = [
            {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "category": product.category,
                "reason": "基于你的历史订单分类和当前库存热度推荐",
            }
            for product in result.scalars().all()
        ]
        return {"user_id": user_id, "recommendations": recommendations}


async def _generate_pricing_suggestion(product_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        product = await db.get(Product, product_id)
        if not product:
            return {"product_id": product_id, "error": "Product not found"}

        if product.stock > 80:
            suggested = round(product.price * 0.95, 2)
            reason = "库存较高，建议小幅降价提升转化。"
        elif product.stock < 10:
            suggested = round(product.price * 1.08, 2)
            reason = "库存较低，建议提高价格保护毛利。"
        else:
            suggested = round(product.price, 2)
            reason = "库存健康，建议保持当前价格并观察转化。"

        result = {
            "product_id": product.id,
            "current_price": product.price,
            "suggested_price": suggested,
            "reason": reason,
        }
        product.pricing_suggestion = json.dumps(result, ensure_ascii=False)
        await db.commit()
        return result


async def _generate_marketing_copy(product_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        product = await db.get(Product, product_id)
        if not product:
            return {"product_id": product_id, "error": "Product not found"}

        fallback = (
            f"正在寻找{product.category or '好物'}？{product.name} 兼顾品质与价格，"
            f"现在仅需 {product.price} 元，适合立即加入购物清单。"
        )
        copy = fallback

        if settings.OPENAI_API_KEY:
            prompt = f"""为下面商品生成一段中文营销文案，60 字以内，强调购买理由和行动号召。
商品名：{product.name}
品牌：{product.brand}
分类：{product.category}
价格：{product.price}
描述：{product.description}
"""
            try:
                response = llm_gateway.invoke(prompt, fallback_content=fallback)
                copy = response.content.strip() or fallback
            except Exception:
                copy = fallback

        product.marketing_copy = copy
        await db.commit()
        return {"product_id": product.id, "marketing_copy": copy}
