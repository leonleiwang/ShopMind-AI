"""
Agent / Planner / MCP / 向量排序测试
"""

from app.services.chatbot.agents.intent_router import IntentRouterAgent
from app.services.chatbot.agents.planning import PlanningAgent
from app.services.chatbot.tools.product_search import ProductSearchTool
from app.services.chatbot.vector_store_manager import VectorStoreManager
from app.mcp.server import _tool_schemas


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
