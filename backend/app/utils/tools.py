"""Tool schema utilities for LLM compatibility."""

from __future__ import annotations

from typing import Any


def _fix_schema_recursive(schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively fix any nested object schemas that have no properties.

    OpenAI (and compatible APIs) reject schemas where a nested object has
    ``additionalProperties: false`` but no ``properties`` key, or has
    ``properties: {}``.  This can happen when ``dict[str, Any]`` is used
    as a type annotation in strict mode.
    """
    if not isinstance(schema, dict):
        return schema

    schema_type = schema.get("type")

    if schema_type == "object":
        props = schema.get("properties", None)
        if props is not None and len(props) == 0:
            # Replace empty properties with a permissive catch-all
            schema = dict(schema)
            schema["properties"] = {
                "_data": {"type": "string", "description": "JSON encoded data"}
            }
            schema.pop("additionalProperties", None)
        elif props is None and schema.get("additionalProperties") is False:
            # No properties at all + additionalProperties=false → same fix
            schema = dict(schema)
            schema["properties"] = {
                "_data": {"type": "string", "description": "JSON encoded data"}
            }
            schema.pop("additionalProperties", None)
        else:
            # Recurse into existing properties
            if props:
                schema = dict(schema)
                schema["properties"] = {
                    k: _fix_schema_recursive(v) for k, v in props.items()
                }

    # Recurse into array items
    if "items" in schema:
        schema = dict(schema)
        schema["items"] = _fix_schema_recursive(schema["items"])

    # Recurse into anyOf / oneOf / allOf
    for key in ("anyOf", "oneOf", "allOf"):
        if key in schema:
            schema = dict(schema)
            schema[key] = [_fix_schema_recursive(s) for s in schema[key]]

    return schema


def fix_noarg_tools(tools: list[Any]) -> list[Any]:
    """Convert no-argument tools to OpenAI-compatible schema dicts, and fix
    nested object schemas that lack properties (e.g. from dict[str, Any]).

    OpenAI (and compatible APIs) reject:
    1. Tools whose top-level parameters schema has an empty ``properties`` object.
    2. Any nested object with ``additionalProperties: false`` but no ``properties``.

    Both cases are fixed here.  Original tool objects are kept for all tools
    that already pass validation so ``tool_map`` execution still works correctly.
    """
    from langchain_core.utils.function_calling import convert_to_openai_tool

    result: list[Any] = []
    for tool in tools:
        try:
            schema = tool.get_input_schema().model_json_schema()  # type: ignore[union-attr]
        except Exception:
            result.append(tool)
            continue

        props = schema.get("properties", None)
        top_empty = props is not None and len(props) == 0

        # Convert to OpenAI dict so we can inspect/patch the full nested schema
        oai = convert_to_openai_tool(tool)
        params = oai.get("function", {}).get("parameters", {})

        if top_empty:
            # No-arg tool: add a dummy optional property
            params["properties"] = {
                "_": {
                    "type": "string",
                    "description": "（此参数忽略，无需填写）",
                    "default": "",
                }
            }
            params["required"] = []
            result.append(oai)
        else:
            # Check for nested empty objects (e.g. dict[str, Any] in strict mode)
            fixed_params = _fix_schema_recursive(params)
            if fixed_params is not params:
                oai["function"]["parameters"] = fixed_params
                result.append(oai)
            else:
                # Schema is fine — keep the original BaseTool object
                result.append(tool)

    return result
