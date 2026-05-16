# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.mcp.server import router as mcp_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

cors_origins = [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS]

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # 生产环境：使用严格的域名列表；开发/测试环境：可以使用 [*] 方便调试
# # ---------- 企业级 CORS 配置 ----------
# if settings.ENVIRONMENT == "production":
#     # 生产环境：严格使用配置的域名列表，不允许通配符
#     origins = settings.BACKEND_CORS_ORIGINS
# else:
#     # 开发/测试环境：可以放宽为通配符，方便本地调试
#     origins = ["*"]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
#     allow_headers=["*"],  # 根据需要可限制为 ["Authorization", "Content-Type"]
# )

# 挂载 API 路由
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(mcp_router, prefix="/mcp", tags=["mcp"])

@app.get("/")
def root():
    return {"message": "ShopMind AI is running", "version": settings.VERSION}
