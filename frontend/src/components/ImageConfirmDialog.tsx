"use client";

import { useEffect, useRef } from "react";
import { ImageIcon, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  prompt: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ImageConfirmDialog({ prompt, onConfirm, onCancel }: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onCancel]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}
    >
      <div
        ref={dialogRef}
        className="w-full max-w-md mx-4 bg-card border border-border rounded-2xl shadow-2xl p-6 space-y-4"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-accent">
            <ImageIcon className="h-5 w-5" />
            <span className="font-semibold text-sm">图片生成确认</span>
          </div>
          <button
            onClick={onCancel}
            title="取消"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="text-sm text-muted-foreground">
          当前对话频率限制尚未达到，AI 希望生成以下场景图片：
        </p>

        <div className="bg-secondary rounded-lg px-4 py-3 text-sm text-foreground/80 italic border border-border">
          {prompt}
        </div>

        <p className="text-xs text-muted-foreground">
          生成图片将消耗 API 额度。确认后立即生成，取消则跳过。
        </p>

        <div className="flex gap-3 pt-1">
          <button
            onClick={onCancel}
            className={cn(
              "flex-1 px-4 py-2 rounded-lg text-sm border border-border",
              "text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors"
            )}
          >
            跳过
          </button>
          <button
            onClick={onConfirm}
            className={cn(
              "flex-1 px-4 py-2 rounded-lg text-sm font-medium",
              "bg-accent text-accent-foreground hover:bg-accent/90 transition-colors"
            )}
          >
            确认生成
          </button>
        </div>
      </div>
    </div>
  );
}
