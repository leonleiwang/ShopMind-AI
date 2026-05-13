"""
Pydantic 校验模型
"""

# backend/app/schemas/product.py
from pydantic import BaseModel
from typing import Optional

class ProductCreate(BaseModel):
    name: str
    description: str = ""
    price: float
    category: str = ""
    brand: str = ""
    image_url: str = ""
    stock: int = 0
    pricing_suggestion: str = ""
    marketing_copy: str = ""

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    stock: Optional[int] = None
    pricing_suggestion: Optional[str] = None
    marketing_copy: Optional[str] = None

class ProductResponse(BaseModel):
    id: int
    name: str
    description: str
    price: float
    category: str
    brand: str
    image_url: str
    stock: int
    pricing_suggestion: Optional[str] = ""
    marketing_copy: Optional[str] = ""

    class Config:
        from_attributes = True
