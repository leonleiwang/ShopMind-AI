# 商品 API：提供商品 CRUD、搜索列表、推荐刷新和 AI 运营草稿生成入口。
"""
商品 API 路由
"""

# backend/app/api/v1/products.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService
from app.tasks.ai_tasks import (
    _batch_update_recommendations,
    _generate_marketing_copy,
    _generate_pricing_suggestion,
    _generate_product_description,
    batch_update_recommendations,
    generate_marketing_copy,
    generate_pricing_suggestion,
    generate_product_description,
)

router = APIRouter()


async def _run_ai_operation(task, direct_runner, *args):
    # 统一兼容 Celery 队列模式和本地 eager 同步模式。
    if settings.CELERY_TASK_ALWAYS_EAGER:
        result = await direct_runner(*args)
        return {
            "mode": "sync",
            "task_id": "eager",
            "result": result,
        }
    async_result = task.delay(*args)
    return {"mode": "queued", "task_id": async_result.id}

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 创建商品，当前版本要求已登录用户。
    product = await ProductService.create_product(db, **product_in.model_dump())
    return product

@router.get("/", response_model=list[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db)
):
    # 商品列表查询，支持分页、关键词和品类过滤。
    products = await ProductService.list_products(db, skip=skip, limit=limit, keyword=keyword, category=category)
    return products


@router.post("/recommendations/batch", response_model=dict)
async def generate_recommendations(
    current_user: User = Depends(get_current_user)
):
    # 触发用户级推荐刷新任务，可同步执行或进入 Celery 队列。
    payload = await _run_ai_operation(batch_update_recommendations, _batch_update_recommendations, current_user.id)
    return {
        "message": "Recommendation refresh submitted",
        "user_id": current_user.id,
        **payload,
    }

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    # 获取单个商品详情。
    product = await ProductService.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 更新商品字段，供运营后台和审批写回链路复用。
    product = await ProductService.update_product(db, product_id, product_in.model_dump(exclude_unset=True))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 删除商品，不存在时返回 404。
    success = await ProductService.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")


@router.post("/{product_id}/generate-description", response_model=dict)
async def generate_description(
    product_id: int,
    current_user: User = Depends(get_current_user)
):
    # 生成商品描述草稿，并进入 HITL 审批。
    payload = await _run_ai_operation(generate_product_description, _generate_product_description, product_id, current_user.id)
    return {
        "message": "Description draft submitted for approval",
        "product_id": product_id,
        **payload,
    }


@router.post("/{product_id}/pricing-suggestion", response_model=dict)
async def pricing_suggestion(
    product_id: int,
    current_user: User = Depends(get_current_user)
):
    # 生成定价建议草稿，并进入 HITL 审批。
    payload = await _run_ai_operation(generate_pricing_suggestion, _generate_pricing_suggestion, product_id, current_user.id)
    return {
        "message": "Pricing suggestion draft submitted for approval",
        "product_id": product_id,
        **payload,
    }


@router.post("/{product_id}/marketing-copy", response_model=dict)
async def marketing_copy(
    product_id: int,
    current_user: User = Depends(get_current_user)
):
    # 生成营销文案草稿，并进入 HITL 审批。
    payload = await _run_ai_operation(generate_marketing_copy, _generate_marketing_copy, product_id, current_user.id)
    return {
        "message": "Marketing copy draft submitted for approval",
        "product_id": product_id,
        **payload,
    }
