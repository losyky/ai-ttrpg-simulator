"use client";

import { useCallback, useState } from "react";
import type { InteractiveElement, DiceResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import DualityDiceCard from "./DualityDiceCard";
import { rollDice } from "@/lib/api";

interface Props {
  element: InteractiveElement;
  sessionId: string;
  onResult: (result: DiceResult) => void;
  disabled?: boolean;
}

export default function DualityDiceButton({ element, sessionId, onResult, disabled }: Props) {
  const [rolling, setRolling] = useState(false);
  const [result, setResult] = useState<DiceResult | null>(element.resolved_dice ?? null);

  const handleRoll = useCallback(async () => {
    if (rolling || result || disabled) return;
    setRolling(true);
    try {
      const res = await rollDice({
        session_id: sessionId,
        expression: element.expression || "2d12",
        dc: element.dc,
        label: element.skill_name || element.trait_name || "",
        modifier: element.modifier,
      });
      setTimeout(() => {
        setResult(res);
        setRolling(false);
        onResult(res);
      }, 700);
    } catch {
      setRolling(false);
    }
  }, [rolling, result, disabled, sessionId, element, onResult]);

  if (result) {
    return <DualityDiceCard dice={result} />;
  }

  return (
    <div className="my-3 rounded-2xl border-2 border-dashed overflow-hidden bg-gradient-to-r from-sky-500/5 to-rose-500/5 border-sky-500/20">
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
            "bg-gradient-to-r from-sky-500 to-rose-500 text-white",
            "font-semibold text-sm transition-all",
            "hover:shadow-[0_0_25px_rgba(56,189,248,0.3)] hover:scale-105",
            "active:scale-95",
            rolling && "animate-pulse pointer-events-none",
            disabled && "opacity-50 cursor-not-allowed",
          )}
        >
          <span className="flex gap-1">
            <span className={cn("text-lg", rolling && "animate-dice-tumble")}>✦</span>
            <span className={cn("text-lg", rolling && "animate-dice-tumble")}>⚡</span>
          </span>
          <span>{rolling ? "投掷中..." : "投掷二元骰"}</span>
          <span className="font-mono text-xs opacity-80">{element.expression}</span>
        </button>

        <div className="flex flex-col text-xs text-muted-foreground">
          {element.trait_name && <span>{element.trait_name} 检定</span>}
          {element.experience_bonus && (
            <span className="text-sky-400">经历加成 +2</span>
          )}
          {(element.dc ?? 0) > 0 && <span>DC {element.dc}</span>}
        </div>
      </div>
    </div>
  );
}
