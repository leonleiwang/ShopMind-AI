# 商品解析器：把自然语言购物意图转成结构化商品查询、属性过滤、候选排序和上下文引用选择。
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chatbot.tools.product_search import ProductSearchTool


@dataclass
class ProductResolution:
    # 商品解析结果，包含命中商品、候选集、排序规则、澄清标记和解释原因。
    product: dict | None
    candidates: list[dict] = field(default_factory=list)
    query: str = ""
    sort_by: str = "relevance"
    max_price: float | None = None
    min_price: float | None = None
    selection_index: int = 0
    reason: str = ""
    needs_clarification: bool = False


@dataclass
class ShoppingRequest:
    # 用户购物请求的结构化表示，供规划、推荐、加购和结算链路复用。
    actions: list[str] = field(default_factory=list)
    product_query: str = ""
    exact_name_hint: str = ""
    category: str = ""
    attribute_filters: dict[str, Any] = field(default_factory=dict)
    selection_rule: str = "relevance"
    max_price: float | None = None
    min_price: float | None = None
    quantity: int = 1
    candidate_reference: int | None = None
    requires_product_resolution: bool = False
    requires_checkout: bool = False


class ShoppingRequestParser:
    # 规则解析器覆盖商品词、品类映射、属性同义词、排序、价格、数量和候选引用。
    PRODUCT_HINTS = [
        "游戏手机",
        "5G 手机",
        "5g 手机",
        "手机",
        "游戏平板电脑",
        "游戏平板",
        "平板电脑",
        "平板",
        "蓝牙耳机 Pro",
        "蓝牙耳机 Lite",
        "蓝牙耳机 Plus",
        "蓝牙耳机",
        "降噪耳机",
        "耳机",
        "机械键盘",
        "无线键盘",
        "键盘",
        "无线鼠标",
        "鼠标",
        "显示器",
        "微单相机",
        "相机镜头",
        "相机",
        "镜头",
        "智能电视",
        "4K 电视",
        "电视",
        "冰箱",
        "空调",
        "扫地机器人",
        "空气炸锅",
        "电饭煲",
        "洗地机",
        "bluetooth earbuds",
        "earbuds",
        "5g phone",
        "gaming phone",
        "phone",
        "gaming tablet",
        "tablet",
        "mechanical keyboard",
        "keyboard",
        "wireless mouse",
        "mouse",
        "monitor",
        "mirrorless camera",
        "camera lens",
        "camera",
        "4k tv",
        "tv",
        "fridge",
        "refrigerator",
        "air conditioner",
    ]

    CATEGORY_MAP = {
        "游戏手机": "phone",
        "5G 手机": "phone",
        "5g 手机": "phone",
        "手机": "phone",
        "gaming phone": "phone",
        "5g phone": "phone",
        "phone": "phone",
        "游戏平板电脑": "tablet",
        "游戏平板": "tablet",
        "平板电脑": "tablet",
        "平板": "tablet",
        "gaming tablet": "tablet",
        "tablet": "tablet",
        "蓝牙耳机 Pro": "bluetooth_earbuds",
        "蓝牙耳机 Lite": "bluetooth_earbuds",
        "蓝牙耳机 Plus": "bluetooth_earbuds",
        "蓝牙耳机": "bluetooth_earbuds",
        "降噪耳机": "bluetooth_earbuds",
        "耳机": "earphones",
        "bluetooth earbuds": "bluetooth_earbuds",
        "earbuds": "bluetooth_earbuds",
        "机械键盘": "keyboard",
        "无线键盘": "keyboard",
        "键盘": "keyboard",
        "mechanical keyboard": "keyboard",
        "keyboard": "keyboard",
        "无线鼠标": "mouse",
        "鼠标": "mouse",
        "wireless mouse": "mouse",
        "mouse": "mouse",
        "显示器": "monitor",
        "monitor": "monitor",
        "微单相机": "camera",
        "相机": "camera",
        "mirrorless camera": "camera",
        "camera": "camera",
        "相机镜头": "lens",
        "镜头": "lens",
        "camera lens": "lens",
        "智能电视": "tv",
        "4K 电视": "tv",
        "电视": "tv",
        "4k tv": "tv",
        "tv": "tv",
        "冰箱": "fridge",
        "fridge": "fridge",
        "refrigerator": "fridge",
        "空调": "air_conditioner",
        "air conditioner": "air_conditioner",
        "扫地机器人": "small_appliance",
        "空气炸锅": "small_appliance",
        "电饭煲": "small_appliance",
        "洗地机": "small_appliance",
    }

    QUERY_ALIASES = {
        "游戏手机": "手机",
        "5G 手机": "手机",
        "5g 手机": "手机",
        "gaming phone": "手机",
        "5g phone": "手机",
        "phone": "手机",
        "游戏平板电脑": "平板电脑",
        "游戏平板": "平板电脑",
        "平板": "平板电脑",
        "gaming tablet": "平板电脑",
        "tablet": "平板电脑",
        "降噪耳机": "蓝牙耳机",
        "耳机": "耳机",
        "bluetooth earbuds": "蓝牙耳机",
        "earbuds": "蓝牙耳机",
        "keyboard": "键盘",
        "mechanical keyboard": "机械键盘",
        "wireless mouse": "无线鼠标",
        "mouse": "鼠标",
        "monitor": "显示器",
        "mirrorless camera": "相机",
        "camera": "相机",
        "camera lens": "相机镜头",
        "4k tv": "电视",
        "tv": "电视",
        "fridge": "冰箱",
        "refrigerator": "冰箱",
        "air conditioner": "空调",
    }

    ATTRIBUTE_SYNONYMS: list[tuple[tuple[str, ...], dict[str, Any]]] = [
        (("低延迟", "低时延", "延迟低", "low-latency", "low latency"), {"latency": "low"}),
        (("中延迟", "中等延迟", "中时延", "mid-latency", "medium latency"), {"latency": "medium"}),
        (("高延迟", "高时延", "high latency"), {"latency": "high"}),
        (("玩游戏", "打游戏", "游戏", "电竞", "手游", "gaming"), {"use_cases": "gaming"}),
        (("通勤", "上班", "commute"), {"use_cases": "commute"}),
        (("日常", "平时用", "daily"), {"use_cases": "daily"}),
        (("拍照", "影像", "摄影", "photo"), {"use_cases": "photo"}),
        (("办公", "办公室", "office"), {"use_cases": "office"}),
        (("学习", "护眼", "study"), {"use_cases": "study"}),
        (("降噪", "主动降噪", "ANC", "noise cancelling", "noise-cancelling"), {"noise_cancellation": True}),
        (("音质好", "高音质", "音质优秀", "good sound quality"), {"sound_quality": "high"}),
        (("一级能效", "节能", "energy-saving"), {"energy_rating": "level_1"}),
    ]

    @classmethod
    def parse(cls, message: str) -> ShoppingRequest:
        # 解析自然语言购物请求，生成后续 Agent/Tool 可直接消费的结构化字段。
        text = message.strip()
        actions = cls._extract_actions(text)
        exact_name_hint = cls._extract_exact_name_hint(text)
        product_query = exact_name_hint or cls._extract_product_query(text)
        category = cls._extract_category(product_query or text)
        request = ShoppingRequest(
            actions=actions,
            product_query=product_query,
            exact_name_hint=exact_name_hint,
            category=category,
            attribute_filters=cls._extract_attribute_filters(text),
            selection_rule=cls._extract_sort(text),
            max_price=cls._extract_max_price(text),
            min_price=cls._extract_min_price(text),
            quantity=cls._extract_quantity(text),
            candidate_reference=cls._extract_selection_index(text),
            requires_checkout="checkout" in actions,
        )
        request.requires_product_resolution = bool(
            request.product_query
            or request.exact_name_hint
            or request.category
            or request.attribute_filters
            or request.candidate_reference is not None
        )
        return request

    @staticmethod
    def _extract_actions(text: str) -> list[str]:
        # 抽取 search/recommend/add_to_cart/checkout 等动作，并处理“不下单”等否定表达。
        actions: list[str] = []
        lower_text = text.lower()
        negative_order = any(
            word in lower_text
            for word in ["先别下单", "别下单", "不下单", "暂不下单", "先别购买", "不购买", "don't checkout", "do not checkout", "do not buy"]
        )
        exploratory_request = any(
            word in lower_text
            for word in ["推荐", "看看", "看一下", "有没有", "有哪些", "哪款", "怎么选", "比较一下", "对比", "recommend", "show me", "compare"]
        )
        if "清空" in text:
            actions.append("clear_cart")
        if any(word in lower_text for word in ["找", "搜索", "有没有", "有哪些", "find", "search", "show me"]):
            actions.append("search")
        if any(word in lower_text for word in ["推荐", "recommend"]):
            actions.append("recommend")
        if any(word in lower_text for word in ["加入", "添加", "加购", "放进", "加进", "加入购物车", "加到购物车", "add to cart", "put in cart"]):
            actions.append("add_to_cart")
        explicit_checkout = any(word in lower_text for word in ["下单", "结算", "购买", "checkout", "place order"])
        implicit_buy = any(word in lower_text for word in ["买", "buy"]) and not exploratory_request
        if not negative_order and (explicit_checkout or implicit_buy):
            actions.append("checkout")
        return list(dict.fromkeys(actions))

    @staticmethod
    def _extract_exact_name_hint(text: str) -> str:
        # 捕捉 Pro/Lite/Plus 等精确型号，避免泛搜索覆盖用户明确选择。
        patterns = [
            r"(蓝牙耳机\s*(?:Pro|Lite|Plus|Max|Air|Ultra|Mini))",
            r"([A-Za-z0-9]+\s*(?:Pro|Lite|Plus|Max|Air|Ultra|Neo|X|S1|S2)\s*[\u4e00-\u9fa5A-Za-z0-9 ]{0,20})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return re.sub(r"\s+", " ", match.group(1)).strip()
        return ""

    @classmethod
    def _extract_product_query(cls, text: str) -> str:
        # 从商品提示词和常见购买句式中抽取核心商品 query。
        lower_text = text.lower()
        for hint in sorted(cls.PRODUCT_HINTS, key=len, reverse=True):
            if hint in text or hint.lower() in lower_text:
                return cls.QUERY_ALIASES.get(hint, hint)

        match = re.search(
            r"(?:搜索|推荐|买|加入|添加|加购|选择|选)(?:一款|一个|一件|一台)?([\u4e00-\u9fa5A-Za-z0-9 ]{2,24}?)(?:加|放|加入|添加|下单|购买|最|，|。|$)",
            text,
        )
        if match:
            query = match.group(1).strip()
            query = re.sub(r"^(最便宜的?|评分最高的?|性价比最高的?|适合.+?的?|低延迟的?|中延迟的?|高延迟的?)", "", query).strip()
            return cls.QUERY_ALIASES.get(query, query)
        return ""

    @classmethod
    def _extract_category(cls, text: str) -> str:
        # 将自然语言品类词映射为内部标准 category。
        lower_text = text.lower()
        for hint, category in sorted(cls.CATEGORY_MAP.items(), key=lambda item: len(item[0]), reverse=True):
            if hint in text or hint.lower() in lower_text:
                return category
        return ""

    @classmethod
    def _extract_attribute_filters(cls, text: str) -> dict[str, Any]:
        # 解析用途、降噪、音质、能效等属性约束。
        lower_text = text.lower()
        filters: dict[str, Any] = {}
        for words, value in cls.ATTRIBUTE_SYNONYMS:
            if any(word in text or word.lower() in lower_text for word in words):
                filters.update(value)
        return filters

    @staticmethod
    def _extract_sort(text: str) -> str:
        # 抽取排序偏好：低价、高价、库存优先或性价比优先。
        lower_text = text.lower()
        if any(word in lower_text for word in ["最便宜", "最低价", "价格最低", "便宜", "cheapest", "lowest price"]):
            return "price_asc"
        if any(word in lower_text for word in ["最贵", "价格最高", "most expensive"]):
            return "price_desc"
        if any(word in lower_text for word in ["库存最大", "有货优先", "in-stock", "in stock"]):
            return "stock_desc"
        if any(word in lower_text for word in ["评分最高", "评价最好", "口碑最好", "性价比最高", "最划算", "推荐", "best value", "recommend"]):
            return "best_value"
        return "relevance"

    @staticmethod
    def _extract_max_price(text: str) -> float | None:
        # 提取“预算以内/低于/不超过”的最高价约束。
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块)?\s*(?:以内|以下|之内)|(?:不超过|低于|小于)\s*(\d+(?:\.\d+)?)", text)
        if not match:
            return None
        return float(next(group for group in match.groups() if group))

    @staticmethod
    def _extract_min_price(text: str) -> float | None:
        # 提取“以上/高于/不少于”的最低价约束。
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块)?\s*(?:以上|起)|(?:高于|大于|不少于)\s*(\d+(?:\.\d+)?)", text)
        if not match:
            return None
        return float(next(group for group in match.groups() if group))

    @staticmethod
    def _extract_quantity(text: str) -> int:
        # 提取购买数量，默认至少为 1。
        match = re.search(r"(\d+)\s*(?:件|个|台|只|副)", text)
        return max(1, int(match.group(1))) if match else 1

    @staticmethod
    def _extract_selection_index(text: str) -> int | None:
        # 解析“第一个/第二个/第三个”等候选引用。
        mapping = {
            "第一个": 0,
            "第一款": 0,
            "第1个": 0,
            "第1款": 0,
            "第二个": 1,
            "第二款": 1,
            "第2个": 1,
            "第2款": 1,
            "第三个": 2,
            "第三款": 2,
            "第3个": 2,
            "第3款": 2,
        }
        for key, value in mapping.items():
            if key in text:
                return value
        return None


class ProductResolver:
    PRODUCT_HINTS = ShoppingRequestParser.PRODUCT_HINTS

    def __init__(self, db: AsyncSession):
        # 复用商品搜索工具，保证解析和普通搜索使用同一套数据库查询口径。
        self.search_tool = ProductSearchTool(db)

    async def resolve(self, message: str, previous_products: list[dict] | None = None) -> ProductResolution:
        # 解析用户需求并返回最合适商品；优先处理上一轮候选引用，再回退到数据库搜索。
        params = self.extract_params(message)
        previous_products = previous_products or []

        if previous_products and self._should_use_previous_products(message, params):
            candidates = self._filter_by_attributes(previous_products, params["attribute_filters"])
            candidates = self._prioritize_attribute_matches(candidates or previous_products, params["attribute_filters"])
            candidates = self._rank(candidates, params["sort_by"])
            product = self._select(candidates, params["selection_index"] or 0)
            return ProductResolution(
                product=product,
                candidates=candidates,
                query="previous_results",
                sort_by=params["sort_by"],
                selection_index=params["selection_index"] or 0,
                reason=self._reason(product, params["sort_by"], "刚才推荐的商品", params["attribute_filters"]),
                needs_clarification=product is None,
            )

        if not params["query"]:
            return ProductResolution(
                product=None,
                query="",
                sort_by=params["sort_by"],
                needs_clarification=True,
                reason="没有识别到明确的商品关键词。",
            )

        candidates = await self.search_tool.execute(
            keyword=params["query"],
            max_price=params["max_price"],
            min_price=params["min_price"],
        )
        exact_product = self._pick_exact_match(candidates, params["exact_name_hint"])
        filtered_candidates = self._filter_by_attributes(candidates, params["attribute_filters"])
        prioritized_candidates = self._prioritize_attribute_matches(filtered_candidates or candidates, params["attribute_filters"])
        ranked_candidates = self._rank(prioritized_candidates, params["sort_by"])
        candidates = self._deduplicate([exact_product] + ranked_candidates if exact_product else ranked_candidates)
        product = self._select(candidates, params["selection_index"] or 0)
        return ProductResolution(
            product=product,
            candidates=candidates,
            query=params["query"],
            sort_by=params["sort_by"],
            max_price=params["max_price"],
            min_price=params["min_price"],
            selection_index=params["selection_index"] or 0,
            reason=self._reason(product, params["sort_by"], params["query"], params["attribute_filters"], params["exact_name_hint"]),
            needs_clarification=product is None,
        )

    @classmethod
    def extract_params(cls, message: str) -> dict[str, Any]:
        # 对外暴露轻量参数抽取，供 ChatService 搜索/推荐/规划逻辑复用。
        request = ShoppingRequestParser.parse(message)
        return {
            "actions": request.actions,
            "query": request.product_query,
            "exact_name_hint": request.exact_name_hint,
            "category": request.category,
            "attribute_filters": request.attribute_filters,
            "sort_by": request.selection_rule,
            "max_price": request.max_price,
            "min_price": request.min_price,
            "quantity": request.quantity,
            "selection_index": request.candidate_reference,
            "requires_product_resolution": request.requires_product_resolution,
            "requires_checkout": request.requires_checkout,
        }

    @classmethod
    def _extract_query(cls, text: str) -> str:
        return ShoppingRequestParser._extract_product_query(text)

    @staticmethod
    def _extract_sort(text: str) -> str:
        return ShoppingRequestParser._extract_sort(text)

    @staticmethod
    def _extract_max_price(text: str) -> float | None:
        return ShoppingRequestParser._extract_max_price(text)

    @staticmethod
    def _extract_min_price(text: str) -> float | None:
        return ShoppingRequestParser._extract_min_price(text)

    @staticmethod
    def _extract_selection_index(text: str) -> int | None:
        return ShoppingRequestParser._extract_selection_index(text)

    @staticmethod
    def _should_use_previous_products(message: str, params: dict[str, Any]) -> bool:
        # 判断是否应从上一轮推荐候选中选择，而不是重新搜索商品库。
        text = message.lower()
        return bool(params["selection_index"] is not None) or any(
            word in text for word in ["这个", "这款", "该商品", "刚才", "推荐的", "这几个", "这三个", "这些", "其中", "previous", "last"]
        )

    @classmethod
    def _filter_by_attributes(cls, products: list[dict], filters: dict[str, Any]) -> list[dict]:
        # 根据结构化属性过滤候选商品。
        if not filters:
            return products
        return [product for product in products if cls._matches_attribute_filters(product, filters)]

    @staticmethod
    def _matches_attribute_filters(product: dict, filters: dict[str, Any]) -> bool:
        # 单商品属性匹配逻辑，同时参考 attributes、tags 和名称信号。
        attributes = product.get("attributes") or {}
        tags = set(product.get("tags") or [])
        name = str(product.get("name") or "")
        for key, expected in filters.items():
            actual = attributes.get(key)
            if key == "use_cases":
                use_cases = actual if isinstance(actual, list) else ([actual] if actual else [])
                if expected not in use_cases and expected not in tags and expected not in name.lower():
                    return False
            elif actual != expected and expected not in tags:
                return False
        return True

    @classmethod
    def _prioritize_attribute_matches(cls, products: list[dict], filters: dict[str, Any]) -> list[dict]:
        # 对强场景属性做二次排序，例如游戏用途优先选择 gaming 信号更强的商品。
        if filters.get("use_cases") != "gaming":
            return products

        def score(product: dict) -> tuple[int, float]:
            name = str(product.get("name") or "").lower()
            tags = {str(tag).lower() for tag in product.get("tags") or []}
            has_strong_gaming_signal = any(word in name for word in ["游戏", "电竞", "gaming"]) or bool(tags & {"gaming", "game", "电竞"})
            return (0 if has_strong_gaming_signal else 1, float(product.get("price") or 0))

        return sorted(products, key=score)

    @classmethod
    def _pick_exact_match(cls, products: list[dict], exact_name_hint: str) -> dict | None:
        # 精确型号优先，防止“蓝牙耳机 Pro”被普通耳机结果冲掉。
        if not exact_name_hint:
            return None
        normalized_hint = cls._normalize_name(exact_name_hint)
        for product in products:
            if cls._normalize_name(product.get("name", "")) == normalized_hint:
                return product
        for product in products:
            if normalized_hint in cls._normalize_name(product.get("name", "")):
                return product
        return None

    @staticmethod
    def _normalize_name(value: str) -> str:
        # 商品名归一化，忽略空白和大小写差异。
        return re.sub(r"\s+", "", str(value).strip().lower())

    @staticmethod
    def _deduplicate(products: list[dict | None]) -> list[dict]:
        # 候选去重，优先使用商品 id，缺失时用名称兜底。
        seen: set[Any] = set()
        unique: list[dict] = []
        for product in products:
            if not product:
                continue
            product_id = product.get("id")
            key = product_id if product_id is not None else product.get("name")
            if key in seen:
                continue
            seen.add(key)
            unique.append(product)
        return unique

    @staticmethod
    def _rank(products: list[dict], sort_by: str) -> list[dict]:
        # 根据用户偏好对候选排序：价格、库存或简化性价比。
        if sort_by == "price_asc":
            return sorted(products, key=lambda product: float(product.get("price") or 0))
        if sort_by == "price_desc":
            return sorted(products, key=lambda product: float(product.get("price") or 0), reverse=True)
        if sort_by == "stock_desc":
            return sorted(products, key=lambda product: int(product.get("stock") or 0), reverse=True)
        if sort_by == "best_value":
            prices = [float(product.get("price") or 0) for product in products]
            max_price = max(prices) if prices else 1

            def score(product: dict) -> tuple[float, int]:
                attributes = product.get("attributes") or {}
                quality_bonus = 0.1 if attributes.get("sound_quality") == "high" else 0
                stock_bonus = 0.05 if int(product.get("stock") or 0) > 0 else 0
                price_score = float(product.get("price") or 0) / max_price
                return (price_score - quality_bonus - stock_bonus, -int(product.get("stock") or 0))

            return sorted(products, key=score)
        return products

    @staticmethod
    def _select(products: list[dict], index: int) -> dict | None:
        # 按候选序号选择商品，越界时返回 None 触发澄清。
        if index < 0 or index >= len(products):
            return None
        return products[index]

    @staticmethod
    def _reason(
        product: dict | None,
        sort_by: str,
        query: str,
        attribute_filters: dict[str, Any] | None = None,
        exact_name_hint: str = "",
    ) -> str:
        # 生成商品选择解释，帮助用户理解为什么选中该候选。
        if not product:
            return "未找到符合条件的商品。"
        if exact_name_hint:
            return f"已优先按商品名精确匹配，选择 {exact_name_hint}。"
        if attribute_filters:
            filters = "、".join(f"{key}={value}" for key, value in attribute_filters.items())
            return f"已按结构化属性筛选 {query}（{filters}）。"
        if sort_by == "price_asc":
            return f"已按价格从低到高筛选，选择最便宜的 {query}。"
        if sort_by == "price_desc":
            return f"已按价格从高到低筛选，选择价格最高的 {query}。"
        if sort_by == "stock_desc":
            return f"已按库存优先筛选，选择库存较充足的 {query}。"
        if sort_by == "best_value":
            return f"已按性价比规则筛选，综合价格、属性和库存选择 {query}。"
        return f"已根据相关性选择 {query}。"
