"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Wrench,
  Trash2,
  RefreshCw,
  Lock,
  ChevronDown,
  ChevronRight,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import {
  listTools,
  createTool,
  deleteTool,
  type ToolInfo,
} from "@/lib/api";

const CATEGORY_LABELS: Record<string, string> = {
  core: "核心工具",
  knowledge: "知识库工具",
  combat: "战斗工具",
  character: "角色工具",
  meta: "元工具",
  custom: "自定义工具",
};

export default function ToolsPanel({ systemId }: { systemId?: string }) {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    tool_id: "",
    name: "",
    description: "",
    instructions: "",
    shared: false,
  });
  const [msg, setMsg] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setTools(await listTools(systemId));
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [systemId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleCreate = useCallback(async () => {
    if (!form.tool_id || !form.name || !form.description) {
      setMsg("请填写 ID、名称和描述");
      return;
    }
    try {
      await createTool({ ...form }, systemId);
      setMsg(`工具「${form.name}」已创建${form.shared ? "（共通）" : ""}`);
      setForm({ tool_id: "", name: "", description: "", instructions: "", shared: false });
      setShowCreate(false);
      refresh();
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      setMsg(`创建失败: ${errMsg}`);
    }
  }, [form, refresh, systemId]);

  const handleDelete = useCallback(
    async (toolId: string) => {
      try {
        await deleteTool(toolId, systemId);
        if (expanded === toolId) setExpanded(null);
        refresh();
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : String(err);
        setMsg(`删除失败: ${errMsg}`);
      }
    },
    [expanded, refresh, systemId],
  );

  // Group by category
  const grouped: Record<string, ToolInfo[]> = {};
  for (const t of tools) {
    const cat = t.category || "custom";
    (grouped[cat] ??= []).push(t);
  }

  const categoryOrder = ["core", "knowledge", "combat", "character", "meta", "custom"];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            工具清单 ({tools.length})
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            内置工具 🔒 不可删除 · 自定义工具 🔧 可创建和删除
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            新建工具
          </button>
          <button
            onClick={refresh}
            disabled={loading}
            className="p-1.5 rounded-lg hover:bg-secondary transition-colors"
          >
            <RefreshCw
              className={cn("h-4 w-4 text-muted-foreground", loading && "animate-spin")}
            />
          </button>
        </div>
      </div>

      {msg && (
        <div className="text-sm text-accent bg-accent/10 rounded-lg px-4 py-2">
          {msg}
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <div className="bg-secondary/50 rounded-xl p-4 border border-border/50 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input
              value={form.tool_id}
              onChange={(e) => setForm((f) => ({ ...f, tool_id: e.target.value }))}
              placeholder="Tool ID (如: npc-generator)"
              className={cn(
                "rounded-lg bg-secondary border border-border px-3 py-2 text-sm",
                "text-foreground placeholder:text-muted-foreground",
                "focus:outline-none focus:ring-2 focus:ring-ring",
              )}
            />
            <input
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="工具名称"
              className={cn(
                "rounded-lg bg-secondary border border-border px-3 py-2 text-sm",
                "text-foreground placeholder:text-muted-foreground",
                "focus:outline-none focus:ring-2 focus:ring-ring",
              )}
            />
          </div>
          <input
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            placeholder="工具功能描述"
            className={cn(
              "w-full rounded-lg bg-secondary border border-border px-3 py-2 text-sm",
              "text-foreground placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-ring",
            )}
          />
          <textarea
            value={form.instructions}
            onChange={(e) => setForm((f) => ({ ...f, instructions: e.target.value }))}
            placeholder="使用说明和实现逻辑（Markdown 格式）..."
            rows={4}
            className={cn(
              "w-full rounded-lg bg-secondary border border-border px-3 py-2 text-sm",
              "text-foreground placeholder:text-muted-foreground resize-none",
              "focus:outline-none focus:ring-2 focus:ring-ring",
            )}
          />
          <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
            <input
              type="checkbox"
              checked={form.shared}
              onChange={(e) => setForm((f) => ({ ...f, shared: e.target.checked }))}
              className="rounded border-border"
            />
            共通工具（所有规则系统可见）
          </label>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleCreate}
              className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm hover:bg-primary/90 transition-colors"
            >
              创建
            </button>
          </div>
        </div>
      )}

      {/* Tool list by category */}
      {categoryOrder
        .filter((cat) => grouped[cat]?.length)
        .map((cat) => (
          <div key={cat}>
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              {CATEGORY_LABELS[cat] || cat}
            </h4>
            <div className="space-y-1.5">
              {grouped[cat].map((tool) => (
                <div
                  key={tool.tool_id}
                  className="bg-secondary/50 rounded-xl border border-border/50 overflow-hidden"
                >
                  <div
                    className="flex items-center gap-3 px-4 py-2.5 cursor-pointer hover:bg-secondary/80 transition-colors"
                    onClick={() =>
                      setExpanded(expanded === tool.tool_id ? null : tool.tool_id)
                    }
                  >
                    {expanded === tool.tool_id ? (
                      <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    )}
                    {tool.builtin ? (
                      <Lock className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    ) : (
                      <Wrench className="h-3.5 w-3.5 text-primary shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-foreground flex items-center gap-1.5 flex-wrap">
                        {tool.name}
                        <span className="text-xs text-muted-foreground font-mono">
                          {tool.tool_id}
                        </span>
                        {tool.shared && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/20 text-accent font-medium">
                            共通
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground truncate">
                        {tool.description}
                      </div>
                    </div>
                    {!tool.builtin && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(tool.tool_id);
                        }}
                        className="p-1.5 rounded-lg hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                  {expanded === tool.tool_id && (
                    <div className="border-t border-border/50 px-4 py-3 space-y-2">
                      {Object.keys(tool.parameters).length > 0 && (
                        <div>
                          <div className="text-xs font-semibold text-muted-foreground mb-1">
                            参数
                          </div>
                          <div className="space-y-1">
                            {Object.entries(tool.parameters).map(([key, desc]) => (
                              <div key={key} className="text-xs">
                                <code className="text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                                  {key}
                                </code>
                                <span className="text-muted-foreground ml-2">{desc}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {tool.instructions && (
                        <div className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2">
                          <div className="text-xs font-semibold text-muted-foreground mb-1">
                            使用说明
                          </div>
                          <ReactMarkdown>{tool.instructions}</ReactMarkdown>
                        </div>
                      )}
                      {tool.builtin && (
                        <div className="text-xs text-muted-foreground italic">
                          🔒 内置工具，不可修改或删除
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
    </div>
  );
}
