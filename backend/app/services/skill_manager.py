"""Skill management system.

Skills are Markdown files stored on disk that define reusable procedures,
templates, or knowledge for AI agents. Agents can create, read, list,
update and delete skills — similar to Cursor's SKILL.md files.

Each skill file has a standard structure:
  - Title (H1)
  - Description (what this skill does)
  - Instructions (step-by-step for the AI)
  - Optional examples
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings

SKILLS_BASE = Path(settings.data_dir) / "skills"


def _skills_dir(system_id: str | None = None) -> Path:
    if system_id:
        d = SKILLS_BASE / system_id
    else:
        d = SKILLS_BASE
    d.mkdir(parents=True, exist_ok=True)
    return d


def _skill_path(skill_id: str, system_id: str | None = None) -> Path:
    safe_id = re.sub(r"[^\w\-]", "_", skill_id)
    return _skills_dir(system_id) / f"{safe_id}.md"


def list_skills(system_id: str | None = None) -> list[dict[str, str]]:
    dirs_to_scan = [_skills_dir(system_id)] if system_id else [SKILLS_BASE]
    shared = SKILLS_BASE / "shared"
    if shared.exists() and shared not in dirs_to_scan:
        dirs_to_scan.append(shared)
    skills = []
    seen: set[str] = set()
    for base in dirs_to_scan:
        is_shared = base.name == "shared"
        for f in sorted(base.glob("*.md")):
            if f.stem in seen:
                continue
            seen.add(f.stem)
            content = f.read_text(encoding="utf-8")
            title_match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
            title = title_match.group(1) if title_match else f.stem
            desc_match = re.search(r"^>\s*(.+)", content, re.MULTILINE)
            description = desc_match.group(1) if desc_match else ""
            skills.append({
                "skill_id": f.stem,
                "title": title,
                "description": description,
                "filename": f.name,
                "shared": is_shared,
            })
    return skills


def get_skill(skill_id: str, system_id: str | None = None) -> dict[str, str] | None:
    path = _skill_path(skill_id, system_id)
    if not path.exists():
        shared_path = _skill_path(skill_id, "shared")
        if shared_path.exists():
            path = shared_path
        else:
            fallback = _skill_path(skill_id, None)
            if not fallback.exists():
                return None
            path = fallback
    content = path.read_text(encoding="utf-8")
    return {"skill_id": skill_id, "content": content, "filename": path.name}


def create_skill(skill_id: str, title: str, description: str, instructions: str, examples: str = "", system_id: str | None = None, shared: bool = False) -> dict[str, str]:
    effective_sid = "shared" if shared else system_id
    path = _skill_path(skill_id, effective_sid)

    content_parts = [
        f"# {title}",
        "",
        f"> {description}",
        "",
        f"*Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "## Instructions",
        "",
        instructions,
    ]

    if examples:
        content_parts.extend(["", "## Examples", "", examples])

    content = "\n".join(content_parts) + "\n"
    path.write_text(content, encoding="utf-8")
    return {"skill_id": skill_id, "filename": path.name, "title": title}


def update_skill(skill_id: str, content: str, system_id: str | None = None) -> bool:
    path = _skill_path(skill_id, system_id)
    if not path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def delete_skill(skill_id: str, system_id: str | None = None) -> bool:
    path = _skill_path(skill_id, system_id)
    if not path.exists():
        return False
    path.unlink()
    return True
