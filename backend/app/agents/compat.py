"""Compatibility layer for reasoning / thinking models.

Providers like DeepSeek, Qwen QwQ, GLM, Moonshot, etc. return a
``reasoning_content`` field alongside ``content``.  The official
``ChatOpenAI`` class does *not* extract or preserve this field.

Different providers have **different** requirements for multi-turn:

+-----------------------+------------------+--------------------+
| Provider / Model      | With tool_calls  | Without tool_calls |
+=======================+==================+====================+
| DeepSeek R1           | MUST include     | MUST remove        |
| DeepSeek V3/V4 think  | MUST include     | Optional (ignored) |
| Qwen QwQ              | —                | MUST remove        |
| OpenAI o1/o3/o4-mini  | N/A (internal)   | N/A (internal)     |
| GLM / Moonshot think  | MUST include     | Similar to DS      |
| Standard (non-reason) | No such field    | No such field      |
+-----------------------+------------------+--------------------+

**Universal rule** (``auto`` strategy):
  * assistant messages WITH ``tool_calls``  → keep reasoning_content
  * assistant messages WITHOUT tool_calls   → strip reasoning_content

This works across all known providers.  An override setting
(``reasoning_content_strategy``) is available for edge cases:
  * ``auto``   – smart per-message logic (default)
  * ``keep``   – always include reasoning_content
  * ``strip``  – always remove reasoning_content

Also includes a **fallback tool-call parser** that extracts tool
invocations from the raw ``content`` text when the model outputs
non-standard formats (DeepSeek DSML, XML-style ``<tool_call>``,
or raw JSON ``{"name": ..., "arguments": ...}``).
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Callable, Literal, Sequence

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

log = logging.getLogger(__name__)

# Official DeepSeek API hostname – only this gets the auto /beta treatment.
_DEEPSEEK_OFFICIAL_HOST = "api.deepseek.com"

# Global strategy – can be changed at runtime via API.
_reasoning_strategy: Literal["auto", "keep", "strip"] = "auto"


def set_reasoning_strategy(strategy: Literal["auto", "keep", "strip"]) -> None:
    global _reasoning_strategy
    _reasoning_strategy = strategy
    log.info("reasoning_content strategy set to: %s", strategy)


def get_reasoning_strategy() -> str:
    return _reasoning_strategy


def sanitize_ai_message(msg: AIMessage) -> AIMessage:
    """Return a copy of *msg* without reasoning / thinking metadata.

    Useful when you want to store a message for logging but do NOT
    plan to send it back to the same provider.
    """
    additional = dict(msg.additional_kwargs) if msg.additional_kwargs else {}
    additional.pop("reasoning_content", None)
    additional.pop("refusal", None)

    resp_meta = dict(msg.response_metadata) if msg.response_metadata else {}
    resp_meta.pop("reasoning_content", None)

    return AIMessage(
        content=msg.content,
        tool_calls=msg.tool_calls if msg.tool_calls else [],
        additional_kwargs=additional,
        response_metadata=resp_meta,
        id=msg.id,
    )


def _should_keep_reasoning(msg: AIMessage) -> bool:
    """Decide whether to include reasoning_content for *msg* based on
    the current global strategy."""
    if _reasoning_strategy == "keep":
        return True
    if _reasoning_strategy == "strip":
        return False
    # auto: keep only when the message has tool_calls
    return bool(msg.tool_calls)


class SafeChatOpenAI(ChatOpenAI):
    """``ChatOpenAI`` subclass that transparently handles the
    ``reasoning_content`` field used by thinking models AND auto-enables
    DeepSeek strict tool-call mode.

    * On the **response** path it captures ``reasoning_content`` from
      the raw API response and stores it in ``additional_kwargs``.
    * On the **request** path it re-injects or strips
      ``reasoning_content`` based on the active strategy.
    * On **400 errors** mentioning ``reasoning_content``, it
      automatically retries with the opposite strategy.
    * ``bind_tools`` is overridden to enable DeepSeek strict mode
      automatically, which forces the model to use structured JSON
      tool_calls instead of falling back to DSML text output.
    """

    # ---- DeepSeek detection helpers ----

    def _is_deepseek_official(self) -> bool:
        """True when pointing at api.deepseek.com (the official endpoint)."""
        return _DEEPSEEK_OFFICIAL_HOST in str(self.openai_api_base or "").lower()

    def _is_deepseek(self) -> bool:
        """True for any DeepSeek model/endpoint (official or third-party)."""
        base = str(self.openai_api_base or "").lower()
        model = str(self.model_name or "").lower()
        return "deepseek" in base or model.startswith("deepseek")

    def _make_beta_instance(self) -> "SafeChatOpenAI":
        """Return a copy of self using the DeepSeek /beta endpoint.

        DeepSeek's strict tool-call mode is only available at
        https://api.deepseek.com/beta.  This method converts
        /v1 (or bare domain) to /beta automatically.
        """
        base = str(self.openai_api_base or "").rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        if not base.endswith("/beta"):
            base = base + "/beta"

        kwargs: dict[str, Any] = dict(
            model=self.model_name,
            api_key=self.openai_api_key.get_secret_value(),
            base_url=base,
            temperature=self.temperature,
        )
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        if self.streaming:
            kwargs["streaming"] = self.streaming
        return SafeChatOpenAI(**kwargs)

    # ---- bind_tools override: auto strict mode for DeepSeek ----

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable | BaseTool],
        *,
        tool_choice: dict | str | bool | None = None,
        strict: bool | None = None,
        parallel_tool_calls: bool | None = None,
        response_format: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Bind tools, automatically enabling strict mode for DeepSeek.

        DeepSeek strict mode guarantees the model outputs structured
        ``tool_calls`` JSON instead of falling back to DSML text.

        For official api.deepseek.com endpoints the request is routed
        through the /beta base URL which is required for strict mode.
        For third-party DeepSeek-compatible endpoints strict=True is
        attempted but the URL is left unchanged.
        """
        if strict is None and self._is_deepseek():
            strict = True
            log.debug(
                "[SafeChatOpenAI] DeepSeek detected – enabling strict tool mode"
            )

            # Official API: recreate on the /beta endpoint
            if self._is_deepseek_official():
                try:
                    beta = self._make_beta_instance()
                    log.debug(
                        "[SafeChatOpenAI] Switching to beta endpoint: %s",
                        beta.openai_api_base,
                    )
                    # Call the grandparent's bind_tools directly on the beta
                    # instance so we don't recurse back into this override.
                    return ChatOpenAI.bind_tools(
                        beta,
                        tools,
                        tool_choice=tool_choice,
                        strict=strict,
                        parallel_tool_calls=parallel_tool_calls,
                        response_format=response_format,
                        **kwargs,
                    )
                except Exception as exc:
                    log.warning(
                        "[SafeChatOpenAI] Beta endpoint switch failed (%s) – "
                        "falling back to standard endpoint with strict=True",
                        exc,
                    )

        return super().bind_tools(
            tools,
            tool_choice=tool_choice,
            strict=strict,
            parallel_tool_calls=parallel_tool_calls,
            response_format=response_format,
            **kwargs,
        )

    # ---- response side: capture reasoning_content ----

    def _create_chat_result(
        self, response: Any, generation_info: dict | None = None
    ) -> Any:
        reasoning_map: dict[int, str] = {}
        try:
            if hasattr(response, "choices") and response.choices:
                for i, choice in enumerate(response.choices):
                    msg = getattr(choice, "message", None)
                    if msg is None:
                        continue
                    rc = getattr(msg, "reasoning_content", None)
                    if rc:
                        reasoning_map[i] = rc
            elif isinstance(response, dict):
                for i, choice in enumerate(response.get("choices", [])):
                    rc = choice.get("message", {}).get("reasoning_content")
                    if rc:
                        reasoning_map[i] = rc
        except Exception:
            pass

        result = super()._create_chat_result(response, generation_info)

        for idx, rc in reasoning_map.items():
            if idx < len(result.generations):
                gen_msg = result.generations[idx].message
                if isinstance(gen_msg, AIMessage):
                    gen_msg.additional_kwargs["reasoning_content"] = rc

        return result

    # ---- request side: re-inject reasoning_content ----

    def _get_request_payload(
        self,
        input_: Any,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        messages: list[BaseMessage] = self._convert_input(input_).to_messages()

        # Build map: index → (reasoning_content, should_include)
        reasoning_actions: dict[int, tuple[str, bool]] = {}
        for i, msg in enumerate(messages):
            if isinstance(msg, AIMessage):
                rc = (msg.additional_kwargs or {}).get("reasoning_content")
                if rc:
                    reasoning_actions[i] = (rc, _should_keep_reasoning(msg))

        payload = super()._get_request_payload(input_, stop=stop, **kwargs)

        if reasoning_actions and "messages" in payload:
            for idx, (rc, keep) in reasoning_actions.items():
                if idx < len(payload["messages"]):
                    if keep:
                        payload["messages"][idx]["reasoning_content"] = rc
                    else:
                        payload["messages"][idx].pop("reasoning_content", None)

        return payload

    # ---- auto-retry on reasoning_content 400 errors ----

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        try:
            return await super()._agenerate(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
        except Exception as exc:
            if _is_reasoning_content_error(exc):
                log.warning(
                    "reasoning_content 400 error detected, retrying with "
                    "opposite strategy for this request."
                )
                return await self._retry_with_flipped_reasoning(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
            raise

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        try:
            return super()._generate(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
        except Exception as exc:
            if _is_reasoning_content_error(exc):
                log.warning(
                    "reasoning_content 400 error detected, retrying with "
                    "opposite strategy for this request."
                )
                return self._retry_with_flipped_reasoning_sync(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
            raise

    async def _retry_with_flipped_reasoning(self, messages, **kwargs):
        """Retry the request after flipping reasoning_content on every
        AIMessage (add if missing, remove if present)."""
        flipped = _flip_reasoning_in_messages(messages)
        return await super()._agenerate(flipped, **kwargs)

    def _retry_with_flipped_reasoning_sync(self, messages, **kwargs):
        flipped = _flip_reasoning_in_messages(messages)
        return super()._generate(flipped, **kwargs)


# ---- helpers ----

def _is_reasoning_content_error(exc: Exception) -> bool:
    """Return True if the exception is a 400 error about reasoning_content."""
    msg = str(exc).lower()
    return (
        "400" in msg
        and "reasoning_content" in msg
    )


def _flip_reasoning_in_messages(
    messages: list[BaseMessage],
) -> list[BaseMessage]:
    """Return a copy of *messages* with reasoning_content flipped:
    - Messages that HAD it → strip it
    - Messages that DIDN'T → leave alone (can't add what we don't have)
    """
    result: list[BaseMessage] = []
    for msg in messages:
        if isinstance(msg, AIMessage):
            ak = dict(msg.additional_kwargs) if msg.additional_kwargs else {}
            had_rc = "reasoning_content" in ak
            if had_rc:
                ak.pop("reasoning_content")
            result.append(
                AIMessage(
                    content=msg.content,
                    tool_calls=msg.tool_calls if msg.tool_calls else [],
                    additional_kwargs=ak,
                    response_metadata=msg.response_metadata or {},
                    id=msg.id,
                )
            )
        else:
            result.append(msg)
    return result


# ====================================================================
# Fallback tool-call parser for non-standard model outputs
# ====================================================================
# Some models emit tool calls inside the text content instead of the
# structured `tool_calls` field.  Known formats:
#   1) DeepSeek DSML: <｜tool▁calls▁begin｜>...<｜tool▁calls▁end｜> or
#                     <｜｜DSML｜｜tool_calls>...<invoke>...</invoke>...
#   2) XML-style:     <tool_call>{"name": ..., "arguments": ...}</tool_call>
#   3) Raw JSON:      {"name": "tool_name", "arguments": {...}}
# ====================================================================

# Match the entire DSML invoke block (from <invoke> to </invoke>).
# The ｜ is U+FF5C (full-width).
_DSML_FULL_INVOKE_RE = re.compile(
    r'<[｜\|]+DSML[｜\|]+invoke\s+name\s*=\s*"([^"]+)"[^>]*>'
    r'(.*?)'
    r'</[｜\|]+DSML[｜\|]+invoke[^>]*>',
    re.DOTALL,
)

# Match a single parameter tag within an invoke block.
_DSML_PARAM_RE = re.compile(
    r'<[｜\|]+DSML[｜\|]+parameter\s+name\s*=\s*"([^"]+)"[^>]*>'
    r'(.*?)'
    r'</[｜\|]+DSML[｜\|]+parameter[^>]*>',
    re.DOTALL,
)

# Kept for backward compat but no longer used in the main parser.
_DSML_INVOKE_RE = _DSML_FULL_INVOKE_RE

_DSML_BLOCK_RE = re.compile(
    r'<\|tool▁calls▁begin\|>(.*?)<\|tool▁calls▁end\|>',
    re.DOTALL,
)

_DSML_CALL_RE = re.compile(
    r'<\|tool▁call▁begin\|>\s*function\s*\n\s*(\w+)\s*\n'
    r'```json\s*\n(.*?)```\s*<\|tool▁sep\|>',
    re.DOTALL,
)

_XML_TOOL_CALL_RE = re.compile(
    r'<tool_call>\s*(\{.*?\})\s*</tool_call>',
    re.DOTALL,
)

_JSON_TOOL_CALL_RE = re.compile(
    r'\{\s*"name"\s*:\s*"(\w+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}',
    re.DOTALL,
)


def parse_tool_calls_from_content(
    content: str,
) -> list[dict[str, Any]]:
    """Try to extract tool calls from raw text content.

    This is the **fallback** path.  Ideally the model should use the
    structured ``tool_calls`` field (guaranteed when DeepSeek strict mode
    is active).  If the model emits tool calls as raw text, this function
    tries to recover them using the following strategies:

      1. DeepSeek DSML v2  (<｜tool▁calls▁begin｜> ... <｜tool▁calls▁end｜>)
      2. DeepSeek DSML v3  (<｜｜DSML｜｜invoke> ... </｜｜DSML｜｜invoke>)
      3. XML style          (<tool_call>{...}</tool_call>)
      4. Plain JSON         ({"name": "...", "arguments": {...}})

    Returns a list of dicts with keys: ``name``, ``args``, ``id``.
    Returns an empty list if no tool calls are found.

    A WARNING is logged whenever this fallback fires so the operator
    knows that strict tool calling is not working as expected.
    """
    if not content:
        return []

    calls: list[dict[str, Any]] = []

    # Strategy 1: DeepSeek DSML v2 (｜tool▁calls▁begin｜ ... ｜tool▁calls▁end｜)
    block_match = _DSML_BLOCK_RE.search(content)
    if block_match:
        for m in _DSML_CALL_RE.finditer(block_match.group(1)):
            fn_name = m.group(1)
            try:
                args = json.loads(m.group(2).strip())
            except json.JSONDecodeError:
                args = {"raw": m.group(2).strip()}
            calls.append({
                "name": fn_name,
                "args": args,
                "id": f"fallback_{uuid.uuid4().hex[:8]}",
            })
        if calls:
            log.warning(
                "[tool_fallback] DSML v2 format detected – model ignored strict "
                "tool_calls API. Recovered %d call(s): %s. "
                "Ensure base_url=https://api.deepseek.com/beta for strict mode.",
                len(calls), [c["name"] for c in calls],
            )
            return calls

    # Strategy 2: DeepSeek DSML v3 (｜｜DSML｜｜ invoke/parameter tags)
    # Each <invoke> block may contain multiple <parameter> tags; collect all
    # of them into a single args dict so the tool receives complete arguments.
    for m in _DSML_FULL_INVOKE_RE.finditer(content):
        fn_name = m.group(1)
        invoke_body = m.group(2)
        args: dict[str, Any] = {}
        for pm in _DSML_PARAM_RE.finditer(invoke_body):
            param_name = pm.group(1)
            param_value = pm.group(2).strip()
            try:
                parsed = json.loads(param_value)
                # If the single param is named "arguments" and is already a
                # dict, treat it as the entire args payload.
                if param_name == "arguments" and isinstance(parsed, dict):
                    args = parsed
                    break
                args[param_name] = parsed
            except json.JSONDecodeError:
                args[param_name] = param_value
        calls.append({
            "name": fn_name,
            "args": args,
            "id": f"fallback_{uuid.uuid4().hex[:8]}",
        })
    if calls:
        log.warning(
            "[tool_fallback] DSML v3 (｜｜DSML｜｜) format detected – model "
            "ignored strict tool_calls API. Recovered %d call(s): %s. "
            "Ensure base_url=https://api.deepseek.com/beta for strict mode.",
            len(calls), [c["name"] for c in calls],
        )
        return calls

    # Strategy 3: XML <tool_call>JSON</tool_call>
    for m in _XML_TOOL_CALL_RE.finditer(content):
        try:
            data = json.loads(m.group(1))
            name = data.get("name", "")
            args = data.get("arguments", data.get("parameters", {}))
            if isinstance(args, str):
                args = json.loads(args)
            if name:
                calls.append({
                    "name": name,
                    "args": args,
                    "id": f"fallback_{uuid.uuid4().hex[:8]}",
                })
        except json.JSONDecodeError:
            continue
    if calls:
        log.warning(
            "[tool_fallback] XML <tool_call> format detected. "
            "Recovered %d call(s): %s",
            len(calls), [c["name"] for c in calls],
        )
        return calls

    # Strategy 4: Plain JSON with "name" and "arguments"
    for m in _JSON_TOOL_CALL_RE.finditer(content):
        fn_name = m.group(1)
        try:
            args = json.loads(m.group(2))
        except json.JSONDecodeError:
            args = {"raw": m.group(2).strip()}
        calls.append({
            "name": fn_name,
            "args": args,
            "id": f"fallback_{uuid.uuid4().hex[:8]}",
        })

    if calls:
        log.warning(
            "[tool_fallback] Plain JSON tool call format detected. "
            "Recovered %d call(s): %s",
            len(calls), [c["name"] for c in calls],
        )
    return calls


def extract_text_without_tool_calls(content: str) -> str:
    """Remove tool call markup from content, returning only the natural
    language portion."""
    if not content:
        return ""
    text = content
    # Remove DSML v2 blocks (｜tool▁calls▁begin｜ ... ｜tool▁calls▁end｜)
    text = _DSML_BLOCK_RE.sub("", text)
    # Remove DSML v3 outer container (<｜｜DSML｜｜tool_calls>...</｜｜DSML｜｜tool_calls>)
    text = re.sub(
        r'<[｜\|]+DSML[｜\|]+tool_calls[^>]*>.*?</[｜\|]+DSML[｜\|]+tool_calls[^>]*>',
        "", text, flags=re.DOTALL
    )
    # Remove stray DSML v1 blocks (legacy pattern without explicit close tag)
    text = re.sub(
        r'<[｜\|]+(?:DSML|tool)[｜\|]+>?\s*tool_calls.*?</[｜\|]+(?:DSML|tool)[｜\|]+>?\s*tool_calls>?',
        "", text, flags=re.DOTALL
    )
    # Remove XML tool calls
    text = _XML_TOOL_CALL_RE.sub("", text)
    return text.strip()
