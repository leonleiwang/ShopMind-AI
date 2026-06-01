# Recommendation Agent：复用商品搜索工具生成推荐列表，并支持排除上一轮已推荐商品。
"""
Recommendation Agent —— 简单推荐（基于销量/评分模拟）
"""

# backend/app/services/chatbot/agents/recommendation.py
from app.services.chatbot.tools.caller import ToolCaller


class RecommendationAgent:
    def __init__(self, tool_caller: ToolCaller):
        # 推荐 Agent 通过 ToolCaller 间接访问商品搜索工具。
        self.tool_caller = tool_caller

    async def recommend(self, params: dict) -> dict:
        # 搜索候选商品后按价格做简化推荐排序，并返回结构化 products + 文案。
        keyword = params.get("keyword", "")
        exclude_ids = {
            int(item)
            for item in (params.get("exclude_ids") or [])
            if str(item).isdigit()
        }
        search_params = dict(params)
        search_params.pop("exclude_ids", None)
        """调用搜索工具，然后模拟推荐（按价格升序的前3个）"""
        if not keyword:
            return {"products": [], "text": "请告诉我你需要什么类型的商品。"}
        # 使用搜索工具得到商品列表
        result = await self.tool_caller.invoke("search_products", **search_params)
        
        if not result:
            return {"products": [], "text": f"没有找到和“{keyword}”相关的商品。"}
        sorted_candidates = sorted(result, key=lambda x: x["price"])
        sorted_items = [p for p in sorted_candidates if p.get("id") not in exclude_ids][:3]
        if not sorted_items:
            sorted_items = sorted_candidates[:3]
        if not sorted_items:
            return {"products": [], "text": "没有合适的推荐。"}
        rec_text = "为你推荐以下商品：\n" + "\n".join([f"- {p['name']} (¥{p['price']})" for p in sorted_items])
        return {"products": sorted_items, "text": rec_text}
        # 简单推荐策略：取价格最低的3个
        # sorted_items = sorted(result, key=lambda x: x["price"])[:3]
        # if not sorted_items:
        #     return "没有合适的推荐。"
        # rec_text = "为你推荐以下商品：\n" + "\n".join(
        #     [f"- {p['name']} (¥{p['price']})" for p in sorted_items]
        # )
        # return rec_text
        
