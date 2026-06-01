# 用户服务：负责注册、密码校验、登录认证和角色归一化。
"""
业务逻辑层
"""

# backend/app/services/user_service.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User


class UserService:
    @staticmethod
    async def create_user(db: AsyncSession, email: str, password: str, full_name: str = "", role: str = "shopper") -> User:
        # 创建用户前检查邮箱唯一性，并保存 bcrypt 哈希密码。
        # 检查邮箱是否已注册
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("Email already registered")
        
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=UserService.normalize_role(role),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
        # 登录认证：校验邮箱、密码和账号启用状态。
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    @staticmethod
    def normalize_role(role: str | None) -> str:
        # 统一角色别名，未知角色回退为 shopper。
        normalized = (role or "shopper").strip().lower()
        aliases = {
            "operator": "merchant",
            "agentops": "admin",
            "developer": "admin",
        }
        normalized = aliases.get(normalized, normalized)
        return normalized if normalized in {"shopper", "merchant", "support", "admin"} else "shopper"
