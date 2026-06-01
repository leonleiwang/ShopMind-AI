# 商品业务服务：提供商品 CRUD、关键词/品类筛选，并为 AI 运营草稿审批提供写回能力。
"""
商品业务逻辑 
"""

# backend/app/services/product_service.py

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductService:
    @staticmethod
    async def create_product(db: AsyncSession, **kwargs) -> Product:
        # 创建商品并返回刷新后的 ORM 对象。
        product = Product(**kwargs)
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product

    @staticmethod
    async def get_product(db: AsyncSession, product_id: int) -> Product | None:
        # 按主键读取单个商品。
        result = await db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_products(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        keyword: str | None = None,
        category: str | None = None
    ) -> list[Product]:
        # 商品列表查询支持关键词和品类过滤，供前台浏览、Agent 工具和后台运营复用。
        query = select(Product)
        if keyword:
            query = query.where(Product.name.ilike(f"%{keyword}%") | Product.description.ilike(f"%{keyword}%"))
        if category:
            query = query.where(Product.category == category)
        query = query.offset(skip).limit(limit).order_by(Product.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_product(db: AsyncSession, product_id: int, update_data: dict) -> Product | None:
        # 局部更新商品字段，忽略 None 值以避免误覆盖。
        product = await ProductService.get_product(db, product_id)
        if not product:
            return None
        for key, value in update_data.items():
            if value is not None:
                setattr(product, key, value)
        await db.commit()
        await db.refresh(product)
        return product

    @staticmethod
    async def delete_product(db: AsyncSession, product_id: int) -> bool:
        # 删除商品并返回是否真实删除。
        product = await ProductService.get_product(db, product_id)
        if not product:
            return False
        await db.delete(product)
        await db.commit()
        return True
