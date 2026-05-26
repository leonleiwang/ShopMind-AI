import asyncio
from pathlib import Path
import sys

from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.demo.commerce_seed_data import (
    DEMO_PASSWORD,
    agent_execution_log_samples,
    demo_users,
    generate_product_catalog,
    support_ticket_samples,
    user_preference_samples,
)
from app.models.cart import CartItem
from app.models.demo_data import AgentExecutionLog, UserPreference
from app.models.hitl import ApprovalRequest
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.support import SupportTicket, TicketAIAssist, TicketEvent
from app.services.support_service import AgentAssistService, LLMRoutingService
from app.models.user import User


async def _get_or_create_users(db):
    users = {}
    for item in demo_users():
        result = await db.execute(select(User).where(User.email == item["email"]))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=item["email"],
                full_name=item["full_name"],
                role=item["role"],
                is_superuser=item["role"] == "admin",
                hashed_password=get_password_hash(DEMO_PASSWORD),
            )
            db.add(user)
            await db.flush()
        users[item["email"]] = user
    return users


async def _seed_products(db):
    inserted = 0
    for item in generate_product_catalog(120):
        result = await db.execute(select(Product).where(Product.name == item["name"]))
        product = result.scalar_one_or_none()
        if product is not None:
            for key in ("description", "price", "category", "brand", "image_url", "stock", "attributes", "tags"):
                setattr(product, key, item[key])
            continue
        db.add(Product(**item))
        inserted += 1
    return inserted


async def _seed_preferences(db, users):
    inserted = 0
    for item in user_preference_samples():
        user = users[item.pop("email")]
        result = await db.execute(select(UserPreference).where(UserPreference.user_id == user.id))
        preference = result.scalar_one_or_none()
        if preference:
            for key, value in item.items():
                setattr(preference, key, value)
        else:
            db.add(UserPreference(user_id=user.id, **item))
            inserted += 1
    return inserted


async def _seed_orders_and_cart(db, users):
    shopper = users["shopper@example.com"]
    products = (await db.execute(select(Product).order_by(Product.id).limit(12))).scalars().all()
    if not products:
        return {"orders": 0, "cart_items": 0}

    order_count = await db.scalar(select(func.count(Order.id)).where(Order.user_id == shopper.id))
    inserted_orders = 0
    if (order_count or 0) < 6:
        for index in range(6):
            selected = products[index * 2 : index * 2 + 2]
            order = Order(
                user_id=shopper.id,
                status=["paid", "shipped", "completed", "pending", "cancelled", "paid"][index],
                total_amount=0,
            )
            db.add(order)
            await db.flush()
            total = 0.0
            for product in selected:
                quantity = 1 + index % 2
                db.add(OrderItem(order_id=order.id, product_id=product.id, quantity=quantity, unit_price=product.price))
                total += product.price * quantity
            order.total_amount = round(total, 2)
            inserted_orders += 1

    cart_count = await db.scalar(select(func.count(CartItem.id)).where(CartItem.user_id == shopper.id))
    inserted_cart = 0
    if (cart_count or 0) == 0:
        for product in products[:3]:
            db.add(CartItem(user_id=shopper.id, product_id=product.id, quantity=1))
            inserted_cart += 1
    return {"orders": inserted_orders, "cart_items": inserted_cart}


async def _seed_support_tickets(db, users):
    existing = await db.scalar(select(func.count(SupportTicket.id)))
    inserted = 0
    if not existing:
        for index, item in enumerate(support_ticket_samples()):
            user = users[item.pop("email")]
            details = item.pop("details", {})
            subject = item.get("subject", "")
            category = item.get("category", "general")
            priority = item.get("priority", "normal")
            risk_level = "high" if category in {"complaint"} else "medium" if category in {"refund", "human_handoff"} else "low"
            db.add(
                SupportTicket(
                    ticket_id=f"DEMO-TCK-{index + 1:04d}",
                    user_id=user.id,
                    customer_id=user.id,
                    conversation_id=f"demo-support-conversation-{index + 1:02d}",
                    channel=["web", "app", "chat"][index % 3],
                    assigned_agent="support@example.com" if index % 2 == 0 else "",
                    summary=subject,
                    risk_level=risk_level,
                    handoff_reason="demo_seed_support_case" if category in {"refund", "complaint", "human_handoff"} else "",
                    details={
                        **details,
                        "intent": AgentAssistService.intent_for_category(category),
                        "confidence": 0.86 if risk_level != "high" else 0.74,
                    },
                    **item,
                )
            )
            inserted += 1
        await db.flush()
    assists = await _seed_support_assists(db)
    return {"tickets": inserted, "ai_assists": assists}


async def _seed_support_assists(db):
    inserted = 0
    tickets = (await db.execute(select(SupportTicket).order_by(SupportTicket.id).limit(20))).scalars().all()
    for ticket in tickets:
        event_exists = await db.scalar(select(func.count(TicketEvent.id)).where(TicketEvent.ticket_id == ticket.id))
        if not event_exists:
            db.add(
                TicketEvent(
                    ticket_id=ticket.id,
                    actor_id=ticket.customer_id,
                    event_type="created",
                    to_status=ticket.status,
                    details={"source": "demo_seed", "category": ticket.category, "priority": ticket.priority},
                )
            )
        assist_exists = await db.scalar(select(func.count(TicketAIAssist.id)).where(TicketAIAssist.ticket_id == ticket.id))
        if assist_exists:
            continue
        intent = str((ticket.details or {}).get("intent") or AgentAssistService.intent_for_category(ticket.category))
        confidence = float((ticket.details or {}).get("confidence") or 0.82)
        routing_strategy = LLMRoutingService.route(
            intent=intent,
            category=ticket.category,
            risk_level=ticket.risk_level,
            confidence=confidence,
            message=ticket.summary,
        )
        assist = AgentAssistService.build_assist(
            message=ticket.summary,
            intent=intent,
            confidence=confidence,
            category=ticket.category,
            risk_level=ticket.risk_level,
            routing_strategy=routing_strategy,
            order_snapshot={"order_id": ticket.order_id, "status": "demo"} if ticket.order_id else {},
        )
        db.add(TicketAIAssist(ticket_id=ticket.id, conversation_id=ticket.conversation_id, **assist.model_dump()))
        db.add(
            TicketEvent(
                ticket_id=ticket.id,
                actor_id=None,
                event_type="ai_assist_generated",
                details={"source": "demo_seed", "intent": intent, "routing_strategy": routing_strategy},
            )
        )
        inserted += 1
    return inserted


async def _seed_approval_samples(db, users):
    existing = await db.scalar(select(func.count(ApprovalRequest.id)).where(ApprovalRequest.summary.ilike("[Demo]%")))
    if existing:
        return 0
    shopper = users["shopper@example.com"]
    samples = [
        {
            "action_type": "place_order",
            "risk_level": "high",
            "risk_reasons": ["order_total_over_2000", "large_quantity"],
            "summary": "[Demo] 高金额订单需要人工审核：20 台手机，总金额超过 50000 元",
            "payload": {"source": "demo_seed", "approval_channel": "governance", "confirmation_level": "manual_review"},
        },
        {
            "action_type": "update_product_price",
            "risk_level": "medium",
            "risk_reasons": ["merchant_ai_price_change"],
            "summary": "[Demo] AI 调价建议需要运营审核",
            "payload": {"source": "demo_seed", "draft_type": "pricing_suggestion"},
        },
        {
            "action_type": "publish_marketing_copy",
            "risk_level": "low",
            "risk_reasons": ["merchant_ai_content_draft"],
            "summary": "[Demo] AI 营销文案草稿待发布审核",
            "payload": {"source": "demo_seed", "draft_type": "marketing_copy"},
        },
    ]
    for sample in samples:
        db.add(ApprovalRequest(user_id=shopper.id, status="pending", result={}, **sample))
    return len(samples)


async def _seed_agent_logs(db, users):
    existing = await db.scalar(select(func.count(AgentExecutionLog.id)))
    if existing:
        return 0
    inserted = 0
    for item in agent_execution_log_samples():
        user = users[item.pop("email")]
        db.add(AgentExecutionLog(user_id=user.id, **item))
        inserted += 1
    return inserted


async def main():
    async with AsyncSessionLocal() as db:
        users = await _get_or_create_users(db)
        summary = {
            "products": await _seed_products(db),
            "preferences": await _seed_preferences(db, users),
            **await _seed_orders_and_cart(db, users),
            "support_tickets": await _seed_support_tickets(db, users),
            "approval_samples": await _seed_approval_samples(db, users),
            "agent_logs": await _seed_agent_logs(db, users),
        }
        await db.commit()
        print("Demo data seed completed:")
        for key, value in summary.items():
            print(f"- {key}: {value}")
        print(f"Demo accounts use password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
