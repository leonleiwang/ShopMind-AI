# V1.1.1 Agent Eval / Data Agent API：提供评测集查看、全量/单条运行和自然语言数据查询入口。
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services.agent_eval import AgentEvalRunner, AgentEvalStore, DataAgentService, EvalCorpus
from app.services.observability import AgentObservability

router = APIRouter()


class EvalRunRequest(BaseModel):
    # 支持全量评测和指定 case 子集评测，mode 当前用于区分 baseline 与 LLM 预留入口。
    case_ids: list[str] | None = Field(default=None, description="Optional subset of eval case ids.")
    mode: str | None = Field(default=None, pattern="^(baseline|deterministic|llm)$")


class DataQueryRequest(BaseModel):
    # Data Agent 查询问题限制长度，避免无界输入影响控制台稳定性。
    question: str = Field(..., min_length=1, max_length=500)


def _require_admin(user: User) -> None:
    # Agent Eval 属于治理/观测能力，仅允许管理员或 superuser 访问。
    if user.role != "admin" and not bool(user.is_superuser):
        raise HTTPException(status_code=403, detail="Only admins can use Agent Eval")


@router.get("/cases")
async def list_eval_cases(current_user: User = Depends(get_current_user)):
    # 返回 50 条 golden-set 评测任务，供前端单条回归选择和面试展示。
    _require_admin(current_user)
    return {
        "total": len(EvalCorpus.cases()),
        "cases": [case.serialize() for case in EvalCorpus.cases()],
    }


@router.get("/summary")
async def eval_summary(current_user: User = Depends(get_current_user)):
    # 获取最近一次评测摘要；首次访问自动跑一次 baseline，保证 Dashboard 有初始数据。
    _require_admin(current_user)
    latest = AgentEvalStore.latest()
    if latest["total_cases"] == 0:
        latest = AgentEvalStore.save(await AgentEvalRunner.run())
    return latest


@router.post("/run")
async def run_eval(payload: EvalRunRequest, current_user: User = Depends(get_current_user)):
    # 运行全量或子集评测，并记录一次 AgentOps 观测事件。
    _require_admin(current_user)
    result = await AgentEvalRunner.run(payload.case_ids, mode=payload.mode or settings.AGENT_EVAL_MODE)
    AgentObservability.record_event("agent_eval_run")
    return AgentEvalStore.save(result)


@router.post("/run/{case_id}")
async def run_single_case(case_id: str, current_user: User = Depends(get_current_user)):
    # 单条 case 回归接口，便于验证某个工具路由、SQL 或 guardrail probe。
    _require_admin(current_user)
    case = EvalCorpus.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Eval case not found")
    case_result = await AgentEvalRunner.run_case(case)
    result = AgentEvalRunner.summarize([case_result])
    AgentObservability.record_event("agent_eval_single_case")
    return {"summary": result, "result": case_result}


@router.post("/data-query")
async def data_query(
    payload: DataQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 自然语言数据查询接口，复用 Data Agent 的只读 SQL、安全策略和答案生成链路。
    _require_admin(current_user)
    result = await DataAgentService.answer(payload.question, db)
    AgentObservability.record_event("data_agent_query")
    return result
