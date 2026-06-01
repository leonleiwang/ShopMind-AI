# 安全工具：提供 bcrypt 密码哈希/校验和 JWT access token 签发。
# backend/app/core/security.py
from datetime import datetime, timedelta

import bcrypt
from jose import jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # 校验明文密码与 bcrypt 哈希是否匹配。
    pwd_bytes = plain_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    # 生成 bcrypt 哈希密码。
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    # 签发 JWT，并写入过期时间。
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
