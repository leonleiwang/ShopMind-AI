# Planning Agent：把多步购物请求拆成可执行工具计划，优先使用确定性规划，LLM 作为补充。
# backend/app/services/chatbot/agents/planning.py
import json
import re

from app.core.llm_gateway import llm_gateway
from app.services.chatbot.product_resolver import ShoppingRequestParser
from app.services.chatbot.prompts import prompt_manager


class PlanningAgent:
    def __init__(self):
        # 使用统一 LLM 网关，自动继承 timeout/retry/fallback 能力。
        self.llm = llm_gateway

    async def create_plan(self, user_message: str) -> list[dict]:
        # 创建执行计划：确定性计划命中时直接返回，否则尝试 LLM 规划。
        deterministic_plan = self._create_deterministic_plan(user_message)
        if deterministic_plan:
            return deterministic_plan

        prompt = prompt_manager.render("planning", user_message=user_message)
        resp = await self.llm.ainvoke(prompt, fallback_content="[]")
        try:
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:].strip()
            plan = json.loads(content)
            return plan
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _create_deterministic_plan(user_message: str) -> list[dict]:
        # 稳定处理“搜索/解析商品/加购/结算/移除购物车”等组合意图。
        text = user_message.strip()
        request = ShoppingRequestParser.parse(text)
        plan: list[dict] = []

        remove_cart_requested = any(
            word in text
            for word in ["取消购物车", "从购物车移除", "移除购物车", "删除购物车", "从购物车删除", "remove from cart"]
        )

        if "清空购物车" in text or "清空" in text:
            plan.append({"intent": "clear_cart", "description": "清空购物车", "params": {}})

        product_match = re.search(r"(?:商品|product|id)\s*#?\s*(\d+)|#\s*(\d+)", text, re.IGNORECASE)
        product_id = int(next(group for group in product_match.groups() if group)) if product_match else None

        add_to_cart_requested = "add_to_cart" in request.actions
        checkout_requested = request.requires_checkout
        explicit_current_cart_checkout = any(
            phrase in text for phrase in ["结算当前购物车", "当前购物车下单", "结算购物车", "购物车结算"]
        )
        checkout_then_recommend = checkout_requested and "recommend" in request.actions and bool(
            re.search(r"(下单|结算).*(然后|再|并且).*推荐", text)
        )
        if checkout_then_recommend:
            return [{"intent": "order", "description": "先结算当前已选商品", "params": {}}]

        if remove_cart_requested and request.product_query:
            plan.append(
                {
                    "intent": "remove_cart",
                    "description": "从购物车移除匹配商品",
                    "params": {"keyword": request.product_query},
                }
            )
            if checkout_requested:
                plan.append({"intent": "order", "description": "提交剩余购物车订单", "params": {}})
            return plan

        cart_scoped_checkout = checkout_requested and any(
            word in text for word in ["购物车里的", "购物车中", "已经加入购物车", "已加入购物车", "加入购物车的", "刚刚推荐已经加入购物车", "刚才推荐已经加入购物车"]
        )
        if cart_scoped_checkout:
            order_params = {"product_id": product_id} if product_id else ({"keyword": request.product_query} if request.product_query else {})
            plan.append({"intent": "order", "description": "结算购物车中已匹配的商品", "params": order_params})
            return plan

        if product_id and add_to_cart_requested:
            plan.append(
                {
                    "intent": "cart",
                    "description": f"将商品 {product_id} 加入购物车",
                    "params": {"product_id": product_id, "quantity": request.quantity},
                }
            )
        elif request.requires_product_resolution and (
            add_to_cart_requested or checkout_requested or "recommend" in request.actions or "search" in request.actions
        ):
            plan.append(
                {
                    "intent": "resolve_product",
                    "description": "解析自然语言商品需求并选择具体商品",
                    "params": {"query": text},
                }
            )
            if add_to_cart_requested or checkout_requested:
                plan.append(
                    {
                        "intent": "cart",
                        "description": "将解析出的商品加入购物车",
                        "params": {"product_id": "FROM_RESOLVED_PRODUCT", "quantity": request.quantity},
                    }
                )

        if checkout_requested and (
            product_id or request.requires_product_resolution or explicit_current_cart_checkout or self_contained_cart_checkout(text)
        ):
            plan.append({"intent": "order", "description": "提交订单", "params": {}})

        if len(plan) > 1:
            return plan
        if plan and plan[0].get("intent") == "resolve_product":
            return plan
        return []

    @staticmethod
    def _needs_product_resolution(text: str) -> bool:
        # 判断当前请求是否需要先解析具体商品再执行工具。
        request = ShoppingRequestParser.parse(text)
        return request.requires_product_resolution


def self_contained_cart_checkout(text: str) -> bool:
    # 判断用户是否在结算当前购物车，而不是要求解析新的商品。
    product_words = ["蓝牙耳机", "耳机", "手机", "平板", "电脑", "键盘", "鼠标", "显示器", "相机", "电视", "冰箱", "空调", "Pro", "Lite"]
    cart_words = ["购物车", "已选", "当前"]
    return any(word in text for word in cart_words) and not any(word in text for word in product_words)
