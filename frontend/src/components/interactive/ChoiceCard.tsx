"use client";

import { useState } from "react";
import type { InteractiveElement } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ChoiceCardProps {
  element: InteractiveElement;
  onSelect: (choiceId: string, label: string) => void;
  disabled?: boolean;
}

export default function ChoiceCard({
  element,
  onSelect,
  disabled,
}: ChoiceCardProps) {
  const resolvedOpt = element.resolved
    ? element.options?.find((o) => o.label === element.resolved_value)?.id ?? element.options?.[0]?.id ?? null
    : null;
  const [selected, setSelected] = useState<string | null>(resolvedOpt);

  const handleSelect = (optId: string, label: string) => {
    if (disabled || selected) return;
    setSelected(optId);
    onSelect(optId, label);
  };

  return (
    <div className="my-3 rounded-2xl border border-border/60 bg-card/50 overflow-hidden">
      {element.prompt && (
        <div className="px-5 pt-4 pb-2">
          <p className="text-sm font-medium text-foreground">
            {element.prompt}
          </p>
        </div>
      )}

      <div className="px-4 pb-4 space-y-2">
        {element.options?.map((opt, i) => {
          const isSelected = selected === opt.id;
          const isOther = selected && !isSelected;

          return (
            <button
              key={opt.id}
              onClick={() => handleSelect(opt.id, opt.label)}
              disabled={disabled || !!selected}
              className={cn(
                "w-full flex items-center gap-3 rounded-xl px-4 py-3 text-left",
                "border-2 transition-all duration-300",
                isSelected
                  ? "border-primary bg-primary/15 scale-[1.01]"
                  : isOther
                    ? "border-border/30 bg-secondary/30 opacity-50 scale-[0.98]"
                    : "border-border/50 bg-secondary/50 hover:border-primary/40 hover:bg-secondary/80",
                !selected && !disabled && "cursor-pointer",
              )}
            >
              <span
                className={cn(
                  "shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-sm",
                  isSelected
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {opt.icon || String.fromCharCode(65 + i)}
              </span>
              <div className="flex-1 min-w-0">
                <div
                  className={cn(
                    "text-sm font-medium",
                    isSelected ? "text-primary" : "text-foreground",
                  )}
                >
                  {opt.label}
                </div>
                {opt.description && (
                  <div className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                    {opt.description}
                  </div>
                )}
              </div>
              {isSelected && (
                <span className="text-primary text-lg animate-result-appear">✓</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
