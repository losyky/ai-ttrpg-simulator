"use client";

import { useState, useCallback } from "react";

interface PF2eDescriptionProps {
  html: string;
  className?: string;
}

export default function PF2eDescription({ html, className = "" }: PF2eDescriptionProps) {
  const [tooltip, setTooltip] = useState<{ name: string; x: number; y: number } | null>(null);

  const handleClick = useCallback((e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.classList.contains("pf2e-ref")) {
      const name = target.dataset.name || target.textContent || "";
      const rect = target.getBoundingClientRect();
      setTooltip({ name, x: rect.left, y: rect.bottom + 4 });
    } else {
      setTooltip(null);
    }
  }, []);

  if (!html) return null;

  return (
    <div className={`pf2e-description relative ${className}`} onClick={handleClick}>
      <div
        className="prose prose-sm prose-invert max-w-none"
        dangerouslySetInnerHTML={{ __html: html }}
      />
      {tooltip && (
        <div
          className="fixed z-50 bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-xl max-w-sm"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <p className="text-sm text-gray-300">
            📖 <strong>{tooltip.name}</strong>
          </p>
          <p className="text-xs text-gray-500 mt-1">点击其他区域关闭</p>
        </div>
      )}

      <style jsx global>{`
        .pf2e-description .pf2e-ref {
          color: #60a5fa;
          cursor: pointer;
          text-decoration: underline;
          text-decoration-style: dotted;
        }
        .pf2e-description .pf2e-ref:hover {
          color: #93bbfc;
        }
        .pf2e-description .pf2e-check {
          display: inline-flex;
          align-items: center;
          gap: 2px;
          background: rgba(139, 92, 246, 0.15);
          color: #a78bfa;
          padding: 1px 6px;
          border-radius: 4px;
          font-weight: 500;
          font-size: 0.875em;
        }
        .pf2e-description .pf2e-damage {
          display: inline-flex;
          align-items: center;
          gap: 2px;
          background: rgba(239, 68, 68, 0.15);
          color: #f87171;
          padding: 1px 6px;
          border-radius: 4px;
          font-weight: 500;
          font-size: 0.875em;
        }
        .pf2e-description .pf2e-template {
          display: inline-flex;
          align-items: center;
          gap: 2px;
          background: rgba(34, 197, 94, 0.15);
          color: #4ade80;
          padding: 1px 6px;
          border-radius: 4px;
          font-weight: 500;
          font-size: 0.875em;
        }
        .pf2e-description .pf2e-roll {
          background: rgba(251, 191, 36, 0.15);
          color: #fbbf24;
          padding: 1px 6px;
          border-radius: 4px;
          font-family: monospace;
          font-size: 0.875em;
        }
      `}</style>
    </div>
  );
}
