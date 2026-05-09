"""Tool registry — manages the list of built-in and custom tools.

Built-in tools are defined statically and cannot be deleted.
Custom tools are stored as JSON files on disk and can be created,
updated, and deleted by the prep agent or the user.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings

CUSTOM_TOOLS_BASE = Path(settings.data_dir) / "custom_tools"

# ── Built-in tool definitions ──

BUILTIN_TOOLS: list[dict[str, Any]] = [
    {
        "tool_id": "dice_roller",
        "name": "骰子投掷器",
        "name_en": "Dice Roller",
        "description": "投掷任意骰子表达式，如 1d20+5、2d6、4d8kh3 等。支持标准 RPG 骰子语法。",
        "category": "core",
        "builtin": True,
        "parameters": {"expression": "骰子表达式，如 1d20+5"},
    },
    # rulebook_search is now registered dynamically by the active game system
    {
        "tool_id": "search_material",
        "name": "资料搜索",
        "name_en": "Search Material",
        "description": "在已上传的参考资料（模组、剧本、JournalEntry 等）中进行全文搜索。",
        "category": "knowledge",
        "builtin": True,
        "parameters": {"query": "搜索关键词", "doc_id": "可选，限定搜索范围"},
    },
    {
        "tool_id": "browse_material",
        "name": "浏览资料",
        "name_en": "Browse Material",
        "description": "按顺序翻阅已上传文档的内容段落，类似翻书。",
        "category": "knowledge",
        "builtin": True,
        "parameters": {"doc_id": "文档 ID", "start": "起始段落索引", "count": "阅读段落数"},
    },
    {
        "tool_id": "list_materials",
        "name": "资料列表",
        "name_en": "List Materials",
        "description": "列出所有已上传的参考资料及其基本信息。",
        "category": "knowledge",
        "builtin": True,
        "parameters": {},
    },
    {
        "tool_id": "encounter_manager",
        "name": "遭遇管理器",
        "name_en": "Encounter Manager",
        "description": "管理战斗遭遇：先攻追踪、回合管理、伤害记录。",
        "category": "combat",
        "builtin": True,
        "parameters": {"action": "start / next_turn / damage / end", "details": "具体参数"},
    },
    {
        "tool_id": "character_sheet",
        "name": "角色卡管理",
        "name_en": "Character Sheet",
        "description": "查询和操作角色卡数据：HP 变更、状态查看、技能查询。",
        "category": "character",
        "builtin": True,
        "parameters": {"character_id": "角色 ID", "action": "view / update_hp / list_abilities"},
    },
    {
        "tool_id": "skill_list",
        "name": "Skill 列表",
        "name_en": "Skill List",
        "description": "列出所有已创建的 AI Skill。",
        "category": "meta",
        "builtin": True,
        "parameters": {},
    },
    {
        "tool_id": "skill_read",
        "name": "Skill 阅读",
        "name_en": "Skill Read",
        "description": "读取指定 Skill 的完整内容。",
        "category": "meta",
        "builtin": True,
        "parameters": {"skill_id": "Skill ID"},
    },
    {
        "tool_id": "skill_create",
        "name": "Skill 创建",
        "name_en": "Skill Create",
        "description": "创建新的 AI Skill（Markdown 格式定义）。",
        "category": "meta",
        "builtin": True,
        "parameters": {"skill_id": "唯一 ID", "title": "标题", "description": "描述", "instructions": "指令"},
    },
    {
        "tool_id": "present_choices",
        "name": "选项展示",
        "name_en": "Present Choices",
        "description": "向玩家展示多选项卡，用于剧情分支、行动选择等互动场景。",
        "category": "interactive",
        "builtin": True,
        "parameters": {"prompt": "提问文本", "options_json": "选项数组 JSON"},
    },
    {
        "tool_id": "request_dice_roll",
        "name": "请求掷骰",
        "name_en": "Request Dice Roll",
        "description": "请求玩家进行骰子检定，前端会展示动画骰子按钮。",
        "category": "interactive",
        "builtin": True,
        "parameters": {"prompt": "检定描述", "expression": "骰子表达式", "dc": "难度等级", "skill_name": "技能名称"},
    },
    {
        "tool_id": "request_player_input",
        "name": "请求输入",
        "name_en": "Request Player Input",
        "description": "请求玩家输入文字信息，如名字、描述、对话等。",
        "category": "interactive",
        "builtin": True,
        "parameters": {"prompt": "提问文本", "placeholder": "占位文字", "input_type": "text/number/name"},
    },
]

TOOL_CATEGORIES = {
    "core": "核心工具",
    "knowledge": "知识库工具",
    "combat": "战斗工具",
    "character": "角色工具",
    "interactive": "交互工具",
    "meta": "元工具",
    "custom": "自定义工具",
}


def _custom_tools_dir(system_id: str | None = None) -> Path:
    if system_id:
        d = CUSTOM_TOOLS_BASE / system_id
    else:
        d = CUSTOM_TOOLS_BASE
    d.mkdir(parents=True, exist_ok=True)
    return d


def _tool_path(tool_id: str, system_id: str | None = None) -> Path:
    safe_id = re.sub(r"[^\w\-]", "_", tool_id)
    return _custom_tools_dir(system_id) / f"{safe_id}.json"


# ── Public API ──

def list_all_tools(system_id: str | None = None) -> list[dict[str, Any]]:
    """Return all tools (built-in + system-specific + shared custom)."""
    tools = list(BUILTIN_TOOLS)
    try:
        from app.systems.registry import get_current_system
        system = get_current_system()
        tools.extend(system.get_builtin_tool_metadata())
    except Exception:
        pass
    dirs_to_scan = [_custom_tools_dir(system_id)] if system_id else [CUSTOM_TOOLS_BASE]
    shared_dir = CUSTOM_TOOLS_BASE / "shared"
    if shared_dir.exists() and shared_dir not in dirs_to_scan:
        dirs_to_scan.append(shared_dir)
    seen: set[str] = set()
    for d in dirs_to_scan:
        is_shared = d.name == "shared"
        for f in sorted(d.glob("*.json")):
            if f.stem in seen:
                continue
            seen.add(f.stem)
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                data["builtin"] = False
                data["shared"] = is_shared
                tools.append(data)
            except Exception:
                continue
    return tools


def get_tool(tool_id: str, system_id: str | None = None) -> dict[str, Any] | None:
    for t in BUILTIN_TOOLS:
        if t["tool_id"] == tool_id:
            return t
    for sid in [system_id, "shared"]:
        path = _tool_path(tool_id, sid)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                data["builtin"] = False
                data["shared"] = sid == "shared"
                return data
            except Exception:
                pass
    return None


def create_custom_tool(
    tool_id: str,
    name: str,
    description: str,
    parameters: dict[str, str] | None = None,
    instructions: str = "",
    category: str = "custom",
    system_id: str | None = None,
    shared: bool = False,
) -> dict[str, Any]:
    for t in BUILTIN_TOOLS:
        if t["tool_id"] == tool_id:
            raise ValueError(f"Tool ID '{tool_id}' conflicts with a built-in tool")

    tool_data = {
        "tool_id": tool_id,
        "name": name,
        "name_en": tool_id.replace("_", " ").replace("-", " ").title(),
        "description": description,
        "category": category,
        "builtin": False,
        "shared": shared,
        "parameters": parameters or {},
        "instructions": instructions,
        "created_at": datetime.now().isoformat(),
    }

    effective_sid = "shared" if shared else system_id
    path = _tool_path(tool_id, effective_sid)
    path.write_text(json.dumps(tool_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return tool_data


def update_custom_tool(tool_id: str, updates: dict[str, Any], system_id: str | None = None) -> dict[str, Any] | None:
    for t in BUILTIN_TOOLS:
        if t["tool_id"] == tool_id:
            raise ValueError("Cannot modify a built-in tool")

    path = _tool_path(tool_id, system_id)
    if not path.exists():
        return None

    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("name", "description", "parameters", "instructions", "category"):
        if key in updates:
            data[key] = updates[key]
    data["updated_at"] = datetime.now().isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    data["builtin"] = False
    return data


def delete_custom_tool(tool_id: str, system_id: str | None = None) -> bool:
    for t in BUILTIN_TOOLS:
        if t["tool_id"] == tool_id:
            raise ValueError("Cannot delete a built-in tool")

    path = _tool_path(tool_id, system_id)
    if not path.exists():
        return False
    path.unlink()
    return True


def load_custom_langchain_tools(system_id: str | None = None) -> list:
    """Load all custom tools as executable LangChain @tool functions.

    Each custom tool becomes a LangChain tool that, when called by an
    agent, returns the tool's instructions + the provided arguments
    so the agent can follow the instructions to produce a result.
    """
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field, create_model

    tools = []
    dirs_to_scan = []
    if system_id:
        dirs_to_scan.append(_custom_tools_dir(system_id))
    else:
        dirs_to_scan.append(CUSTOM_TOOLS_BASE)
    shared_dir = CUSTOM_TOOLS_BASE / "shared"
    if shared_dir.exists():
        dirs_to_scan.append(shared_dir)

    seen: set[str] = set()
    for d in dirs_to_scan:
        for f in sorted(d.glob("*.json")):
            if f.stem in seen:
                continue
            seen.add(f.stem)
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue

            tid = data.get("tool_id", f.stem)
            name = data.get("name", tid)
            desc = data.get("description", "")
            instructions = data.get("instructions", "")
            params = data.get("parameters", {})

            field_defs: dict[str, Any] = {}
            for param_name, param_desc in params.items():
                safe_name = re.sub(r"[^\w]", "_", param_name)
                field_defs[safe_name] = (str, Field(default="", description=str(param_desc)))

            if not field_defs:
                field_defs["input"] = (str, Field(default="", description="输入内容"))

            args_model = create_model(f"{tid}_args", **field_defs)

            def _make_fn(instr: str, tool_name: str):
                def fn(**kwargs) -> str:
                    parts = [f"[自定义工具: {tool_name}]"]
                    if instr:
                        parts.append(f"指令:\n{instr}")
                    if kwargs:
                        args_text = "\n".join(f"- {k}: {v}" for k, v in kwargs.items() if v)
                        if args_text:
                            parts.append(f"参数:\n{args_text}")
                    parts.append("请根据以上指令和参数生成结果。")
                    return "\n\n".join(parts)
                return fn

            lc_tool = StructuredTool.from_function(
                func=_make_fn(instructions, name),
                name=tid,
                description=f"{name}: {desc}",
                args_schema=args_model,
            )
            tools.append(lc_tool)

    return tools
