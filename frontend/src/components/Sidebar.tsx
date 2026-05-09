"use client";

import type { SessionState } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Swords,
  Compass,
  MessageCircle,
  Bed,
  Settings,
  Heart,
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

interface SidebarProps {
  session: SessionState | null;
  systemId?: string;
}

export default function Sidebar({ session, systemId = "pf2e" }: SidebarProps) {
  const meta = SYSTEM_META[systemId] ?? SYSTEM_META.pf2e;

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

      {/* Player */}
      {session?.player && (
        <div className="px-4 py-3 border-b border-border">
          <div className="text-xs text-muted-foreground mb-1">你的角色</div>
          <div className="text-sm font-semibold text-foreground">
            {session.player.name}
          </div>
          <div className="text-xs text-muted-foreground">
            {session.player.ancestry} {session.player.character_class} Lv.
            {session.player.level}
          </div>
          <div className="flex items-center gap-1 mt-1 text-xs">
            <Heart className="h-3 w-3 text-red-400" />
            <span className="text-red-400 font-mono">
              {session.player.hp}/{session.player.max_hp}
            </span>
          </div>
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
                <Heart className="h-3 w-3 text-red-400" />
                {t.hp}/{t.max_hp}
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
