"""
Pydantic 校验模型
"""

# backend/app/schemas/product.py

from typing import Any

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str
    description: str = ""
    price: float
    category: str = ""
    brand: str = ""
    image_url: str = ""
    stock: int = 0
    attributes: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    pricing_suggestion: str = ""
    marketing_copy: str = ""

class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    category: str | None = None
    brand: str | None = None
    image_url: str | None = None
    stock: int | None = None
    attributes: dict[str, Any] | None = None
    tags: list[str] | None = None
    pricing_suggestion: str | None = None
    marketing_copy: str | None = None

class ProductResponse(BaseModel):
    id: int
    name: str
    description: str
    price: float
    category: str
    brand: str
    image_url: str
    stock: int
    attributes: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    pricing_suggestion: str | None = ""
    marketing_copy: str | None = ""

    class Config:
        from_attributes = True
