# backend/app/core/llm.py
from langchain_openai import ChatOpenAI
from app.core.config import settings

def get_llm():
    return ChatOpenAI(
        model=settings.OPENAI_MODEL_NAME,      # qwen3-max
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_BASE_URL,  # DashScope 兼容接口
        temperature=0.7,
        verbose=True,
    )