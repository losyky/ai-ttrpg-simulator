"""AI agent tools for managing skills.

These tools allow the out-of-game AI to create, read, and manage
reusable skill files that define procedures and templates.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.services.skill_manager import (
    list_skills,
    get_skill,
    create_skill,
    update_skill,
    delete_skill,
)


@tool
def skill_list() -> str:
    """List all available skills.

    Returns a list of skills with their IDs and descriptions.
    """
    skills = list_skills()
    if not skills:
        return "当前没有已创建的 Skill。你可以使用 skill_create 来创建新的 Skill。"

    lines = ["已有的 Skill："]
    for s in skills:
        desc = f" — {s['description']}" if s['description'] else ""
        lines.append(f"  - [{s['skill_id']}] {s['title']}{desc}")
    return "\n".join(lines)


@tool
def skill_read(skill_id: str) -> str:
    """Read the full content of a specific skill.

    Args:
        skill_id: The ID of the skill to read.
    """
    data = get_skill(skill_id)
    if not data:
        return f"未找到 Skill「{skill_id}」。"
    return data["content"]


@tool
def skill_create(
    skill_id: str,
    title: str,
    description: str,
    instructions: str,
    examples: str = "",
) -> str:
    """Create a new skill for the AI to use in future sessions.

    Args:
        skill_id: Unique identifier (letters, numbers, hyphens). e.g. "pf2e-combat-flow"
        title: Human-readable title of the skill.
        description: One-line description of what this skill does.
        instructions: Detailed step-by-step instructions in Markdown.
        examples: Optional examples demonstrating how to use the skill.
    """
    result = create_skill(skill_id, title, description, instructions, examples)
    return f"Skill「{result['title']}」已创建，ID: {result['skill_id']}"


@tool
def skill_update(skill_id: str, content: str) -> str:
    """Update the full content of an existing skill.

    Args:
        skill_id: The ID of the skill to update.
        content: The new full Markdown content.
    """
    ok = update_skill(skill_id, content)
    if not ok:
        return f"未找到 Skill「{skill_id}」，无法更新。"
    return f"Skill「{skill_id}」已更新。"


@tool
def skill_delete(skill_id: str) -> str:
    """Delete a skill.

    Args:
        skill_id: The ID of the skill to delete.
    """
    ok = delete_skill(skill_id)
    if not ok:
        return f"未找到 Skill「{skill_id}」。"
    return f"Skill「{skill_id}」已删除。"
