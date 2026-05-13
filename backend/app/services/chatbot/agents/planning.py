# backend/app/services/chatbot/agents/planning.py
import json
import re
from app.core.llm import get_llm

class PlanningAgent:
    def __init__(self):
        self.llm = get_llm()

    async def create_plan(self, user_message: str) -> list[dict]:
        deterministic_plan = self._create_deterministic_plan(user_message)
        if deterministic_plan:
            return deterministic_plan

        prompt = f"""You are a task planner for a shopping assistant. The user has said: "{user_message}"

Break this down into a sequence of simple steps that the assistant can perform. Each step must use one of the following intents: search, recommend, cart, clear_cart, order.

**Critical Rules:**
- If the user wants to "clear cart", "清空购物车", etc., add a "clear_cart" step before adding new items.
- If the user wants to "buy", "order", "下单", "购买", etc., you MUST first have a "cart" step to add the product to the cart before the "order" step.
- If the user wants a recommendation, the "recommend" step should be followed by a "cart" step (to add the recommended item(s) to cart) if the user intends to buy.
- In the "cart" step, use "product_id" from the previous step's result. If the previous step returns multiple items, select the first one unless the user specifies.

Return a JSON list of steps. Each step:
- "intent": string (search, recommend, cart, clear_cart, order)
- "description": string
- "params": object (e.g., for recommend: {{"keyword": "..." }}, for cart: {{"product_id": "FROM_PREVIOUS", "quantity": 1}}, for order: {{}})

**Example** for "推荐一款蓝牙耳机并下单":
[
  {{"intent": "recommend", "description": "推荐蓝牙耳机", "params": {{"keyword": "蓝牙耳机"}}}},
  {{"intent": "cart", "description": "将推荐的耳机加入购物车", "params": {{"product_id": "FROM_PREVIOUS", "quantity": 1}}}},
  {{"intent": "order", "description": "下单购买", "params": {{}}}}
]

Output only the JSON list."""
        resp = await self.llm.ainvoke(prompt)
        try:
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:].strip()
            plan = json.loads(content)
            return plan
        except:
            return []

    @staticmethod
    def _create_deterministic_plan(user_message: str) -> list[dict]:
        text = user_message.strip()
        plan: list[dict] = []

        if "清空购物车" in text or "清空" in text:
            plan.append({"intent": "clear_cart", "description": "清空购物车", "params": {}})

        product_match = re.search(r"(?:商品|product|id)\s*#?\s*(\d+)|#\s*(\d+)", text, re.IGNORECASE)
        product_id = None
        if product_match:
            product_id = int(next(group for group in product_match.groups() if group))

        if product_id and any(word in text for word in ["加入", "添加", "加购", "放进", "加进去"]):
            plan.append({
                "intent": "cart",
                "description": f"将商品 {product_id} 加入购物车",
                "params": {"product_id": product_id, "quantity": 1}
            })

        if "下单" in text or "结算" in text or "购买" in text:
            plan.append({"intent": "order", "description": "提交订单", "params": {}})

        return plan if len(plan) > 1 else []
