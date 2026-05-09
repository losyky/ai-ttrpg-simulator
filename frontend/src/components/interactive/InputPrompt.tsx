"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import type { InteractiveElement } from "@/lib/types";
import { cn } from "@/lib/utils";

interface InputPromptProps {
  element: InteractiveElement;
  onSubmit: (value: string) => void;
  disabled?: boolean;
}

export default function InputPrompt({
  element,
  onSubmit,
  disabled,
}: InputPromptProps) {
  const [value, setValue] = useState(element.resolved_value ?? "");
  const [submitted, setSubmitted] = useState(!!element.resolved);

  const handleSubmit = () => {
    if (!value.trim() || submitted || disabled) return;
    setSubmitted(true);
    onSubmit(value.trim());
  };

  if (submitted) {
    return (
      <div className="my-3 rounded-xl border border-primary/30 bg-primary/10 px-4 py-3">
        <div className="text-xs text-muted-foreground mb-1">{element.prompt}</div>
        <div className="text-sm text-primary font-medium">{value}</div>
      </div>
    );
  }

  return (
    <div className="my-3 rounded-2xl border border-border/60 bg-card/50 overflow-hidden">
      {element.prompt && (
        <div className="px-5 pt-4 pb-2">
          <p className="text-sm font-medium text-foreground">{element.prompt}</p>
        </div>
      )}

      <div className="px-4 pb-4 flex gap-2">
        <input
          type={element.input_type === "number" ? "number" : "text"}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          placeholder={element.placeholder || "输入内容..."}
          disabled={disabled}
          className={cn(
            "flex-1 rounded-xl bg-secondary border border-border px-4 py-2.5 text-sm",
            "text-foreground placeholder:text-muted-foreground",
            "focus:outline-none focus:ring-2 focus:ring-ring",
          )}
        />
        <button
          onClick={handleSubmit}
          disabled={!value.trim() || disabled}
          className={cn(
            "p-2.5 rounded-xl bg-primary text-primary-foreground transition-colors",
            "hover:bg-primary/90 disabled:opacity-50",
          )}
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
