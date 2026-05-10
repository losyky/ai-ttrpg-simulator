"use client";

import { useCallback, useState } from "react";
import type { InteractiveElement, DiceResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import DiceResultCard from "./DiceResultCard";
import { rollDice, rerollDice } from "@/lib/api";

interface DiceRollButtonProps {
  element: InteractiveElement;
  sessionId: string;
  onResult: (result: DiceResult) => void;
  disabled?: boolean;
  storyPoints?: number;
  pointName?: string;
  onStoryPointsChanged?: (pts: number) => void;
}

export default function DiceRollButton({
  element,
  sessionId,
  onResult,
  disabled,
  storyPoints = 0,
  pointName = "叙事点",
  onStoryPointsChanged,
}: DiceRollButtonProps) {
  const [rolling, setRolling] = useState(false);
  const [rerolling, setRerolling] = useState(false);
  const [result, setResult] = useState<DiceResult | null>(element.resolved_dice ?? null);

  const handleRoll = useCallback(async () => {
    if (rolling || result || disabled) return;
    setRolling(true);

    try {
      const res = await rollDice({
        session_id: sessionId,
        expression: element.expression || "1d20",
        dc: element.dc,
        label: element.skill_name || "",
        modifier: element.modifier,
      });
      setTimeout(() => {
        setResult(res);
        setRolling(false);
        onResult(res);
      }, 600);
    } catch {
      setRolling(false);
    }
  }, [rolling, result, disabled, sessionId, element, onResult]);

  const handleReroll = useCallback(async () => {
    if (!result || rerolling || result.is_reroll) return;
    setRerolling(true);
    try {
      const res = await rerollDice({
        session_id: sessionId,
        expression: element.expression || "1d20",
        dc: element.dc,
        label: element.skill_name || "",
        modifier: element.modifier,
        original_total: result.total,
      });
      setResult(res);
      onStoryPointsChanged?.((storyPoints ?? 1) - 1);
      onResult(res);
    } catch { /* point insufficient or network error */ }
    setRerolling(false);
  }, [result, rerolling, sessionId, element, storyPoints, onResult, onStoryPointsChanged]);

  const canReroll = result && !result.is_reroll && storyPoints > 0 && !rerolling;

  if (result) {
    return (
      <div>
        <DiceResultCard dice={result} />
        {canReroll && (
          <button
            onClick={handleReroll}
            disabled={rerolling}
            className={cn(
              "mt-1 flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium",
              "border border-amber-500/40 bg-amber-500/5 text-amber-300",
              "hover:bg-amber-500/10 hover:border-amber-500/60 transition-all",
              rerolling && "animate-pulse pointer-events-none",
            )}
          >
            <span className="text-base">✦</span>
            <span>{rerolling ? "重投中..." : `花费 1${pointName} 重投`}</span>
            <span className="ml-1 text-[10px] text-amber-400/60">
              (剩余 {storyPoints})
            </span>
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="my-3 rounded-2xl border-2 border-dashed border-primary/40 bg-primary/5 overflow-hidden">
      {element.prompt && (
        <div className="px-5 pt-4 pb-2">
          <p className="text-sm font-medium text-foreground">{element.prompt}</p>
        </div>
      )}

      <div className="px-5 pb-4 flex items-center gap-4">
        <button
          onClick={handleRoll}
          disabled={rolling || disabled}
          className={cn(
            "flex items-center gap-3 px-6 py-3 rounded-xl",
            "bg-gradient-to-r from-primary to-primary/80 text-primary-foreground",
            "font-semibold text-sm transition-all",
            "hover:shadow-[0_0_20px_rgba(109,93,252,0.4)] hover:scale-105",
            "active:scale-95",
            rolling && "animate-pulse pointer-events-none",
            disabled && "opacity-50 cursor-not-allowed",
          )}
        >
          <span
            className={cn(
              "text-2xl transition-transform",
              rolling && "animate-dice-tumble",
            )}
          >
            🎲
          </span>
          <span>{rolling ? "投掷中..." : "投掷骰子"}</span>
          <span className="font-mono text-xs opacity-80">
            {element.expression}
          </span>
        </button>

        <div className="flex flex-col text-xs text-muted-foreground">
          {element.skill_name && (
            <span>
              {element.skill_name}检定
            </span>
          )}
          {(element.dc ?? 0) > 0 && <span>DC {element.dc}</span>}
        </div>
      </div>
    </div>
  );
}
