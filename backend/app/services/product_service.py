"""
商品业务逻辑 
"""

# backend/app/services/product_service.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.product import Product

class ProductService:
    @staticmethod
    async def create_product(db: AsyncSession, **kwargs) -> Product:
        product = Product(**kwargs)
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product

    @staticmethod
    async def get_product(db: AsyncSession, product_id: int) -> Optional[Product]:
        result = await db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_products(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        keyword: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Product]:
        query = select(Product)
        if keyword:
            query = query.where(Product.name.ilike(f"%{keyword}%") | Product.description.ilike(f"%{keyword}%"))
        if category:
            query = query.where(Product.category == category)
        query = query.offset(skip).limit(limit).order_by(Product.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_product(db: AsyncSession, product_id: int, update_data: dict) -> Optional[Product]:
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
        product = await ProductService.get_product(db, product_id)
        if not product:
            return False
        await db.delete(product)
        await db.commit()
        return True