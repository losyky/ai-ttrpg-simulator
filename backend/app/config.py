from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings

# Project root: 跑团系统/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "AI TTRPG Simulator"
    debug: bool = True

    # All data lives under <project_root>/data/
    data_dir: str = str(_PROJECT_ROOT / "data")
    upload_dir: str = str(_PROJECT_ROOT / "data" / "uploads")
    db_path: str = str(_PROJECT_ROOT / "data" / "game.db")
    chroma_dir: str = str(_PROJECT_ROOT / "data" / "chroma")

    # AI workspace — prep agent has full file access here
    workspace_dir: str = str(_PROJECT_ROOT / "data" / "workspace")

    # Generated images (portraits, scenes)
    images_dir: str = str(_PROJECT_ROOT / "data" / "images")

    # Default game system
    default_system_id: str = "pf2e"

    # Populated at runtime from the frontend per-session
    default_api_key: str = ""
    default_model: str = "gpt-4o"
    default_base_url: str = "https://api.openai.com/v1"

    cors_origins: list[str] = [
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:8001", "http://127.0.0.1:8001",
    ]

    model_config = {"env_prefix": "TTRPG_", "env_file": ".env", "extra": "ignore"}


settings = Settings()

# Ensure all directories exist at startup
_SYSTEMS = ["pf2e", "daggerheart", "swade"]
for _d in [
    settings.data_dir,
    settings.upload_dir,
    settings.chroma_dir,
    settings.workspace_dir,
    str(Path(settings.data_dir) / "characters"),
    str(Path(settings.data_dir) / "skills"),
    str(Path(settings.data_dir) / "custom_tools"),
    str(Path(settings.data_dir) / "saves"),
    str(Path(settings.data_dir) / "checkpoints"),
    str(Path(settings.data_dir) / "images"),
] + [
    str(Path(settings.data_dir) / sub / sid)
    for sub in ("characters", "skills", "custom_tools")
    for sid in _SYSTEMS + ["shared"]
] + [
    str(Path(settings.workspace_dir) / sid)
    for sid in _SYSTEMS
]:
    os.makedirs(_d, exist_ok=True)

# One-time migration from old backend/data/ to project-level data/
_OLD_DATA = Path(__file__).resolve().parent.parent / "data"
_NEW_DATA = Path(settings.data_dir)
_MIGRATION_MARKER = _NEW_DATA / ".migrated_from_backend"
if (
    _OLD_DATA.exists()
    and _OLD_DATA.resolve() != _NEW_DATA.resolve()
    and not _MIGRATION_MARKER.exists()
):
    import shutil
    for item in _OLD_DATA.iterdir():
        dest = _NEW_DATA / item.name
        if item.is_dir():
            shutil.copytree(str(item), str(dest), dirs_exist_ok=True)
        elif not dest.exists():
            shutil.copy2(str(item), str(dest))
    _MIGRATION_MARKER.write_text("migrated", encoding="utf-8")
