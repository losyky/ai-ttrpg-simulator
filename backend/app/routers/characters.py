"""Character management — import FVTT actors, CRUD, and session binding."""

from __future__ import annotations

import json
import traceback
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Body

from app.config import settings
from app.models.character import (
    CharacterSheet,
    parse_fvtt_actor,
    character_to_summary,
)
from app.models.schemas import CharacterSummary
from app.services.event_log import log_event

router = APIRouter(prefix="/api/characters", tags=["characters"])

# In-memory character store (keyed by character id)
_characters: dict[str, CharacterSheet] = {}
# Raw FVTT data preserved for export
_raw_data: dict[str, dict[str, Any]] = {}

_SUPPORTED_TYPES = {"character", "npc"}


def _detect_system_id(data: dict[str, Any], fallback: str = "pf2e") -> str:
    """Detect which game system a character belongs to."""
    flags = data.get("flags", {})
    if isinstance(flags, dict):
        gs = flags.get("gameSystem", "")
        if gs:
            return gs
    return fallback


def _char_dir(system_id: str) -> Path:
    """Get the on-disk directory for a specific system's characters."""
    d = Path(settings.data_dir) / "characters" / system_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_saved_characters() -> None:
    """Load all character/NPC JSON files from disk on startup."""
    base = Path(settings.data_dir) / "characters"
    if not base.exists():
        return

    # Load from system subdirectories: data/characters/{system_id}/*.json
    for sys_dir in base.iterdir():
        if sys_dir.is_dir():
            for fpath in sys_dir.glob("*.json"):
                _load_one(fpath)

    # Migrate legacy files sitting directly in data/characters/
    for fpath in base.glob("*.json"):
        _load_one(fpath, migrate=True)


def _load_one(fpath: Path, migrate: bool = False) -> None:
    try:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        if data.get("type") not in _SUPPORTED_TYPES:
            return
        sheet = parse_fvtt_actor(data)
        if not sheet.id:
            sheet.id = fpath.stem
        _characters[sheet.id] = sheet
        _raw_data[sheet.id] = data

        if migrate:
            sys_id = _detect_system_id(data)
            new_path = _char_dir(sys_id) / fpath.name
            if not new_path.exists():
                import shutil
                shutil.move(str(fpath), str(new_path))
    except Exception:
        pass


_load_saved_characters()


def _sheet_to_api(sheet: CharacterSheet) -> dict[str, Any]:
    """Convert a CharacterSheet to the API response format."""
    return {
        "id": sheet.id,
        "name": sheet.name,
        "level": sheet.level,
        "ancestry": sheet.ancestry,
        "heritage": sheet.heritage,
        "background": sheet.background,
        "character_class": sheet.character_class,
        "key_ability": sheet.key_ability,
        "hp": sheet.hp,
        "max_hp": sheet.max_hp,
        "temp_hp": sheet.temp_hp,
        "hero_points": sheet.hero_points,
        "abilities": sheet.abilities.model_dump(by_alias=True),
        "skills": [s.model_dump() for s in sheet.skills],
        "saves": [s.model_dump() for s in sheet.saves],
        "feats": [f.model_dump() for f in sheet.feats],
        "spells": [s.model_dump() for s in sheet.spells],
        "inventory": [i.model_dump() for i in sheet.inventory],
        "lore_skills": [s.model_dump() for s in sheet.lore_skills],
        "backstory": sheet.backstory,
        "gender": sheet.gender,
        "perception_rank": sheet.perception_rank,
        "summary": character_to_summary(sheet),
    }


@router.post("/import")
async def import_fvtt_character(file: UploadFile = File(...), system_id: str | None = None):
    """Import a character from a FVTT Actor JSON export file."""
    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(400, "无效的 JSON 文件")

    if data.get("type") not in _SUPPORTED_TYPES:
        raise HTTPException(400, f"不支持的 Actor 类型: {data.get('type')}。支持: {', '.join(_SUPPORTED_TYPES)}")

    # Tag with game system
    if system_id:
        data.setdefault("flags", {})["gameSystem"] = system_id

    sheet = parse_fvtt_actor(data)
    if not sheet.id:
        sheet.id = uuid.uuid4().hex[:12]

    _characters[sheet.id] = sheet
    _raw_data[sheet.id] = data

    sys_id = _detect_system_id(data)
    save_path = _char_dir(sys_id) / f"{sheet.id}.json"
    save_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    log_event("data", "character_imported", detail=f"{sheet.name} (Lv.{sheet.level} {sheet.character_class})", data={"id": sheet.id, "name": sheet.name, "system_id": sys_id})

    return _sheet_to_api(sheet)


@router.post("/create")
async def create_character(data: dict[str, Any] = Body(...)):
    """Create a character or NPC from inline FVTT-format JSON."""
    if "type" not in data:
        data["type"] = "character"
    if data.get("type") not in _SUPPORTED_TYPES:
        raise HTTPException(400, f"不支持的 Actor 类型: {data.get('type')}。支持: {', '.join(_SUPPORTED_TYPES)}")

    sheet = parse_fvtt_actor(data)
    if not sheet.id:
        sheet.id = uuid.uuid4().hex[:12]

    _characters[sheet.id] = sheet
    _raw_data[sheet.id] = data

    sys_id = _detect_system_id(data)
    save_path = _char_dir(sys_id) / f"{sheet.id}.json"
    save_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    log_event("data", "character_created", detail=f"{sheet.name} ({data['type']})", data={"id": sheet.id, "type": data["type"], "system_id": sys_id})
    return _sheet_to_api(sheet)


@router.get("")
async def list_characters(type: str | None = None, system_id: str | None = None):
    """List loaded characters. Optional ?type=character|npc and ?system_id=pf2e filter."""
    results = []
    for cid, sheet in _characters.items():
        raw = _raw_data.get(cid, {})
        actor_type = raw.get("type", "character")
        if type and actor_type != type:
            continue
        if system_id:
            char_sys = _detect_system_id(raw)
            if char_sys != system_id:
                continue
        results.append({
            "id": sheet.id, "name": sheet.name, "level": sheet.level,
            "type": actor_type,
            "system_id": _detect_system_id(raw),
            "ancestry": sheet.ancestry, "character_class": sheet.character_class,
            "hp": sheet.hp, "max_hp": sheet.max_hp,
        })
    return results


@router.get("/{char_id}")
async def get_character(char_id: str):
    """Get full character details."""
    sheet = _characters.get(char_id)
    if not sheet:
        raise HTTPException(404, "角色未找到")
    return _sheet_to_api(sheet)


@router.get("/{char_id}/summary")
async def get_character_summary(char_id: str):
    """Get a concise text summary of a character (for agent consumption)."""
    sheet = _characters.get(char_id)
    if not sheet:
        raise HTTPException(404, "角色未找到")
    return {"summary": character_to_summary(sheet)}


@router.get("/{char_id}/fvtt")
async def export_fvtt(char_id: str):
    """Export the character back as FVTT-compatible JSON."""
    raw = _raw_data.get(char_id)
    if not raw:
        raise HTTPException(404, "角色未找到")
    return raw


@router.patch("/{char_id}")
async def update_character(char_id: str, updates: dict[str, Any] = Body(...)):
    """Update character fields. Supports nested paths for abilities, skills, etc."""
    sheet = _characters.get(char_id)
    if not sheet:
        raise HTTPException(404, "角色未找到")

    SIMPLE_FIELDS = {
        "name", "level", "ancestry", "heritage", "background",
        "character_class", "key_ability", "deity",
        "hp", "max_hp", "temp_hp", "hero_points",
        "perception_rank", "backstory", "age", "gender",
    }

    for key, val in updates.items():
        if key in SIMPLE_FIELDS:
            setattr(sheet, key, val)
        elif key == "abilities" and isinstance(val, dict):
            for ab_key, ab_val in val.items():
                mapped = {"str": "str_", "int": "int_"}.get(ab_key, ab_key)
                if hasattr(sheet.abilities, mapped):
                    setattr(sheet.abilities, mapped, ab_val)
        elif key == "skills" and isinstance(val, list):
            from app.models.character import SkillEntry
            sheet.skills = [SkillEntry(**s) for s in val]
        elif key == "saves" and isinstance(val, list):
            from app.models.character import SaveEntry
            sheet.saves = [SaveEntry(**s) for s in val]
        elif key == "feats" and isinstance(val, list):
            from app.models.character import FeatEntry
            sheet.feats = [FeatEntry(**f) for f in val]
        elif key == "spells" and isinstance(val, list):
            from app.models.character import SpellEntry
            sheet.spells = [SpellEntry(**s) for s in val]
        elif key == "inventory" and isinstance(val, list):
            from app.models.character import ItemEntry
            sheet.inventory = [ItemEntry(**i) for i in val]
        elif key == "lore_skills" and isinstance(val, list):
            from app.models.character import SkillEntry
            sheet.lore_skills = [SkillEntry(**s) for s in val]

    _characters[char_id] = sheet

    # Persist to disk
    raw = _raw_data.get(char_id, {})
    _sync_sheet_to_raw(sheet, raw)
    sys_id = _detect_system_id(raw)
    save_path = _char_dir(sys_id) / f"{char_id}.json"
    save_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    log_event("data", "character_updated", detail=f"{sheet.name}", data={"id": char_id, "fields": list(updates.keys())})
    return _sheet_to_api(sheet)


def _ensure_dict(parent: dict, key: str) -> dict:
    """Like setdefault but replaces None/non-dict values with {}."""
    val = parent.get(key)
    if not isinstance(val, dict):
        parent[key] = {}
    return parent[key]


def _sync_sheet_to_raw(sheet: CharacterSheet, raw: dict[str, Any]) -> None:
    """Sync structured sheet changes back to the raw FVTT JSON."""
    raw["name"] = sheet.name
    system = _ensure_dict(raw, "system")
    details = _ensure_dict(system, "details")
    _ensure_dict(details, "level")["value"] = sheet.level
    attrs = _ensure_dict(system, "attributes")
    hp = _ensure_dict(attrs, "hp")
    hp["value"] = sheet.hp
    hp["max"] = sheet.max_hp
    hp["temp"] = sheet.temp_hp
    resources = _ensure_dict(system, "resources")
    _ensure_dict(resources, "heroPoints")["value"] = sheet.hero_points
    _ensure_dict(details, "keyability")["value"] = sheet.key_ability
    _ensure_dict(details, "deity")["value"] = sheet.deity
    bio = _ensure_dict(details, "biography")
    bio["backstory"] = sheet.backstory
    _ensure_dict(details, "age")["value"] = sheet.age
    _ensure_dict(details, "gender")["value"] = sheet.gender
    abilities = _ensure_dict(system, "abilities")
    _ensure_dict(abilities, "str")["mod"] = sheet.abilities.str_
    _ensure_dict(abilities, "dex")["mod"] = sheet.abilities.dex
    _ensure_dict(abilities, "con")["mod"] = sheet.abilities.con
    _ensure_dict(abilities, "int")["mod"] = sheet.abilities.int_
    _ensure_dict(abilities, "wis")["mod"] = sheet.abilities.wis
    _ensure_dict(abilities, "cha")["mod"] = sheet.abilities.cha


@router.patch("/{char_id}/hp")
async def update_hp(char_id: str, hp_change: int = Body(..., embed=True)):
    """Modify a character's HP."""
    sheet = _characters.get(char_id)
    if not sheet:
        raise HTTPException(404, "角色未找到")

    sheet.hp = max(0, min(sheet.max_hp, sheet.hp + hp_change))
    return {"hp": sheet.hp, "max_hp": sheet.max_hp}


@router.patch("/{char_id}/fvtt")
async def update_fvtt_raw(char_id: str, updates: dict[str, Any] = Body(...)):
    """Patch raw FVTT data fields.  Supports top-level keys that map into
    `system.*`, for example::

        {"wounds": {"value": 1}, "resources": {"mp": {"value": 20}}}

    Also supports ``"name"`` to rename.
    Persists changes to disk and reloads the in-memory CharacterSheet.
    """
    raw = _raw_data.get(char_id)
    if raw is None:
        raise HTTPException(404, "角色未找到")

    system = raw.setdefault("system", {})

    for key, val in updates.items():
        if key == "name":
            raw["name"] = val
        elif key in ("wounds", "fatigue", "bennies"):
            if isinstance(val, dict):
                existing = system.get(key, {})
                if isinstance(existing, dict):
                    existing.update(val)
                    system[key] = existing
                else:
                    system[key] = val
        elif key == "resources" and isinstance(val, dict):
            res = system.setdefault("resources", {})
            for rk, rv in val.items():
                if isinstance(rv, dict):
                    existing = res.get(rk, {})
                    if isinstance(existing, dict):
                        existing.update(rv)
                        res[rk] = existing
                    else:
                        res[rk] = rv
        elif key == "stats" and isinstance(val, dict):
            stats = system.setdefault("stats", {})
            for sk, sv in val.items():
                if isinstance(sv, dict):
                    existing = stats.get(sk, {})
                    if isinstance(existing, dict):
                        existing.update(sv)
                        stats[sk] = existing
                    else:
                        stats[sk] = sv
        elif key == "advances":
            if isinstance(val, dict):
                existing = system.get("advances", {})
                if isinstance(existing, dict):
                    existing.update(val)
                    system["advances"] = existing
                else:
                    system["advances"] = val
            else:
                system["advances"] = {"value": int(val)}
        elif key == "attributes" and isinstance(val, dict):
            attrs = system.setdefault("attributes", {})
            for ak, av in val.items():
                if isinstance(av, dict):
                    existing = attrs.get(ak, {})
                    if isinstance(existing, dict):
                        existing.update(av)
                        attrs[ak] = existing
                    else:
                        attrs[ak] = av
                else:
                    attrs[ak] = av
        elif key == "pending_levelup":
            system["pending_levelup"] = bool(val)
        elif key == "elementalResistances" and isinstance(val, dict):
            system["elementalResistances"] = val
        elif key == "details" and isinstance(val, dict):
            details = system.setdefault("details", {})
            details.update(val)
        elif key == "items" and isinstance(val, list):
            raw["items"] = val
        elif key == "bonds" and isinstance(val, list):
            system["bonds"] = val
        elif key == "traits" and isinstance(val, dict):
            # DH: merge each trait sub-dict
            tdict = system.setdefault("traits", {})
            for tk, tv in val.items():
                if isinstance(tv, dict):
                    existing = tdict.get(tk, {})
                    if isinstance(existing, dict):
                        existing.update(tv)
                        tdict[tk] = existing
                    else:
                        tdict[tk] = tv
                else:
                    tdict[tk] = tv
        elif key == "experiences" and isinstance(val, list):
            system["experiences"] = val
        elif key == "biography" and isinstance(val, dict):
            bio = system.setdefault("biography", {})
            bio.update(val)
        elif key == "heritage" and isinstance(val, dict):
            h = system.setdefault("heritage", {})
            h.update(val)
        elif key not in ("system",) and isinstance(val, (str, int, float, bool)):
            # Generic scalar passthrough for system-level fields (class, subclass, level, evasion, etc.)
            system[key] = val

    _raw_data[char_id] = raw

    sheet = parse_fvtt_actor(raw)
    sheet.id = char_id
    _characters[char_id] = sheet

    sys_id = _detect_system_id(raw)
    save_path = _char_dir(sys_id) / f"{char_id}.json"
    save_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    log_event("data", "character_fvtt_updated", detail=f"{raw.get('name', '?')}",
              data={"id": char_id, "fields": list(updates.keys())})
    return raw


@router.post("/{char_id}/award_advance")
async def award_advance(char_id: str):
    """Grant the character 1 advance (SWADE level-up) and mark pending_levelup=true.

    The narrator will see the [⬆ 可升级] flag and remind the player at the next
    appropriate narrative moment to visit the character page to spend the advance.
    """
    raw = _raw_data.get(char_id)
    if raw is None:
        raise HTTPException(404, "角色未找到")

    system = raw.setdefault("system", {})
    advances_data = system.get("advances", {})
    if isinstance(advances_data, dict):
        current = advances_data.get("value", 0) or 0
        advances_data["value"] = current + 1
        system["advances"] = advances_data
    else:
        current = int(advances_data or 0)
        system["advances"] = {"value": current + 1}

    system["pending_levelup"] = True
    _raw_data[char_id] = raw

    sheet = parse_fvtt_actor(raw)
    sheet.id = char_id
    _characters[char_id] = sheet

    sys_id = _detect_system_id(raw)
    save_path = _char_dir(sys_id) / f"{char_id}.json"
    save_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    new_value = (system["advances"] if isinstance(system["advances"], int)
                 else system["advances"].get("value", 1))
    log_event("data", "character_advance_awarded", detail=f"{raw.get('name', '?')} → advance {new_value}",
              data={"id": char_id, "advances": new_value})
    return {"name": raw.get("name", "?"), "advances": new_value, "pending_levelup": True}


@router.delete("/{char_id}")
async def delete_character(char_id: str):
    """Remove a character."""
    if char_id not in _characters:
        raise HTTPException(404, "角色未找到")
    name = _characters[char_id].name
    raw = _raw_data.get(char_id, {})
    sys_id = _detect_system_id(raw)
    _characters.pop(char_id)
    _raw_data.pop(char_id, None)

    # Delete from system subdirectory
    (_char_dir(sys_id) / f"{char_id}.json").unlink(missing_ok=True)

    # Also delete from legacy flat location and old backend/data/ copy
    (Path(settings.data_dir) / "characters" / f"{char_id}.json").unlink(missing_ok=True)
    old_path = Path(__file__).resolve().parent.parent / "data" / "characters" / f"{char_id}.json"
    old_path.unlink(missing_ok=True)

    log_event("data", "character_deleted", detail=f"{name}", data={"id": char_id})
    return {"deleted": True}


@router.get("/{char_id}/as_session_character")
async def as_session_character(char_id: str) -> CharacterSummary:
    """Convert a full character sheet into a lightweight CharacterSummary for session binding."""
    sheet = _characters.get(char_id)
    if not sheet:
        raise HTTPException(404, "角色未找到")

    from app.agents.graph import _build_character_extras
    raw = _raw_data.get(char_id, {})
    sys_id = _detect_system_id(raw)
    extras = _build_character_extras(sheet, sys_id)
    raw_sys = raw.get("system", {})

    if sys_id == "daggerheart":
        res = raw_sys.get("resources", {})
        hp_val = res.get("hitPoints", {}).get("value", sheet.hp)
        hp_max = res.get("hitPoints", {}).get("max", sheet.max_hp)
        heritage = raw_sys.get("heritage", {})
        ancestry_name = heritage.get("ancestry", sheet.ancestry) if isinstance(heritage, dict) else sheet.ancestry
        return CharacterSummary(
            name=sheet.name,
            ancestry=ancestry_name,
            character_class=raw_sys.get("class", sheet.character_class),
            level=raw_sys.get("level", sheet.level) or sheet.level,
            hp=hp_val,
            max_hp=hp_max,
            extras=extras,
        )
    elif sys_id == "swade":
        return CharacterSummary(
            name=sheet.name,
            ancestry=raw_sys.get("details", {}).get("species", sheet.ancestry),
            character_class="冒险者",
            level=raw_sys.get("advances", {}).get("value", 0),
            hp=0,
            max_hp=0,
            extras=extras,
        )
    else:
        return CharacterSummary(
            name=sheet.name,
            ancestry=sheet.ancestry,
            character_class=sheet.character_class,
            level=sheet.level,
            hp=sheet.hp,
            max_hp=sheet.max_hp,
            conditions=[],
            extras=extras,
        )


@router.post("/{char_id}/portrait")
async def generate_portrait(char_id: str, body: dict):
    """Generate a portrait for a character and store the URL in raw data.

    Body: { api_key, model, base_url, style_prefix, description }
    Returns: { portrait_url }
    """
    raw = _raw_data.get(char_id)
    if raw is None:
        raise HTTPException(404, "角色未找到")

    char_name = raw.get("name", "角色")
    description = body.get("description", "")
    style_prefix = body.get("style_prefix", "")
    api_key = body.get("api_key", "")
    model = body.get("model", "dall-e-3")
    base_url = body.get("base_url", "https://api.grsaiapi.com/v1")

    if not api_key:
        raise HTTPException(400, "缺少 api_key")

    prompt = f"{char_name} portrait{', ' + description if description else ''}"

    from app.services.image_gen import generate_image
    try:
        portrait_url = await generate_image(
            prompt,
            api_key=api_key,
            session_id="portraits",
            style_prefix=style_prefix,
            model=model,
            base_url=base_url,
        )
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(500, str(exc))

    raw["img"] = portrait_url
    _raw_data[char_id] = raw

    # Persist to disk
    sys_id = _detect_system_id(raw)
    char_file = _char_dir(sys_id) / f"{char_id}.json"
    char_file.write_text(
        __import__("json").dumps(raw, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log_event("data", "portrait_generated", detail=char_name, data={"id": char_id, "url": portrait_url})
    return {"portrait_url": portrait_url}


def get_loaded_character(char_id: str) -> CharacterSheet | None:
    """Internal API for agents to access character data."""
    return _characters.get(char_id)
