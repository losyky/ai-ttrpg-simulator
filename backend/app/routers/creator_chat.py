"""Creator-mode chat endpoint — streams responses from the creator agent via SSE."""

from __future__ import annotations

import logging
import traceback
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import LLMConfig, ChatResponseChunk
from app.agents.creator_agent import run_creator_agent_stream
from app.services import chat_history as ch

router = APIRouter(prefix="/api/creator-chat", tags=["creator-chat"])
log = logging.getLogger(__name__)

_AGENT_TYPE = "creator"


class CreatorChatRequest(BaseModel):
    session_id: str
    message: str
    llm_config: LLMConfig


@router.post("")
async def creator_chat(req: CreatorChatRequest):
    async def event_generator():
        try:
            async for chunk in run_creator_agent_stream(
                session_id=req.session_id,
                user_message=req.message,
                llm_config=req.llm_config,
            ):
                chunk_type = chunk.get("type", "text")
                content = chunk.get("content", "")

                if chunk_type == "status":
                    yield {
                        "data": ChatResponseChunk(
                            type="text", content=f"\n\n*{content}*\n\n"
                        ).model_dump_json()
                    }
                elif chunk_type in ("text", "error", "done"):
                    yield {
                        "data": ChatResponseChunk(
                            type=chunk_type, content=content
                        ).model_dump_json()
                    }
        except Exception as exc:
            log.error("creator_chat error: %s", exc, exc_info=True)
            traceback.print_exc()
            yield {
                "data": ChatResponseChunk(
                    type="error", content=str(exc)
                ).model_dump_json()
            }

    return EventSourceResponse(event_generator(), ping=15)


@router.get("/sessions")
async def list_creator_sessions():
    return ch.list_sessions(_AGENT_TYPE)


@router.get("/sessions/{session_id}")
async def get_creator_history(session_id: str):
    return ch.get_history(_AGENT_TYPE, session_id)


@router.patch("/sessions/{session_id}")
async def update_creator_session(session_id: str, body: dict[str, Any]):
    if "label" in body:
        ch.update_session_label(_AGENT_TYPE, session_id, body["label"])
    return {"ok": True}


@router.delete("/sessions/{session_id}")
async def delete_creator_session(session_id: str):
    ch.delete_session(_AGENT_TYPE, session_id)
    return {"deleted": True}
