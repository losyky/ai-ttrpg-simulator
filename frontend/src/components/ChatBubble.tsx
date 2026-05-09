"use client";

import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import DiceResultCard from "./interactive/DiceResultCard";
import DualityDiceCard from "./interactive/DualityDiceCard";
import ReactMarkdown from "react-markdown";

const ROLE_META: Record<string, { label: string; color: string }> = {
  user: { label: "你", color: "text-primary" },
  narrator: { label: "讲述者", color: "text-accent" },
  referee: { label: "裁决者", color: "text-green-400" },
  teammate: { label: "队友", color: "text-sky-400" },
  system: { label: "系统", color: "text-muted-foreground" },
};

export default function ChatBubble({
  msg,
  isStreaming,
}: {
  msg: ChatMessage;
  isStreaming?: boolean;
}) {
  const meta = ROLE_META[msg.role] ?? ROLE_META.system;
  const isUser = msg.role === "user";

  // Referee dice results: Daggerheart duality vs standard
  if (msg.role === "referee" && msg.dice) {
    const DiceCard = msg.dice.duality_outcome ? DualityDiceCard : DiceResultCard;
    return (
      <div className="flex w-full justify-start">
        <div className="max-w-[85%]">
          <DiceCard dice={msg.dice} />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex w-full gap-3",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3",
          isUser
            ? "bg-primary/20 border border-primary/30 rounded-br-sm"
            : "bg-card border border-border rounded-bl-sm",
        )}
      >
        {!isUser && (
          <div className={cn("text-xs font-semibold mb-1", meta.color)}>
            {meta.label}
          </div>
        )}

        {msg.content && (
          <div
            className={cn(
              "text-sm leading-relaxed prose prose-invert prose-sm max-w-none",
              "prose-p:my-1.5 prose-headings:my-2 prose-hr:my-3",
              "prose-strong:text-foreground prose-em:text-foreground/90",
              "prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5",
              "prose-blockquote:border-l-primary prose-blockquote:text-muted-foreground",
              isStreaming && "typing-cursor",
            )}
          >
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}

        {msg.dice && !msg.content && (
          msg.dice.duality_outcome
            ? <DualityDiceCard dice={msg.dice} />
            : <DiceResultCard dice={msg.dice} />
        )}
      </div>
    </div>
  );
}
