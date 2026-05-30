"""
Agent / Planner / MCP / 向量排序测试
"""

from app.demo.commerce_seed_data import generate_product_catalog, nlu_regression_corpus
from app.mcp.server import _tool_schemas
from app.schemas.support import HandoffEvaluationRequest
from app.services.agent_eval import (
    AgentEvalRunner,
    DataAgentRouter,
    DataAgentService,
    EvalCorpus,
    ReadOnlySQLValidator,
)
from app.services.chatbot.agents.conversation import ClarificationAgent
from app.services.chatbot.agents.intent_router import IntentRouterAgent
from app.services.chatbot.agents.planning import PlanningAgent
from app.services.chatbot.agents.recommendation import RecommendationAgent
from app.services.chatbot.chat_service import ChatService
from app.services.chatbot.knowledge_base import BusinessKnowledgeRetriever
from app.services.chatbot.product_resolver import ProductResolver, ShoppingRequestParser
from app.services.chatbot.prompts import prompt_manager
from app.services.chatbot.tools.product_search import ProductSearchTool
from app.services.chatbot.tools.registry import ToolRegistry
from app.services.chatbot.vector_store_manager import VectorStoreManager
from app.services.hitl_service import ApprovalService
from app.services.support_service import (
    AgentAssistService,
    HumanHandoffService,
    LLMRoutingService,
    SupportTicketService,
)


def test_keyword_router_handles_negative_order_intent():
    assert IntentRouterAgent._route_by_keywords("推荐一款蓝牙耳机，但先别下单") == "recommend"


def test_keyword_router_detects_multi_step_plan():
    assert IntentRouterAgent._route_by_keywords("清空购物车，然后把商品4加入购物车，再下单") == "plan"


def test_keyword_router_routes_natural_language_cart_selection_to_plan():
    assert IntentRouterAgent._route_by_keywords("把最便宜的一款蓝牙耳机加进购物车") == "plan"


def test_keyword_router_routes_product_checkout_to_plan():
    assert IntentRouterAgent._route_by_keywords("买一个中延迟的蓝牙耳机") == "plan"


def test_planner_builds_clear_cart_add_and_order_plan():
    plan = PlanningAgent._create_deterministic_plan("帮我清空购物车，然后重新把商品4加进去，再下单")
    assert [step["intent"] for step in plan] == ["clear_cart", "cart", "order"]
    assert plan[1]["params"]["product_id"] == 4


def test_planner_builds_product_resolution_plan_for_cheapest_product():
    plan = PlanningAgent._create_deterministic_plan("帮我清空购物车，然后重新把最便宜的一款蓝牙耳机加进去")
    assert [step["intent"] for step in plan] == ["clear_cart", "resolve_product", "cart"]
    assert plan[2]["params"]["product_id"] == "FROM_RESOLVED_PRODUCT"


def test_planner_completes_product_resolution_before_checkout():
    plan = PlanningAgent._create_deterministic_plan("推荐一个中延迟的蓝牙耳机并下单")
    assert [step["intent"] for step in plan] == ["resolve_product", "cart", "order"]


def test_planner_treats_buy_product_request_as_resolution_checkout():
    plan = PlanningAgent._create_deterministic_plan("买一个中延迟的蓝牙耳机")
    assert [step["intent"] for step in plan] == ["resolve_product", "cart", "order"]


def test_planner_keeps_exploratory_recommendation_read_only():
    request = ShoppingRequestParser.parse("想买个相机，推荐一下")
    plan = PlanningAgent._create_deterministic_plan("想买个相机，推荐一下")
    assert request.actions == ["recommend"]
    assert request.requires_checkout is False
    assert [step["intent"] for step in plan] == ["resolve_product"]


def test_planner_keeps_clear_cart_before_attribute_checkout_flow():
    plan = PlanningAgent._create_deterministic_plan("清空购物车然后推荐一个中延迟的蓝牙耳机并下单")
    assert [step["intent"] for step in plan] == ["clear_cart", "resolve_product", "cart", "order"]


def test_planner_exact_product_name_checkout_flow():
    plan = PlanningAgent._create_deterministic_plan("把蓝牙耳机 Pro 加入购物车然后下单")
    assert [step["intent"] for step in plan] == ["resolve_product", "cart", "order"]
    assert plan[1]["params"]["product_id"] == "FROM_RESOLVED_PRODUCT"


def test_planner_does_not_add_recommended_followup_to_current_checkout():
    plan = PlanningAgent._create_deterministic_plan("下单这个冰箱然后推荐一款电视")
    assert [step["intent"] for step in plan] == ["order"]


def test_product_resolver_extracts_natural_language_selection_params():
    params = ProductResolver.extract_params("搜索 300 元以内最便宜的蓝牙耳机并加入购物车")
    assert params["query"] == "蓝牙耳机"
    assert params["sort_by"] == "price_asc"
    assert params["max_price"] == 300


def test_shopping_request_parser_extracts_structured_attribute_query():
    request = ShoppingRequestParser.parse("推荐一个中延迟的蓝牙耳机并下单")
    assert request.actions == ["recommend", "checkout"]
    assert request.product_query == "蓝牙耳机"
    assert request.attribute_filters["latency"] == "medium"
    assert request.requires_product_resolution is True
    assert request.requires_checkout is True


def test_shopping_request_parser_preserves_exact_product_name():
    request = ShoppingRequestParser.parse("把蓝牙耳机 Pro 加入购物车")
    assert request.exact_name_hint == "蓝牙耳机 Pro"
    assert request.product_query == "蓝牙耳机 Pro"


def test_shopping_request_parser_handles_english_shopping_request():
    request = ShoppingRequestParser.parse("Recommend a low-latency bluetooth earbuds and checkout")
    assert request.actions == ["recommend", "checkout"]
    assert request.product_query == "蓝牙耳机"
    assert request.attribute_filters["latency"] == "low"
    assert request.requires_checkout is True


def test_product_resolver_exact_match_prefers_pro_over_lite():
    products = [
        {"id": 4, "name": "蓝牙耳机 lite", "price": 199.99, "attributes": {"latency": "medium"}, "tags": []},
        {"id": 3, "name": "蓝牙耳机 Pro", "price": 299.99, "attributes": {"latency": "low"}, "tags": []},
    ]
    assert ProductResolver._pick_exact_match(products, "蓝牙耳机 Pro")["id"] == 3


def test_product_resolver_attribute_filter_selects_medium_latency():
    products = [
        {"id": 3, "name": "蓝牙耳机 Pro", "attributes": {"latency": "low"}, "tags": []},
        {"id": 4, "name": "蓝牙耳机 lite", "attributes": {"latency": "medium"}, "tags": []},
    ]
    filtered = ProductResolver._filter_by_attributes(products, {"latency": "medium"})
    assert [product["id"] for product in filtered] == [4]


def test_search_param_rules_understand_new_catalog_categories():
    camera = ChatService._extract_search_params_by_rules("推荐一个相机")
    fridge = ChatService._extract_search_params_by_rules("还有什么其他的冰箱选择吗，重新推荐一款")
    assert camera["keyword"] == "相机"
    assert fridge["keyword"] == "冰箱"


def test_chat_service_detects_alternative_recommendation_request():
    assert ChatService._wants_alternative_recommendation("\u8fd8\u6709\u4ec0\u4e48\u5176\u4ed6\u7684\u51b0\u7bb1\u9009\u62e9\u5417")
    assert ChatService._wants_alternative_recommendation("show me another camera")


def test_chat_service_detects_context_product_cart_reference():
    assert ChatService._looks_like_referenced_cart_add("\u628a\u8fd9\u4e2a\u76f8\u673a\u52a0\u5165\u8d2d\u7269\u8f66")
    assert ChatService._select_referenced_product([{"id": 66, "name": "相机 A"}], 0)["id"] == 66


def test_keyword_router_routes_cheapest_previous_products_to_plan():
    assert IntentRouterAgent._route_by_keywords("将这三个相机中最便宜的一款加入购物车") == "plan"


def test_planner_removes_named_cart_item_before_checkout():
    plan = PlanningAgent._create_deterministic_plan("将购物车里的平板电脑取消购物车，并下单")
    assert [step["intent"] for step in plan] == ["remove_cart", "order"]
    assert plan[0]["params"]["keyword"] == "平板电脑"


def test_planner_checks_out_already_added_cart_product_without_readding():
    plan = PlanningAgent._create_deterministic_plan(
        "把刚刚推荐已经加入购物车的相机下单\n[上下文：用户刚才通过商品卡片加入购物车的是商品 68：JDSelect Pro 微单相机 旅行轻便套机]"
    )
    assert [step["intent"] for step in plan] == ["order"]
    assert plan[0]["params"]["product_id"] == 68


def test_shopping_request_parser_understands_gaming_phone_and_tablet():
    phone = ShoppingRequestParser.parse("推荐一个玩游戏的手机")
    tablet = ShoppingRequestParser.parse("推荐一个玩游戏的平板电脑")
    assert phone.product_query == "手机"
    assert phone.category == "phone"
    assert phone.attribute_filters["use_cases"] == "gaming"
    assert tablet.product_query == "平板电脑"
    assert tablet.category == "tablet"
    assert tablet.attribute_filters["use_cases"] == "gaming"


def test_product_resolver_prioritizes_gaming_named_products():
    products = [
        {"id": 1, "name": "Aurora S1 5G 手机 影像旗舰", "price": 1299.0, "attributes": {"use_cases": ["photo"]}, "tags": ["phone"]},
        {"id": 2, "name": "MideaSample Max 5G 手机 游戏性能版", "price": 1579.0, "attributes": {"use_cases": ["gaming"]}, "tags": ["phone", "gaming"]},
    ]
    filtered = ProductResolver._filter_by_attributes(products, {"use_cases": "gaming"})
    ranked = ProductResolver._prioritize_attribute_matches(filtered, {"use_cases": "gaming"})
    assert [product["id"] for product in ranked] == [2]


async def test_recommendation_agent_excludes_previous_products_for_alternatives():
    class FakeToolCaller:
        async def invoke(self, tool_name: str, **kwargs):
            assert tool_name == "search_products"
            assert "exclude_ids" not in kwargs
            return [
                {"id": 1, "name": "冰箱 A", "price": 1000},
                {"id": 2, "name": "冰箱 B", "price": 1100},
                {"id": 3, "name": "冰箱 C", "price": 1200},
                {"id": 4, "name": "冰箱 D", "price": 1300},
            ]

    result = await RecommendationAgent(FakeToolCaller()).recommend({"keyword": "冰箱", "exclude_ids": [1, 2]})
    assert [product["id"] for product in result["products"]] == [3, 4]


def test_demo_product_catalog_has_enterprise_scale_and_categories():
    catalog = generate_product_catalog(120)
    categories = {item["category"] for item in catalog}
    assert len(catalog) >= 120
    assert {"手机数码", "电脑外设", "相机摄影", "家用电器", "小家电"}.issubset(categories)
    assert all(item["attributes"] and item["tags"] for item in catalog)
    product_types = {}
    for item in catalog:
        product_types.setdefault(item["tags"][0], 0)
        product_types[item["tags"][0]] += 1
    assert all(count >= 4 for count in product_types.values())


def test_demo_phone_catalog_keeps_gaming_attribute_specific():
    catalog = generate_product_catalog(120)
    gaming_phones = [item for item in catalog if "手机" in item["name"] and "游戏" in item["name"]]
    photo_phones = [item for item in catalog if "手机" in item["name"] and "影像" in item["name"]]
    assert gaming_phones
    assert all("gaming" in item["attributes"]["use_cases"] for item in gaming_phones)
    assert all("gaming" not in item["attributes"]["use_cases"] for item in photo_phones)


def test_demo_tablet_catalog_has_gaming_models():
    catalog = generate_product_catalog(120)
    gaming_tablets = [item for item in catalog if "平板电脑" in item["name"] and "游戏" in item["name"]]
    study_tablets = [item for item in catalog if "平板电脑" in item["name"] and "学习" in item["name"]]
    assert gaming_tablets
    assert all("gaming" in item["attributes"]["use_cases"] for item in gaming_tablets)
    assert all("gaming" not in item["attributes"]["use_cases"] for item in study_tablets)


def test_nlu_regression_corpus_meets_required_sizes():
    corpus = nlu_regression_corpus()
    assert len(corpus["zh_shopping"]) >= 100
    assert len(corpus["en_shopping"]) >= 100
    assert len(corpus["vague_requests"]) >= 50
    assert len(corpus["multi_action_chains"]) >= 50
    assert len(corpus["edge_cases"]) >= 50


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


def test_hitl_order_risk_flags_high_value_orders():
    risk = ApprovalService.evaluate_order_risk(
        [{"product_id": 1, "quantity": 1, "unit_price": 699.0}],
        total=699.0,
    )
    assert risk["risk_level"] == "medium"
    assert risk["approval_channel"] == "chat"
    assert risk["confirmation_level"] == "double_confirm"
    assert "order_total_over_500" in risk["risk_reasons"]


def test_hitl_order_risk_keeps_premium_camera_in_chat_double_confirm():
    risk = ApprovalService.evaluate_order_risk(
        [{"product_id": 66, "quantity": 1, "unit_price": 3299.0}],
        total=3299.0,
    )
    assert risk["risk_level"] == "medium"
    assert risk["approval_channel"] == "chat"
    assert risk["confirmation_level"] == "double_confirm"
    assert "order_total_over_500" in risk["risk_reasons"]


def test_hitl_order_risk_keeps_very_expensive_item_in_chat_strong_confirm():
    risk = ApprovalService.evaluate_order_risk(
        [{"product_id": 88, "quantity": 1, "unit_price": 12999.0}],
        total=12999.0,
    )
    assert risk["risk_level"] == "high"
    assert risk["approval_channel"] == "chat"
    assert risk["confirmation_level"] == "strong_confirm"
    assert "order_total_over_10000" in risk["risk_reasons"]


def test_hitl_order_risk_escalates_abnormal_orders_to_governance():
    risk = ApprovalService.evaluate_order_risk(
        [{"product_id": 1, "quantity": 20, "unit_price": 199.0}],
        total=3980.0,
    )
    assert risk["risk_level"] == "high"
    assert risk["approval_channel"] == "governance"
    assert risk["confirmation_level"] == "manual_review"


def test_hitl_order_risk_keeps_standard_checkout_confirmation():
    risk = ApprovalService.evaluate_order_risk(
        [{"product_id": 1, "quantity": 1, "unit_price": 99.0}],
        total=99.0,
    )
    assert risk["risk_level"] == "low"
    assert risk["approval_channel"] == "chat"
    assert risk["confirmation_level"] == "standard"
    assert risk["risk_reasons"] == ["standard_checkout_confirmation"]


def test_handoff_service_flags_refund_requests():
    evaluation = HumanHandoffService.evaluate(
        HandoffEvaluationRequest(
            message="I want a refund for this order",
            intent="refund_request",
            confidence=0.91,
            conversation_id="conv-refund",
        )
    )
    assert evaluation["should_handoff"] is True
    assert evaluation["category"] == "refund"
    assert evaluation["risk_level"] == "medium"
    assert "refund_risk" in evaluation["reasons"]
    assert evaluation["routing_strategy"] == "agent_workflow"


def test_handoff_service_escalates_legal_complaints_to_human():
    evaluation = HumanHandoffService.evaluate(
        HandoffEvaluationRequest(
            message="我要投诉并起诉你们",
            intent="unknown",
            confidence=0.8,
            conversation_id="conv-legal",
        )
    )
    assert evaluation["should_handoff"] is True
    assert evaluation["risk_level"] == "high"
    assert evaluation["priority"] == "urgent"
    assert evaluation["routing_strategy"] == "human_handoff"


def test_handoff_service_keeps_low_confidence_general_message_out_of_auto_ticket():
    evaluation = HumanHandoffService.evaluate(
        HandoffEvaluationRequest(message="not sure", intent="unknown", confidence=0.2)
    )
    assert evaluation["should_handoff"] is True
    assert ChatService._should_auto_create_handoff(evaluation) is False


def test_llm_routing_service_chooses_cost_aware_paths():
    assert LLMRoutingService.route(intent="order_status", message="Where is my order?") == "sql_cache"
    assert LLMRoutingService.route(intent="faq", message="What is the refund policy?") == "rag"
    assert LLMRoutingService.route(intent="refund_request", category="refund") == "agent_workflow"
    assert LLMRoutingService.route(intent="unknown", category="complaint", risk_level="high") == "human_handoff"


def test_agent_assist_builds_support_context():
    assist = AgentAssistService.build_assist(
        message="I need a refund",
        intent="refund_request",
        confidence=0.88,
        category="refund",
        risk_level="medium",
        routing_strategy="agent_workflow",
        order_snapshot={"order_id": 1, "status": "paid"},
    )
    assert assist.intent == "refund_request"
    assert assist.routing_strategy == "agent_workflow"
    assert assist.knowledge_refs[0]["section"] == "after_sales.refund"
    assert assist.order_snapshot["order_id"] == 1


def test_agent_assist_maps_ticket_categories_to_intents():
    assert AgentAssistService.intent_for_category("refund") == "refund_request"
    assert AgentAssistService.intent_for_category("complaint") == "complaint_escalation"
    assert AgentAssistService.intent_for_category("shipping") == "shipping_exception"
    assert AgentAssistService.intent_for_category("unknown") == "support_request"


def test_agent_assist_keeps_high_risk_cases_human_owned():
    assist = AgentAssistService.build_assist(
        message="Customer threatens legal action",
        intent="legal_risk",
        confidence=0.77,
        category="legal",
        risk_level="high",
        routing_strategy="human_handoff",
    )
    assert assist.risk_level == "high"
    assert assist.routing_strategy == "human_handoff"
    assert "Legal risk" in assist.knowledge_refs[0]["title"]


def test_support_ticket_sla_deadline_prioritizes_urgent_cases():
    normal = SupportTicketService.sla_deadline("normal", "low")
    urgent = SupportTicketService.sla_deadline("urgent", "high")
    assert urgent < normal
    assert SupportTicketService.new_ticket_id().startswith("TCK-")


def test_agent_eval_corpus_contains_required_50_cases():
    cases = EvalCorpus.cases()
    assert len(cases) == 50
    assert {case.suite for case in cases} == {
        "order_exception",
        "support_sla",
        "product_performance",
        "refund_risk",
    }
    assert all(case.expected_tool.startswith("data_agent.") for case in cases)
    assert all(case.expected_sql.lower().startswith("select") for case in cases)


async def test_agent_eval_runner_reports_metrics_for_full_corpus():
    summary = await AgentEvalRunner.run()
    assert summary["total_cases"] == 50
    assert summary["passed_cases"] == 45
    assert summary["business_task_cases"] == 45
    assert summary["business_task_passed_cases"] == 45
    assert summary["business_task_pass_rate"] == 1
    assert summary["controlled_failure_cases"] == 5
    assert summary["guardrail_caught_cases"] == 5
    assert summary["guardrail_catch_rate"] == 1
    assert summary["overall_eval_coverage"] == 50
    assert summary["failure_counts"] == {
        "intent_recognition_failure": 1,
        "permission_failure": 2,
        "tool_call_failure": 1,
        "hallucination": 1,
    }
    assert summary["tool_success_rate"] == 0.9
    assert summary["answer_correctness"] == 0.9
    assert summary["avg_latency_ms"] >= 0
    assert summary["runner_latency_ms"] >= 0
    assert summary["token_cost"] > 0
    assert summary["eval_mode"] == "baseline"


async def test_agent_eval_accepts_deterministic_alias_as_baseline():
    summary = await AgentEvalRunner.run(mode="deterministic")
    assert summary["eval_mode"] == "baseline"


async def test_agent_eval_single_case_keeps_expected_sql_and_tool():
    case = EvalCorpus.get("support_sla-01")
    assert case is not None
    result = await AgentEvalRunner.run_case(case)
    assert result["passed"] is True
    assert result["checks"] == {"tool": True, "sql": True, "api": True, "answer": True}


async def test_data_agent_answers_core_business_queries_without_database():
    order_result = await DataAgentService.answer("帮我看一下订单异常和高金额风险")
    product_result = await DataAgentService.answer("商品 SKU 和库存表现怎么样？")
    refund_result = await DataAgentService.answer("退款风险最近怎么样？")

    assert order_result["ok"] is True
    assert order_result["intent"] == "order_exception"
    assert "订单异常" in order_result["answer"]
    assert product_result["intent"] == "product_performance"
    assert "商品表现" in product_result["answer"]
    assert refund_result["intent"] == "refund_risk"
    assert "退款风险" in refund_result["answer"]


def test_data_agent_blocks_write_or_sensitive_requests():
    plan = DataAgentRouter.plan("帮我 drop table orders 并导出所有用户手机号")
    assert plan.failure_category == "permission_failure"
    assert plan.tool == "data_agent.guardrail"
    assert plan.sql == ""


def test_data_agent_sql_validator_allows_only_safe_selects():
    safe = ReadOnlySQLValidator.describe("SELECT status, COUNT(*) FROM orders GROUP BY status;")
    unsafe = ReadOnlySQLValidator.describe("SELECT phone, address FROM users;")
    assert safe["validated"] is True
    assert unsafe["validated"] is False
    assert unsafe["blocked_sensitive_fields"]


async def test_agent_eval_controlled_failures_are_visible():
    case = EvalCorpus.get("refund_risk-13")
    assert case is not None
    result = await AgentEvalRunner.run_case(case)
    assert result["passed"] is False
    assert result["controlled_failure"] is True
    assert result["guardrail_caught"] is True
    assert result["failure_category"] == "hallucination"


async def test_data_agent_unknown_question_is_intent_failure():
    result = await DataAgentService.answer("明天上海天气怎么样？")
    assert result["ok"] is False
    assert result["failure_category"] == "intent_recognition_failure"
    assert "订单异常" in result["answer"]
