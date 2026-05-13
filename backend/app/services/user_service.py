"""
业务逻辑层
"""

# backend/app/services/user_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.core.security import get_password_hash, verify_password

class UserService:
    @staticmethod
    async def create_user(db: AsyncSession, email: str, password: str, full_name: str = "") -> User:
        # 检查邮箱是否已注册
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("Email already registered")
        
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user