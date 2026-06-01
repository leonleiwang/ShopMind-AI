# Cart/Order Agent：处理购物车和订单类单步意图，并把真实下单转成 HITL 审批。
# backend/app/services/chatbot/agents/cart_order.py
import json
import re

from app.core.llm_gateway import llm_gateway
from app.services.chatbot.tools.caller import ToolCaller


class CartOrderAgent:
    def __init__(self, tool_caller: ToolCaller):
        # 复用统一 ToolCaller，购物车和订单工具都走观测链路。
        self.llm = llm_gateway
        self.tool_caller = tool_caller

    async def handle(self, user_message: str, intent: str):
        # 根据 cart/order intent 执行查看、加购、清空、下单审批或订单查询。
        if intent == "cart":
            if "清空" in user_message:
                await self.tool_caller.invoke("clear_cart")
                return "购物车已清空。"
            # 判断是添加还是查看
            if "添加" in user_message or "加入" in user_message or "加购" in user_message:
                # 提取 product_id 和 quantity
                params = self._extract_cart_params(user_message)
                if not params.get("product_id"):
                    prompt = f"""Extract product_id and quantity from: {user_message}. Output JSON: {{"product_id": ..., "quantity": ...}}"""
                    resp = await self.llm.ainvoke(prompt, fallback_content="{}")
                    try:
                        params = json.loads(resp.content)
                    except json.JSONDecodeError:
                        return "请提供商品ID和数量。"
                result = await self.tool_caller.invoke("add_to_cart", **params)
                if "error" in result:
                    return result["error"]
                return f"已添加商品 {params.get('product_id')} 到购物车，数量 {params.get('quantity', 1)}。"
            else:
                result = await self.tool_caller.invoke("view_cart")
                if not result:
                    return "你的购物车是空的。"
                cart_text = "购物车：\n" + "\n".join([f"- {i['product_name']} × {i['quantity']} (单价 ¥{i['unit_price']})" for i in result])
                return cart_text
        elif intent == "order":
            if "下单" in user_message or "结算" in user_message:
                result = await self.tool_caller.invoke("place_order")
                if "error" in result:
                    return result["error"]
                if result.get("approval_required"):
                    return {
                        "content": self._format_order_approval(result),
                        "approval": self._approval_payload(result),
                    }
                return f"下单成功！订单号 {result['order_id']}，总金额 ¥{result['total_amount']}。"
            else:
                # 查询订单
                prompt = f"Extract order_id from: {user_message}. Output JSON: {{\"order_id\": ...}}"
                resp = await self.llm.ainvoke(prompt, fallback_content="{}")
                try:
                    params = json.loads(resp.content)
                except json.JSONDecodeError:
                    return "请提供订单ID。"
                result = await self.tool_caller.invoke("check_order", **params)
                if "error" in result:
                    return result["error"]
                return f"订单 {result['order_id']} 状态: {result['status']}，总金额 ¥{result['total_amount']}。"
        return "无法处理你的请求。"

    @staticmethod
    def _format_order_approval(result: dict) -> str:
        # 把下单审批结果转成用户可读的风险说明。
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
            "确认无误后可在当前 Chat 页面完成下单，或取消本次订单草稿。"
        )

    @staticmethod
    def _approval_payload(result: dict) -> dict:
        # 提取前端审批卡片字段。
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

    @staticmethod
    def _extract_cart_params(user_message: str) -> dict:
        # 从自然语言中抽取 product_id 和 quantity。
        product_match = re.search(r"(?:商品|product|id)\s*#?\s*(\d+)|#\s*(\d+)", user_message, re.IGNORECASE)
        quantity_match = re.search(r"(?:数量|x|×|\*)\s*(\d+)|(\d+)\s*(?:件|个)", user_message, re.IGNORECASE)
        params = {"quantity": 1}
        if product_match:
            params["product_id"] = int(next(group for group in product_match.groups() if group))
        if quantity_match:
            params["quantity"] = int(next(group for group in quantity_match.groups() if group))
        return params
