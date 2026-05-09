"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Brain,
  Plus,
  Trash2,
  X,
  MapPin,
  GitBranch,
  Target,
  Users,
  Package,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
} from "lucide-react";
import {
  listMemories,
  addMemory,
  deleteMemory,
  clearMemories,
  type MemoryItem,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const CATEGORIES = [
  { id: "facts", label: "世界事实", icon: MapPin, color: "text-blue-400" },
  { id: "decisions", label: "关键决策", icon: GitBranch, color: "text-purple-400" },
  { id: "quests", label: "任务目标", icon: Target, color: "text-yellow-400" },
  { id: "npcs", label: "NPC 记录", icon: Users, color: "text-green-400" },
  { id: "items", label: "物品变动", icon: Package, color: "text-orange-400" },
] as const;

interface MemoryPanelProps {
  sessionId: string;
  collapsed?: boolean;
}

export default function MemoryPanel({
  sessionId,
  collapsed = false,
}: MemoryPanelProps) {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [filter, setFilter] = useState("");
  const [adding, setAdding] = useState(false);
  const [newText, setNewText] = useState("");
  const [newCat, setNewCat] = useState("facts");
  const [expandedCat, setExpandedCat] = useState<string | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(collapsed);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      const list = await listMemories(sessionId, filter || undefined);
      setMemories(list);
    } catch {
      /* ignore */
    }
  }, [sessionId, filter]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, [refresh]);

  const grouped = CATEGORIES.map((cat) => ({
    ...cat,
    items: memories.filter((m) => m.category === cat.id),
  }));

  const totalCount = memories.length;

  const handleAdd = async () => {
    if (!newText.trim()) return;
    try {
      await addMemory(sessionId, newText.trim(), newCat);
      setNewText("");
      setAdding(false);
      refresh();
    } catch {
      /* ignore */
    }
  };

  const handleDelete = async (item: MemoryItem) => {
    try {
      await deleteMemory(sessionId, item.category, item.key);
      refresh();
    } catch {
      /* ignore */
    }
  };

  const handleClear = async () => {
    if (!confirm("确认清除该会话的所有长期记忆？")) return;
    try {
      await clearMemories(sessionId);
      refresh();
    } catch {
      /* ignore */
    }
  };

  if (isCollapsed) {
    return (
      <button
        onClick={() => setIsCollapsed(false)}
        className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-card border border-border text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 transition-colors"
        title="展开记忆面板"
      >
        <Brain className="h-3.5 w-3.5 text-primary" />
        <span>{totalCount}</span>
      </button>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
        <Brain className="h-4 w-4 text-primary" />
        <span className="text-sm font-semibold text-foreground">长期记忆</span>
        <span className="text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded-full">
          {totalCount}
        </span>
        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={() => setAdding(!adding)}
            className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-primary transition-colors"
            title="手动添加记忆"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
          {totalCount > 0 && (
            <button
              onClick={handleClear}
              className="p-1 rounded hover:bg-red-400/10 text-muted-foreground hover:text-red-400 transition-colors"
              title="清除所有"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
          <button
            onClick={() => setIsCollapsed(true)}
            className="p-1 rounded hover:bg-secondary text-muted-foreground transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-1 px-3 py-2 border-b border-border/50 overflow-x-auto">
        <button
          onClick={() => setFilter("")}
          className={cn(
            "shrink-0 px-2 py-0.5 rounded text-[10px] font-medium transition-colors",
            !filter
              ? "bg-primary/20 text-primary"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          全部
        </button>
        {CATEGORIES.map((cat) => {
          const count = memories.filter(
            (m) => m.category === cat.id,
          ).length;
          return (
            <button
              key={cat.id}
              onClick={() => setFilter(filter === cat.id ? "" : cat.id)}
              className={cn(
                "shrink-0 flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium transition-colors",
                filter === cat.id
                  ? "bg-primary/20 text-primary"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <cat.icon className="h-2.5 w-2.5" />
              {cat.label}
              {count > 0 && (
                <span className="text-[9px] opacity-60">{count}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Add form */}
      {adding && (
        <div className="px-3 py-2 border-b border-border/50 bg-secondary/30">
          <div className="flex gap-1.5 mb-1.5">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setNewCat(cat.id)}
                className={cn(
                  "px-2 py-0.5 rounded text-[10px] transition-colors",
                  newCat === cat.id
                    ? `bg-primary/20 ${cat.color}`
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>
          <div className="flex gap-1.5">
            <input
              value={newText}
              onChange={(e) => setNewText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              placeholder="输入要记住的事实..."
              autoFocus
              className="flex-1 rounded bg-secondary px-2 py-1 text-xs text-foreground border border-border focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground"
            />
            <button
              onClick={handleAdd}
              className="px-2 py-1 rounded text-[10px] font-medium bg-primary text-primary-foreground hover:bg-primary/90"
            >
              添加
            </button>
          </div>
        </div>
      )}

      {/* Memory list */}
      <div className="max-h-[400px] overflow-y-auto">
        {totalCount === 0 ? (
          <div className="px-4 py-6 text-center">
            <Brain className="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
            <p className="text-xs text-muted-foreground">
              暂无长期记忆。游戏过程中 AI 会自动提取关键信息。
            </p>
          </div>
        ) : filter ? (
          <div className="p-2 space-y-1">
            {memories
              .filter((m) => m.category === filter)
              .map((m) => (
                <MemoryRow
                  key={m.key}
                  item={m}
                  onDelete={() => handleDelete(m)}
                />
              ))}
          </div>
        ) : (
          grouped.map((g) => {
            if (g.items.length === 0) return null;
            const isOpen = expandedCat === g.id || expandedCat === null;
            return (
              <div key={g.id} className="border-b border-border/30 last:border-0">
                <button
                  onClick={() =>
                    setExpandedCat(expandedCat === g.id ? null : g.id)
                  }
                  className="flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-secondary/30 transition-colors"
                >
                  <g.icon className={cn("h-3 w-3", g.color)} />
                  <span className={cn("text-xs font-medium", g.color)}>
                    {g.label}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {g.items.length}
                  </span>
                  <span className="ml-auto">
                    {isOpen ? (
                      <ChevronUp className="h-3 w-3 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="h-3 w-3 text-muted-foreground" />
                    )}
                  </span>
                </button>
                {isOpen && (
                  <div className="px-2 pb-2 space-y-0.5">
                    {g.items.map((m) => (
                      <MemoryRow
                        key={m.key}
                        item={m}
                        onDelete={() => handleDelete(m)}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function MemoryRow({
  item,
  onDelete,
}: {
  item: MemoryItem;
  onDelete: () => void;
}) {
  return (
    <div className="group flex items-start gap-1.5 px-2 py-1.5 rounded-lg hover:bg-secondary/40 transition-colors">
      <span className="text-xs text-foreground/90 flex-1 leading-relaxed">
        {item.text}
      </span>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="shrink-0 p-0.5 rounded opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400 transition-all"
        title="删除此记忆"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}
