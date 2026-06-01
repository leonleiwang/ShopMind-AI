# HITL 审批服务：统一管理高风险下单、AI 运营草稿、人工审批、执行落库和审计日志。
import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.config import settings
from app.models.hitl import ApprovalAuditLog, ApprovalRequest
from app.services.order_service import CartService, OrderService
from app.services.product_service import ProductService

# 2. [反思5a-统一审批层] 包含订单审批、风险分级、AI 运营草稿审批、Approve/Reject 执行和审计日志
class ApprovalService:
    ORDER_ACTION = "place_order"
    PRODUCT_FIELD_ACTIONS = {
        "product_description_update": "description",
        "pricing_suggestion_update": "pricing_suggestion",
        "marketing_copy_update": "marketing_copy",
    }

    @staticmethod
    async def create_order_approval(
        db: AsyncSession,
        user_id: int,
        product_ids: list[int] | None = None,
        keyword: str | None = None,
    ) -> ApprovalRequest:
        # 根据购物车子集创建下单审批，保存风险等级、确认级别和订单快照。
        cart_items = await CartService.get_cart_subset(db, user_id, product_ids=product_ids, keyword=keyword)
        if not cart_items:
            raise ValueError("Cart is empty")

        total = ApprovalService._cart_total(cart_items)
        risk = ApprovalService.evaluate_order_risk(cart_items, total)
        payload = {
            "items": cart_items,
            "total_amount": total,
            "cart_signature": ApprovalService._cart_signature(cart_items),
            "payment_method": "demo_default",
            "shipping_address": "demo_default_address",
            "approval_channel": risk["approval_channel"],
            "confirmation_level": risk["confirmation_level"],
            "checkout_scope": {
                "product_ids": product_ids or [],
                "keyword": keyword or "",
            },
        }
        summary = ApprovalService._order_summary(payload)
        approval = ApprovalRequest(
            user_id=user_id,
            action_type=ApprovalService.ORDER_ACTION,
            status="pending",
            risk_level=risk["risk_level"],
            risk_reasons=risk["risk_reasons"],
            summary=summary,
            payload=payload,
        )
        db.add(approval)
        await db.flush()
        await ApprovalService._audit(
            db,
            approval.id,
            user_id,
            "approval_requested",
            {
                "action_type": approval.action_type,
                "risk_level": approval.risk_level,
                "approval_channel": risk["approval_channel"],
            },
        )
        await db.commit()
        await db.refresh(approval)
        return approval

    # 2. [反思5c-订单风险分层] LOW：Chat 普通确认 / MEDIUM：Chat 二次确认 / HIGH：Governance 后台人工审核
    @staticmethod
    def evaluate_order_risk(cart_items: list[dict], total: float) -> dict[str, Any]:
        # 订单风险分层：普通确认、二次确认和治理后台人工审核三档。
        reasons: list[str] = []
        risk_level = "low"
        approval_channel = "chat"
        confirmation_level = "standard"
        high_value_threshold = settings.HITL_HIGH_VALUE_ORDER_THRESHOLD
        manual_review_threshold = settings.HITL_MANUAL_REVIEW_ORDER_THRESHOLD

        if any(item.get("quantity", 0) >= settings.HITL_ABNORMAL_QUANTITY_THRESHOLD for item in cart_items):
            risk_level = "high"
            approval_channel = "governance"
            confirmation_level = "manual_review"
            reasons.append("abnormal_quantity")

        if approval_channel != "governance":
            if total >= manual_review_threshold:
                risk_level = "high"
                confirmation_level = "strong_confirm"
                reasons.append(f"order_total_over_{manual_review_threshold:g}")
            elif total >= high_value_threshold:
                risk_level = "medium"
                confirmation_level = "double_confirm"
                reasons.append(f"order_total_over_{high_value_threshold:g}")
            if risk_level != "high" and any(item.get("quantity", 0) >= settings.HITL_LARGE_QUANTITY_THRESHOLD for item in cart_items):
                risk_level = "medium"
                confirmation_level = "double_confirm"
                reasons.append("large_quantity")
            if risk_level != "high" and any(float(item.get("unit_price") or 0) >= high_value_threshold for item in cart_items):
                risk_level = "medium"
                confirmation_level = "double_confirm"
                reasons.append("high_price_item")

        if not reasons:
            reasons.append("standard_checkout_confirmation")
        return {
            "risk_level": risk_level,
            "risk_reasons": reasons,
            "approval_channel": approval_channel,
            "confirmation_level": confirmation_level,
        }

    @staticmethod
    async def create_product_draft(
        db: AsyncSession,
        user_id: int,
        product_id: int,
        action_type: str,
        generated_value: Any,
        metadata: dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        # AI 生成的商品描述、定价建议和营销文案先进入草稿审批，不直接改线上商品。
        if action_type not in ApprovalService.PRODUCT_FIELD_ACTIONS:
            raise ValueError("Unsupported product draft action")

        product = await ProductService.get_product(db, product_id)
        if not product:
            raise ValueError("Product not found")

        field_name = ApprovalService.PRODUCT_FIELD_ACTIONS[action_type]
        payload = {
            "product_id": product.id,
            "product_name": product.name,
            "field": field_name,
            "current_value": getattr(product, field_name, ""),
            "draft_value": generated_value,
            "metadata": metadata or {},
        }
        approval = ApprovalRequest(
            user_id=user_id,
            action_type=action_type,
            status="pending",
            risk_level="medium",
            risk_reasons=["merchant_content_requires_review"],
            summary=ApprovalService._product_draft_summary(payload),
            payload=payload,
        )
        db.add(approval)
        await db.flush()
        await ApprovalService._audit(
            db,
            approval.id,
            user_id,
            "draft_created",
            {"action_type": action_type, "product_id": product.id, "field": field_name},
        )
        await db.commit()
        await db.refresh(approval)
        return approval

    @staticmethod
    async def approve(
        db: AsyncSession,
        approval_id: int,
        user_id: int,
        note: str = "",
        payload_override: dict[str, Any] | None = None,
    ) -> ApprovalRequest | None:
        # 审批通过后执行对应业务动作，并写入 approved 审计事件。
        approval = await ApprovalService.get(db, approval_id)
        if not approval or approval.user_id != user_id:
            return None
        if approval.status != "pending":
            raise ValueError(f"Approval request is already {approval.status}")

        if payload_override:
            approval.payload = {**(approval.payload or {}), **payload_override}

        if approval.action_type == ApprovalService.ORDER_ACTION:
            result = await ApprovalService._execute_order_approval(db, approval, user_id)
        elif approval.action_type in ApprovalService.PRODUCT_FIELD_ACTIONS:
            result = await ApprovalService._apply_product_draft(db, approval)
        else:
            raise ValueError("Unsupported approval action")

        approval.status = "executed"
        approval.result = result
        approval.reviewed_at = func.now()
        await ApprovalService._audit(
            db,
            approval.id,
            user_id,
            "approved",
            {"note": note, "result": result},
        )
        await db.commit()
        await db.refresh(approval)
        return approval

    @staticmethod
    async def reject(db: AsyncSession, approval_id: int, user_id: int, note: str = "") -> ApprovalRequest | None:
        # 拒绝审批时仅更新状态和审计，不执行原业务动作。
        approval = await ApprovalService.get(db, approval_id)
        if not approval or approval.user_id != user_id:
            return None
        if approval.status != "pending":
            raise ValueError(f"Approval request is already {approval.status}")

        approval.status = "rejected"
        approval.reviewed_at = func.now()
        await ApprovalService._audit(db, approval.id, user_id, "rejected", {"note": note})
        await db.commit()
        await db.refresh(approval)
        return approval

    @staticmethod
    async def get(db: AsyncSession, approval_id: int) -> ApprovalRequest | None:
        # 读取单个审批请求。
        result = await db.execute(select(ApprovalRequest).where(ApprovalRequest.id == approval_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_user_approvals(
        db: AsyncSession,
        user_id: int,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ApprovalRequest]:
        # 查询用户审批列表，支撑 Governance 页面和 Chat 审批状态展示。
        query = select(ApprovalRequest).where(ApprovalRequest.user_id == user_id)
        if status:
            query = query.where(ApprovalRequest.status == status)
        query = query.order_by(ApprovalRequest.created_at.desc()).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def list_audit_logs(db: AsyncSession, user_id: int, limit: int = 80) -> list[ApprovalAuditLog]:
        # 查询用户审批审计日志，保留请求、通过、拒绝和执行信息。
        query = (
            select(ApprovalAuditLog)
            .where(ApprovalAuditLog.user_id == user_id)
            .order_by(ApprovalAuditLog.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def _execute_order_approval(db: AsyncSession, approval: ApprovalRequest, user_id: int) -> dict[str, Any]:
        # 执行已通过的下单审批，防止 Agent 在未授权时直接创建订单。
        checkout_scope = (approval.payload or {}).get("checkout_scope") or {}
        product_ids = checkout_scope.get("product_ids") or None
        keyword = checkout_scope.get("keyword") or None
        current_cart = await CartService.get_cart_subset(db, user_id, product_ids=product_ids, keyword=keyword)
        expected_signature = (approval.payload or {}).get("cart_signature")
        if expected_signature != ApprovalService._cart_signature(current_cart):
            raise ValueError("Cart changed after approval was requested. Please create a new approval request.")

        order = await OrderService.create_order(db, user_id, product_ids=product_ids, keyword=keyword)
        return {"order_id": order.id, "status": order.status, "total_amount": order.total_amount}

    @staticmethod
    async def _apply_product_draft(db: AsyncSession, approval: ApprovalRequest) -> dict[str, Any]:
        # 将通过审批的 AI 运营草稿写回商品字段。
        payload = approval.payload or {}
        product_id = int(payload.get("product_id"))
        field = ApprovalService.PRODUCT_FIELD_ACTIONS[approval.action_type]
        draft_value = payload.get("draft_value")
        product = await ProductService.update_product(db, product_id, {field: draft_value})
        if not product:
            raise ValueError("Product not found")
        return {"product_id": product.id, "field": field, "applied": True}

    @staticmethod
    async def _audit(
        db: AsyncSession,
        approval_id: int,
        user_id: int,
        event: str,
        details: dict[str, Any],
    ) -> None:
        # 审批审计统一入口，记录 actor、事件类型和结构化细节。
        db.add(
            ApprovalAuditLog(
                approval_id=approval_id,
                user_id=user_id,
                event=event,
                details=details,
            )
        )

    @staticmethod
    def _cart_total(cart_items: list[dict]) -> float:
        # 根据购物车快照计算审批金额。
        return round(sum(float(item["unit_price"]) * int(item["quantity"]) for item in cart_items), 2)

    @staticmethod
    def _cart_signature(cart_items: list[dict]) -> str:
        # 生成购物车签名，帮助识别审批后购物车是否发生变化。
        normalized = [
            {
                "product_id": item.get("product_id"),
                "quantity": item.get("quantity"),
                "unit_price": float(item.get("unit_price") or 0),
            }
            for item in sorted(cart_items, key=lambda item: int(item.get("product_id") or 0))
        ]
        raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _order_summary(payload: dict[str, Any]) -> str:
        # 生成审批卡片中的订单摘要，突出商品、数量和总金额。
        item_lines = [
            f"- {item['product_name']} x {item['quantity']} @ {item['unit_price']}"
            for item in payload.get("items", [])
        ]
        return "\n".join(
            [
                ApprovalService._order_summary_title(payload),
                *item_lines,
                f"Total: {payload.get('total_amount')}",
                f"Shipping address: {payload.get('shipping_address')}",
                f"Payment method: {payload.get('payment_method')}",
            ]
        )

    @staticmethod
    def _order_summary_title(payload: dict[str, Any]) -> str:
        # 根据确认级别生成更醒目的订单审批标题。
        if payload.get("approval_channel") == "governance":
            return "Manual review required before checkout"
        if payload.get("confirmation_level") == "strong_confirm":
            return "High-risk purchase confirmation required"
        if payload.get("confirmation_level") == "double_confirm":
            return "High-value order confirmation required"
        return "Order confirmation required"

    @staticmethod
    def _product_draft_summary(payload: dict[str, Any]) -> str:
        # 生成 AI 商品运营草稿审批摘要。
        return (
            f"AI draft approval required for {payload.get('product_name')} "
            f"({payload.get('field')}). Review, edit, approve, or reject before publishing."
        )
