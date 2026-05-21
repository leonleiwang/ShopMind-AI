"""
API 路由
"""

# backend/app/api/v1/orders.py
import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import AsyncSessionLocal, get_db
from app.models.user import User
from app.schemas.hitl import ApprovalResponse
from app.schemas.order import CartItemCreate, CartItemResponse, OrderResponse, OrderStatusUpdate
from app.services.hitl_service import ApprovalService
from app.services.order_service import CartService, OrderService

router = APIRouter()


class OrderWebSocketManager:
    def __init__(self):
        self.connections: dict[int, list[WebSocket]] = {}

    async def connect(self, order_id: int, websocket: WebSocket):
        await websocket.accept()
        self.connections.setdefault(order_id, []).append(websocket)

    def disconnect(self, order_id: int, websocket: WebSocket):
        sockets = self.connections.get(order_id, [])
        if websocket in sockets:
            sockets.remove(websocket)
        if not sockets and order_id in self.connections:
            del self.connections[order_id]

    async def broadcast(self, order_id: int, payload: dict):
        stale: list[WebSocket] = []
        for websocket in self.connections.get(order_id, []):
            try:
                await websocket.send_text(json.dumps(payload, ensure_ascii=False))
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(order_id, websocket)


order_ws_manager = OrderWebSocketManager()


async def _get_user_from_ws_token(token: str | None, db: AsyncSession) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    result = await db.execute(select(User).where(User.id == int(user_id)))
    return result.scalar_one_or_none()

# ---------- 购物车 ----------
@router.post("/cart", response_model=dict)
async def add_to_cart(
    item: CartItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cart_item = await CartService.add_to_cart(db, current_user.id, item.product_id, item.quantity)
    return {"message": "Added to cart", "cart_item_id": cart_item.id}

@router.get("/cart", response_model=list[CartItemResponse])
async def view_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await CartService.get_cart(db, current_user.id)

@router.delete("/cart", response_model=dict)
async def clear_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await CartService.clear_cart(db, current_user.id)
    return {"message": "Cart cleared"}

# [反思5c-风险点接入HITL] 订单审批入口：下单前先生成审批请求，确认后才真正创建订单；订单状态更新后通过 WebSocket 广播给用户
@router.post("/checkout-approval", response_model=ApprovalResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_checkout_approval(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        approval = await ApprovalService.create_order_approval(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return approval


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_order(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        order = await OrderService.create_order(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await order_ws_manager.broadcast(
        order.id,
        {"event": "created", "order_id": order.id, "status": order.status, "total_amount": order.total_amount},
    )
    return order

@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    orders = await OrderService.list_user_orders(db, current_user.id)
    return orders

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = await OrderService.get_order(db, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing_order = await OrderService.get_order(db, order_id)
    if not existing_order or existing_order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    order = await OrderService.update_order_status(db, order_id, status_update.status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await order_ws_manager.broadcast(
        order_id,
        {"event": "status_updated", "order_id": order.id, "status": order.status, "total_amount": order.total_amount},
    )
    return order


@router.websocket("/ws/{order_id}")
async def order_status_ws(websocket: WebSocket, order_id: int, token: str | None = None):
    async with AsyncSessionLocal() as db:
        user = await _get_user_from_ws_token(token, db)
        if user is None:
            await websocket.close(code=1008)
            return
        order = await OrderService.get_order(db, order_id)
        if order is None or order.user_id != user.id:
            await websocket.close(code=1008)
            return

        await order_ws_manager.connect(order_id, websocket)
        await websocket.send_text(
            json.dumps(
                {
                    "event": "snapshot",
                    "order_id": order.id,
                    "status": order.status,
                    "total_amount": order.total_amount,
                },
                ensure_ascii=False,
            )
        )
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            order_ws_manager.disconnect(order_id, websocket)
