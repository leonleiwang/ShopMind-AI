# backend/app/core/config.py

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 核心应用配置
    PROJECT_NAME: str = "ShopMind AI"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "change-me-for-production"
    ENVIRONMENT: str = "development"

    # 跨域 (CORS) 配置
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",  # Next.js 默认端口
        "http://127.0.0.1:3000",
        "http://localhost:5173"   # Vite 备用
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # # 跨域 (CORS) 配置 —— 企业级方案使用 List[str]，避免 AnyHttpUrl 的类型转化副作用
    # BACKEND_CORS_ORIGINS: List[str] = [
    #     "http://localhost:3000",   # Next.js 开发服务器
    #     "http://127.0.0.1:3000",  # 某些浏览器可能使用 127.0.0.1
    # ]

    # @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    # @classmethod
    # def assemble_cors_origins(cls, v):
    #     # 支持通过环境变量传入逗号分隔的字符串，如 "https://shop.example.com,https://admin.example.com"
    #     if isinstance(v, str) and not v.startswith("["):
    #         return [i.strip() for i in v.split(",") if i.strip()]
    #     return v
    
    # 数据库配置
    DATABASE_URL: str | None = None
    POSTGRES_USER: str = "shopmind"
    POSTGRES_PASSWORD: str = "shopmind"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DATABASE: str = "shopmind"

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            return (
                self.DATABASE_URL
                .replace("postgres://", "postgresql+asyncpg://", 1)
                .replace("postgresql://", "postgresql+asyncpg://", 1)
            )
        return (f"postgresql+asyncpg://{self.POSTGRES_USER}:"
                f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
                f"{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}")

    # Redis 配置
    REDIS_URL: str | None = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    CELERY_TASK_ALWAYS_EAGER: bool = False
    CONVERSATION_STATE_BACKEND: str = "redis"
    CONVERSATION_STATE_TTL_SECONDS: int = 60 * 60 * 24

    @property
    def CELERY_BROKER_URL(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        pw = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{pw}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # JWT 配置
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    # LLM 配置
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_NAME: str = "qwen3-max"
    OPENAI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_TIMEOUT_SECONDS: float = 8.0
    LLM_MAX_RETRIES: int = 2
    LLM_CIRCUIT_BREAKER_THRESHOLD: int = 3
    LLM_CIRCUIT_BREAKER_RESET_SECONDS: int = 30

    # Embedding 配置
    DASHSCOPE_API_KEY: str | None = None
    EMBEDDING_MODEL_NAME: str = "text-embedding-v4"
    EMBEDDING_BASE_URL: str | None = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # 向量数据库配置
    VECTOR_STORE_TYPE: str = "milvus"   # 生产用 "milvus"
    MILVUS_URI: str | None = None
    MILVUS_TOKEN: str | None = None
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    ENABLE_VECTOR_RANKING: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

settings = Settings()
