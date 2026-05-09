"""FastAPI application entry-point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import sessions, chat, documents, rules, characters, skills, tools, prep_chat, creator_chat, dice_roll, debug, saves, memories, backup, workspace, compendium, data_updater

# Register game system modules
from app.systems.registry import register, get_default_system, list_systems, iter_systems, _init_default
from app.systems.pf2e.system import PF2eSystem
from app.systems.daggerheart.system import DaggerheartSystem
from app.systems.swade.system import SWADESystem
register(PF2eSystem())
register(DaggerheartSystem())
register(SWADESystem())
_init_default()

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(prep_chat.router)
app.include_router(creator_chat.router)
app.include_router(documents.router)
app.include_router(rules.router)
app.include_router(characters.router)
app.include_router(skills.router)
app.include_router(tools.router)
app.include_router(dice_roll.router)
app.include_router(debug.router)
app.include_router(saves.router)
app.include_router(memories.router)
app.include_router(backup.router)
app.include_router(workspace.router)
app.include_router(compendium.router)
app.include_router(data_updater.router)

# Mount game-system-specific routers for ALL registered systems
for _sys in iter_systems():
    _rules_router = _sys.get_rules_router()
    if _rules_router:
        app.include_router(_rules_router)
    _cb_router = _sys.get_charbuilder_router()
    if _cb_router:
        app.include_router(_cb_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/systems")
async def get_game_systems():
    """List all registered game systems."""
    return {"systems": list_systems()}


# ── Game system selection ──

@app.get("/api/settings/system")
async def get_system_setting():
    """Get the current default game system."""
    return {"system_id": get_default_system().system_id}


@app.put("/api/settings/system")
async def set_system_setting(body: dict):
    """Set the default game system."""
    from app.systems.registry import set_default_system
    system_id = body.get("system_id", "pf2e")
    try:
        set_default_system(system_id)
    except KeyError as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))
    return {"system_id": system_id}


# ── Reasoning content strategy ──

@app.get("/api/settings/reasoning-strategy")
async def get_reasoning_strategy():
    from app.agents.compat import get_reasoning_strategy as _get
    return {"strategy": _get()}


@app.put("/api/settings/reasoning-strategy")
async def set_reasoning_strategy(body: dict):
    from app.agents.compat import set_reasoning_strategy as _set
    strategy = body.get("strategy", "auto")
    if strategy not in ("auto", "keep", "strip"):
        from fastapi import HTTPException
        raise HTTPException(400, "strategy must be 'auto', 'keep', or 'strip'")
    _set(strategy)
    return {"strategy": strategy}
