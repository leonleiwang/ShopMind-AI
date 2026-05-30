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
    case_ids: list[str] | None = Field(default=None, description="Optional subset of eval case ids.")
    mode: str | None = Field(default=None, pattern="^(baseline|deterministic|llm)$")


class DataQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


def _require_admin(user: User) -> None:
    if user.role != "admin" and not bool(user.is_superuser):
        raise HTTPException(status_code=403, detail="Only admins can use Agent Eval")


@router.get("/cases")
async def list_eval_cases(current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    return {
        "total": len(EvalCorpus.cases()),
        "cases": [case.serialize() for case in EvalCorpus.cases()],
    }


@router.get("/summary")
async def eval_summary(current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    latest = AgentEvalStore.latest()
    if latest["total_cases"] == 0:
        latest = AgentEvalStore.save(await AgentEvalRunner.run())
    return latest


@router.post("/run")
async def run_eval(payload: EvalRunRequest, current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    result = await AgentEvalRunner.run(payload.case_ids, mode=payload.mode or settings.AGENT_EVAL_MODE)
    AgentObservability.record_event("agent_eval_run")
    return AgentEvalStore.save(result)


@router.post("/run/{case_id}")
async def run_single_case(case_id: str, current_user: User = Depends(get_current_user)):
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
    _require_admin(current_user)
    result = await DataAgentService.answer(payload.question, db)
    AgentObservability.record_event("data_agent_query")
    return result
