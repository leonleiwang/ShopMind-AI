from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from threading import Lock
from time import time
from uuid import uuid4

from app.core.config import settings


@dataclass
class ConversationState:
    """[反思1a-多轮澄清] 会话状态，保存历史、槽位和上一轮候选范围。"""

    user_id: int
    conversation_id: str = field(default_factory=lambda: str(uuid4()))
    history: list[dict] = field(default_factory=list)
    slots: dict = field(default_factory=dict)
    pending_slots: list[str] = field(default_factory=list)
    last_intent: str | None = None
    last_products: list[dict] = field(default_factory=list)
    updated_at: float = field(default_factory=time)

    def add_message(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        self.history = self.history[-12:]
        self.updated_at = time()


class ConversationStore:
    """[反思1a-多轮澄清] Redis-first 会话状态仓库。

    本地测试或 Redis 暂不可用时回退到进程内内存；生产环境通过 REDIS_URL/REDIS_HOST
    使用 Redis 保存 conversation_id、history、slots 和 pending_slots。
    """

    def __init__(self) -> None:
        self._states: dict[tuple[int, str], ConversationState] = {}
        self._lock = Lock()
        self._redis = None
        self._redis_disabled = settings.CONVERSATION_STATE_BACKEND.lower() != "redis"

    def get(self, user_id: int, conversation_id: str | None = None) -> ConversationState:
        redis_state = self._get_from_redis(user_id, conversation_id)
        if redis_state:
            with self._lock:
                self._states[(user_id, redis_state.conversation_id)] = redis_state
            return redis_state

        with self._lock:
            if conversation_id:
                key = (user_id, conversation_id)
                if key not in self._states:
                    self._states[key] = ConversationState(user_id=user_id, conversation_id=conversation_id)
                return self._states[key]

            for (stored_user_id, _), state in self._states.items():
                if stored_user_id == user_id:
                    return state

            state = ConversationState(user_id=user_id)
            self._states[(user_id, state.conversation_id)] = state
            return state

    def save(self, state: ConversationState) -> None:
        with self._lock:
            self._states[(state.user_id, state.conversation_id)] = state
        self._save_to_redis(state)

    def _get_from_redis(self, user_id: int, conversation_id: str | None) -> ConversationState | None:
        client = self._redis_client()
        if not client:
            return None
        try:
            if not conversation_id:
                conversation_id = client.get(self._last_key(user_id))
            if not conversation_id:
                return None
            raw = client.get(self._state_key(user_id, conversation_id))
            if not raw:
                return None
            data = json.loads(raw)
            return ConversationState(
                user_id=int(data["user_id"]),
                conversation_id=data["conversation_id"],
                history=list(data.get("history") or []),
                slots=dict(data.get("slots") or {}),
                pending_slots=list(data.get("pending_slots") or []),
                last_intent=data.get("last_intent"),
                last_products=list(data.get("last_products") or []),
                updated_at=float(data.get("updated_at") or time()),
            )
        except Exception:
            self._redis_disabled = True
            return None

    def _save_to_redis(self, state: ConversationState) -> None:
        client = self._redis_client()
        if not client:
            return
        try:
            ttl = settings.CONVERSATION_STATE_TTL_SECONDS
            client.setex(
                self._state_key(state.user_id, state.conversation_id),
                ttl,
                json.dumps(asdict(state), ensure_ascii=False),
            )
            client.setex(self._last_key(state.user_id), ttl, state.conversation_id)
        except Exception:
            self._redis_disabled = True

    def _redis_client(self):
        if self._redis_disabled:
            return None
        if self._redis is not None:
            return self._redis
        try:
            from redis import Redis

            self._redis = Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
            self._redis.ping()
            return self._redis
        except Exception:
            self._redis_disabled = True
            return None

    @staticmethod
    def _state_key(user_id: int, conversation_id: str) -> str:
        return f"shopmind:conversation:{user_id}:{conversation_id}"

    @staticmethod
    def _last_key(user_id: int) -> str:
        return f"shopmind:conversation:last:{user_id}"


class ClarificationAgent:
    """[反思1a-多轮澄清] 对模糊请求做槽位判断，并生成候选问题。"""

    SEARCH_TRIGGERS = ("不好用", "不会用", "不能用", "怎么用", "怎么弄", "怎么办", "有问题")
    PRODUCT_HINTS = ("耳机", "手机", "电脑", "键盘", "鼠标", "显示器", "充电器", "商品")

    def inspect(self, message: str, intent: str, params: dict | None = None) -> dict:
        params = params or {}
        required_slots: list[str] = []
        text = message.strip()

        is_support_like = any(trigger in text for trigger in self.SEARCH_TRIGGERS)
        has_product_hint = any(hint in text for hint in self.PRODUCT_HINTS)
        if intent in {"search", "recommend"} and not params.get("keyword") and not params.get("category"):
            required_slots.append("keyword")
        if is_support_like and not has_product_hint:
            required_slots.extend(["business_domain", "symptom"])

        required_slots = list(dict.fromkeys(required_slots))
        return {
            "needs_clarification": bool(required_slots),
            "required_slots": required_slots,
            "question": self._build_question(required_slots),
            "options": self._build_options(required_slots),
        }

    @staticmethod
    def _build_question(required_slots: list[str]) -> str:
        if "business_domain" in required_slots:
            return "你说的“不好用/不会办”具体是哪个业务或功能？我先帮你缩小范围。"
        if "keyword" in required_slots:
            return "你想找哪类商品？可以补充品类、预算或使用场景。"
        return "我需要再确认一个关键信息，才能继续处理。"

    @staticmethod
    def _build_options(required_slots: list[str]) -> list[str]:
        if "business_domain" in required_slots:
            return ["商品搜索/推荐", "购物车/下单", "订单查询/售后"]
        if "keyword" in required_slots:
            return ["蓝牙耳机", "手机", "电脑/外设"]
        return []


conversation_store = ConversationStore()
