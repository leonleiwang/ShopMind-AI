# backend/app/services/chatbot/agents/cart_order.py
import json
import re

from app.core.llm_gateway import llm_gateway
from app.services.chatbot.tools.caller import ToolCaller


class CartOrderAgent:
    def __init__(self, tool_caller: ToolCaller):
        self.llm = llm_gateway
        self.tool_caller = tool_caller

    async def handle(self, user_message: str, intent: str):
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
    def _extract_cart_params(user_message: str) -> dict:
        product_match = re.search(r"(?:商品|product|id)\s*#?\s*(\d+)|#\s*(\d+)", user_message, re.IGNORECASE)
        quantity_match = re.search(r"(?:数量|x|×|\*)\s*(\d+)|(\d+)\s*(?:件|个)", user_message, re.IGNORECASE)
        params = {"quantity": 1}
        if product_match:
            params["product_id"] = int(next(group for group in product_match.groups() if group))
        if quantity_match:
            params["quantity"] = int(next(group for group in quantity_match.groups() if group))
        return params
