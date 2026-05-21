from __future__ import annotations

from itertools import cycle, islice, product
from typing import Any


DEMO_PASSWORD = "Demo@123456"


PRODUCT_SPECS: list[dict[str, Any]] = [
    {
        "category": "手机数码",
        "category_key": "phone",
        "type": "5G 手机",
        "names": ["影像旗舰", "轻薄长续航", "游戏性能版", "折叠屏商务版", "学生高性价比"],
        "base_price": 1299,
        "attributes": {"network": "5g", "screen_refresh_rate": 120, "use_cases": ["daily", "gaming", "photo"]},
        "tags": ["phone", "5g", "mobile"],
    },
    {
        "category": "手机数码",
        "category_key": "tablet",
        "type": "平板电脑",
        "names": ["学习护眼版", "影音娱乐版", "游戏高刷版", "生产力键盘套装", "轻薄随行版", "大屏绘画版"],
        "base_price": 999,
        "attributes": {"screen_size": "11-13 inch", "stylus_support": True, "use_cases": ["study", "office"]},
        "tags": ["tablet", "study", "portable"],
    },
    {
        "category": "手机数码",
        "category_key": "bluetooth_earbuds",
        "type": "蓝牙耳机",
        "names": ["Lite 中延迟版", "Pro 低延迟降噪版", "Air 通勤版", "Gaming 电竞低延迟版", "Max 长续航版"],
        "base_price": 159,
        "attributes": {"bluetooth_version": "5.3", "sound_quality": "medium", "noise_cancellation": False},
        "tags": ["bluetooth_earbuds", "audio", "portable"],
    },
    {
        "category": "电脑外设",
        "category_key": "keyboard",
        "type": "机械键盘",
        "names": ["青轴办公版", "茶轴静音版", "矮轴便携版", "三模无线版", "电竞 RGB 版"],
        "base_price": 199,
        "attributes": {"connection": "tri-mode", "latency": "low", "use_cases": ["office", "gaming"]},
        "tags": ["keyboard", "peripheral", "mechanical"],
    },
    {
        "category": "电脑外设",
        "category_key": "mouse",
        "type": "无线鼠标",
        "names": ["人体工学版", "游戏低延迟版", "静音办公版", "轻量化电竞版", "多设备切换版"],
        "base_price": 89,
        "attributes": {"connection": "wireless", "latency": "low", "use_cases": ["office", "gaming"]},
        "tags": ["mouse", "peripheral", "wireless"],
    },
    {
        "category": "电脑外设",
        "category_key": "monitor",
        "type": "显示器",
        "names": ["27 寸 2K 办公屏", "32 寸 4K 设计屏", "高刷电竞屏", "护眼低蓝光屏", "带鱼屏"],
        "base_price": 799,
        "attributes": {"resolution": "2k", "refresh_rate": 144, "use_cases": ["office", "design", "gaming"]},
        "tags": ["monitor", "display", "office"],
    },
    {
        "category": "相机摄影",
        "category_key": "camera",
        "type": "微单相机",
        "names": ["入门 Vlog 套机", "旅行轻便套机", "全画幅影像机", "人像拍摄套机", "直播视频套机"],
        "base_price": 3299,
        "attributes": {"camera_type": "mirrorless", "video": "4k", "use_cases": ["travel", "vlog", "portrait"]},
        "tags": ["camera", "photo", "vlog"],
    },
    {
        "category": "相机摄影",
        "category_key": "lens",
        "type": "相机镜头",
        "names": ["定焦人像镜头", "广角风光镜头", "长焦运动镜头", "微距静物镜头", "轻便套机镜头"],
        "base_price": 899,
        "attributes": {"camera_accessory": True, "use_cases": ["portrait", "travel", "macro"]},
        "tags": ["lens", "camera_accessory"],
    },
    {
        "category": "家用电器",
        "category_key": "tv",
        "type": "智能电视",
        "names": ["55 寸 4K 版", "65 寸影院版", "75 寸高刷版", "Mini LED 画质版", "客厅大屏版"],
        "base_price": 1599,
        "attributes": {"resolution": "4k", "smart_tv": True, "use_cases": ["home", "movie"]},
        "tags": ["tv", "appliance", "home"],
    },
    {
        "category": "家用电器",
        "category_key": "fridge",
        "type": "冰箱",
        "names": ["三门节能版", "对开门大容量", "母婴净味版", "一级能效风冷", "嵌入式超薄版"],
        "base_price": 1899,
        "attributes": {"energy_rating": "level_1", "capacity_liters": 450, "use_cases": ["home"]},
        "tags": ["fridge", "appliance", "energy_saving"],
    },
    {
        "category": "家用电器",
        "category_key": "air_conditioner",
        "type": "空调",
        "names": ["1.5 匹新一级能效", "客厅立式柜机", "静音卧室版", "智能变频版", "快速冷暖版"],
        "base_price": 1699,
        "attributes": {"energy_rating": "level_1", "inverter": True, "use_cases": ["home"]},
        "tags": ["air_conditioner", "appliance", "energy_saving"],
    },
    {
        "category": "小家电",
        "category_key": "small_appliance",
        "type": "厨房小家电",
        "names": ["空气炸锅", "扫地机器人", "破壁机", "智能电饭煲", "洗地机"],
        "base_price": 299,
        "attributes": {"smart_home": True, "use_cases": ["home", "kitchen", "cleaning"]},
        "tags": ["small_appliance", "smart_home"],
    },
]

BRANDS = ["Aurora", "Nova", "Pioneer", "Meridian", "MideaSample", "HaierSample", "JDSelect", "TmallChoice"]
SERIES = ["S1", "S2", "Pro", "Plus", "Max", "Air", "Ultra", "Lite", "Neo", "X"]


def generate_product_catalog(min_count: int = 120) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    brand_cycle = cycle(BRANDS)
    series_cycle = cycle(SERIES)
    for spec in PRODUCT_SPECS:
        for index, name_part in enumerate(spec["names"]):
            for variant in range(2):
                brand = next(brand_cycle)
                series = next(series_cycle)
                price = spec["base_price"] + index * 180 + variant * 70
                attributes = dict(spec["attributes"])
                tags = list(dict.fromkeys([*spec["tags"], spec["category_key"], name_part.lower().replace(" ", "_")]))
                if spec["category_key"] == "phone":
                    if "\u6e38\u620f" in name_part:
                        attributes.update({"use_cases": ["gaming", "daily"], "performance_tier": "gaming"})
                        tags.extend(["gaming", "performance"])
                    elif "\u5f71\u50cf" in name_part:
                        attributes.update({"use_cases": ["photo", "daily"], "camera_tier": "flagship"})
                        tags.extend(["photo", "camera_flagship"])
                    elif "\u5546\u52a1" in name_part:
                        attributes.update({"use_cases": ["business", "daily"], "form_factor": "foldable"})
                        tags.extend(["business", "foldable"])
                    elif "\u5b66\u751f" in name_part:
                        attributes.update({"use_cases": ["study", "daily"], "value_tier": "budget"})
                        tags.extend(["student", "best_value"])
                    else:
                        attributes.update({"use_cases": ["daily"], "battery_life": "long"})
                        tags.extend(["daily", "long_battery"])
                if spec["category_key"] == "tablet":
                    if "\u6e38\u620f" in name_part or "\u9ad8\u5237" in name_part:
                        attributes.update({"use_cases": ["gaming", "entertainment"], "refresh_rate": 144, "performance_tier": "gaming"})
                        tags.extend(["gaming", "high_refresh_rate"])
                    elif "\u5f71\u97f3" in name_part:
                        attributes.update({"use_cases": ["movie", "daily"], "speaker_tier": "enhanced"})
                        tags.extend(["entertainment", "movie"])
                    elif "\u751f\u4ea7\u529b" in name_part:
                        attributes.update({"use_cases": ["office", "study"], "keyboard_bundle": True})
                        tags.extend(["office", "productivity"])
                    elif "\u7ed8\u753b" in name_part:
                        attributes.update({"use_cases": ["design", "study"], "stylus_support": True})
                        tags.extend(["design", "stylus"])
                    else:
                        attributes.update({"use_cases": ["study", "daily"], "eye_protection": True})
                        tags.extend(["study", "eye_protection"])
                if spec["category_key"] == "bluetooth_earbuds":
                    if "低延迟" in name_part or "Gaming" in name_part:
                        attributes.update({"latency": "low", "sound_quality": "high", "use_cases": ["gaming", "commute"]})
                        tags.extend(["low_latency", "gaming"])
                    elif "中延迟" in name_part or "Lite" in name_part:
                        attributes.update({"latency": "medium", "sound_quality": "medium", "use_cases": ["daily", "commute"]})
                        tags.extend(["medium_latency", "budget"])
                    if "降噪" in name_part:
                        attributes["noise_cancellation"] = True
                        tags.append("noise_cancellation")
                products.append(
                    {
                        "name": f"{brand} {series} {spec['type']} {name_part}",
                        "description": f"{brand} {spec['type']}，适合{spec['category']}场景，包含结构化属性用于自然语言选品演示。",
                        "price": round(float(price), 2),
                        "category": spec["category"],
                        "brand": brand,
                        "image_url": "",
                        "stock": 20 + (index + 1) * 7 + variant * 3,
                        "attributes": attributes,
                        "tags": list(dict.fromkeys(tags)),
                    }
                )
    return products[:max(min_count, len(products))]


CHINESE_PRODUCTS = ["蓝牙耳机", "5G 手机", "机械键盘", "无线鼠标", "4K 电视", "冰箱", "空调", "微单相机", "平板电脑", "显示器"]
ENGLISH_PRODUCTS = ["bluetooth earbuds", "5G phone", "mechanical keyboard", "wireless mouse", "4K TV", "fridge", "air conditioner", "mirrorless camera", "tablet", "monitor"]
CHINESE_CONSTRAINTS = ["最便宜的", "低延迟的", "中延迟的", "适合通勤的", "适合打游戏的", "3000 元以内的", "库存充足的", "性价比高的", "音质好的", "一级能效的"]
ENGLISH_CONSTRAINTS = ["cheapest", "low-latency", "mid-latency", "commute-friendly", "gaming", "under 3000 yuan", "in-stock", "best value", "good sound quality", "energy-saving"]


def _take(items, count: int) -> list[str]:
    return list(islice(items, count))


def chinese_shopping_expressions(count: int = 100) -> list[str]:
    templates = [
        "帮我找一款{constraint}{product}",
        "推荐一个{constraint}{product}",
        "我想买{constraint}{product}",
        "有没有{constraint}{product}可以看看",
        "帮我对比几款{constraint}{product}",
    ]
    return _take((tpl.format(constraint=c, product=p) for tpl, c, p in product(templates, CHINESE_CONSTRAINTS, CHINESE_PRODUCTS)), count)


def english_shopping_expressions(count: int = 100) -> list[str]:
    templates = [
        "Find me a {constraint} {product}",
        "Recommend a {constraint} {product}",
        "I want to buy a {constraint} {product}",
        "Show me some {constraint} {product} options",
        "Compare several {constraint} {product} for me",
    ]
    return _take((tpl.format(constraint=c, product=p) for tpl, c, p in product(templates, ENGLISH_CONSTRAINTS, ENGLISH_PRODUCTS)), count)


def vague_product_requests(count: int = 50) -> list[str]:
    bases = [
        "帮我买个好一点的",
        "推荐一个适合家里用的",
        "我想换个新的数码产品",
        "有没有更划算的",
        "帮我挑个别太贵的",
        "送朋友买什么比较合适",
        "办公室用的有推荐吗",
        "想买个耐用的",
        "给父母用买哪个",
        "我要一个轻便一点的",
    ]
    endings = ["", "，预算还没想好", "，质量要稳", "，不要太复杂", "，最好今天能下单"]
    return _take((f"{base}{ending}" for base, ending in product(bases, endings)), count)


def multi_action_chains(count: int = 50) -> list[str]:
    templates = [
        "清空购物车，然后把{constraint}{product}加入购物车",
        "搜索{constraint}{product}，选第一款加入购物车，再下单",
        "帮我找{constraint}{product}，加入购物车，但先别下单",
        "清空购物车，推荐{constraint}{product}并下单",
        "对比两款{product}，把更便宜的加入购物车",
    ]
    return _take((tpl.format(constraint=c, product=p) for tpl, c, p in product(templates, CHINESE_CONSTRAINTS[:5], CHINESE_PRODUCTS)), count)


def edge_case_requests(count: int = 50) -> list[str]:
    cases = [
        "买 0 件蓝牙耳机",
        "买 -1 个手机",
        "下单当前购物车，但购物车是空的",
        "推荐一个不存在的火星冰箱",
        "把刚才第 99 个加入购物车",
        "买 30 台手机寄到新地址",
        "50000 元以内买 20 台相机",
        "推荐耳机，但先别下单",
        "我不要 Pro，换 Lite",
        "帮我买最贵的，但预算 100 元",
    ]
    suffixes = ["", "，马上处理", "，不要问我", "，如果失败就转人工", "，越快越好"]
    return _take((f"{case}{suffix}" for case, suffix in product(cases, suffixes)), count)


def nlu_regression_corpus() -> dict[str, list[str]]:
    return {
        "zh_shopping": chinese_shopping_expressions(100),
        "en_shopping": english_shopping_expressions(100),
        "vague_requests": vague_product_requests(50),
        "multi_action_chains": multi_action_chains(50),
        "edge_cases": edge_case_requests(50),
    }


def demo_users() -> list[dict[str, Any]]:
    return [
        {"email": "shopper@example.com", "full_name": "购物者 Demo", "role": "shopper"},
        {"email": "merchant@example.com", "full_name": "运营 Demo", "role": "merchant"},
        {"email": "support@example.com", "full_name": "客服 Demo", "role": "support"},
        {"email": "admin@example.com", "full_name": "管理员 Demo", "role": "admin"},
    ]


def user_preference_samples() -> list[dict[str, Any]]:
    return [
        {
            "email": "shopper@example.com",
            "preferred_categories": ["手机数码", "电脑外设"],
            "preferred_brands": ["Aurora", "Nova"],
            "preferred_tags": ["best_value", "low_latency", "portable"],
            "disliked_tags": ["expensive_flagship"],
            "budget_min": 100,
            "budget_max": 3000,
            "shipping_city": "南京",
            "notes": "偏好性价比、低延迟和库存充足的商品。",
        }
    ]


def support_ticket_samples() -> list[dict[str, Any]]:
    categories = ["refund", "complaint", "shipping", "invoice", "human_handoff"]
    priorities = ["normal", "high", "urgent"]
    return [
        {
            "email": "shopper@example.com",
            "category": categories[i % len(categories)],
            "status": "open" if i % 3 else "pending_review",
            "priority": priorities[i % len(priorities)],
            "subject": f"售后样本 {i + 1}: 商品体验或订单问题",
            "description": "用于演示客服 Agent、退款/投诉识别和人工接管队列。",
            "details": {"source": "demo_seed", "case_no": i + 1},
        }
        for i in range(20)
    ]


def agent_execution_log_samples() -> list[dict[str, Any]]:
    messages = multi_action_chains(20) + edge_case_requests(20)
    logs = []
    for index, message in enumerate(messages):
        failed = index % 5 == 0
        logs.append(
            {
                "email": "shopper@example.com",
                "conversation_id": f"demo-conversation-{index // 4 + 1}",
                "user_message": message,
                "intent": "plan" if "购物车" in message or "下单" in message else "search",
                "plan": ["resolve_product", "cart", "order"] if "下单" in message else ["resolve_product", "cart"],
                "tool_calls": [{"tool": "search_products"}, {"tool": "add_to_cart"}],
                "status": "failed" if failed else "success",
                "failure_reason": "demo_failure_case_for_agent_iteration" if failed else "",
                "latency_ms": 420 + index * 17,
            }
        )
    return logs
