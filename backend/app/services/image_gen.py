"""Image generation service using the nano-banana API (grsaiapi.com)."""

from __future__ import annotations

import uuid
from pathlib import Path

import httpx

from app.config import settings


async def generate_image(
    prompt: str,
    *,
    api_key: str,
    session_id: str,
    style_prefix: str = "",
    model: str = "nano-banana-2",
    base_url: str = "https://grsaiapi.com",
    aspect_ratio: str = "16:9",
    image_size: str = "1K",
) -> str:
    """Call the nano-banana image generation API, download the result, return a local URL path.

    API docs: https://qmy27nhsd9.apifox.cn/452392911e0
    Endpoint: POST {base_url}/v1/api/generate

    Returns:
        A path like ``/api/static/images/<session_id>/<uuid>.webp`` served by FastAPI StaticFiles.
    """
    full_prompt = f"{style_prefix}, {prompt}".strip(", ") if style_prefix else prompt

    endpoint = base_url.rstrip("/")

    # --- Call image generation API ---
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "prompt": full_prompt,
                "aspectRatio": aspect_ratio,
                "imageSize": image_size,
                "replyType": "json",
            },
        )
        # Read and parse the response inside the context so content is buffered
        raw_bytes = resp.content
        try:
            data = resp.json()
        except Exception:
            data = {}

    # Handle HTTP-level errors
    if resp.status_code not in (200, 400):
        raise ValueError(
            f"nano-banana API returned HTTP {resp.status_code}: {raw_bytes[:500].decode('utf-8', errors='replace')}"
        )

    # Both 200 and 400 from nano-banana carry a JSON body with status/error fields
    status = data.get("status", "")
    error_msg = data.get("error", "")

    if status not in ("succeeded", "success", ""):
        if status in ("failed", "violation"):
            raise ValueError(f"nano-banana 生成失败 (status={status}): {error_msg or data}")
        # Unknown status — surface it
        if status and status != "running":
            raise ValueError(f"nano-banana 意外状态 status={status}: {data}")

    results = data.get("results", [])
    if not results:
        raise ValueError(f"nano-banana 返回空 results (status={status}): {data}")

    image_url: str = results[0].get("url", "")
    if not image_url:
        raise ValueError(f"nano-banana results 中无 url 字段: {results}")

    # --- Download and save locally to avoid CDN link expiry ---
    out_dir = Path(settings.images_dir) / session_id
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.webp"
    out_path = out_dir / filename

    async with httpx.AsyncClient(timeout=60) as client:
        img_resp = await client.get(image_url, follow_redirects=True)
        img_resp.raise_for_status()
        out_path.write_bytes(img_resp.content)

    return f"/api/static/images/{session_id}/{filename}"
