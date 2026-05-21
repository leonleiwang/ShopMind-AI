"""
业务逻辑层
"""

# backend/app/services/order_service.py

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import CartItem
from app.models.order import Order, OrderItem
from app.models.product import Product


class CartService:
    @staticmethod
    async def add_to_cart(db: AsyncSession, user_id: int, product_id: int, quantity: int = 1) -> CartItem:
        if not product_id:
            raise ValueError("请提供有效的商品ID。")
        if quantity < 1:
            raise ValueError("商品数量必须大于 0。")

        product_result = await db.execute(select(Product.id).where(Product.id == product_id))
        if product_result.scalar_one_or_none() is None:
            raise ValueError(f"商品 {product_id} 不存在。")

        # 检查是否已有相同商品
        result = await db.execute(
            select(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == product_id)
        )
        cart_item = result.scalar_one_or_none()
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
            db.add(cart_item)
        await db.commit()
        await db.refresh(cart_item)
        return cart_item

    @staticmethod
    async def get_cart(db: AsyncSession, user_id: int) -> list[dict]:
        result = await CartService._cart_rows(db, user_id)
        rows = result.all()
        return [
            {
                "id": cart.id,
                "product_id": cart.product_id,
                "product_name": product.name,
                "quantity": cart.quantity,
                "unit_price": product.price,
                "line_total": round(product.price * cart.quantity, 2),
            }
            for cart, product in rows
        ]

    @staticmethod
    async def get_cart_subset(
        db: AsyncSession,
        user_id: int,
        product_ids: list[int] | None = None,
        keyword: str | None = None,
    ) -> list[dict]:
        result = await CartService._cart_rows(db, user_id, product_ids=product_ids, keyword=keyword)
        rows = result.all()
        return [
            {
                "id": cart.id,
                "product_id": cart.product_id,
                "product_name": product.name,
                "quantity": cart.quantity,
                "unit_price": product.price,
                "line_total": round(product.price * cart.quantity, 2),
            }
            for cart, product in rows
        ]

    @staticmethod
    async def _cart_rows(
        db: AsyncSession,
        user_id: int,
        product_ids: list[int] | None = None,
        keyword: str | None = None,
    ):
        query = (
            select(CartItem, Product)
            .join(Product, CartItem.product_id == Product.id)
            .where(CartItem.user_id == user_id)
        )
        if product_ids:
            query = query.where(CartItem.product_id.in_(product_ids))
        if keyword:
            query = query.where(Product.name.ilike(f"%{keyword}%") | Product.category.ilike(f"%{keyword}%"))
        return await db.execute(query)

    @staticmethod
    async def clear_cart(db: AsyncSession, user_id: int):
        await db.execute(delete(CartItem).where(CartItem.user_id == user_id))
        await db.commit()

    @staticmethod
    async def remove_from_cart(db: AsyncSession, user_id: int, product_id: int | None = None, keyword: str | None = None) -> int:
        query = select(CartItem).join(Product, CartItem.product_id == Product.id).where(CartItem.user_id == user_id)
        if product_id:
            query = query.where(CartItem.product_id == product_id)
        if keyword:
            query = query.where(Product.name.ilike(f"%{keyword}%") | Product.category.ilike(f"%{keyword}%"))

        result = await db.execute(query)
        items = result.scalars().all()
        for item in items:
            await db.delete(item)
        await db.commit()
        return len(items)

class OrderService:
    @staticmethod
    async def create_order(
        db: AsyncSession,
        user_id: int,
        product_ids: list[int] | None = None,
        keyword: str | None = None,
    ) -> Order:
        # 获取购物车内容
        result = await CartService._cart_rows(db, user_id, product_ids=product_ids, keyword=keyword)
        rows = result.all()
        if not rows:
            raise ValueError("Cart is empty")

        order = Order(user_id=user_id, status="pending", total_amount=0.0)
        db.add(order)
        await db.flush()

        total = 0.0
        for cart, product in rows:
            item_total = product.price * cart.quantity
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=cart.quantity,
                unit_price=product.price
            )
            db.add(order_item)
            total += item_total

        order.total_amount = total
        # 只移除本次结算范围内的购物车商品，避免“下单购物车里的相机”误结算其他残留商品。
        cart_item_ids = [cart.id for cart, _ in rows]
        await db.execute(delete(CartItem).where(CartItem.user_id == user_id, CartItem.id.in_(cart_item_ids)))
        await db.commit()

        # 重新加载订单，并预加载 items 关系
        reloaded = await db.execute(
            select(Order).options(selectinload(Order.items).selectinload(OrderItem.product)).where(Order.id == order.id)
        )
        order = reloaded.scalar_one()
        return order

    @staticmethod
    async def get_order(db: AsyncSession, order_id: int) -> Order | None:
        result = await db.execute(
            select(Order).options(selectinload(Order.items).selectinload(OrderItem.product)).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_user_orders(db: AsyncSession, user_id: int) -> list[Order]:
        result = await db.execute(
            select(Order).options(selectinload(Order.items).selectinload(OrderItem.product)).where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def update_order_status(db: AsyncSession, order_id: int, status: str) -> Order | None:
        order = await OrderService.get_order(db, order_id)
        if not order:
            return None
        order.status = status
        await db.commit()
        await db.refresh(order)
        return order
