"use client";

import { useCallback, useState } from "react";
import type { InteractiveElement, DiceResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import DiceResultCard from "./DiceResultCard";
import { rollDice } from "@/lib/api";

interface DiceRollButtonProps {
  element: InteractiveElement;
  sessionId: string;
  onResult: (result: DiceResult) => void;
  disabled?: boolean;
}

export default function DiceRollButton({
  element,
  sessionId,
  onResult,
  disabled,
}: DiceRollButtonProps) {
  const [rolling, setRolling] = useState(false);
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
      // Delay slightly for animation buildup
      setTimeout(() => {
        setResult(res);
        setRolling(false);
        onResult(res);
      }, 600);
    } catch {
      setRolling(false);
    }
  }, [rolling, result, disabled, sessionId, element, onResult]);

  if (result) {
    return <DiceResultCard dice={result} />;
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
