# backend/app/services/chatbot/agents/comparison.py
import json
import re

from app.core.llm_gateway import llm_gateway
from app.services.chatbot.tools.caller import ToolCaller


class ComparisonAgent:
    def __init__(self, tool_caller: ToolCaller):
        self.llm = llm_gateway
        self.tool_caller = tool_caller

    async def compare(self, user_message: str, conversation_history: list = None):
        ids = self._extract_product_ids(user_message)
        if not ids:
            ids = await self._extract_product_ids_with_llm(user_message, conversation_history)
        if not ids:
            return "请先说出你想对比哪些商品。"
        # 调用对比工具
        result = await self.tool_caller.invoke("compare_products", product_ids=ids)
        # 生成对比回答
        if not result:
            return "未找到这些商品。"
        compare_text = "商品对比：\n" + "\n".join(
            [f"- 商品{p['id']}：{p['name']}，¥{p['price']}，分类：{p['category']}，品牌：{p['brand'] or '未知'}" for p in result]
        )
        return compare_text

    async def _extract_product_ids_with_llm(self, user_message: str, conversation_history: list = None):
        # 先提取需要对比的商品ID（假设用户已经在之前的对话中得到了商品列表）
        # 此处简化：要求LLM从上下文中提取IDs
        prompt = f"""Extract product IDs to compare from the user's message and conversation history. Output JSON list.
Message: {user_message}
History: {json.dumps(conversation_history or [])}
Output: [1, 2, 3]"""
        resp = await self.llm.ainvoke(prompt, fallback_content="[]")
        try:
            return json.loads(resp.content)
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _extract_product_ids(user_message: str) -> list[int]:
        ids = re.findall(r"(?:商品|product|id)\s*#?\s*(\d+)|#\s*(\d+)", user_message, re.IGNORECASE)
        return [int(next(group for group in match if group)) for match in ids]
