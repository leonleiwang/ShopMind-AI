# backend/app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1 import agent_eval, approvals, auth, chatbot, orders, products, support

# 后续会逐个注册以下路由
# from app.api.v1 import auth
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(chatbot.router, prefix="/chat", tags=["chat"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(support.router, prefix="/support", tags=["support"])
api_router.include_router(agent_eval.router, prefix="/agent-eval", tags=["agent-eval"])

@api_router.get("/health")
def health_check():
    return {"status": "ok"}
