"""Chat endpoint – streams responses via SSE."""

from __future__ import annotations

import json
import traceback
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ChatRequest, ChatResponseChunk, LLMConfig
from app.models.game_state import get_session, append_history
from app.agents.graph import run_graph, resume_graph
from app.services.event_log import log_event

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat(req: ChatRequest):
    state = get_session(req.session_id)
    if state is None:
        raise HTTPException(404, "Session not found")

    append_history(req.session_id, {"role": "user", "content": req.message})

    async def event_generator():
        try:
            async for chunk in run_graph(
                session_id=req.session_id,
                user_message=req.message,
                llm_config=req.llm_config,
            ):
                yield {"data": chunk.model_dump_json()}

            yield {"data": ChatResponseChunk(type="done").model_dump_json()}
        except Exception as exc:
            traceback.print_exc()
            log_event("error", "chat_error", session_id=req.session_id, detail=str(exc)[:300])
            err = ChatResponseChunk(type="error", content=str(exc))
            yield {"data": err.model_dump_json()}

    return EventSourceResponse(event_generator(), ping=15)


class ResumeRequest(BaseModel):
    session_id: str
    resume_value: dict[str, Any]


@router.post("/resume")
async def resume_interrupted(req: ResumeRequest):
    """Resume a graph that was interrupted (e.g., waiting for player dice roll).

    The frontend sends the dice roll result here, and the graph continues
    from where it left off.
    """
    async def event_generator():
        try:
            async for chunk in resume_graph(
                session_id=req.session_id,
                resume_value=req.resume_value,
            ):
                yield {"data": chunk.model_dump_json()}

            yield {"data": ChatResponseChunk(type="done").model_dump_json()}
        except Exception as exc:
            traceback.print_exc()
            err = ChatResponseChunk(type="error", content=str(exc))
            yield {"data": err.model_dump_json()}

    return EventSourceResponse(event_generator(), ping=15)
