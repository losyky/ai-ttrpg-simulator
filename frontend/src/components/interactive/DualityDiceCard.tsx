"use client";

import { useEffect, useState } from "react";
import type { DiceResult } from "@/lib/types";
import { cn } from "@/lib/utils";

const DUALITY_CONFIG = {
  with_hope: {
    label: "以希望成功",
    labelEn: "WITH HOPE",
    color: "text-sky-300",
    bg: "bg-sky-500/10",
    border: "border-sky-500/40",
    glow: "shadow-[0_0_25px_rgba(56,189,248,0.25)]",
    icon: "✦",
    hopeColor: "from-sky-400 to-blue-500",
    fearColor: "from-slate-500 to-slate-700",
  },
  with_fear: {
    label: "以恐惧成功",
    labelEn: "WITH FEAR",
    color: "text-rose-400",
    bg: "bg-rose-500/10",
    border: "border-rose-500/40",
    glow: "shadow-[0_0_25px_rgba(244,63,94,0.25)]",
    icon: "⚡",
    hopeColor: "from-slate-500 to-slate-700",
    fearColor: "from-rose-500 to-red-600",
  },
  critical_success: {
    label: "大成功",
    labelEn: "CRITICAL SUCCESS",
    color: "text-amber-300",
    bg: "bg-amber-500/10",
    border: "border-amber-500/50",
    glow: "shadow-[0_0_35px_rgba(245,158,11,0.35)]",
    icon: "★",
    hopeColor: "from-amber-400 to-yellow-500",
    fearColor: "from-amber-400 to-yellow-500",
  },
} as const;

export default function DualityDiceCard({ dice }: { dice: DiceResult }) {
  const [phase, setPhase] = useState<"rolling" | "landing" | "result">("rolling");
  const [hopeDisplay, setHopeDisplay] = useState(0);
  const [fearDisplay, setFearDisplay] = useState(0);

  const outcome = (dice.duality_outcome || "with_hope") as keyof typeof DUALITY_CONFIG;
  const config = DUALITY_CONFIG[outcome] ?? DUALITY_CONFIG.with_hope;
  const hopeDie = dice.hope_die || dice.rolls[0] || 0;
  const fearDie = dice.fear_die || dice.rolls[1] || 0;
  const description = (dice.system_info?.description as string) || "";

  useEffect(() => {
    let frame = 0;
    const interval = setInterval(() => {
      setHopeDisplay(Math.floor(Math.random() * 12) + 1);
      setFearDisplay(Math.floor(Math.random() * 12) + 1);
      frame++;
      if (frame >= 14) {
        clearInterval(interval);
        setPhase("landing");
        setTimeout(() => {
          setHopeDisplay(hopeDie);
          setFearDisplay(fearDie);
          setPhase("result");
        }, 350);
      }
    }, 75);
    return () => clearInterval(interval);
  }, [dice, hopeDie, fearDie]);

  return (
    <div
      className={cn(
        "rounded-2xl border-2 px-5 py-4 my-3 transition-all duration-500",
        config.bg,
        config.border,
        phase === "result" && config.glow,
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-muted-foreground font-mono uppercase tracking-wider">
          {dice.label || "⚔ 二元骰检定"}
        </span>
        {(dice.dc ?? 0) > 0 && (
          <span className="text-xs text-muted-foreground ml-auto">DC {dice.dc}</span>
        )}
      </div>

      {/* Dual dice display */}
      <div className="flex items-center gap-5">
        <div className="flex gap-3">
          {/* Hope Die */}
          <div className="flex flex-col items-center gap-1">
            <span className="text-[10px] font-bold text-sky-400 uppercase tracking-widest">Hope</span>
            <div
              className={cn(
                "relative w-16 h-16 rounded-xl flex items-center justify-center text-2xl font-black transition-all duration-500",
                phase === "rolling" && "animate-dice-tumble",
                phase === "landing" && "animate-dice-land",
                phase === "result"
                  ? `bg-gradient-to-br ${config.hopeColor} text-white shadow-lg`
                  : "bg-secondary text-foreground border border-border",
              )}
            >
              {phase === "rolling" ? hopeDisplay : hopeDie}
            </div>
          </div>

          <div className="flex items-center text-muted-foreground text-xl font-light self-end mb-3">
            vs
          </div>

          {/* Fear Die */}
          <div className="flex flex-col items-center gap-1">
            <span className="text-[10px] font-bold text-rose-400 uppercase tracking-widest">Fear</span>
            <div
              className={cn(
                "relative w-16 h-16 rounded-xl flex items-center justify-center text-2xl font-black transition-all duration-500",
                phase === "rolling" && "animate-dice-tumble",
                phase === "landing" && "animate-dice-land",
                phase === "result"
                  ? `bg-gradient-to-br ${config.fearColor} text-white shadow-lg`
                  : "bg-secondary text-foreground border border-border",
              )}
            >
              {phase === "rolling" ? fearDisplay : fearDie}
            </div>
          </div>
        </div>

        {/* Total */}
        <div className="flex flex-col items-center">
          <span className="text-xs text-muted-foreground">总计</span>
          <span
            className={cn(
              "text-3xl font-black transition-all duration-300",
              phase === "result" ? config.color : "text-foreground opacity-50",
            )}
          >
            {phase === "result" ? dice.total : "?"}
          </span>
        </div>

        {/* Outcome badge */}
        {phase === "result" && (
          <div className="ml-auto flex flex-col items-center animate-result-appear">
            <span className={cn("text-3xl mb-1", config.color)}>{config.icon}</span>
            <span className={cn("text-sm font-bold", config.color)}>{config.label}</span>
            <span className="text-[10px] text-muted-foreground tracking-widest">{config.labelEn}</span>
          </div>
        )}
      </div>

      {/* Description */}
      {description && phase === "result" && (
        <p className="mt-3 text-sm text-muted-foreground italic">{description}</p>
      )}

      {/* Detail line */}
      <div className="mt-2 text-xs text-muted-foreground font-mono">
        {dice.expression} → Hope: {hopeDie}, Fear: {fearDie}
        {(dice.dc ?? 0) > 0 && ` (DC ${dice.dc})`}
      </div>
    </div>
  );
}
