"""Creator Agent — the out-of-game AI for writing adventure modules and world content.

Dedicated to generating scripts, world-building, NPC backgrounds, plot hooks,
encounter designs, and other creative content for TTRPGs that may lack
pre-written modules (e.g. Daggerheart, SWADE/七物语).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from .compat import SafeChatOpenAI as ChatOpenAI, parse_tool_calls_from_content, extract_text_without_tool_calls

from app.models.schemas import LLMConfig
from app.config import settings
from app.services import knowledge_base as kb
from app.services.event_log import log_event

log = logging.getLogger(__name__)

_WORKSPACE = Path(settings.workspace_dir)

from app.services.chat_history import get_history as _ch_get, append as _ch_append

_AGENT_TYPE = "creator"


def _get_history(session_id: str) -> list[dict[str, str]]:
    return _ch_get(_AGENT_TYPE, session_id)


def _append(session_id: str, role: str, content: str) -> None:
    _ch_append(_AGENT_TYPE, session_id, role, content)


CREATOR_SYSTEM = """\
你是一位专业的 TTRPG 剧本创作家（Creator）。你的使命是帮助用户创作高质量的跑团内容。

## 你的能力
1. **冒险模组创作**: 设计完整的冒险剧本，包含场景、NPC、遭遇、谜题和剧情分支
2. **世界观构建**: 创造城市、地区、组织、历史背景等世界设定
3. **NPC 设计**: 创作有深度的 NPC，包含动机、秘密、关系网
4. **遭遇设计**: 设计战斗遭遇、社交遭遇和探索遭遇，包含平衡建议
5. **剧情钩子**: 生成能引发冒险的剧情钩子和任务线索
6. **随机表格**: 创建各类随机事件表、宝物表、遭遇表

## 创作原则
- **系统适配**: 根据当前游戏系统（PF2e / Daggerheart / 七物语）调整机制细节
- **叙事为先**: 任何遭遇和设计都应服务于叙事，不是纯数值对抗
- **分支设计**: 剧本应包含多条可能的发展路线，而非线性铁路
- **可玩性**: 考虑实际游戏中的节奏、时长和玩家体验
- **氛围营造**: 提供场景描述、环境音效建议、氛围文字

## 输出格式
- 使用 Markdown 格式输出
- 模组用 ## 分节（概述、背景、场景列表、NPC 一览、遭遇详情等）
- NPC 信息包含：名字、种族/身份、外貌、性格、动机、秘密、关键台词
- 遭遇包含：场景描述、敌方构成、DC/难度建议、可能的结果

## 系统适配指南

### PF2e 模组
- 遭遇等级应标注（如 Moderate/Severe）
- NPC 使用 PF2e 数据格式（等级、种族、职业、技能等）
- 技能检定注明 DC 和可用技能

### Daggerheart 模组
- 设计时考虑 Hope/Fear 经济的节奏
- 为关键场景提供 Fear 花费建议（如何用 Fear 制造戏剧高潮）
- NPC 使用 Tier 制，注明 HP、Evasion、Thresholds
- 场景设计应支持叙事流式推进，无需严格轮次

### 七物语 (SWADE) 模组
- 注明双属性骰检定的推荐属性组合和 DC
- 利用物语点和元素系统增强叙事
- NPC 注明是否为不羁角色(Wildcard)，以及属性骰面

## 工具使用
你可以使用以下工具：
- `search_docs`: 搜索已上传的资料作为创作参考
- `browse_doc`: 浏览特定文档内容
- `ws_write_file`: 将创作完成的内容保存到工作区
- `ws_read_file`: 读取工作区中已有的创作内容
- `ws_list_files`: 列出工作区文件
- `ws_mkdir`: 在工作区创建目录

将创作的模组保存到工作区的 `创作内容/` 目录下，使用 `.md` 格式。

## 发布到资料库
创作完成后，**务必使用 `publish_to_documents` 工具将重要内容发布到资料库**。
发布后的内容会进入知识库，其他智能体可以在跑团中搜索和引用。
- 短篇、笔记等可以不发布（只保存到工作区）
- 完整模组、世界设定、NPC 档案等重要创作内容应发布到资料库
"""


@tool
def search_docs(query: str, limit: int = 5) -> str:
    """Search uploaded documents for reference material.

    Args:
        query: The search query.
        limit: Max results to return.
    """
    try:
        hits = kb.search_documents(query, limit=limit)
        if not hits:
            return "未找到相关资料。"
        parts = []
        for h in hits:
            section = h.get("section", "")
            content = h.get("content", "")[:600]
            parts.append(f"**[{section}]**\n{content}")
        return "\n---\n".join(parts)
    except Exception as e:
        return f"搜索失败: {e}"


@tool
def browse_doc(doc_id: str, page: int = 0) -> str:
    """Browse a specific document's content.

    Args:
        doc_id: The document ID.
        page: Page offset (each page ~2000 chars).
    """
    try:
        chunks = kb.read_document_section(doc_id, start=page * 3, count=3)
        if not chunks:
            return "文档不存在或无内容。"
        parts = []
        for c in chunks:
            parts.append(f"[{c.get('section', '')}]\n{c.get('content', '')}")
        return "\n---\n".join(parts)
    except Exception as e:
        return f"浏览失败: {e}"


def _safe_path(rel: str) -> Path | None:
    """Ensure the path stays within the workspace."""
    try:
        target = (_WORKSPACE / rel).resolve()
        if not str(target).startswith(str(_WORKSPACE.resolve())):
            return None
        return target
    except Exception:
        return None


@tool
def ws_list_files(directory: str = ".") -> str:
    """List files in the workspace directory.

    Args:
        directory: Relative path within workspace.
    """
    p = _safe_path(directory)
    if not p or not p.exists():
        return "目录不存在。"
    items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
    lines = []
    for item in items[:50]:
        prefix = "📁" if item.is_dir() else "📄"
        rel = item.relative_to(_WORKSPACE)
        lines.append(f"{prefix} {rel}")
    return "\n".join(lines) if lines else "（空目录）"


@tool
def ws_read_file(file_path: str) -> str:
    """Read a file from the workspace.

    Args:
        file_path: Relative path within workspace.
    """
    p = _safe_path(file_path)
    if not p or not p.is_file():
        return "文件不存在。"
    try:
        content = p.read_text(encoding="utf-8")
        if len(content) > 8000:
            content = content[:8000] + "\n... (truncated)"
        return content
    except Exception as e:
        return f"读取失败: {e}"


@tool
def ws_write_file(file_path: str, content: str) -> str:
    """Write content to a file in the workspace.

    Args:
        file_path: Relative path within workspace.
        content: The text content to write.
    """
    p = _safe_path(file_path)
    if not p:
        return "路径无效。"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"已保存到 {p.relative_to(_WORKSPACE)}"


@tool
def ws_mkdir(directory: str) -> str:
    """Create a directory in the workspace.

    Args:
        directory: Relative path within workspace.
    """
    p = _safe_path(directory)
    if not p:
        return "路径无效。"
    p.mkdir(parents=True, exist_ok=True)
    return f"目录已创建: {p.relative_to(_WORKSPACE)}"


@tool
def publish_to_documents(title: str, content: str, system_id: str = "") -> str:
    """Publish creative content to the knowledge base so other agents can reference it during gameplay.

    Args:
        title: Title for the document (e.g. "暗影酒馆冒险模组", "NPC: 铁匠威廉").
        content: The full Markdown content to publish.
        system_id: Game system ID (auto-detected if empty).
    """
    import uuid
    try:
        if not system_id:
            from app.systems.registry import get_default_system
            system_id = get_default_system().system_id

        doc_id = f"creator-{uuid.uuid4().hex[:12]}"
        chunk_count = kb.ingest_text_string(
            text=content,
            doc_id=doc_id,
            title=title,
            system_id=system_id,
            doc_type="creator",
        )
        if chunk_count == 0:
            return "内容为空，未发布。"

        return (
            f"✅ 已发布到资料库！\n"
            f"- 标题: {title}\n"
            f"- 文档 ID: {doc_id}\n"
            f"- 片段数: {chunk_count}\n"
            f"- 系统: {system_id}\n"
            f"其他智能体（叙述者等）现在可以搜索到此内容。"
        )
    except Exception as e:
        return f"发布失败: {e}"


def _get_creator_tools(session_id: str | None = None) -> list:
    """Get tools available to the creator agent."""
    from app.systems.registry import get_current_system
    system = get_current_system(session_id)
    npc_tools = system.get_npc_builder_tools()

    base_tools = [
        search_docs,
        browse_doc,
        publish_to_documents,
        ws_list_files,
        ws_read_file,
        ws_write_file,
        ws_mkdir,
    ]
    return base_tools + npc_tools


async def run_creator_agent_stream(
    session_id: str,
    user_message: str,
    llm_config: LLMConfig,
) -> AsyncGenerator[dict[str, str], None]:
    """Run the creator agent and yield SSE-compatible chunks in real-time.

    Uses ainvoke for tool-calling iterations (preserves reasoning_content
    for thinking models like DeepSeek R1). Uses astream for the final
    non-tool response to provide token-level streaming.
    """
    from app.systems.registry import get_current_system

    log.info("[creator] session=%s starting, message=%.100s", session_id, user_message)

    llm = ChatOpenAI(
        model=llm_config.model,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        temperature=0.85,
    )
    CREATOR_TOOLS = _get_creator_tools(session_id)
    from app.utils.tools import fix_noarg_tools
    llm_with_tools = llm.bind_tools(fix_noarg_tools(CREATOR_TOOLS))

    _append(session_id, "user", user_message)
    log_event("chat", "creator_input", session_id=session_id,
              agent="creator_agent", detail=user_message[:200])
    history = _get_history(session_id)

    system = get_current_system(session_id)
    system_name = system.display_name

    system_creator_prompt = system.get_prompts().get("creator", "")
    system_prompt = CREATOR_SYSTEM
    if system_creator_prompt:
        system_prompt += f"\n\n---\n## 当前系统: {system_name}\n{system_creator_prompt}"
    else:
        system_prompt += f"\n\n当前游戏系统: **{system_name}** (system_id: {system.system_id})\n请根据此系统的特点进行创作。"

    messages: list = [SystemMessage(content=system_prompt)]
    for msg in history[-20:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    tool_map = {t.name: t for t in CREATOR_TOOLS}
    max_iterations = 8
    collected_text = ""

    for iteration in range(max_iterations):
        log.info("[creator] session=%s iteration=%d", session_id, iteration)

        try:
            response = await llm_with_tools.ainvoke(messages)
        except Exception as exc:
            log.error("[creator] LLM error: %s", exc, exc_info=True)
            yield {"type": "error", "content": f"LLM 调用失败: {exc}"}
            return

        messages.append(response)

        tool_calls = response.tool_calls or []

        if not tool_calls and response.content:
            fallback_calls = parse_tool_calls_from_content(str(response.content))
            if fallback_calls:
                tool_calls = fallback_calls
                log.info("[creator] fallback parsed %d tool call(s)", len(fallback_calls))

        if response.content:
            text = str(response.content)
            if not response.tool_calls:
                text = extract_text_without_tool_calls(text)
            if text:
                yield {"type": "text", "content": text}
                collected_text += text

        if not tool_calls:
            _append(session_id, "assistant", collected_text)
            log.info("[creator] session=%s done, length=%d", session_id, len(collected_text))
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
                    log.warning("[creator] tool %s error: %s", tc["name"], e)
            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))

    log.info("[creator] session=%s max iterations, final streaming call", session_id)
    try:
        async for chunk in llm.astream(messages):
            if chunk.content:
                token = str(chunk.content)
                collected_text += token
                yield {"type": "text", "content": token}
    except Exception as exc:
        log.error("[creator] final LLM stream error: %s", exc, exc_info=True)
        yield {"type": "error", "content": f"LLM 调用失败: {exc}"}
        return

    _append(session_id, "assistant", collected_text)
    yield {"type": "done", "content": ""}


async def run_creator_agent(
    session_id: str,
    user_message: str,
    llm_config: LLMConfig,
) -> str:
    """Non-streaming wrapper for backward compatibility."""
    result = ""
    async for chunk in run_creator_agent_stream(session_id, user_message, llm_config):
        if chunk["type"] == "text":
            result += chunk["content"]
        elif chunk["type"] == "error":
            raise RuntimeError(chunk["content"])
    return result
