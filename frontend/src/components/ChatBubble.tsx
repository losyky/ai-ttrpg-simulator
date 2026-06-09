"use client";

import { useState } from "react";
import type { ChatMessage } from "@/lib/types";
import { cn, toImageUrl } from "@/lib/utils";
import DiceResultCard from "./interactive/DiceResultCard";
import DualityDiceCard from "./interactive/DualityDiceCard";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import { X, ZoomIn } from "lucide-react";

const ROLE_META: Record<string, { label: string; color: string }> = {
  user: { label: "你", color: "text-primary" },
  narrator: { label: "讲述者", color: "text-accent" },
  referee: { label: "裁决者", color: "text-green-400" },
  teammate: { label: "队友", color: "text-sky-400" },
  system: { label: "系统", color: "text-muted-foreground" },
};

const PLACEHOLDER_SVG =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'%3E%3Crect width='400' height='300' fill='%23374151'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%236B7280' font-size='14' font-family='sans-serif'%3E图片加载失败%3C/text%3E%3C/svg%3E";

function ImageCard({ src, alt }: { src: string; alt?: string }) {
  const [lightbox, setLightbox] = useState(false);

  return (
    <>
      <div
        className="relative group cursor-zoom-in rounded-lg overflow-hidden border border-border/50 shadow-md mt-3 max-w-[480px]"
        onClick={() => setLightbox(true)}
      >
        <img
          src={toImageUrl(src)}
          alt={alt ?? "生成图片"}
          loading="lazy"
          onError={(e) => {
            (e.currentTarget as HTMLImageElement).src = PLACEHOLDER_SVG;
          }}
          className="w-full h-auto block"
        />
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
          <ZoomIn className="h-6 w-6 text-white opacity-0 group-hover:opacity-80 transition-opacity" />
        </div>
      </div>

      {lightbox && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={() => setLightbox(false)}
        >
          <button
            title="关闭"
            onClick={() => setLightbox(false)}
            className="absolute top-4 right-4 text-white/70 hover:text-white transition-colors"
          >
            <X className="h-8 w-8" />
          </button>
          <img
            src={toImageUrl(src)}
            alt={alt ?? "生成图片"}
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).src = PLACEHOLDER_SVG;
            }}
            className="max-w-[90vw] max-h-[90vh] rounded-xl shadow-2xl object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  );
}

const markdownImgComponent: Components["img"] = ({ src, alt }) => (
  <ImageCard src={toImageUrl(src ?? "")} alt={alt} />
);

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
            <ReactMarkdown components={{ img: markdownImgComponent }}>
              {msg.content}
            </ReactMarkdown>
          </div>
        )}

        {msg.dice && !msg.content && (
          msg.dice.duality_outcome
            ? <DualityDiceCard dice={msg.dice} />
            : <DiceResultCard dice={msg.dice} />
        )}

        {/* Images array — shown below text content */}
        {msg.images && msg.images.length > 0 && (
          <div className="space-y-2">
            {msg.images.map((url, i) => (
              <ImageCard key={i} src={url} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
