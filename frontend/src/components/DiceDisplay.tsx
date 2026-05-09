"use client";

import type { DiceResult } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function DiceDisplay({ dice }: { dice: DiceResult }) {
  const isCrit = dice.rolls.some((r) => r === 20);
  const isFumble = dice.rolls.some((r) => r === 1) && dice.rolls.length === 1;

  return (
    <div className="inline-flex items-center gap-2 rounded-lg bg-secondary/80 px-3 py-2 my-1 border border-border">
      <span className="text-sm text-muted-foreground font-mono">
        🎲 {dice.expression}
      </span>
      <div className="flex gap-1">
        {dice.rolls.map((r, i) => (
          <span
            key={i}
            className={cn(
              "inline-flex h-8 w-8 items-center justify-center rounded-md font-bold text-sm animate-dice",
              r === 20
                ? "bg-accent text-accent-foreground shadow-[0_0_8px_var(--dice-glow)]"
                : r === 1
                  ? "bg-destructive text-white"
                  : "bg-muted text-foreground",
            )}
          >
            {r}
          </span>
        ))}
      </div>
      <span
        className={cn(
          "font-bold text-lg",
          isCrit ? "text-accent" : isFumble ? "text-destructive" : "text-foreground",
        )}
      >
        = {dice.total}
      </span>
      <span className="text-xs text-muted-foreground">{dice.detail}</span>
    </div>
  );
}
