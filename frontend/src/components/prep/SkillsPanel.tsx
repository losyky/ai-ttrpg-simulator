"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Plus,
  Trash2,
  RefreshCw,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import {
  listSkills,
  getSkill,
  createSkill,
  deleteSkill,
  type SkillInfo,
  type SkillDetail,
} from "@/lib/api";

export default function SkillsPanel({ systemId }: { systemId?: string }) {
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [expandedContent, setExpandedContent] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    skill_id: "",
    title: "",
    description: "",
    instructions: "",
    examples: "",
    shared: false,
  });
  const [msg, setMsg] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setSkills(await listSkills(systemId));
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [systemId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const toggleExpand = useCallback(
    async (skillId: string) => {
      if (expanded === skillId) {
        setExpanded(null);
        return;
      }
      try {
        const detail: SkillDetail = await getSkill(skillId, systemId);
        setExpandedContent(detail.content);
        setExpanded(skillId);
      } catch {
        /* ignore */
      }
    },
    [expanded, systemId],
  );

  const handleCreate = useCallback(async () => {
    if (!form.skill_id || !form.title || !form.instructions) {
      setMsg("请填写 ID、标题和指令");
      return;
    }
    try {
      await createSkill(form, systemId);
      setMsg(`Skill「${form.title}」已创建${form.shared ? "（共通）" : ""}`);
      setForm({ skill_id: "", title: "", description: "", instructions: "", examples: "", shared: false });
      setShowCreate(false);
      refresh();
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      setMsg(`创建失败: ${errMsg}`);
    }
  }, [form, refresh, systemId]);

  const handleDelete = useCallback(
    async (skillId: string) => {
      try {
        await deleteSkill(skillId, systemId);
        if (expanded === skillId) setExpanded(null);
        refresh();
      } catch {
        /* ignore */
      }
    },
    [expanded, refresh, systemId],
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            AI Skills ({skills.length})
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            AI 可自主创建的技能和工作流程
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            新建 Skill
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
              value={form.skill_id}
              onChange={(e) => setForm((f) => ({ ...f, skill_id: e.target.value }))}
              placeholder="Skill ID (如: pf2e-combat-flow)"
              className={cn(
                "rounded-lg bg-secondary border border-border px-3 py-2 text-sm",
                "text-foreground placeholder:text-muted-foreground",
                "focus:outline-none focus:ring-2 focus:ring-ring",
              )}
            />
            <input
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              placeholder="标题"
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
            placeholder="简短描述"
            className={cn(
              "w-full rounded-lg bg-secondary border border-border px-3 py-2 text-sm",
              "text-foreground placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-ring",
            )}
          />
          <textarea
            value={form.instructions}
            onChange={(e) => setForm((f) => ({ ...f, instructions: e.target.value }))}
            placeholder="详细指令（Markdown 格式）..."
            rows={5}
            className={cn(
              "w-full rounded-lg bg-secondary border border-border px-3 py-2 text-sm",
              "text-foreground placeholder:text-muted-foreground resize-none",
              "focus:outline-none focus:ring-2 focus:ring-ring",
            )}
          />
          <textarea
            value={form.examples}
            onChange={(e) => setForm((f) => ({ ...f, examples: e.target.value }))}
            placeholder="示例（可选）..."
            rows={3}
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
            共通 Skill（所有规则系统可见）
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

      {/* Skill list */}
      {skills.length === 0 ? (
        <div className="text-center py-8">
          <Zap className="h-8 w-8 mx-auto text-muted-foreground mb-3" />
          <p className="text-sm text-muted-foreground">
            还没有 Skill。AI 可以在「团外」模式下自主创建，或手动新建。
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {skills.map((skill) => (
            <div
              key={skill.skill_id}
              className="bg-secondary/50 rounded-xl border border-border/50 overflow-hidden"
            >
              <div
                className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-secondary/80 transition-colors"
                onClick={() => toggleExpand(skill.skill_id)}
              >
                {expanded === skill.skill_id ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
                <BookOpen className="h-4 w-4 text-primary shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-foreground flex items-center gap-1.5">
                    {skill.title}
                    {(skill as any).shared && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/20 text-accent font-medium">
                        共通
                      </span>
                    )}
                  </div>
                  {skill.description && (
                    <div className="text-xs text-muted-foreground truncate">
                      {skill.description}
                    </div>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(skill.skill_id);
                  }}
                  className="p-1.5 rounded-lg hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              {expanded === skill.skill_id && (
                <div className="border-t border-border/50 px-4 py-3 prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2">
                  <ReactMarkdown>{expandedContent}</ReactMarkdown>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
