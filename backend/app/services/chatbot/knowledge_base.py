# 轻量业务知识检索器：在意图路由前提供可解释业务上下文，生产可替换为真实 RAG/FAQ 知识库。
from __future__ import annotations


class BusinessKnowledgeRetriever:
    """[反思1b-有依据路由] 路由前的轻量业务知识检索器。

    当前用内置业务域文档做 demo 级召回；生产可替换成 Milvus/Elasticsearch/FAQ 工单知识库。
    """

    SCHEMA_VERSION = "business-knowledge-v1"
    DOCUMENTS = [
        {
            "domain": "product_discovery",
            "summary": "商品搜索、商品推荐、预算筛选、品类筛选、商品对比。",
            "intents": ["search", "recommend", "compare"],
            "keywords": ["找", "搜索", "推荐", "预算", "以内", "对比", "比较", "商品"],
        },
        {
            "domain": "cart_order",
            "summary": "购物车管理、添加商品、清空购物车、结算、提交订单、查询订单。",
            "intents": ["cart", "order"],
            "keywords": ["购物车", "加入", "添加", "加购", "清空", "下单", "结算", "订单"],
        },
        {
            "domain": "customer_support",
            "summary": "用户描述模糊问题时先追问业务域、功能、错误现象，再进入具体工具链。",
            "intents": ["clarify"],
            "keywords": ["不好用", "不会用", "不能用", "怎么办", "有问题", "报错"],
        },
    ]

    def retrieve(self, query: str, limit: int = 3) -> list[dict]:
        # 基于关键词重叠召回业务域文档，并附带 schema_version 便于追踪口径。
        scored = []
        for doc in self.DOCUMENTS:
            score = sum(1 for keyword in doc["keywords"] if keyword in query)
            if score:
                scored.append({**doc, "score": score, "schema_version": self.SCHEMA_VERSION})
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]
