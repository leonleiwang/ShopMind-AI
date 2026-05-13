# backend/app/db/base.py
from sqlalchemy.ext.asyncio import AsyncAttrs  # 可选，方便异步
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase, AsyncAttrs):
    pass