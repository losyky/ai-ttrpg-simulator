"""Prep Agent — the out-of-game AI assistant.

Helps the user organize materials, create skills and tools,
and prepare for game sessions. Runs independently from the
in-game multi-agent graph.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from .compat import SafeChatOpenAI as ChatOpenAI, parse_tool_calls_from_content, extract_text_without_tool_calls

from app.models.schemas import LLMConfig
from app.config import settings
from app.services import knowledge_base as kb
from app.services import skill_manager as sm
from app.services import tool_registry as tr
from app.services.event_log import log_event

log = logging.getLogger(__name__)

_WORKSPACE = Path(settings.workspace_dir)
_current_prep_system_id: str | None = None

# ── Persistent chat history ──
from app.services.chat_history import get_history as _ch_get, append as _ch_append

_AGENT_TYPE = "prep"


def _get_history(session_id: str) -> list[dict[str, str]]:
    return _ch_get(_AGENT_TYPE, session_id)


def _append(session_id: str, role: str, content: str) -> None:
    _ch_append(_AGENT_TYPE, session_id, role, content)


PREP_SYSTEM = """\
你是一位 AI 跑团准备助手（团外模式）。你是整个跑团系统的"管家"和"开发者"，帮助用户管理和增强跑团体验。

你拥有广泛的能力，可以自主创作、修改和管理各种内容，但有明确的安全边界：
- ✅ 你可以自由创建和修改 Skill、自定义工具、补充规则、工作区文件、知识库内容
- ❌ 你不能修改系统核心设定（如智能体的人设提示词、代码逻辑等）

## 你的工具

**资料管理（知识库）：**
- `list_uploaded_docs` — 查看已上传的所有参考资料
- `search_docs` — 在已上传的资料中搜索内容
- `browse_doc` — 按顺序阅读某个文档的段落
- `publish_to_documents` — 📤 将创作内容发布到知识库，发布后团内智能体可以搜索和引用

**Skill 管理（完整 CRUD）：**
- `list_all_skills` — 查看所有已创建的 Skill
- `read_skill` — 阅读某个 Skill 的内容
- `create_new_skill` — 创建新的 Skill
- `update_existing_skill` — 更新已有 Skill 的内容
- `delete_existing_skill` — 删除一个 Skill

**自定义工具管理（完整 CRUD）：**
- `list_all_tools_tool` — 查看所有可用工具（内置 + 自定义）
- `create_new_tool` — 创建新的自定义工具（创建后团内智能体会自动加载使用）
- `update_existing_tool` — 更新已有的自定义工具
- `delete_existing_tool` — 删除自定义工具（内置工具不可删除）

**补充规则管理（影响团内智能体行为的安全方式）：**
- `list_supplementary_rules` — 查看所有补充规则文件
- `read_supplementary_rule` — 读取规则文件内容
- `write_supplementary_rule` — 创建或更新补充规则（Markdown 格式）
- `delete_supplementary_rule` — 删除规则文件

补充规则的用途：自制专长、自制物品、世界观设定、特殊规则变体、自创怪物模板等。
这些规则会自动作为额外上下文提供给团内智能体（讲述者、裁决者），但不会修改它们的核心设定。

**工作区文件操作（workspace/）：**
- `ws_list_files` / `ws_read_file` / `ws_write_file` / `ws_delete_file` / `ws_mkdir`
用于保存规划、笔记、NPC 设计、草稿等各种文件。

**规则查询：**
系统根据当前规则会自动提供对应的规则检索工具（如 PF2e 的规则书搜索等）。

**角色卡创建工具：**
系统根据当前规则会自动提供对应的角色创建工具。

## 行为准则
1. 你可以**自主**创作和管理内容，但重要操作前应征求用户确认
2. 主动发现问题并提出改进建议（如缺少某个 Skill、某个工具可以优化等）
3. 创建的自定义工具会被团内智能体自动加载使用，请确保工具描述和指令清晰
4. 补充规则会影响团内体验，请确保内容准确且符合规则精神
5. 用中文回复，保持友好和专业，使用 Markdown 格式
"""


# ── Tool definitions for the prep agent ──

@tool
def list_uploaded_docs() -> str:
    """列出所有已上传的参考资料。"""
    docs = kb.list_documents()
    if not docs:
        return "当前没有已上传的参考资料。"
    lines = ["已上传的参考资料："]
    for d in docs:
        lines.append(f"- **{d['title']}** ({d['doc_type']}, {d['chunk_count']} 个片段, ID: `{d['doc_id']}`)")
    return "\n".join(lines)


@tool
def search_docs(query: str, doc_id: str = "") -> str:
    """在已上传的资料中搜索内容。

    Args:
        query: 搜索关键词
        doc_id: 可选，限定搜索范围到某个文档
    """
    results = kb.search_documents(query, doc_id=doc_id or None, limit=5)
    if not results:
        return f"未找到与「{query}」相关的内容。"
    parts = [f"搜索「{query}」的结果："]
    for r in results:
        parts.append(f"---\n**{r['section']}**\n{r['content'][:600]}")
    return "\n\n".join(parts)


@tool
def browse_doc(doc_id: str, start: int = 0, count: int = 3) -> str:
    """按顺序阅读某个文档的段落。

    Args:
        doc_id: 文档 ID
        start: 起始段落索引
        count: 阅读段落数 (1-5)
    """
    count = min(max(count, 1), 5)
    chunks = kb.read_document_section(doc_id, start=start, count=count)
    if not chunks:
        return f"未找到文档 {doc_id} 或已读完。"
    parts = []
    for c in chunks:
        parts.append(f"### {c['section']} (index {c['chunk_index']})\n{c['content']}")
    toc = kb.get_document_toc(doc_id)
    total = len(toc) if toc else "?"
    parts.append(f"\n*共 {total} 个片段，当前 {chunks[0]['chunk_index']}-{chunks[-1]['chunk_index']}*")
    return "\n\n".join(parts)


@tool
def list_all_skills() -> str:
    """查看所有已创建的 Skill。"""
    skills = sm.list_skills()
    if not skills:
        return "当前没有已创建的 Skill。"
    lines = ["已创建的 Skill："]
    for s in skills:
        lines.append(f"- **{s['title']}** (ID: `{s['skill_id']}`) — {s.get('description', '')}")
    return "\n".join(lines)


@tool
def read_skill(skill_id: str) -> str:
    """阅读某个 Skill 的完整内容。

    Args:
        skill_id: Skill 的 ID
    """
    result = sm.get_skill(skill_id)
    if result is None:
        return f"未找到 Skill: {skill_id}"
    return result["content"]


@tool
def create_new_skill(skill_id: str, title: str, description: str, instructions: str, examples: str = "") -> str:
    """创建新的 Skill。

    Args:
        skill_id: 唯一标识符 (如 pf2e-combat-flow)
        title: Skill 标题
        description: 简短描述
        instructions: 详细指令（Markdown 格式）
        examples: 可选的示例
    """
    try:
        result = sm.create_skill(skill_id, title, description, instructions, examples)
        return f"Skill **{result['title']}** (ID: `{result['skill_id']}`) 创建成功！"
    except Exception as e:
        return f"创建失败: {e}"


@tool
def update_existing_skill(skill_id: str, content: str) -> str:
    """更新已有 Skill 的内容。

    Args:
        skill_id: Skill 的 ID
        content: 新的完整 Markdown 内容
    """
    ok = sm.update_skill(skill_id, content)
    return f"Skill `{skill_id}` 已更新。" if ok else f"未找到 Skill: {skill_id}"


@tool
def delete_existing_skill(skill_id: str) -> str:
    """删除一个 Skill。

    Args:
        skill_id: Skill 的 ID
    """
    ok = sm.delete_skill(skill_id)
    return f"Skill `{skill_id}` 已删除。" if ok else f"未找到 Skill: {skill_id}"


@tool
def list_all_tools_tool() -> str:
    """查看所有可用工具（内置 + 自定义）。"""
    tools = tr.list_all_tools()
    categories: dict[str, list] = {}
    for t in tools:
        cat = t.get("category", "custom")
        categories.setdefault(cat, []).append(t)

    parts = ["所有可用工具："]
    for cat, cat_tools in categories.items():
        cat_name = tr.TOOL_CATEGORIES.get(cat, cat)
        parts.append(f"\n### {cat_name}")
        for t in cat_tools:
            lock = "🔒" if t.get("builtin") else "🔧"
            parts.append(f"- {lock} **{t['name']}** (`{t['tool_id']}`) — {t['description'][:80]}")
    return "\n".join(parts)


@tool
def create_new_tool(tool_id: str, name: str, description: str, instructions: str = "", parameters_json: str = "{}") -> str:
    """创建新的自定义工具。

    Args:
        tool_id: 唯一标识符 (如 npc-generator)
        name: 工具名称
        description: 工具功能描述
        instructions: 使用说明和实现逻辑
        parameters_json: 参数定义的 JSON 字符串，如 {"name": "NPC 名称"}
    """
    try:
        params = json.loads(parameters_json) if parameters_json else {}
    except json.JSONDecodeError:
        params = {}

    try:
        result = tr.create_custom_tool(
            tool_id=tool_id,
            name=name,
            description=description,
            parameters=params,
            instructions=instructions,
        )
        return f"工具 **{result['name']}** (ID: `{result['tool_id']}`) 创建成功！"
    except ValueError as e:
        return f"创建失败: {e}"


@tool
def update_existing_tool(tool_id: str, name: str = "", description: str = "", instructions: str = "", parameters_json: str = "") -> str:
    """更新已有的自定义工具。只需提供要更新的字段，空字符串的字段不会被修改。内置工具不可修改。

    Args:
        tool_id: 工具的 ID
        name: 新的工具名称（空则不改）
        description: 新的描述（空则不改）
        instructions: 新的使用说明（空则不改）
        parameters_json: 新的参数定义 JSON 字符串（空则不改）
    """
    updates: dict = {}
    if name:
        updates["name"] = name
    if description:
        updates["description"] = description
    if instructions:
        updates["instructions"] = instructions
    if parameters_json:
        try:
            updates["parameters"] = json.loads(parameters_json)
        except json.JSONDecodeError:
            return "parameters_json 格式错误，请提供有效的 JSON。"
    if not updates:
        return "没有提供任何要更新的字段。"
    try:
        result = tr.update_custom_tool(tool_id, updates)
        if result:
            return f"工具 `{tool_id}` 已更新。"
        return f"未找到自定义工具: {tool_id}"
    except ValueError as e:
        return str(e)


@tool
def delete_existing_tool(tool_id: str) -> str:
    """删除一个自定义工具。内置工具不可删除。

    Args:
        tool_id: 工具的 ID
    """
    try:
        ok = tr.delete_custom_tool(tool_id)
        return f"工具 `{tool_id}` 已删除。" if ok else f"未找到自定义工具: {tool_id}"
    except ValueError as e:
        return str(e)


# ── Workspace file system tools ──

def _get_workspace() -> Path:
    """Return workspace root, scoped to current system if set."""
    if _current_prep_system_id:
        ws = _WORKSPACE / _current_prep_system_id
    else:
        ws = _WORKSPACE
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def _safe_path(relative: str) -> Path | None:
    """Resolve a relative path inside the workspace. Returns None if it escapes."""
    ws = _get_workspace()
    try:
        target = (ws / relative).resolve()
        if not str(target).startswith(str(ws.resolve())):
            return None
        return target
    except Exception:
        return None


@tool
def ws_list_files(path: str = "") -> str:
    """列出工作区中的文件和子目录。

    Args:
        path: 相对于 workspace 的子路径，空字符串表示根目录
    """
    ws = _get_workspace()
    target = _safe_path(path) if path else ws
    if target is None or not target.exists():
        return f"目录不存在: {path}"
    if not target.is_dir():
        return f"不是目录: {path}"

    entries = []
    for item in sorted(target.iterdir()):
        rel = item.relative_to(ws)
        if item.is_dir():
            entries.append(f"📁 {rel}/")
        else:
            size_kb = round(item.stat().st_size / 1024, 1)
            entries.append(f"📄 {rel} ({size_kb} KB)")
    return "\n".join(entries) if entries else "（空目录）"


@tool
def ws_read_file(path: str) -> str:
    """读取工作区中的文件内容。

    Args:
        path: 相对于 workspace 的文件路径
    """
    target = _safe_path(path)
    if target is None:
        return "路径不合法（不能超出工作区）"
    if not target.exists():
        return f"文件不存在: {path}"
    if not target.is_file():
        return f"不是文件: {path}"
    try:
        content = target.read_text(encoding="utf-8")
        if len(content) > 8000:
            return content[:8000] + f"\n\n... (截断，总共 {len(content)} 字符)"
        return content
    except UnicodeDecodeError:
        return f"无法读取二进制文件: {path}"


@tool
def ws_write_file(path: str, content: str) -> str:
    """创建或覆盖工作区中的文件。

    Args:
        path: 相对于 workspace 的文件路径
        content: 文件内容
    """
    target = _safe_path(path)
    if target is None:
        return "路径不合法（不能超出工作区）"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    size_kb = round(target.stat().st_size / 1024, 1)
    log_event("data", "ws_write", detail=f"workspace/{path} ({size_kb} KB)")
    return f"已写入 workspace/{path} ({size_kb} KB)"


@tool
def ws_delete_file(path: str) -> str:
    """删除工作区中的文件。

    Args:
        path: 相对于 workspace 的文件路径
    """
    target = _safe_path(path)
    if target is None:
        return "路径不合法（不能超出工作区）"
    if not target.exists():
        return f"文件不存在: {path}"
    if target.is_dir():
        import shutil
        shutil.rmtree(target)
        return f"已删除目录 workspace/{path}"
    target.unlink()
    return f"已删除 workspace/{path}"


@tool
def ws_mkdir(path: str) -> str:
    """在工作区中创建子目录。

    Args:
        path: 相对于 workspace 的目录路径
    """
    target = _safe_path(path)
    if target is None:
        return "路径不合法（不能超出工作区）"
    target.mkdir(parents=True, exist_ok=True)
    return f"已创建目录 workspace/{path}"


from app.systems.registry import get_current_system

# ── Publish to knowledge base ──

@tool
def publish_to_documents(title: str, content: str) -> str:
    """将创作内容发布到资料库（知识库），发布后团内智能体可以在跑团中搜索和引用。

    适用于：完整的模组、世界设定、NPC 档案、规则补充等重要创作内容。
    不需要发布的：临时笔记、规划草稿（保存在工作区即可）。

    Args:
        title: 文档标题（如 "暗影酒馆冒险模组"、"NPC: 铁匠威廉"）
        content: 完整的 Markdown 内容
    """
    import uuid
    try:
        from app.systems.registry import get_default_system
        system_id = get_default_system()
        doc_id = f"prep-{uuid.uuid4().hex[:12]}"
        chunk_count = kb.ingest_text_string(
            text=content, doc_id=doc_id, title=title,
            system_id=system_id, doc_type="prep",
        )
        return (
            f"✅ 已发布到资料库！\n"
            f"- 标题: {title}\n- 文档 ID: {doc_id}\n- 片段数: {chunk_count}\n"
            f"团内智能体现在可以搜索到此内容。"
        )
    except Exception as e:
        return f"发布失败: {e}"


# ── Supplementary rules (extra context for in-game agents) ──

_RULES_DIR = Path(settings.data_dir) / "supplementary_rules"


def _rules_safe_path(filename: str, system_id: str = "") -> Path | None:
    base = _RULES_DIR / system_id if system_id else _RULES_DIR
    base.mkdir(parents=True, exist_ok=True)
    target = (base / filename).resolve()
    if not str(target).startswith(str(base.resolve())):
        return None
    return target


@tool
def list_supplementary_rules() -> str:
    """列出所有补充规则文件。这些规则会作为额外上下文提供给团内智能体使用。"""
    _RULES_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(_RULES_DIR.rglob("*.md")):
        rel = f.relative_to(_RULES_DIR)
        size_kb = round(f.stat().st_size / 1024, 1)
        files.append(f"- 📜 `{rel}` ({size_kb} KB)")
    return "\n".join(files) if files else "当前没有补充规则文件。"


@tool
def read_supplementary_rule(filename: str) -> str:
    """读取一个补充规则文件的内容。

    Args:
        filename: 文件名（如 "homebrew-feats.md"）
    """
    target = _rules_safe_path(filename)
    if not target or not target.exists():
        return f"规则文件不存在: {filename}"
    content = target.read_text(encoding="utf-8")
    if len(content) > 8000:
        return content[:8000] + f"\n\n... (截断，总共 {len(content)} 字符)"
    return content


@tool
def write_supplementary_rule(filename: str, content: str) -> str:
    """创建或更新一个补充规则文件。这些规则会作为额外上下文自动提供给团内智能体。

    适用于：自制专长、自制物品、世界观设定、特殊规则变体等。
    注意：此文件不会修改系统核心设定（如智能体人设），只是提供额外的参考信息。
    使用 Markdown 格式编写。

    Args:
        filename: 文件名，必须以 .md 结尾（如 "homebrew-feats.md"、"world-setting.md"）
        content: Markdown 格式的规则内容
    """
    if not filename.endswith(".md"):
        filename += ".md"
    target = _rules_safe_path(filename)
    if not target:
        return "路径不合法"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    size_kb = round(target.stat().st_size / 1024, 1)
    log_event("data", "rule_write", detail=f"supplementary_rules/{filename} ({size_kb} KB)")
    return f"✅ 补充规则已保存: `{filename}` ({size_kb} KB)\n团内智能体将在下次对话时参考此规则。"


@tool
def delete_supplementary_rule(filename: str) -> str:
    """删除一个补充规则文件。

    Args:
        filename: 文件名
    """
    target = _rules_safe_path(filename)
    if not target or not target.exists():
        return f"规则文件不存在: {filename}"
    target.unlink()
    return f"补充规则 `{filename}` 已删除。"


def _get_prep_tools(session_id: str | None = None):
    system = get_current_system(session_id)
    system_tools = system.get_tools().get("prep", [])
    rulebook_tools = system.get_tools().get("referee", [])
    return [
        # Knowledge base
        list_uploaded_docs,
        search_docs,
        browse_doc,
        publish_to_documents,
        # Skills CRUD
        list_all_skills,
        read_skill,
        create_new_skill,
        update_existing_skill,
        delete_existing_skill,
        # Custom tools CRUD
        list_all_tools_tool,
        create_new_tool,
        update_existing_tool,
        delete_existing_tool,
        # Supplementary rules
        list_supplementary_rules,
        read_supplementary_rule,
        write_supplementary_rule,
        delete_supplementary_rule,
        # Workspace filesystem
        ws_list_files,
        ws_read_file,
        ws_write_file,
        ws_delete_file,
        ws_mkdir,
    ] + system_tools + rulebook_tools


async def run_prep_agent_stream(
    session_id: str,
    user_message: str,
    llm_config: LLMConfig,
) -> AsyncGenerator[dict[str, str], None]:
    """Run the prep agent and yield SSE-compatible chunks in real-time.

    Uses ainvoke for tool-calling iterations (preserves reasoning_content
    for thinking models). Uses astream for the final non-tool response.
    """
    log.info("[prep] session=%s starting, message=%.100s", session_id, user_message)

    global _current_prep_system_id
    system = get_current_system(session_id)
    _current_prep_system_id = system.system_id

    llm = ChatOpenAI(
        model=llm_config.model,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        temperature=0.7,
    )
    PREP_TOOLS = _get_prep_tools(session_id)
    llm_with_tools = llm.bind_tools(PREP_TOOLS)

    _append(session_id, "user", user_message)
    log_event("chat", "prep_input", session_id=session_id,
              agent="prep_agent", detail=user_message[:200])
    history = _get_history(session_id)

    system = get_current_system(session_id)
    system_prep_prompt = system.get_prompts().get("prep", PREP_SYSTEM)
    messages: list = [SystemMessage(content=system_prep_prompt)]
    for msg in history[-20:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    tool_map = {t.name: t for t in PREP_TOOLS}
    max_iterations = 8
    collected_text = ""

    for iteration in range(max_iterations):
        log.info("[prep] session=%s iteration=%d", session_id, iteration)

        try:
            response = await llm_with_tools.ainvoke(messages)
        except Exception as exc:
            log.error("[prep] LLM error: %s", exc, exc_info=True)
            yield {"type": "error", "content": f"LLM 调用失败: {exc}"}
            return

        messages.append(response)

        tool_calls = response.tool_calls or []

        if not tool_calls and response.content:
            fallback_calls = parse_tool_calls_from_content(str(response.content))
            if fallback_calls:
                tool_calls = fallback_calls
                log.info("[prep] fallback parsed %d tool call(s)", len(fallback_calls))

        if response.content:
            text = str(response.content)
            if tool_calls and not response.tool_calls:
                text = extract_text_without_tool_calls(text)
            if text:
                yield {"type": "text", "content": text}
                collected_text += text

        if not tool_calls:
            _append(session_id, "assistant", collected_text)
            log.info("[prep] session=%s done, length=%d", session_id, len(collected_text))
            yield {"type": "done", "content": ""}
            return

        for tc in tool_calls:
            tool_fn = tool_map.get(tc["name"])
            if tool_fn is None:
                tool_result = f"Unknown tool: {tc['name']}"
                yield {"type": "status", "content": f"⚠️ 未知工具: {tc['name']}"}
            else:
                yield {"type": "status", "content": f"🔧 正在使用工具: {tc['name']}…"}
                try:
                    tool_result = await tool_fn.ainvoke(tc["args"])
                except Exception as e:
                    tool_result = f"Tool error: {e}"
                    log.warning("[prep] tool %s error: %s", tc["name"], e)
            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))

    log.info("[prep] session=%s max iterations, final streaming call", session_id)
    try:
        async for chunk in llm.astream(messages):
            if chunk.content:
                token = str(chunk.content)
                collected_text += token
                yield {"type": "text", "content": token}
    except Exception as exc:
        log.error("[prep] final LLM error: %s", exc, exc_info=True)
        yield {"type": "error", "content": f"LLM 调用失败: {exc}"}
        return

    _append(session_id, "assistant", collected_text)
    yield {"type": "done", "content": ""}


async def run_prep_agent(
    session_id: str,
    user_message: str,
    llm_config: LLMConfig,
) -> str:
    """Non-streaming wrapper for backward compatibility."""
    result = ""
    async for chunk in run_prep_agent_stream(session_id, user_message, llm_config):
        if chunk["type"] == "text":
            result += chunk["content"]
        elif chunk["type"] == "error":
            raise RuntimeError(chunk["content"])
    return result
