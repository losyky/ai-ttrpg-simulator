"use client";

import type { InteractiveElement } from "@/lib/types";
import { cn } from "@/lib/utils";

const TOKEN_CONFIG = {
  hope: {
    label: "Hope",
    labelCn: "希望",
    color: "text-sky-400",
    bg: "bg-sky-500/10",
    border: "border-sky-500/30",
    icon: "✦",
    gradient: "from-sky-400 to-blue-500",
  },
  fear: {
    label: "Fear",
    labelCn: "恐惧",
    color: "text-rose-400",
    bg: "bg-rose-500/10",
    border: "border-rose-500/30",
    icon: "⚡",
    gradient: "from-rose-500 to-red-600",
  },
  story_point: {
    label: "Story Point",
    labelCn: "叙事点",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    icon: "✦",
    gradient: "from-amber-400 to-yellow-500",
  },
} as const;

export default function TokenUpdateCard({ element }: { element: InteractiveElement }) {
  const type = (element.token_type || "hope") as keyof typeof TOKEN_CONFIG;
  const config = TOKEN_CONFIG[type] ?? TOKEN_CONFIG.hope;
  const change = element.token_change ?? 0;
  const total = element.token_total ?? 0;
  const reason = element.token_reason || element.prompt || "";

  return (
    <div
      className={cn(
        "rounded-xl border px-4 py-3 my-2 flex items-center gap-3 transition-all",
        config.bg,
        config.border,
      )}
    >
      {/* Token icon */}
      <div
        className={cn(
          "w-10 h-10 rounded-full flex items-center justify-center text-white text-lg font-bold",
          `bg-gradient-to-br ${config.gradient}`,
        )}
      >
        {config.icon}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={cn("text-sm font-bold", config.color)}>
            {config.labelCn} ({config.label})
          </span>
          <span
            className={cn(
              "text-sm font-mono font-bold",
              change > 0 ? "text-emerald-400" : "text-rose-400",
            )}
          >
            {change > 0 ? `+${change}` : change}
          </span>
        </div>
        {reason && (
          <p className="text-xs text-muted-foreground mt-0.5 truncate">{reason}</p>
        )}
      </div>

      {/* Total counter */}
      <div className="flex flex-col items-center">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">总计</span>
        <span className={cn("text-2xl font-black", config.color)}>{total}</span>
      </div>
    </div>
  );
}
