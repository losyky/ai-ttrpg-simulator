"""Tools for the narrator to manage the party and request prep agent work.

These tools let the narrator:
  - List available character cards that could be teammates
  - Suggest adding a teammate (with player approval via interactive choice)
  - Send a request to the prep agent for content creation
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from langchain_core.tools import tool


@tool
def list_available_characters() -> str:
    """List all imported character cards that could serve as teammates.

    Returns a summary of each character including name, ancestry, class, and level.
    Use this to know which characters are available before suggesting teammates.
    """
    from app.routers.characters import _characters
    from app.models.character import character_to_summary

    if not _characters:
        return "当前没有已导入的角色卡。请建议玩家在「团外准备」中导入角色卡。"

    lines = [f"共 {len(_characters)} 张角色卡:\n"]
    for sheet in _characters.values():
        lines.append(f"- **{sheet.name}** (ID: {sheet.id})")
        lines.append(f"  {sheet.ancestry} {sheet.character_class} Lv.{sheet.level} | HP {sheet.hp}/{sheet.max_hp}")
    return "\n".join(lines)


@tool
def suggest_add_teammate(character_name: str, reason: str) -> str:
    """Suggest adding a character as an AI teammate to the current party.

    This presents an interactive choice to the player asking for their approval.
    Only use this when the story genuinely needs more party members.

    Args:
        character_name: The exact name of the character to add.
        reason: Why this character should join the party (1-2 sentences).
    """
    result = {
        "__interactive__": True,
        "element_type": "choices",
        "id": f"add-teammate-{uuid.uuid4().hex[:8]}",
        "prompt": f"💡 **队友建议**: {reason}\n\n是否将 **{character_name}** 加入队伍作为 AI 队友？",
        "options": [
            {"id": f"accept_{character_name}", "label": f"欢迎加入", "description": f"将 {character_name} 加入队伍", "icon": "✅"},
            {"id": "decline", "label": "暂时不需要", "description": "维持当前队伍", "icon": "❌"},
        ],
    }
    return json.dumps(result, ensure_ascii=False)


@tool
def request_prep_work(task_type: str, description: str) -> str:
    """Send a content creation request to the prep agent (团外AI).

    Use this when you need content that doesn't exist yet — such as
    character cards for NPCs, custom skills, special tools, or scenario materials.

    The request will be queued and the prep agent will handle it.

    Args:
        task_type: Type of work: "character" | "skill" | "tool" | "material" | "other"
        description: Detailed description of what needs to be created and why.
    """
    from app.services.event_log import log_event

    request_id = uuid.uuid4().hex[:8]
    log_event("cross_agent", "prep_request", detail=f"[{task_type}] {description[:200]}",
              data={"request_id": request_id, "task_type": task_type})

    return (
        f"已向团外准备助手发送制作请求 (#{request_id}):\n"
        f"类型: {task_type}\n"
        f"内容: {description}\n\n"
        f"请告知玩家：可以切换到「团外准备 → 助手」标签页查看和处理此请求。"
    )


PARTY_TOOLS = [list_available_characters, suggest_add_teammate, request_prep_work]
