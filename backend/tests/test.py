"""
Agent / Planner / MCP / 向量排序测试
"""

from app.mcp.server import _tool_schemas
from app.services.chatbot.agents.conversation import ClarificationAgent
from app.services.chatbot.agents.intent_router import IntentRouterAgent
from app.services.chatbot.agents.planning import PlanningAgent
from app.services.chatbot.knowledge_base import BusinessKnowledgeRetriever
from app.services.chatbot.prompts import prompt_manager
from app.services.chatbot.tools.product_search import ProductSearchTool
from app.services.chatbot.tools.registry import ToolRegistry
from app.services.chatbot.vector_store_manager import VectorStoreManager


def test_keyword_router_handles_negative_order_intent():
    assert IntentRouterAgent._route_by_keywords("推荐一款蓝牙耳机，但先别下单") == "recommend"


def test_keyword_router_detects_multi_step_plan():
    assert IntentRouterAgent._route_by_keywords("清空购物车，然后把商品4加入购物车，再下单") == "plan"


def test_planner_builds_clear_cart_add_and_order_plan():
    plan = PlanningAgent._create_deterministic_plan("帮我清空购物车，然后重新把商品4加进去，再下单")
    assert [step["intent"] for step in plan] == ["clear_cart", "cart", "order"]
    assert plan[1]["params"]["product_id"] == 4


def test_product_search_normalizes_common_categories():
    assert ProductSearchTool._clean_category("电子产品") == "电子"
    assert ProductSearchTool._clean_category("0") is None


def test_vector_ranker_prefers_semantically_related_product():
    products = [
        {"id": 1, "name": "办公椅", "category": "家具", "brand": "", "description": "人体工学"},
        {"id": 2, "name": "蓝牙耳机", "category": "电子", "brand": "", "description": "低延迟 音质好"},
    ]
    ranked = VectorStoreManager("chroma").rank_products("低延迟蓝牙耳机", products)
    assert ranked[0]["id"] == 2


def test_mcp_tool_schemas_include_core_commerce_tools():
    tool_names = {tool["name"] for tool in _tool_schemas()}
    assert {"search_products", "compare_products", "add_to_cart", "place_order"}.issubset(tool_names)


def test_request_scoped_tool_registry_isolated():
    class FakeTool:
        name = "fake"
        description = "fake"
        parameters = {"type": "object", "properties": {}}

        def __init__(self, owner):
            self.owner = owner

        async def execute(self, **kwargs):
            return self.owner

    first = ToolRegistry()
    second = ToolRegistry()
    first.register(FakeTool("user-a"))
    second.register(FakeTool("user-b"))

    assert first.get("fake").owner == "user-a"
    assert second.get("fake").owner == "user-b"


def test_clarification_agent_detects_vague_support_question():
    result = ClarificationAgent().inspect("这个功能不好用，怎么办", "clarify")
    assert result["needs_clarification"] is True
    assert "business_domain" in result["required_slots"]
    assert result["options"]


def test_business_knowledge_retriever_returns_route_evidence():
    docs = BusinessKnowledgeRetriever().retrieve("我想清空购物车然后下单")
    assert docs[0]["domain"] == "cart_order"
    assert "order" in docs[0]["intents"]


def test_prompt_manager_loads_versioned_template():
    prompt = prompt_manager.load("intent_router")
    rendered = prompt_manager.render(
        "intent_router",
        business_context="[]",
        tool_schemas="[]",
        user_message="推荐耳机",
    )
    assert prompt.version == "route-evidence-v1"
    assert "推荐耳机" in rendered
