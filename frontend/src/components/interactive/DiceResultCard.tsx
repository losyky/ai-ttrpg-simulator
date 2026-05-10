"use client";

import { useEffect, useState } from "react";
import type { DiceResult } from "@/lib/types";
import { cn } from "@/lib/utils";

const SUCCESS_CONFIG = {
  critical_success: {
    label: "大成功",
    labelEn: "CRITICAL SUCCESS",
    color: "text-yellow-300",
    bg: "bg-yellow-500/10",
    border: "border-yellow-500/50",
    glow: "shadow-[0_0_30px_rgba(234,179,8,0.3)]",
    icon: "✦",
  },
  success: {
    label: "成功",
    labelEn: "SUCCESS",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/40",
    glow: "shadow-[0_0_20px_rgba(16,185,129,0.2)]",
    icon: "✓",
  },
  failure: {
    label: "失败",
    labelEn: "FAILURE",
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/40",
    glow: "shadow-[0_0_20px_rgba(239,68,68,0.2)]",
    icon: "✗",
  },
  critical_failure: {
    label: "大失败",
    labelEn: "CRITICAL FAILURE",
    color: "text-red-600",
    bg: "bg-red-900/20",
    border: "border-red-700/50",
    glow: "shadow-[0_0_30px_rgba(185,28,28,0.3)]",
    icon: "☠",
  },
} as const;

export default function DiceResultCard({ dice }: { dice: DiceResult }) {
  const [phase, setPhase] = useState<"rolling" | "landing" | "result">("rolling");
  const [displayValue, setDisplayValue] = useState(0);

  const config = dice.success_level
    ? SUCCESS_CONFIG[dice.success_level as keyof typeof SUCCESS_CONFIG]
    : null;

  const natural20 = dice.rolls.includes(20);
  const natural1 = dice.rolls.length === 1 && dice.rolls[0] === 1;
  const isDualAttribute = dice.system_info?.dual_attribute === true;
  const usedIdx = isDualAttribute
    ? (dice.system_info?.used === "secondary" ? 1 : 0)
    : -1;
  const acedFlags = isDualAttribute
    ? [dice.system_info?.primary_aced === true, dice.system_info?.secondary_aced === true]
    : [];

  useEffect(() => {
    // Tumbling phase: show random numbers
    let frame = 0;
    const interval = setInterval(() => {
      setDisplayValue(Math.floor(Math.random() * 20) + 1);
      frame++;
      if (frame >= 12) {
        clearInterval(interval);
        setPhase("landing");
        setTimeout(() => {
          setDisplayValue(dice.rolls[0] ?? dice.total);
          setPhase("result");
        }, 300);
      }
    }, 80);

    return () => clearInterval(interval);
  }, [dice]);

  return (
    <div
      className={cn(
        "rounded-2xl border-2 px-5 py-4 my-3 transition-all duration-500",
        config ? config.bg : "bg-secondary/50",
        config ? config.border : "border-border",
        phase === "result" && config ? config.glow : "",
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-muted-foreground font-mono uppercase tracking-wider">
          {dice.label || "🎲 骰子检定"}
        </span>
        {(dice.dc ?? 0) > 0 && (
          <span className="text-xs text-muted-foreground ml-auto">
            DC {dice.dc}
          </span>
        )}
      </div>

      {/* Dice display */}
      <div className="flex items-center gap-4">
        <div className="flex gap-2">
          {dice.rolls.map((r, i) => {
            const isUsed = usedIdx === i;
            const isDiscarded = isDualAttribute && usedIdx >= 0 && !isUsed;
            const dieLabel = isDualAttribute
              ? (i === 0 ? `d${dice.system_info?.primary_sides ?? "?"}` : `d${dice.system_info?.secondary_sides ?? "?"}`)
              : null;
            return (
              <div key={i} className="flex flex-col items-center gap-1">
                <div
                  className={cn(
                    "relative w-14 h-14 rounded-xl flex items-center justify-center text-xl font-bold",
                    "transition-all duration-500",
                    phase === "rolling" && "animate-dice-tumble",
                    phase === "landing" && "animate-dice-land",
                    natural20 && phase === "result"
                      ? "bg-gradient-to-br from-yellow-400 to-amber-600 text-black shadow-[0_0_20px_rgba(234,179,8,0.5)]"
                      : natural1 && phase === "result"
                        ? "bg-gradient-to-br from-red-600 to-red-900 text-white shadow-[0_0_20px_rgba(185,28,28,0.5)]"
                        : isUsed && phase === "result"
                          ? "bg-primary/20 text-primary border-2 border-primary/60 ring-2 ring-primary/30"
                          : isDiscarded && phase === "result"
                            ? "bg-secondary/50 text-muted-foreground border border-border/50 opacity-50"
                            : "bg-secondary text-foreground border border-border",
                  )}
                >
                  {phase === "rolling" ? displayValue : r}
                </div>
                {dieLabel && phase === "result" && (
                  <span className={cn(
                    "text-[10px] font-mono",
                    isUsed ? "text-primary" : "text-muted-foreground/60",
                  )}>
                    {dieLabel}{acedFlags[i] ? " 💥" : ""}{isUsed ? " ✓" : ""}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Total */}
        <div className="flex flex-col items-center">
          <span className="text-xs text-muted-foreground">总计</span>
          <span
            className={cn(
              "text-3xl font-black transition-all duration-300",
              phase === "result" && config ? config.color : "text-foreground",
              phase !== "result" && "opacity-50",
            )}
          >
            {phase === "result" ? dice.total : "?"}
          </span>
        </div>

        {/* Success badge */}
        {config && phase === "result" && (
          <div
            className={cn(
              "ml-auto flex flex-col items-center animate-result-appear",
            )}
          >
            <span className={cn("text-3xl mb-1", config.color)}>
              {config.icon}
            </span>
            <span className={cn("text-sm font-bold", config.color)}>
              {config.label}
            </span>
            <span className="text-[10px] text-muted-foreground tracking-widest">
              {config.labelEn}
            </span>
          </div>
        )}
      </div>

      {/* SWADE raises indicator */}
      {(dice.raises ?? 0) > 0 && phase === "result" && (
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs text-amber-400 font-bold">
            优良 ×{dice.raises}
          </span>
          <span className="text-[10px] text-muted-foreground tracking-wider">
            RAISE{(dice.raises ?? 0) > 1 ? "S" : ""}
          </span>
        </div>
      )}

      {/* Detail line */}
      <div className="mt-3 text-xs text-muted-foreground font-mono">
        {dice.expression} → {dice.detail}
        {(dice.dc ?? 0) > 0 && ` (DC ${dice.dc})`}
      </div>
    </div>
  );
}
