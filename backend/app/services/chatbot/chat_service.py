"""
对话服务（核心）
"""

# backend/app/services/chatbot/chat_service.py
import asyncio
import json
import re
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_gateway import llm_gateway
from app.services.chatbot.agents.cart_order import CartOrderAgent
from app.services.chatbot.agents.comparison import ComparisonAgent
from app.services.chatbot.agents.conversation import (
    ClarificationAgent,
    conversation_store,
)
from app.services.chatbot.agents.intent_router import IntentRouterAgent
from app.services.chatbot.agents.planning import PlanningAgent
from app.services.chatbot.agents.product_search import ProductSearchAgent
from app.services.chatbot.agents.recommendation import RecommendationAgent
from app.services.chatbot.prompts import prompt_manager
from app.services.chatbot.tools.caller import ToolCaller
from app.services.chatbot.tools.cart_tools import AddToCartTool, ClearCartTool, ViewCartTool
from app.services.chatbot.tools.order_tools import CheckOrderTool, PlaceOrderTool
from app.services.chatbot.tools.product_compare import ProductCompareTool
from app.services.chatbot.tools.product_search import ProductSearchTool
from app.services.chatbot.tools.registry import ToolRegistry
from app.services.observability import AgentObservability


class ChatService:
    def __init__(self, db: AsyncSession, user_id: int, conversation_id: str | None = None):
        self.db = db
        self.user_id = user_id
        self.state = conversation_store.get(user_id, conversation_id)
        self.llm = llm_gateway
        self.tool_registry = ToolRegistry()
        self.tool_caller = ToolCaller(self.tool_registry)
        self._register_tools()
        self.router = IntentRouterAgent(tool_schemas=self.tool_caller.get_tool_schemas())
        self.clarification = ClarificationAgent()
        self.planning = PlanningAgent()
        self.product_search = ProductSearchAgent(self.tool_caller)
        self.recommendation = RecommendationAgent(self.tool_caller)
        self.comparison = ComparisonAgent(self.tool_caller)
        self.cart_order = CartOrderAgent(self.tool_caller)

    def _register_tools(self):
        self.tool_registry.register(ProductSearchTool(self.db))
        self.tool_registry.register(ProductCompareTool(self.db))
        self.tool_registry.register(AddToCartTool(self.db, self.user_id))
        self.tool_registry.register(ViewCartTool(self.db, self.user_id))
        self.tool_registry.register(ClearCartTool(self.db, self.user_id))
        self.tool_registry.register(PlaceOrderTool(self.db, self.user_id))
        self.tool_registry.register(CheckOrderTool(self.db))

    async def process_message(self, user_message: str) -> AsyncGenerator[dict, None]:
        self._remember("user", user_message)

        # 1. [反思1b-有依据路由] 识别意图并输出置信度、依据、缺失槽位
        route = await self.router.route_decision(user_message)
        intent = route.intent
        self.state.last_intent = intent
        AgentObservability.record_intent(intent, user_message)
        yield self._event(
            "intent",
            {
                "intent": intent,
                "confidence": route.confidence,
                "evidence": route.evidence,
                "required_slots": route.required_slots,
                "conversation_id": self.state.conversation_id,
            },
        )
        await asyncio.sleep(0.3)

        params = await self._extract_search_params(user_message) if intent in {"search", "recommend"} else {}
        clarification = self.clarification.inspect(user_message, intent, params)
        if intent == "clarify" or clarification["needs_clarification"] or route.required_slots:
            self.state.pending_slots = list(dict.fromkeys(route.required_slots + clarification["required_slots"]))
            content = self._format_clarification(clarification)
            self._remember("assistant", content)
            yield self._event(
                "final",
                {
                    "content": content,
                    "conversation_id": self.state.conversation_id,
                    "required_slots": self.state.pending_slots,
                },
            )
            return

        try:
            # 2. 针对不同意图处理
            if intent == "plan":
                # 复杂任务：生成计划并逐步执行
                async for event in self._handle_plan(user_message):
                    yield event
            elif intent == "search":
                async for event in self._handle_search(user_message, params):
                    yield event
            elif intent == "compare":
                final = await self.comparison.compare(user_message, self.state.history)
                self._remember("assistant", final)
                yield self._event("final", {"content": final, "conversation_id": self.state.conversation_id})
            elif intent == "recommend":
                final = await self.recommendation.recommend(params)
                self.state.last_products = final["products"]
                self._remember("assistant", final["text"])
                yield self._event("final", {"content": final["text"], "conversation_id": self.state.conversation_id})
            elif intent in ["cart", "order"]:
                final = await self.cart_order.handle(user_message, intent)
                self._remember("assistant", final)
                yield self._event("final", {"content": final, "conversation_id": self.state.conversation_id})
            else:
                content = "我可以帮你搜索、比较商品、管理购物车和下单。试着说“推荐一款蓝牙耳机并下单”吧！"
                self._remember("assistant", content)
                yield self._event("final", {"content": content, "conversation_id": self.state.conversation_id})
        except Exception:
            content = self._human_handoff_text()
            self._remember("assistant", content)
            yield self._event("final", {"content": content, "conversation_id": self.state.conversation_id, "degraded": True})

    @staticmethod
    def _event(event: str, payload: dict) -> dict:
        AgentObservability.record_event(event)
        return {"event": event, "data": json.dumps(payload, ensure_ascii=False)}

    async def _handle_search(self, user_message: str, params: dict | None = None):
        # 1. 提取搜索参数
        params = params or await self._extract_search_params(user_message)

        # 2. 执行搜索
        search_result = await self.product_search.search(params)
        result = search_result["products"]
        self.state.last_products = result
        conversation_store.save(self.state)
        yield self._event("thought", {"content": "正在搜索商品..."})
        yield self._event("action", {"tool": "search_products", "input": params})
        yield self._event("observation", {"content": f"找到 {len(result)} 件商品"})

        # 3. 生成最终回答
        self._remember("assistant", search_result["text"])
        yield self._event("final", {"content": search_result["text"], "conversation_id": self.state.conversation_id})

    async def _extract_search_params(self, user_message: str) -> dict:
        fallback = self._extract_search_params_by_rules(user_message)
        extract_prompt = prompt_manager.render("search_params", user_message=user_message)
        try:
            resp = await self.llm.ainvoke(extract_prompt, fallback_content="{}")
            params = self._parse_json_object(resp.content)
        except Exception:
            params = {}
        return self._normalize_search_params(params, fallback)

    @staticmethod
    def _format_clarification(clarification: dict) -> str:
        question = clarification.get("question") or "我需要再确认一个关键信息，才能继续处理。"
        options = clarification.get("options") or []
        if not options:
            return question
        return question + "\n可选方向：" + " / ".join(options)

    @staticmethod
    def _human_handoff_text() -> str:
        return "当前智能客服链路繁忙或工具调用失败，我先为你保留上下文。你可以稍后重试，或转人工继续处理。"

    @staticmethod
    def _parse_json_object(content: str) -> dict:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _extract_search_params_by_rules(user_message: str) -> dict:
        text = user_message.strip()
        params: dict[str, Any] = {"keyword": text, "category": None, "max_price": None, "min_price": None}

        product_keywords = ["蓝牙耳机", "耳机", "手机", "笔记本", "电脑", "键盘", "鼠标", "充电器", "显示器"]
        for keyword in product_keywords:
            if keyword in text:
                params["keyword"] = keyword
                break

        if any(word in text for word in ["电子产品", "数码产品", "电子类"]):
            params["category"] = "电子"
            if params["keyword"] == text:
                params["keyword"] = ""

        max_match = re.search(r"(\d+(?:\.\d+)?)\s*元?\s*(?:以下|以内|内|之内)|(?:低于|小于|不超过|不高于)\s*(\d+(?:\.\d+)?)", text)
        if max_match:
            params["max_price"] = float(next(group for group in max_match.groups() if group))

        min_match = re.search(r"(\d+(?:\.\d+)?)\s*元?\s*(?:以上|起)|(?:高于|大于|不少于|不低于)\s*(\d+(?:\.\d+)?)", text)
        if min_match:
            params["min_price"] = float(next(group for group in min_match.groups() if group))

        return params

    @staticmethod
    def _normalize_search_params(params: dict, fallback: dict) -> dict:
        invalid_values = {"", "0", "none", "null", "不限", "全部", "任意"}

        def clean_text(value: Any) -> str:
            if value is None:
                return ""
            text = str(value).strip()
            return "" if text.lower() in invalid_values else text

        keyword = clean_text(params.get("keyword")) or clean_text(fallback.get("keyword"))
        category = clean_text(params.get("category")) or clean_text(fallback.get("category"))
        fallback_keyword = clean_text(fallback.get("keyword"))

        if fallback_keyword and (not keyword or len(keyword) > len(fallback_keyword) + 4):
            keyword = fallback_keyword

        if category in {"电子产品", "数码产品"}:
            category = "电子"
        if category and keyword and category == keyword:
            category = ""
        if keyword in {"电子产品", "数码产品", "电子类"} and category:
            keyword = ""

        normalized = {
            "keyword": keyword,
            "category": category or None,
            "max_price": ChatService._clean_number(params.get("max_price"), fallback.get("max_price")),
            "min_price": ChatService._clean_number(params.get("min_price"), fallback.get("min_price")),
        }
        return normalized

    @staticmethod
    def _clean_number(primary: Any, fallback: Any) -> float | None:
        for value in (primary, fallback):
            if value in (None, "", "null", "None"):
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None

    async def _handle_plan(self, user_message: str):
        plan = await self.planning.create_plan(user_message)
        if not plan:
            yield self._event("final", {"content": "抱歉，我没有理解你的要求，请再试一次。"})
            return

        # 用于在步骤间传递数据，例如推荐出的商品列表
        context = {}

        for step in plan:
            intent = step.get("intent")
            params = step.get("params", {})
            step_desc = step.get("description", "")
            yield self._event("thought", {"content": f"执行步骤：{step_desc}"})

            # 处理参数中的占位符 FROM_PREVIOUS
            resolved_params = {}
            for key, value in params.items():
                if value == "FROM_PREVIOUS":
                    # 尝试从上下文中获取 product_id（例如推荐结果中的第一个商品 ID）
                    if "last_products" in context and context["last_products"]:
                        # 取第一个商品
                        resolved_params[key] = context["last_products"][0].get("id")
                else:
                    resolved_params[key] = value

            # 执行对应工具
            try:
                if intent == "search":
                    resolved_params = self._normalize_search_params(resolved_params, self._extract_search_params_by_rules(step_desc))
                    result = await self.tool_caller.invoke("search_products", **resolved_params)
                    context["last_products"] = result
                elif intent == "compare":
                    result = await self.tool_caller.invoke("compare_products", product_ids=resolved_params.get("product_ids", []))
                elif intent == "clear_cart":
                    result = await self.tool_caller.invoke("clear_cart")
                elif intent == "cart":
                    # 确保有 product_id
                    if "product_id" not in resolved_params:
                        raise ValueError("缺少 product_id，无法加入购物车")
                    result = await self.tool_caller.invoke("add_to_cart", **resolved_params)
                elif intent == "order":
                    result = await self.tool_caller.invoke("place_order")
                elif intent == "recommend":
                    resolved_params = self._normalize_search_params(resolved_params, self._extract_search_params_by_rules(step_desc))
                    rec_result = await self.recommendation.recommend(resolved_params)
                    context["last_products"] = rec_result["products"]
                    result = rec_result["text"]    
                # elif intent == "recommend":
                #     rec_result = await self.recommendation.recommend(resolved_params)
                #     # recommend 返回字符串，但我们需要结构化数据以传给下一步，所以重新搜索一次获取完整商品列表
                #     products = await ToolCaller.invoke("search_products", **resolved_params)
                #     context["last_products"] = products
                #     result = rec_result  # 用于显示
                else:
                    result = f"不支持的步骤：{intent}"
            except Exception as e:
                result = str(e)

            # 输出本步结果
            result_text = self._format_step_result(intent, result, resolved_params)
            yield self._event("observation", {"content": result_text})
            context["last_result_text"] = result_text
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict) and "id" in result[0]:
                context["last_products"] = result  # 保存商品列表

        # 生成最终答案
        final_parts = []
        if "last_result_text" in context:
            final_parts.append(context["last_result_text"])
        else:
            final_parts.append("计划执行完毕。")
        final_text = "\n".join(final_parts)
        self._remember("assistant", final_text)
        yield self._event("final", {"content": final_text, "conversation_id": self.state.conversation_id})

    @staticmethod
    def _format_step_result(intent: str, result: Any, params: dict) -> str:
        if isinstance(result, str):
            return result
        if isinstance(result, dict) and "error" in result:
            return str(result["error"])
        if intent == "clear_cart":
            return "购物车已清空。"
        if intent == "cart":
            return f"已添加商品 {params.get('product_id')} 到购物车，数量 {params.get('quantity', 1)}。"
        if intent == "order" and isinstance(result, dict):
            return f"下单成功！订单号 {result.get('order_id')}，总金额 ¥{result.get('total_amount')}。"
        if intent == "search" and isinstance(result, list):
            if not result:
                return "没有找到符合条件的商品，试试换个关键词吧～"
            products = "\n".join([f"- 商品{p['id']}：{p['name']} (¥{p['price']})" for p in result[:5]])
            return f"为你找到以下商品：\n{products}"
        if intent == "compare" and isinstance(result, list):
            if not result:
                return "未找到这些商品。"
            return "商品对比：\n" + "\n".join([f"- 商品{p['id']}：{p['name']}，¥{p['price']}" for p in result])
        return json.dumps(result, ensure_ascii=False)

    def _remember(self, role: str, content: str) -> None:
        self.state.add_message(role, content)
        conversation_store.save(self.state)

    
