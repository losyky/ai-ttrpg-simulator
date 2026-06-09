"""LangGraph multi-agent orchestration for the TTRPG simulator.

Key LangGraph features used:
  - StateGraph with conditional edges for multi-agent routing
  - SqliteSaver checkpointer for persistent graph state across restarts
  - astream(stream_mode=updates) for real-time node-level streaming
  - RetryPolicy on LLM-calling nodes for transient failures
  - Annotated reducers for list field accumulation
  - asyncio.Queue for narrator token-level streaming

The notetaker runs as a fire-and-forget background task AFTER the
graph completes, so the SSE response closes as soon as narration is
streamed.  Summary update and memory extraction run in parallel.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, AsyncGenerator

import aiosqlite

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import RetryPolicy

from app.agents.state import AgentState
from app.agents.narrator import (
    analyze_intent,
    narrate,
    register_narrator_queue,
    unregister_narrator_queue,
)
from app.agents.referee import referee_judge
from app.agents.teammate import teammates_act
from app.agents.notetaker import schedule_notetaker
from app.agents.dice_interrupt import dice_interrupt_node
from app.models.schemas import (
    ChatResponseChunk,
    DiceResult,
    InteractiveElement,
    LLMConfig,
)
from app.models.game_state import get_session, update_session, append_history
from app.systems.registry import get_current_system
from app.services.event_log import log_event
from app.config import settings

log = logging.getLogger(__name__)


def _build_character_extras(sheet: Any, system_id: str) -> dict[str, Any]:
    """Extract system-specific extras from a CharacterSheet for sidebar display."""
    raw = getattr(sheet, "fvtt_raw", None) or getattr(sheet, "raw", None) or {}
    system = raw.get("system", {})
    extras: dict[str, Any] = {}

    if system_id == "swade":
        stats = system.get("stats", {})
        resources = system.get("resources", {})
        attrs_raw = system.get("attributes", {})
        attrs = {}
        for a in ("dexterity", "smarts", "spirit", "strength", "vigor"):
            die_data = attrs_raw.get(a, {})
            if a == "dexterity" and not die_data:
                die_data = attrs_raw.get("agility", {})
            if isinstance(die_data, dict) and "die" in die_data:
                attrs[a] = f"d{die_data['die'].get('sides', 4)}"
            else:
                attrs[a] = "d4"
        toughness_data = stats.get("toughness") or {}
        parry_data = stats.get("parry") or {}
        speed_data = stats.get("speed") or {}
        wounds_raw = system.get("wounds")
        fatigue_raw = system.get("fatigue")
        extras = {
            "attributes": attrs,
            "toughness": toughness_data.get("value", 5),
            "toughness_armor": toughness_data.get("armor", 0),
            "parry": parry_data.get("value", 4),
            "pace": speed_data.get("value", 6),
            "mp": (resources.get("mp") or {}).get("value", 0),
            "mp_max": (resources.get("mp") or {}).get("max", 0),
            "ip": (resources.get("ip") or {}).get("value", 0),
            "ip_max": (resources.get("ip") or {}).get("max", 0),
            # wounds / fatigue may be None, int, or {"value": n, "max": n}
            "wounds": (wounds_raw or {}).get("value", 0) if isinstance(wounds_raw, dict) else (wounds_raw or 0),
            "wounds_max": (wounds_raw or {}).get("max", 3) if isinstance(wounds_raw, dict) else 3,
            "fatigue": (fatigue_raw or {}).get("value", 0) if isinstance(fatigue_raw, dict) else (fatigue_raw or 0),
            "fatigue_max": (fatigue_raw or {}).get("max", 2) if isinstance(fatigue_raw, dict) else 2,
            "advances": (system.get("advances") or {}).get("value", 0),
            "pending_levelup": bool(system.get("pending_levelup", False)),
        }
    elif system_id == "daggerheart":
        resources = system.get("resources", {})
        traits_raw = system.get("traits", {})
        traits = {k: v.get("value", 0) if isinstance(v, dict) else v
                  for k, v in traits_raw.items()}
        extras = {
            "hp": resources.get("hitPoints", {}).get("value", 0),
            "max_hp": resources.get("hitPoints", {}).get("max", 0),
            "stress": resources.get("stress", {}).get("value", 0),
            "stress_max": resources.get("stress", {}).get("max", 6),
            "hope": resources.get("hope", {}).get("value", 0),
            "hope_max": resources.get("hope", {}).get("max", 6),
            "armor_slots": resources.get("armorSlots", {}).get("value", 0),
            "armor_max": resources.get("armorSlots", {}).get("max", 0),
            "evasion": system.get("evasion", 10),
            "traits": traits,
            "dh_class": system.get("class", ""),
            "subclass": system.get("subclass", ""),
        }
    else:
        ac_data = system.get("attributes", {}).get("ac", {})
        extras = {
            "ac": ac_data.get("value", 10) if isinstance(ac_data, dict) else 10,
            "temp_hp": getattr(sheet, "temp_hp", 0),
            "hero_points": getattr(sheet, "hero_points", 1),
        }
    # Include portrait URL (stored at raw level, not under system)
    portrait_url = raw.get("img", "")
    if portrait_url:
        extras["portrait_url"] = portrait_url
    return extras


def _try_auto_bind_character(session: Any, user_message: str, session_id: str) -> None:
    """If the user mentions a loaded character's name, auto-bind it to the session."""
    from app.routers.characters import _characters, _raw_data
    from app.models.schemas import CharacterSummary

    system_id = getattr(session, "system_id", "pf2e")
    msg_lower = user_message.lower()
    for char_id, sheet in _characters.items():
        if sheet.name.lower() in msg_lower:
            raw = _raw_data.get(char_id, {})
            raw_sys = raw.get("system", {})
            extras = _build_character_extras(sheet, system_id)

            if system_id == "daggerheart":
                res = raw_sys.get("resources", {})
                hp_val = res.get("hitPoints", {}).get("value", 0)
                hp_max = res.get("hitPoints", {}).get("max", 0)
                heritage = raw_sys.get("heritage", {})
                ancestry_name = heritage.get("ancestry", "") if isinstance(heritage, dict) else ""
                summary = CharacterSummary(
                    name=sheet.name,
                    ancestry=ancestry_name,
                    character_class=raw_sys.get("class", sheet.character_class),
                    level=raw_sys.get("level", sheet.level) or sheet.level,
                    hp=hp_val or sheet.hp,
                    max_hp=hp_max or sheet.max_hp,
                    extras=extras,
                )
            elif system_id == "swade":
                summary = CharacterSummary(
                    name=sheet.name,
                    ancestry=raw_sys.get("details", {}).get("species", sheet.ancestry),
                    character_class="冒险者",
                    level=raw_sys.get("advances", {}).get("value", 0),
                    hp=0,
                    max_hp=0,
                    extras=extras,
                )
            else:
                summary = CharacterSummary(
                    name=sheet.name,
                    ancestry=sheet.ancestry,
                    character_class=sheet.character_class,
                    level=sheet.level,
                    hp=sheet.hp,
                    max_hp=sheet.max_hp,
                    extras=extras,
                )

            updates: dict = {"player": summary}
            hero_pts = getattr(sheet, "hero_points", None)
            if hero_pts is not None and hero_pts > 0:
                updates["story_points"] = min(hero_pts, 3)
            update_session(session_id, **updates)
            session.player = summary
            log_event("session", "auto_bind_character", session_id=session_id,
                      detail=f"Auto-bound character: {sheet.name}")
            return


def _build_player_context(session: Any) -> str:
    """Build a rich character context string from the session's player
    and the full character store.  Uses system-specific summary when available."""
    from app.routers.characters import _characters
    from app.models.character import character_to_summary as pf2e_summary

    parts: list[str] = []
    system_id = getattr(session, "system_id", "pf2e")

    if session and session.player:
        player_name = session.player.name
        full_sheet = None
        for sheet in _characters.values():
            if sheet.name == player_name:
                full_sheet = sheet
                break
        if full_sheet:
            try:
                sys_obj = get_current_system(system_id)
                summary_data = sys_obj.character_to_summary(full_sheet)
                if isinstance(summary_data, str):
                    parts.append(f"[玩家角色详细信息]\n{summary_data}")
                else:
                    parts.append(f"[玩家角色详细信息]\n{pf2e_summary(full_sheet)}")
                    parts.append(f"[系统数据] {json.dumps(summary_data, ensure_ascii=False)}")
            except Exception:
                parts.append(f"[玩家角色详细信息]\n{pf2e_summary(full_sheet)}")
        else:
            p = session.player
            parts.append(
                f"[玩家角色]\n{p.name} — {p.ancestry} {p.character_class} Lv.{p.level}"
                f"  HP: {p.hp}/{p.max_hp}"
            )

    # SWADE level-up notification: triggered when character has a pending advance
    # (GM awards advances by updating the character's `pending_levelup` flag in raw data)
    if system_id == "swade" and session and session.player:
        extras = session.player.extras or {}
        advances = extras.get("advances", 0) or 0
        pending_levelup = extras.get("pending_levelup", False)
        if pending_levelup:
            adv_int = int(advances) if isinstance(advances, (int, float)) else 0
            rank_names = [(16, "传奇"), (12, "英杰"), (8, "老练"), (4, "行家")]
            rank_name = next((r for threshold, r in rank_names if adv_int >= threshold), "入门")
            parts.append(
                f"[⬆ 可升级] {session.player.name} 获得了新的 advance（当前共 {adv_int} 次，位阶：{rank_name}）。"
                f"请在适当叙事节点提醒玩家可前往角色页面更新角色卡（提升属性骰或选择专长）。"
            )

    other_chars = [
        s for s in _characters.values()
        if not session or not session.player or s.name != session.player.name
    ]
    if other_chars:
        names = ", ".join(f"{s.name}(Lv.{s.level} {s.character_class})" for s in other_chars[:5])
        parts.append(f"[其他可用角色卡] {names}")

    return "\n\n".join(parts)


# ── Routing functions ──

def route_after_intent(state: AgentState) -> str:
    """Route to referee for all situations (combat or not).

    Combat is handled through the same referee → narrator flow,
    with encounter tools and combat-aware prompts providing structure.
    """
    return "referee"


def route_after_referee(state: AgentState) -> str:
    if state.get("pending_dice_request"):
        return "dice_check"
    if state.get("needs_teammates"):
        return "teammates"
    return "narrate"


# ── Build the graph ──

def _build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    llm_retry = RetryPolicy(
        max_attempts=3,
        initial_interval=1.0,
        backoff_factor=2.0,
    )

    graph.add_node("analyze_intent", analyze_intent, retry_policy=llm_retry)
    graph.add_node("referee", referee_judge, retry_policy=llm_retry)
    graph.add_node("dice_check", dice_interrupt_node)
    graph.add_node("teammates", teammates_act, retry_policy=llm_retry)
    graph.add_node("narrate", narrate, retry_policy=llm_retry)

    graph.set_entry_point("analyze_intent")

    graph.add_edge("analyze_intent", "referee")

    graph.add_conditional_edges(
        "referee",
        route_after_referee,
        {
            "dice_check": "dice_check",
            "teammates": "teammates",
            "narrate": "narrate",
        },
    )

    graph.add_edge("dice_check", "narrate")
    graph.add_edge("teammates", "narrate")
    graph.add_edge("narrate", END)

    return graph


# ── Persistent async checkpointer — initialized lazily ──
_checkpoint_db = str(Path(settings.data_dir) / "checkpoints" / "graph.db")
_checkpointer: AsyncSqliteSaver | None = None
_graph_def = _build_graph()
_compiled = None  # compiled lazily


async def _get_compiled():
    global _checkpointer, _compiled
    if _compiled is not None:
        return _compiled
    conn = await aiosqlite.connect(_checkpoint_db)
    _checkpointer = AsyncSqliteSaver(conn)
    await _checkpointer.setup()
    _compiled = _graph_def.compile(checkpointer=_checkpointer)
    return _compiled


def _extract_interactive_from_text(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Pull embedded interactive JSON blocks out of narrator text."""
    elements: list[dict[str, Any]] = []
    clean_parts: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip()
        try:
            data = json.loads(stripped)
            if isinstance(data, dict) and data.get("__interactive__"):
                data.pop("__interactive__", None)
                elements.append(data)
                continue
        except (json.JSONDecodeError, TypeError):
            pass
        clean_parts.append(line)

    return "\n".join(clean_parts).strip(), elements


# ── Public API ──

async def run_graph(
    session_id: str,
    user_message: str,
    llm_config: LLMConfig,
    image_gen_config: dict[str, Any] | None = None,
) -> AsyncGenerator[ChatResponseChunk, None]:
    """Execute the multi-agent graph and yield SSE chunks.

    Uses AsyncSqliteSaver checkpointer for persistent graph state.
    Narrator tokens are streamed in real-time via an asyncio Queue
    while the graph runs concurrently.
    """
    compiled = await _get_compiled()

    session = get_session(session_id)
    game_phase = session.phase if session else "exploration"

    if session and not session.player:
        _try_auto_bind_character(session, user_message, session_id)

    player_context = _build_player_context(session)

    log_event("chat", "user_input", session_id=session_id,
              detail=user_message[:200], data={"model": llm_config.model, "phase": game_phase})

    # Increment image generation turn counter for rate limiting
    from app.tools.image_gen import init_turn_counter as _img_init
    _img_init(session_id)

    initial_state: dict[str, Any] = {
        "session_id": session_id,
        "user_message": user_message,
        "api_key": llm_config.api_key,
        "model": llm_config.model,
        "base_url": llm_config.base_url,
        "game_phase": game_phase,
        "player_context": player_context,
        "referee_output": "",
        "teammate_output": "",
        "needs_referee": False,
        "needs_teammates": False,
        "dice_results": [],
        "interactive_elements": [],
        "narrator_response": "",
        "image_gen_config": image_gen_config,
        "generated_images": [],
    }

    config = {
        "configurable": {
            "thread_id": session_id,
        }
    }

    import time as _t
    _t0 = _t.time()

    token_queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    event_queue: asyncio.Queue = asyncio.Queue()
    register_narrator_queue(session_id, token_queue)

    result: dict[str, Any] = {}
    streamed_nodes: list[str] = []
    graph_error: BaseException | None = None

    _SENTINEL = object()

    async def _graph_runner():
        nonlocal graph_error
        try:
            async for event in compiled.astream(initial_state, config=config, stream_mode="updates"):
                await event_queue.put(event)
        except Exception as exc:
            graph_error = exc
            log.error("[graph] error: %s", exc, exc_info=True)
        finally:
            await event_queue.put(_SENTINEL)

    task = asyncio.create_task(_graph_runner())
    narrator_tokens_streamed = False
    yielded_interactive_ids: set[str] = set()

    yield ChatResponseChunk(type="thinking", thinking_step="分析意图...")

    try:
        while True:
            while not token_queue.empty():
                try:
                    token = token_queue.get_nowait()
                    if isinstance(token, dict) and "__thinking__" in token:
                        yield ChatResponseChunk(type="thinking", thinking_step=token["__thinking__"])
                    elif isinstance(token, str):
                        narrator_tokens_streamed = True
                        yield ChatResponseChunk(type="text", content=token)
                except asyncio.QueueEmpty:
                    break

            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.05)
            except asyncio.TimeoutError:
                if task.done() and event_queue.empty():
                    break
                continue

            if event is _SENTINEL:
                while not token_queue.empty():
                    try:
                        token = token_queue.get_nowait()
                        if isinstance(token, dict) and "__thinking__" in token:
                            yield ChatResponseChunk(type="thinking", thinking_step=token["__thinking__"])
                        elif isinstance(token, str):
                            narrator_tokens_streamed = True
                            yield ChatResponseChunk(type="text", content=token)
                    except asyncio.QueueEmpty:
                        break
                break

            for node_name, node_output in event.items():
                streamed_nodes.append(node_name)
                result.update(node_output)

                if node_name == "analyze_intent":
                    yield ChatResponseChunk(type="thinking", thinking_step="规则裁定中...")
                elif node_name == "referee":
                    if result.get("needs_teammates"):
                        yield ChatResponseChunk(type="thinking", thinking_step="队友行动中...")
                    else:
                        yield ChatResponseChunk(type="thinking", thinking_step="构思叙事...")
                elif node_name in ("teammates", "dice_check"):
                    yield ChatResponseChunk(type="thinking", thinking_step="构思叙事...")

                log_event("agent", "node_complete", session_id=session_id,
                          detail=f"Node '{node_name}' finished",
                          data={"node": node_name})

                if node_name == "referee":
                    for dr in node_output.get("dice_results", []):
                        dice_obj = DiceResult(
                            expression=dr["expression"],
                            rolls=dr["rolls"],
                            total=dr["total"],
                            detail=dr["detail"],
                            label=dr.get("label", ""),
                            dc=dr.get("dc", 0),
                        )
                        yield ChatResponseChunk(type="dice", dice=dice_obj)
                        append_history(session_id, {
                            "role": "referee", "content": "",
                            "dice": dice_obj.model_dump(),
                        })
                    for ie_dict in node_output.get("interactive_elements", []):
                        try:
                            ie_obj = InteractiveElement(**(ie_dict if isinstance(ie_dict, dict) else ie_dict.model_dump()))
                            yield ChatResponseChunk(type="interactive", interactive=ie_obj)
                            yielded_interactive_ids.add(ie_obj.id)
                        except Exception:
                            pass

                if node_name == "teammates":
                    tm_text = node_output.get("teammate_output", "")
                    if tm_text:
                        yield ChatResponseChunk(type="text", content=tm_text)
                        append_history(session_id, {"role": "teammate", "content": tm_text})

                if node_name == "narrate":
                    while not token_queue.empty():
                        try:
                            token = token_queue.get_nowait()
                            if isinstance(token, dict) and "__thinking__" in token:
                                yield ChatResponseChunk(type="thinking", thinking_step=token["__thinking__"])
                            elif isinstance(token, str):
                                narrator_tokens_streamed = True
                                yield ChatResponseChunk(type="text", content=token)
                        except asyncio.QueueEmpty:
                            break

                    narrator_text = node_output.get("narrator_response", "")
                    extra_elements: list[dict] = []
                    if narrator_text:
                        narrator_text, extra_elements = _extract_interactive_from_text(narrator_text)

                    log_event("chat", "narrator_response", session_id=session_id,
                              agent="narrator",
                              detail=narrator_text[:200] if narrator_text else "(empty)",
                              data={"text_length": len(narrator_text) if narrator_text else 0})

                    all_interactive_dicts: list[dict] = []
                    if narrator_text:
                        if not narrator_tokens_streamed:
                            yield ChatResponseChunk(type="text", content=narrator_text)

                    for elem in extra_elements:
                        try:
                            ie_obj = InteractiveElement(**elem)
                            yield ChatResponseChunk(type="interactive", interactive=ie_obj)
                            yielded_interactive_ids.add(ie_obj.id)
                            all_interactive_dicts.append(ie_obj.model_dump())
                        except Exception:
                            pass

                    for elem in node_output.get("interactive_elements", []):
                        try:
                            ie_obj = InteractiveElement(**(elem if isinstance(elem, dict) else elem.model_dump()))
                            if ie_obj.id not in yielded_interactive_ids:
                                yield ChatResponseChunk(type="interactive", interactive=ie_obj)
                                yielded_interactive_ids.add(ie_obj.id)
                            all_interactive_dicts.append(ie_obj.model_dump())
                        except Exception:
                            pass

                    # Emit generated images as SSE image chunks
                    generated_imgs: list[str] = node_output.get("generated_images", [])
                    for img_url in generated_imgs:
                        yield ChatResponseChunk(type="image", image_url=img_url)

                    if narrator_text:
                        history_entry: dict = {"role": "narrator", "content": narrator_text}
                        if all_interactive_dicts:
                            history_entry["interactive"] = all_interactive_dicts
                        if generated_imgs:
                            history_entry["images"] = generated_imgs
                        append_history(session_id, history_entry)
                    elif generated_imgs:
                        append_history(session_id, {
                            "role": "narrator", "content": "",
                            "images": generated_imgs,
                        })

                    if all_interactive_dicts:
                        yield ChatResponseChunk(type="thinking", thinking_step="整理中...")
    finally:
        unregister_narrator_queue(session_id)
        if not task.done():
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.TimeoutError, Exception):
                task.cancel()

    if graph_error:
        raise graph_error

    _elapsed = round((_t.time() - _t0) * 1000)

    log_event("agent", "graph_complete", session_id=session_id,
              detail=f"Graph finished in {_elapsed}ms (nodes: {', '.join(streamed_nodes)})",
              data={
                  "elapsed_ms": _elapsed,
                  "nodes_executed": streamed_nodes,
                  "needs_referee": result.get("needs_referee"),
                  "needs_teammates": result.get("needs_teammates"),
                  "dice_count": len(result.get("dice_results", [])),
                  "interactive_count": len(result.get("interactive_elements", [])),
                  "narrator_len": len(result.get("narrator_response", "")),
              })

    # Fire-and-forget: notetaker runs in background after SSE closes
    schedule_notetaker(
        session_id=session_id,
        user_message=user_message,
        referee_output=result.get("referee_output", ""),
        teammate_output=result.get("teammate_output", ""),
        narrator_response=result.get("narrator_response", ""),
        llm_config={
            "model": llm_config.model,
            "api_key": llm_config.api_key,
            "base_url": llm_config.base_url,
        },
    )

    for elem in result.get("interactive_elements", []):
        try:
            ie = InteractiveElement(**(elem if isinstance(elem, dict) else elem.model_dump()))
            if ie.id not in yielded_interactive_ids:
                yield ChatResponseChunk(type="interactive", interactive=ie)
                yielded_interactive_ids.add(ie.id)
        except Exception:
            pass

    graph_state = await compiled.aget_state(config)
    if graph_state and graph_state.next:
        for t in graph_state.tasks:
            if hasattr(t, "interrupts") and t.interrupts:
                for intr in t.interrupts:
                    yield ChatResponseChunk(
                        type="interrupt",
                        interrupt_data=intr.value if hasattr(intr, "value") else {},
                    )

    updated_session = get_session(session_id)
    if updated_session:
        yield ChatResponseChunk(type="state_update", state=updated_session)


async def resume_graph(
    session_id: str,
    resume_value: dict[str, Any],
) -> AsyncGenerator[ChatResponseChunk, None]:
    """Resume a graph that was interrupted by dice_interrupt_node.

    Uses LangGraph Command to resume with the player's roll result.
    Supports narrator token streaming via asyncio Queue.
    """
    from langgraph.types import Command

    compiled = await _get_compiled()
    config = {"configurable": {"thread_id": session_id}}

    log_event("agent", "graph_resume", session_id=session_id,
              detail=f"Resuming with: {str(resume_value)[:200]}")

    token_queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    event_queue: asyncio.Queue = asyncio.Queue()
    register_narrator_queue(session_id, token_queue)

    result: dict[str, Any] = {}
    graph_error: BaseException | None = None
    _SENTINEL = object()

    async def _graph_runner():
        nonlocal graph_error
        try:
            async for event in compiled.astream(
                Command(resume=resume_value),
                config=config,
                stream_mode="updates",
            ):
                await event_queue.put(event)
        except Exception as exc:
            graph_error = exc
        finally:
            await event_queue.put(_SENTINEL)

    task = asyncio.create_task(_graph_runner())
    narrator_tokens_streamed = False

    yield ChatResponseChunk(type="thinking", thinking_step="处理骰子结果...")

    try:
        while True:
            while not token_queue.empty():
                try:
                    token = token_queue.get_nowait()
                    if isinstance(token, dict) and "__thinking__" in token:
                        yield ChatResponseChunk(type="thinking", thinking_step=token["__thinking__"])
                    elif isinstance(token, str):
                        narrator_tokens_streamed = True
                        yield ChatResponseChunk(type="text", content=token)
                except asyncio.QueueEmpty:
                    break

            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.05)
            except asyncio.TimeoutError:
                if task.done() and event_queue.empty():
                    break
                continue

            if event is _SENTINEL:
                while not token_queue.empty():
                    try:
                        token = token_queue.get_nowait()
                        if isinstance(token, dict) and "__thinking__" in token:
                            yield ChatResponseChunk(type="thinking", thinking_step=token["__thinking__"])
                        elif isinstance(token, str):
                            narrator_tokens_streamed = True
                            yield ChatResponseChunk(type="text", content=token)
                    except asyncio.QueueEmpty:
                        break
                break

            for node_name, node_output in event.items():
                result.update(node_output)

                if node_name == "narrate":
                    yield ChatResponseChunk(type="thinking", thinking_step="构思叙事...")

                if node_name == "referee":
                    for dr in node_output.get("dice_results", []):
                        dice_obj = DiceResult(
                            expression=dr["expression"],
                            rolls=dr["rolls"],
                            total=dr["total"],
                            detail=dr["detail"],
                            label=dr.get("label", ""),
                            dc=dr.get("dc", 0),
                        )
                        yield ChatResponseChunk(type="dice", dice=dice_obj)
                        append_history(session_id, {
                            "role": "referee", "content": "",
                            "dice": dice_obj.model_dump(),
                        })
                    for ie_dict in node_output.get("interactive_elements", []):
                        try:
                            ie_obj = InteractiveElement(**(ie_dict if isinstance(ie_dict, dict) else ie_dict.model_dump()))
                            yield ChatResponseChunk(type="interactive", interactive=ie_obj)
                        except Exception:
                            pass

                if node_name == "narrate":
                    while not token_queue.empty():
                        try:
                            token = token_queue.get_nowait()
                            if isinstance(token, dict) and "__thinking__" in token:
                                yield ChatResponseChunk(type="thinking", thinking_step=token["__thinking__"])
                            elif isinstance(token, str):
                                narrator_tokens_streamed = True
                                yield ChatResponseChunk(type="text", content=token)
                        except asyncio.QueueEmpty:
                            break

                    narrator_text = node_output.get("narrator_response", "")
                    all_interactive_resume: list[dict] = []
                    if narrator_text:
                        narrator_text, extra_elements = _extract_interactive_from_text(narrator_text)
                        if narrator_text:
                            if not narrator_tokens_streamed:
                                yield ChatResponseChunk(type="text", content=narrator_text)
                        for elem in extra_elements:
                            try:
                                ie_obj = InteractiveElement(**elem)
                                yield ChatResponseChunk(type="interactive", interactive=ie_obj)
                                all_interactive_resume.append(ie_obj.model_dump())
                            except Exception:
                                pass

                    for elem in node_output.get("interactive_elements", []):
                        try:
                            ie_obj = InteractiveElement(**(elem if isinstance(elem, dict) else elem.model_dump()))
                            yield ChatResponseChunk(type="interactive", interactive=ie_obj)
                            all_interactive_resume.append(ie_obj.model_dump())
                        except Exception:
                            pass

                    if narrator_text:
                        history_entry: dict = {"role": "narrator", "content": narrator_text}
                        if all_interactive_resume:
                            history_entry["interactive"] = all_interactive_resume
                        append_history(session_id, history_entry)

                    if all_interactive_resume:
                        yield ChatResponseChunk(type="thinking", thinking_step="整理中...")
    finally:
        unregister_narrator_queue(session_id)
        if not task.done():
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.TimeoutError, Exception):
                task.cancel()

    if graph_error:
        raise graph_error

    # Fire-and-forget notetaker for resumed graph
    narrator_text = result.get("narrator_response", "")
    if narrator_text:
        # Recover LLM config from the checkpointed graph state
        _gs = await compiled.aget_state(config)
        _vals = _gs.values if _gs else {}
        _api_key = _vals.get("api_key", "")
        _model = _vals.get("model", "gpt-4o")
        _base_url = _vals.get("base_url", "https://api.openai.com/v1")
        if _api_key:
            schedule_notetaker(
                session_id=session_id,
                user_message=_vals.get("user_message", ""),
                referee_output=result.get("referee_output", _vals.get("referee_output", "")),
                teammate_output=result.get("teammate_output", _vals.get("teammate_output", "")),
                narrator_response=narrator_text,
                llm_config={"model": _model, "api_key": _api_key, "base_url": _base_url},
            )

    updated_session = get_session(session_id)
    if updated_session:
        yield ChatResponseChunk(type="state_update", state=updated_session)


async def get_graph_checkpoint(session_id: str) -> dict[str, Any] | None:
    """Retrieve the latest checkpoint for a session (for debugging)."""
    compiled = await _get_compiled()
    config = {"configurable": {"thread_id": session_id}}
    try:
        state = await compiled.aget_state(config)
        if state and state.values:
            return {
                "values": {k: str(v)[:200] for k, v in state.values.items()},
                "next": list(state.next) if state.next else [],
            }
    except Exception:
        pass
    return None
