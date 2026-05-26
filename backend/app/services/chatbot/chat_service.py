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

from app.core.config import settings
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
from app.services.chatbot.product_resolver import ProductResolution, ProductResolver, ShoppingRequestParser
from app.services.chatbot.tools.caller import ToolCaller
from app.services.chatbot.tools.cart_tools import AddToCartTool, ClearCartTool, RemoveFromCartTool, ViewCartTool
from app.services.chatbot.tools.order_tools import CheckOrderTool, PlaceOrderTool
from app.services.chatbot.tools.product_compare import ProductCompareTool
from app.services.chatbot.tools.product_search import ProductSearchTool
from app.services.chatbot.tools.registry import ToolRegistry
from app.schemas.support import HandoffEvaluationRequest
from app.services.hitl_service import ApprovalService
from app.services.observability import AgentObservability
from app.services.support_service import HumanHandoffService, SupportTicketService


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
        self.product_resolver = ProductResolver(self.db)
        self.recommendation = RecommendationAgent(self.tool_caller)
        self.comparison = ComparisonAgent(self.tool_caller)
        self.cart_order = CartOrderAgent(self.tool_caller)

    def _register_tools(self):
        self.tool_registry.register(ProductSearchTool(self.db))
        self.tool_registry.register(ProductCompareTool(self.db))
        self.tool_registry.register(AddToCartTool(self.db, self.user_id))
        self.tool_registry.register(ViewCartTool(self.db, self.user_id))
        self.tool_registry.register(ClearCartTool(self.db, self.user_id))
        self.tool_registry.register(RemoveFromCartTool(self.db, self.user_id))
        self.tool_registry.register(PlaceOrderTool(self.db, self.user_id))
        self.tool_registry.register(CheckOrderTool(self.db))

    async def process_message(self, user_message: str) -> AsyncGenerator[dict, None]:
        self._remember("user", user_message)

        approval_response = await self._handle_approval_command(user_message)
        if approval_response:
            self._remember("assistant", approval_response)
            yield self._event("final", {"content": approval_response, "conversation_id": self.state.conversation_id})
            return

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

        handoff_request = HandoffEvaluationRequest(
            message=user_message,
            conversation_id=self.state.conversation_id,
            intent=intent,
            confidence=route.confidence,
            channel="chat",
            create_ticket=True,
        )
        handoff_evaluation = HumanHandoffService.evaluate(handoff_request)
        if handoff_evaluation["should_handoff"] and self._should_auto_create_handoff(handoff_evaluation):
            ticket = await self._create_handoff_ticket(handoff_request, handoff_evaluation)
            content = self._format_handoff_created(ticket["ticket_id"], handoff_evaluation["reasons"])
            self._remember("assistant", content)
            yield self._event(
                "handoff",
                {
                    "ticket": ticket,
                    "reasons": handoff_evaluation["reasons"],
                    "routing_strategy": handoff_evaluation["routing_strategy"],
                    "conversation_id": self.state.conversation_id,
                },
            )
            yield self._event("final", {"content": content, "conversation_id": self.state.conversation_id})
            return

        # 2. [反思5a-低置信度澄清 gate] 对于可执行工具的意图，如果置信度较低，先进行澄清确认，避免误操作
        if self._needs_low_confidence_clarification(route.confidence, intent):
            content = self._format_low_confidence_clarification(intent, route.confidence)
            self._remember("assistant", content)
            yield self._event(
                "final",
                {
                    "content": content,
                    "conversation_id": self.state.conversation_id,
                    "required_slots": ["intent_confirmation"],
                },
            )
            return

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
                params = self._normalize_search_params(params, self._extract_search_params_by_rules(user_message))
                if self._wants_alternative_recommendation(user_message) and self.state.last_products:
                    params["exclude_ids"] = [
                        product.get("id")
                        for product in self.state.last_products
                        if isinstance(product, dict) and product.get("id")
                    ]
                final = await self._recommend_products(user_message, params)
                self.state.last_products = final["products"]
                self._remember("assistant", final["text"])
                yield self._event(
                    "final",
                    {
                        "content": final["text"],
                        "conversation_id": self.state.conversation_id,
                        "products": final["products"],
                    },
                )
            elif intent in ["cart", "order"]:
                if intent == "cart":
                    referenced_cart_result = await self._handle_referenced_cart_add(user_message)
                    if referenced_cart_result:
                        self._remember("assistant", referenced_cart_result)
                        yield self._event(
                            "final",
                            {"content": referenced_cart_result, "conversation_id": self.state.conversation_id},
                        )
                        return
                final = await self.cart_order.handle(user_message, intent)
                if isinstance(final, dict):
                    content = str(final.get("content") or "")
                    self._remember("assistant", content)
                    yield self._event(
                        "final",
                        {
                            "content": content,
                            "conversation_id": self.state.conversation_id,
                            "approval": final.get("approval"),
                        },
                    )
                else:
                    self._remember("assistant", final)
                    yield self._event("final", {"content": final, "conversation_id": self.state.conversation_id})
            else:
                content = "我可以帮你搜索、比较商品、管理购物车和下单。试着说“推荐一款蓝牙耳机并下单”吧！"
                self._remember("assistant", content)
                yield self._event("final", {"content": content, "conversation_id": self.state.conversation_id})
        except Exception:
            await self._create_tool_failure_handoff(user_message)
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
    def _should_auto_create_handoff(evaluation: dict) -> bool:
        reasons = set(evaluation.get("reasons") or [])
        if evaluation.get("category") != "general":
            return True
        return bool(reasons & {"negative_sentiment", "tool_failed", "repeated_unresolved_followup"})

    async def _create_handoff_ticket(self, request: HandoffEvaluationRequest, evaluation: dict) -> dict:
        ticket, _ = await SupportTicketService.create_from_handoff(
            self.db,
            customer_id=self.user_id,
            actor_id=self.user_id,
            request=request,
            evaluation=evaluation,
        )
        return SupportTicketService.serialize_ticket(ticket)

    async def _create_tool_failure_handoff(self, user_message: str) -> None:
        request = HandoffEvaluationRequest(
            message=user_message,
            conversation_id=self.state.conversation_id,
            intent=self.state.last_intent or "unknown",
            confidence=0.0,
            tool_failed=True,
            channel="chat",
            create_ticket=True,
        )
        evaluation = HumanHandoffService.evaluate(request)
        try:
            await self._create_handoff_ticket(request, evaluation)
        except Exception:
            return

    @staticmethod
    def _format_handoff_created(ticket_id: str, reasons: list[str]) -> str:
        reason_text = ", ".join(reasons) if reasons else "manual_review"
        return (
            "我已经为这次咨询创建客服工单，并保留当前会话上下文。\n"
            f"Ticket: {ticket_id}\n"
            f"Handoff reason: {reason_text}\n"
            "人工客服会基于订单、政策和会话摘要继续处理。"
        )

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

        request = ShoppingRequestParser.parse(text)
        if request.product_query:
            params["keyword"] = request.product_query
        elif request.category:
            params["keyword"] = ""
            params["category"] = request.category
        else:
            product_keywords = [
                "蓝牙耳机",
                "耳机",
                "5G 手机",
                "手机",
                "平板电脑",
                "笔记本",
                "电脑",
                "机械键盘",
                "键盘",
                "无线鼠标",
                "鼠标",
                "充电器",
                "显示器",
                "微单相机",
                "相机",
                "镜头",
                "电视",
                "冰箱",
                "空调",
                "扫地机器人",
            ]
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
    def _wants_alternative_recommendation(user_message: str) -> bool:
        text = user_message.lower()
        terms = (
            "\u5176\u4ed6",
            "\u522b\u7684",
            "\u53e6\u5916",
            "\u53e6\u4e00",
            "\u6362\u4e00",
            "\u91cd\u65b0\u63a8\u8350",
            "other",
            "another",
            "different",
        )
        return any(term in text for term in terms)

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
                elif value == "FROM_RESOLVED_PRODUCT":
                    if "resolved_product" in context and context["resolved_product"]:
                        resolved_params[key] = context["resolved_product"].get("id")
                else:
                    resolved_params[key] = value

            # 执行对应工具
            try:
                if intent == "search":
                    resolved_params = self._normalize_search_params(resolved_params, self._extract_search_params_by_rules(step_desc))
                    result = await self.tool_caller.invoke("search_products", **resolved_params)
                    context["last_products"] = result
                elif intent == "resolve_product":
                    resolution = await self.product_resolver.resolve(
                        str(resolved_params.get("query") or step_desc or user_message),
                        context.get("last_products") or self.state.last_products,
                    )
                    result = self._serialize_resolution(resolution)
                    context["last_products"] = resolution.candidates
                    if resolution.product:
                        context["resolved_product"] = resolution.product
                elif intent == "compare":
                    result = await self.tool_caller.invoke("compare_products", product_ids=resolved_params.get("product_ids", []))
                elif intent == "clear_cart":
                    result = await self.tool_caller.invoke("clear_cart")
                elif intent == "remove_cart":
                    result = await self.tool_caller.invoke("remove_from_cart", **resolved_params)
                elif intent == "cart":
                    # 确保有 product_id
                    if "product_id" not in resolved_params:
                        raise ValueError("缺少 product_id，无法加入购物车")
                    if context.get("resolved_product"):
                        resolved_params["_product_name"] = context["resolved_product"].get("name")
                    result = await self.tool_caller.invoke("add_to_cart", **resolved_params)
                elif intent == "order":
                    result = await self.tool_caller.invoke("place_order")
                elif intent == "recommend":
                    resolved_params = self._normalize_search_params(resolved_params, self._extract_search_params_by_rules(step_desc))
                    rec_result = await self._recommend_products(step_desc or user_message, resolved_params)
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
            context.setdefault("step_results", []).append(result_text)
            if isinstance(result, dict) and result.get("error") and intent == "resolve_product":
                break
            if isinstance(result, dict) and result.get("approval_required"):
                context["approval"] = self._approval_payload_from_tool_result(result)
                break
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict) and "id" in result[0]:
                context["last_products"] = result  # 保存商品列表

        # 生成最终答案
        final_parts = []
        if context.get("step_results"):
            final_parts.extend(context["step_results"])
        elif "last_result_text" in context:
            final_parts.append(context["last_result_text"])
        else:
            final_parts.append("计划执行完毕。")
        final_text = "\n".join(final_parts)
        if context.get("last_products"):
            self.state.last_products = context["last_products"]
        self._remember("assistant", final_text)
        final_payload = {"content": final_text, "conversation_id": self.state.conversation_id}
        if context.get("last_products"):
            final_payload["products"] = context["last_products"][:5]
        if context.get("approval"):
            final_payload["approval"] = context["approval"]
        yield self._event("final", final_payload)

    @staticmethod
    def _format_step_result(intent: str, result: Any, params: dict) -> str:
        if isinstance(result, str):
            return result
        if isinstance(result, dict) and "error" in result:
            return str(result["error"])
        if isinstance(result, dict) and result.get("approval_required"):
            risk_reasons = ", ".join(result.get("risk_reasons") or [])
            if result.get("approval_channel") == "governance":
                return (
                    "这个订单触发了异常风险规则，已提交到 Governance 后台人工审核。\n"
                    f"Approval ID: {result.get('approval_id')}\n"
                    f"Risk level: {result.get('risk_level')}\n"
                    f"Risk reasons: {risk_reasons}\n"
                    f"{result.get('summary')}"
                )
            title = "高金额订单需要再次确认" if result.get("confirmation_level") == "double_confirm" else "请确认订单"
            return (
                f"{title}\n"
                f"Approval ID: {result.get('approval_id')}\n"
                f"Risk level: {result.get('risk_level')}\n"
                f"Risk reasons: {risk_reasons}\n"
                f"{result.get('summary')}\n"
                "确认后再执行真实下单，避免 Agent 直接完成不可逆业务动作。"
            )
        if intent == "clear_cart":
            return "购物车已清空。"
        if intent == "remove_cart" and isinstance(result, dict):
            count = int(result.get("removed_count") or 0)
            keyword = params.get("keyword") or "指定商品"
            return f"已从购物车移除 {count} 件与“{keyword}”匹配的商品。"
        if intent == "resolve_product" and isinstance(result, dict):
            product = result.get("product") or {}
            return (
                f"已解析商品需求：{result.get('query')}。\n"
                f"{result.get('reason')}\n"
                f"选择商品 {product.get('id')}：{product.get('name')}，价格 ¥{product.get('price')}，库存 {product.get('stock', '未知')}。"
            )
        if intent == "cart":
            product_id = params.get("product_id")
            product_name = params.get("_product_name")
            label = f"{product_name}（商品 {product_id}）" if product_name else f"商品 {product_id}"
            return f"已添加{label}到购物车，数量 {params.get('quantity', 1)}。"
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

    @staticmethod
    def _serialize_resolution(resolution: ProductResolution) -> dict:
        if resolution.needs_clarification or not resolution.product:
            return {
                "error": resolution.reason or "没有找到可加入购物车的商品，请补充品牌、预算或品类。",
                "query": resolution.query,
                "candidates": resolution.candidates[:5],
            }
        return {
            "query": resolution.query,
            "sort_by": resolution.sort_by,
            "reason": resolution.reason,
            "product": resolution.product,
            "candidates": resolution.candidates[:5],
        }

    async def _recommend_products(self, user_message: str, params: dict) -> dict:
        request = ShoppingRequestParser.parse(user_message)
        if request.requires_product_resolution or request.attribute_filters:
            resolution = await self.product_resolver.resolve(user_message, self.state.last_products)
            if resolution.candidates:
                products = resolution.candidates
                exclude_ids = {int(item) for item in (params.get("exclude_ids") or []) if str(item).isdigit()}
                if exclude_ids:
                    products = [product for product in products if product.get("id") not in exclude_ids] or products
                return {"products": products[:4], "text": self._format_recommendation_text(products[:4])}
        return await self.recommendation.recommend(params)

    @staticmethod
    def _format_recommendation_text(products: list[dict]) -> str:
        if not products:
            return "没有找到合适的推荐商品。"
        return "为你推荐以下商品：\n" + "\n".join(
            [f"- {product.get('name')} (¥{product.get('price')})" for product in products[:4]]
        )

    @staticmethod
    def _approval_payload_from_tool_result(result: dict) -> dict:
        return {
            "id": result.get("approval_id"),
            "action_type": "place_order",
            "status": result.get("status"),
            "risk_level": result.get("risk_level"),
            "risk_reasons": result.get("risk_reasons") or [],
            "approval_channel": result.get("approval_channel"),
            "confirmation_level": result.get("confirmation_level"),
            "summary": result.get("summary"),
            "payload": result.get("payload") or {},
        }

    async def _handle_referenced_cart_add(self, user_message: str) -> str | None:
        if not self._looks_like_referenced_cart_add(user_message) or not self.state.last_products:
            return None

        request = ShoppingRequestParser.parse(user_message)
        index = request.candidate_reference if request.candidate_reference is not None else self._reference_index(user_message)
        product = self._select_referenced_product(self.state.last_products, index)
        if not product:
            return None

        quantity = request.quantity or 1
        result = await self.tool_caller.invoke("add_to_cart", product_id=product.get("id"), quantity=quantity)
        if isinstance(result, dict) and result.get("error"):
            return str(result["error"])
        return f"已将 {product.get('name')} 加入购物车，数量 {quantity}。"

    @staticmethod
    def _looks_like_referenced_cart_add(user_message: str) -> bool:
        text = user_message.lower()
        add_terms = ("加入", "添加", "加购", "放进", "加进", "add to cart", "put in cart")
        reference_terms = ("这个", "这款", "刚才", "推荐的", "上一个", "第一个", "第二个", "第三个", "this", "that", "recommended")
        return any(term in text for term in add_terms) and any(term in text for term in reference_terms)

    @staticmethod
    def _reference_index(user_message: str) -> int:
        text = user_message.lower()
        if any(term in text for term in ("第二", "第2", "second")):
            return 1
        if any(term in text for term in ("第三", "第3", "third")):
            return 2
        return 0

    @staticmethod
    def _select_referenced_product(products: list[dict], index: int) -> dict | None:
        candidates = [product for product in products if isinstance(product, dict) and product.get("id")]
        if index < 0 or index >= len(candidates):
            return None
        return candidates[index]

    def _remember(self, role: str, content: str) -> None:
        self.state.add_message(role, content)
        conversation_store.save(self.state)

    async def _handle_approval_command(self, user_message: str) -> str | None:
        match = re.search(r"(?:approval\s*id|审批|确认|approve|reject|拒绝)\D*(\d+)", user_message, re.IGNORECASE)
        if not match:
            return None

        approval_id = int(match.group(1))
        reject = any(word in user_message.lower() for word in ["reject", "拒绝", "取消"])
        approval = await ApprovalService.get(self.db, approval_id)
        if not approval or approval.user_id != self.user_id:
            return "未找到属于你的审批请求。"
        if (approval.payload or {}).get("approval_channel") == "governance" and not reject:
            return "这个订单需要后台人工审核，不能在 Chat 里直接确认。"
        try:
            if reject:
                approval = await ApprovalService.reject(self.db, approval_id, self.user_id, note="chat_rejection")
                action = "已拒绝"
            else:
                approval = await ApprovalService.approve(self.db, approval_id, self.user_id, note="chat_approval")
                action = "已确认并执行"
        except ValueError as exc:
            return f"审批处理失败：{exc}"

        if not approval:
            return "未找到属于你的审批请求。"
        result = json.dumps(approval.result or {}, ensure_ascii=False)
        return f"审批 {approval.id} {action}。状态：{approval.status}。结果：{result}"

    @staticmethod
    def _needs_low_confidence_clarification(confidence: float, intent: str) -> bool:
        executable_intents = {"search", "recommend", "compare", "cart", "order", "plan"}
        return intent in executable_intents and confidence < settings.HITL_INTENT_CONFIDENCE_THRESHOLD

    @staticmethod
    def _format_low_confidence_clarification(intent: str, confidence: float) -> str:
        return (
            "我对你的意图还不够确定，先不执行工具。\n"
            f"Current route: {intent} (confidence {confidence:.2f})\n"
            "请补充预算、商品品类、偏好，或明确是要搜索、加入购物车、结算，还是查询订单。"
        )

    
