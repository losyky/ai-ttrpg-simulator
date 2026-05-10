"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { SessionState } from "@/lib/types";
import { cn } from "@/lib/utils";
import { updateStoryPoints } from "@/lib/api";
import {
  Swords,
  Compass,
  MessageCircle,
  Bed,
  Settings,
  Heart,
  ChevronDown,
  Sparkles,
  Shield,
  Plus,
  Pen,
  Zap,
  Flame,
  Activity,
  ShieldHalf,
} from "lucide-react";
import Link from "next/link";

const PHASE_ICON: Record<string, React.ReactNode> = {
  exploration: <Compass className="h-4 w-4" />,
  combat: <Swords className="h-4 w-4" />,
  social: <MessageCircle className="h-4 w-4" />,
  downtime: <Bed className="h-4 w-4" />,
};

const PHASE_LABEL: Record<string, string> = {
  exploration: "探索",
  combat: "战斗",
  social: "社交",
  downtime: "休整",
};

const SYSTEM_META: Record<string, { icon: string; name: string; tagline: string; accentClass: string }> = {
  pf2e: {
    icon: "⚔️",
    name: "Pathfinder 2e",
    tagline: "探索、战斗、成长 — 规则严谨的史诗冒险",
    accentClass: "from-emerald-600/20 to-amber-500/10",
  },
  daggerheart: {
    icon: "🗡️",
    name: "Daggerheart",
    tagline: "希望与恐惧的二元 — 叙事驱动的英勇传说",
    accentClass: "from-violet-500/20 to-yellow-500/10",
  },
  swade: {
    icon: "🌊",
    name: "七物语",
    tagline: "双属性骰检 · 元素共鸣 — 狂野世界的东方物语",
    accentClass: "from-sky-500/20 to-teal-500/10",
  },
};

const POINT_NAME: Record<string, string> = {
  pf2e: "英雄点",
  swade: "物语点",
  daggerheart: "叙事点",
};

/* ── SWADE stat mini-panel ── */

const ATTR_LABELS: Record<string, string> = {
  dexterity: "灵巧", smarts: "聪慧", spirit: "心魂", strength: "力量", vigor: "活力",
};

function SWADEStats({ extras }: { extras: Record<string, unknown> }) {
  if (!extras) return null;
  const attrs = (extras.attributes ?? {}) as Record<string, string>;
  const toughness = (extras.toughness ?? 0) as number;
  const armor = (extras.toughness_armor ?? 0) as number;
  const parry = (extras.parry ?? 0) as number;
  const mp = (extras.mp ?? 0) as number;
  const mpMax = (extras.mp_max ?? 0) as number;
  const ip = (extras.ip ?? 0) as number;
  const ipMax = (extras.ip_max ?? 0) as number;
  const wounds = (extras.wounds ?? 0) as number;
  const fatigue = (extras.fatigue ?? 0) as number;

  return (
    <div className="space-y-1.5 mt-1">
      {/* Attributes */}
      <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-muted-foreground">
        {Object.entries(attrs).map(([k, v]) => (
          <span key={k}>{ATTR_LABELS[k] ?? k} <span className="text-foreground font-mono">{v}</span></span>
        ))}
      </div>
      {/* Core derived stats */}
      <div className="grid grid-cols-3 gap-1 text-xs">
        <div className="flex items-center gap-1">
          <Shield className="h-3 w-3 text-slate-400" />
          <span className="text-muted-foreground">坚韧</span>
          <span className="text-foreground font-mono ml-auto">
            {toughness}{armor > 0 && <span className="text-muted-foreground">({armor})</span>}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <ShieldHalf className="h-3 w-3 text-sky-400" />
          <span className="text-muted-foreground">格挡</span>
          <span className="text-foreground font-mono ml-auto">{parry}</span>
        </div>
        <div className="flex items-center gap-1">
          <Activity className="h-3 w-3 text-amber-400" />
          <span className="text-muted-foreground">移速</span>
          <span className="text-foreground font-mono ml-auto">{(extras.pace ?? 6) as number}</span>
        </div>
      </div>
      {/* Resources */}
      <div className="grid grid-cols-2 gap-1 text-xs">
        {mpMax > 0 && (
          <div className="flex items-center gap-1">
            <Zap className="h-3 w-3 text-blue-400" />
            <span className="text-muted-foreground">MP</span>
            <span className="text-blue-400 font-mono ml-auto">{mp}/{mpMax}</span>
          </div>
        )}
        {ipMax > 0 && (
          <div className="flex items-center gap-1">
            <Flame className="h-3 w-3 text-orange-400" />
            <span className="text-muted-foreground">IP</span>
            <span className="text-orange-400 font-mono ml-auto">{ip}/{ipMax}</span>
          </div>
        )}
      </div>
      {/* Wounds / Fatigue */}
      {(wounds > 0 || fatigue > 0) && (
        <div className="flex gap-3 text-xs">
          {wounds > 0 && (
            <span className="text-red-400">
              负伤 <span className="font-mono">{wounds}</span>
            </span>
          )}
          {fatigue > 0 && (
            <span className="text-yellow-400">
              疲劳 <span className="font-mono">{fatigue}</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Daggerheart stat mini-panel ── */

const DH_TRAIT_LABELS: Record<string, string> = {
  agility: "敏捷", strength: "力量", finesse: "灵巧",
  instinct: "本能", presence: "风度", knowledge: "学识",
};

function DHStats({ extras }: { extras: Record<string, unknown> }) {
  if (!extras) return null;
  const hp = (extras.hp ?? 0) as number;
  const maxHp = (extras.max_hp ?? 0) as number;
  const stress = (extras.stress ?? 0) as number;
  const stressMax = (extras.stress_max ?? 6) as number;
  const hope = (extras.hope ?? 0) as number;
  const hopeMax = (extras.hope_max ?? 6) as number;
  const evasion = (extras.evasion ?? 10) as number;
  const armorSlots = (extras.armor_slots ?? 0) as number;
  const armorMax = (extras.armor_max ?? 0) as number;
  const traits = (extras.traits ?? {}) as Record<string, number>;

  return (
    <div className="space-y-1.5 mt-1">
      {/* HP */}
      <div className="flex items-center gap-1 text-xs">
        <Heart className="h-3 w-3 text-red-400" />
        <span className="text-muted-foreground">HP</span>
        <span className="text-red-400 font-mono ml-auto">{hp}/{maxHp}</span>
      </div>
      {/* Stress bar */}
      <div className="flex items-center gap-1 text-xs">
        <Activity className="h-3 w-3 text-purple-400" />
        <span className="text-muted-foreground">压力</span>
        <div className="flex gap-0.5 ml-auto">
          {Array.from({ length: stressMax }).map((_, i) => (
            <span
              key={i}
              className={cn(
                "w-2.5 h-2.5 rounded-sm border",
                i < stress
                  ? "bg-purple-500 border-purple-600"
                  : "bg-secondary border-border",
              )}
            />
          ))}
        </div>
      </div>
      {/* Hope */}
      <div className="flex items-center gap-1 text-xs">
        <Sparkles className="h-3 w-3 text-yellow-400" />
        <span className="text-muted-foreground">希望</span>
        <div className="flex gap-0.5 ml-auto">
          {Array.from({ length: hopeMax }).map((_, i) => (
            <span
              key={i}
              className={cn(
                "w-2.5 h-2.5 rounded-full border",
                i < hope
                  ? "bg-yellow-400 border-yellow-500 shadow-[0_0_4px_rgba(250,204,21,0.4)]"
                  : "bg-secondary border-border",
              )}
            />
          ))}
        </div>
      </div>
      {/* Evasion / Armor */}
      <div className="grid grid-cols-2 gap-1 text-xs">
        <div className="flex items-center gap-1">
          <Shield className="h-3 w-3 text-slate-400" />
          <span className="text-muted-foreground">闪避</span>
          <span className="font-mono text-foreground ml-auto">{evasion}</span>
        </div>
        {armorMax > 0 && (
          <div className="flex items-center gap-1">
            <ShieldHalf className="h-3 w-3 text-sky-400" />
            <span className="text-muted-foreground">护甲</span>
            <span className="font-mono text-foreground ml-auto">{armorSlots}/{armorMax}</span>
          </div>
        )}
      </div>
      {/* Traits */}
      <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-muted-foreground">
        {Object.entries(traits).map(([k, v]) => (
          <span key={k}>
            {DH_TRAIT_LABELS[k] ?? k}{" "}
            <span className={cn("font-mono", v > 0 ? "text-emerald-400" : v < 0 ? "text-red-400" : "text-foreground")}>
              {v > 0 ? `+${v}` : v}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}

/* ── PF2e stat mini-panel ── */

function PF2eStats({ player }: { player: { hp: number; max_hp: number; extras: Record<string, unknown> } }) {
  const ac = (player.extras?.ac ?? 0) as number;
  const tempHp = (player.extras?.temp_hp ?? 0) as number;

  return (
    <div className="space-y-1 mt-1">
      <div className="flex items-center gap-3 text-xs">
        <div className="flex items-center gap-1">
          <Heart className="h-3 w-3 text-red-400" />
          <span className="text-red-400 font-mono">
            {player.hp}/{player.max_hp}
          </span>
          {tempHp > 0 && (
            <span className="text-cyan-400 font-mono text-[10px]">+{tempHp}</span>
          )}
        </div>
        {ac > 0 && (
          <div className="flex items-center gap-1">
            <Shield className="h-3 w-3 text-slate-400" />
            <span className="text-muted-foreground">AC</span>
            <span className="text-foreground font-mono">{ac}</span>
          </div>
        )}
      </div>
    </div>
  );
}

interface SidebarProps {
  session: SessionState | null;
  systemId?: string;
  onSendMessage?: (msg: string) => void;
  onStoryPointsChanged?: (points: number) => void;
}

export default function Sidebar({ session, systemId = "pf2e", onSendMessage, onStoryPointsChanged }: SidebarProps) {
  const meta = SYSTEM_META[systemId] ?? SYSTEM_META.pf2e;
  const pointName = POINT_NAME[systemId] ?? "叙事点";
  const [menuOpen, setMenuOpen] = useState(false);
  const [narrateOpen, setNarrateOpen] = useState(false);
  const [narrateText, setNarrateText] = useState("");
  const menuRef = useRef<HTMLDivElement>(null);

  const points = session?.story_points ?? 0;
  const maxPoints = session?.max_story_points ?? 3;
  const canSpend = points > 0 && !!session;

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    if (menuOpen) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  const spendPoint = useCallback(async (reason: string, chatMessage: string) => {
    if (!session || points < 1) return;
    try {
      const res = await updateStoryPoints(session.session_id, -1, reason);
      onStoryPointsChanged?.(res.story_points);
      onSendMessage?.(chatMessage);
    } catch { /* ignore */ }
    setMenuOpen(false);
  }, [session, points, onStoryPointsChanged, onSendMessage]);

  const handleNarrate = useCallback(() => {
    if (!narrateText.trim()) return;
    spendPoint("narrate", `[${pointName}·陈述] ${narrateText.trim()}`);
    setNarrateText("");
    setNarrateOpen(false);
  }, [narrateText, spendPoint, pointName]);

  const showPoints = systemId !== "daggerheart" && session;

  return (
    <aside className="w-64 shrink-0 border-r border-border bg-card flex flex-col">
      {/* Header */}
      <div className={cn("px-4 py-5 border-b border-border bg-gradient-to-br", meta.accentClass)}>
        <h1 className="text-lg font-bold tracking-tight text-foreground">
          {meta.icon} AI 跑团模拟器
        </h1>
        <p className="text-xs font-medium text-primary mt-1">{meta.name}</p>
        <p className="text-[10px] text-muted-foreground mt-0.5 leading-relaxed">{meta.tagline}</p>
      </div>

      {/* Current campaign */}
      {session && (
        <div className="px-4 py-3 border-b border-border">
          <div className="text-xs text-muted-foreground mb-1">当前团</div>
          <div className="text-sm font-semibold text-foreground truncate mb-1.5">
            {session.label || "未命名冒险"}
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {PHASE_ICON[session.phase]}
            {PHASE_LABEL[session.phase] ?? session.phase}
            {session.phase === "combat" && (
              <span className="ml-auto">
                第 {session.round_number} 轮
              </span>
            )}
          </div>
        </div>
      )}

      {/* Player — system-specific dashboard */}
      {session?.player && (
        <div className="px-4 py-3 border-b border-border space-y-1.5">
          <div className="text-xs text-muted-foreground">你的角色</div>
          <div className="text-sm font-semibold text-foreground">
            {session.player.name}
          </div>
          <div className="text-xs text-muted-foreground">
            {session.player.ancestry} {session.player.character_class}
            {session.player.level > 0 && ` Lv.${session.player.level}`}
          </div>

          {systemId === "swade" && <SWADEStats extras={session.player.extras} />}
          {systemId === "daggerheart" && <DHStats extras={session.player.extras} />}
          {systemId === "pf2e" && <PF2eStats player={session.player} />}
          {!["swade", "daggerheart", "pf2e"].includes(systemId) && session.player.max_hp > 0 && (
            <div className="flex items-center gap-1 text-xs">
              <Heart className="h-3 w-3 text-red-400" />
              <span className="text-red-400 font-mono">
                {session.player.hp}/{session.player.max_hp}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Story / Hero Points */}
      {showPoints && (
        <div className="px-4 py-3 border-b border-border" ref={menuRef}>
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-xs font-medium text-foreground">{pointName}</span>
            <div className="flex gap-1 ml-auto">
              {Array.from({ length: maxPoints }).map((_, i) => (
                <span
                  key={i}
                  className={cn(
                    "w-3 h-3 rounded-full border transition-colors",
                    i < points
                      ? "bg-amber-400 border-amber-500 shadow-[0_0_6px_rgba(251,191,36,0.4)]"
                      : "bg-secondary border-border",
                  )}
                />
              ))}
            </div>
          </div>

          <button
            onClick={() => setMenuOpen(!menuOpen)}
            disabled={!canSpend}
            className={cn(
              "w-full flex items-center justify-between gap-1 rounded-lg px-2.5 py-1.5 text-xs",
              "border border-border transition-colors",
              canSpend
                ? "hover:bg-secondary hover:text-foreground text-muted-foreground cursor-pointer"
                : "text-muted-foreground/40 cursor-not-allowed",
            )}
          >
            <span>使用{pointName}</span>
            <ChevronDown className={cn("h-3 w-3 transition-transform", menuOpen && "rotate-180")} />
          </button>

          {menuOpen && (
            <div className="mt-1.5 rounded-lg border border-border bg-popover shadow-md overflow-hidden">
              <button
                onClick={() => {
                  setNarrateOpen(true);
                  setMenuOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-secondary transition-colors text-left"
              >
                <Pen className="h-3 w-3 text-sky-400" />
                <span>陈述世界细节</span>
              </button>
              <button
                onClick={() => spendPoint("recover_shaken", `[${pointName}·恢复] 从动摇中立即恢复`)}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-secondary transition-colors text-left"
              >
                <Shield className="h-3 w-3 text-emerald-400" />
                <span>动摇恢复</span>
              </button>
              <button
                onClick={() => spendPoint("bonus", `[${pointName}·加值] 本轮检定 +1`)}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-secondary transition-colors text-left"
              >
                <Plus className="h-3 w-3 text-violet-400" />
                <span>+1 检定加值</span>
              </button>
            </div>
          )}

          {narrateOpen && (
            <div className="mt-1.5 rounded-lg border border-border bg-popover shadow-md p-2.5">
              <textarea
                autoFocus
                rows={2}
                placeholder="描述你想陈述的世界细节..."
                value={narrateText}
                onChange={(e) => setNarrateText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleNarrate();
                  }
                }}
                className="w-full rounded border border-border bg-background px-2 py-1.5 text-xs text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <div className="flex justify-end gap-1.5 mt-1.5">
                <button
                  onClick={() => { setNarrateOpen(false); setNarrateText(""); }}
                  className="px-2 py-1 rounded text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleNarrate}
                  disabled={!narrateText.trim()}
                  className="px-2.5 py-1 rounded bg-primary text-primary-foreground text-[10px] font-medium disabled:opacity-50"
                >
                  花费 1{pointName}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Teammates */}
      {session && session.teammates.length > 0 && (
        <div className="px-4 py-3 border-b border-border">
          <div className="text-xs text-muted-foreground mb-2">队友</div>
          {session.teammates.map((t) => (
            <div key={t.name} className="mb-2 last:mb-0">
              <div className="text-sm font-medium text-sky-400">{t.name}</div>
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                {t.max_hp > 0 && (
                  <>
                    <Heart className="h-3 w-3 text-red-400" />
                    <span className="text-red-400 font-mono">{t.hp}/{t.max_hp}</span>
                  </>
                )}
                {systemId === "swade" && t.extras?.toughness != null && (
                  <span className="ml-1">坚韧 <span className="font-mono text-foreground">{t.extras.toughness as number}</span></span>
                )}
                {systemId === "daggerheart" && t.extras?.evasion != null && (
                  <span className="ml-1">闪避 <span className="font-mono text-foreground">{t.extras.evasion as number}</span></span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="mt-auto flex flex-col gap-1 p-3">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-2 rounded-lg px-3 py-2 text-sm",
            "text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors",
          )}
        >
          <Settings className="h-4 w-4" /> 设置
        </Link>
      </div>
    </aside>
  );
}
