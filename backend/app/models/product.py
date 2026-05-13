"""
商品数据模型
"""

# backend/app/models/product.py
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, default="")
    price = Column(Float, nullable=False, default=0.0)
    category = Column(String(100), default="")
    brand = Column(String(100), default="")
    image_url = Column(String(500), default="")
    stock = Column(Integer, default=0)
    pricing_suggestion = Column(Text, default="")
    marketing_copy = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
