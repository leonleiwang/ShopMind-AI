"""
Schema 定义
"""

# backend/app/schemas/order.py
from datetime import datetime

from pydantic import BaseModel


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1

class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str = ""
    quantity: int
    unit_price: float = 0.0
    line_total: float = 0.0

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str = ""
    quantity: int
    unit_price: float

class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: str
    total_amount: float
    created_at: datetime | None = None
    items: list[OrderItemResponse] = []

    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: str
