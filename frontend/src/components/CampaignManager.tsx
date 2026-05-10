"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Plus,
  Play,
  Trash2,
  Pencil,
  Check,
  X,
  Clock,
  User,
  Users,
  MessageSquare,
  Swords,
  Compass,
  MessageCircle,
  Bed,
  FolderOpen,
  UserPlus,
  UserMinus,
  BookOpen,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import {
  listSessions,
  createSession,
  deleteSession,
  updateSession,
  getSession,
  listSaves,
  loadSave,
  getSaveHistory,
  listCharacters,
  getCharacterSummary,
  addTeammate,
  removeTeammate,
  getSessionDocuments,
  setSessionDocuments,
  type SaveInfo,
  type CharacterListItem,
  type SessionDocumentItem,
} from "@/lib/api";
import { loadLLMConfig, saveSessionId } from "@/lib/store";
import { cn, hydrateHistory } from "@/lib/utils";
import type { SessionState, SessionListItem, ChatMessage, LLMConfig } from "@/lib/types";

const PHASE_ICON: Record<string, React.ReactNode> = {
  exploration: <Compass className="h-3.5 w-3.5" />,
  combat: <Swords className="h-3.5 w-3.5 text-red-400" />,
  social: <MessageCircle className="h-3.5 w-3.5 text-yellow-400" />,
  downtime: <Bed className="h-3.5 w-3.5 text-blue-400" />,
};

const PHASE_LABEL: Record<string, string> = {
  exploration: "探索",
  combat: "战斗",
  social: "社交",
  downtime: "休整",
};

interface CampaignManagerProps {
  currentSession: SessionState | null;
  onSessionSwitch: (state: SessionState, history: ChatMessage[]) => void;
  onNewSession: (state: SessionState) => void;
  systemId?: string;
}

export default function CampaignManager({
  currentSession,
  onSessionSwitch,
  onNewSession,
  systemId,
}: CampaignManagerProps) {
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [saves, setSaves] = useState<SaveInfo[]>([]);
  const [characters, setCharacters] = useState<CharacterListItem[]>([]);
  const [creating, setCreating] = useState(false);
  const [newLabel, setNewLabel] = useState("");
  const [selectedCharId, setSelectedCharId] = useState<string>("");
  const [selectedTeammateIds, setSelectedTeammateIds] = useState<string[]>([]);
  const [managingTeammates, setManagingTeammates] = useState<string | null>(null);
  const [managingDocs, setManagingDocs] = useState<string | null>(null);
  const [sessionDocs, setSessionDocs] = useState<SessionDocumentItem[]>([]);
  const [docsMode, setDocsMode] = useState<"all" | "selective">("all");
  const [docsSaving, setDocsSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState("");
  const [statusMsg, setStatusMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [sessionList, saveList, charList] = await Promise.all([
        listSessions(systemId),
        listSaves(systemId),
        listCharacters(systemId),
      ]);
      setSessions(sessionList);
      setSaves(saveList);
      setCharacters(charList);
    } catch {
      /* ignore */
    }
  }, [systemId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const flash = (msg: string) => {
    setStatusMsg(msg);
    setTimeout(() => setStatusMsg(""), 3000);
  };

  const handleCreate = async () => {
    const cfg = loadLLMConfig();
    if (!cfg.api_key) {
      flash("请先在设置中配置 API Key");
      return;
    }
    setLoading(true);
    try {
      let player = undefined;
      if (selectedCharId) {
        player = await getCharacterSummary(selectedCharId);
      }
      let systemId: string | undefined;
      try {
        const sysRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/settings/system`);
        const sysData = await sysRes.json();
        systemId = sysData.system_id;
      } catch {}
      const state = await createSession(cfg, player, newLabel || undefined, selectedTeammateIds, systemId);
      onNewSession(state);
      setNewLabel("");
      setSelectedCharId("");
      setSelectedTeammateIds([]);
      setCreating(false);
      flash(`已创建: ${state.label}`);
      refresh();
    } catch (err) {
      flash(`创建失败: ${err instanceof Error ? err.message : err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSwitch = async (sessionId: string) => {
    if (currentSession?.session_id === sessionId) return;
    setLoading(true);
    try {
      const state = await getSession(sessionId);
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/debug/sessions/${sessionId}/history`,
      );
      const rawHistory: Record<string, unknown>[] = resp.ok
        ? await resp.json()
        : [];
      const history = hydrateHistory(rawHistory, `s_${sessionId}`);
      onSessionSwitch(state, history);
      flash(`已切换到: ${state.label}`);
    } catch (err) {
      flash(`切换失败: ${err instanceof Error ? err.message : err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSave = async (saveId: string) => {
    setLoading(true);
    try {
      const state = await loadSave(saveId);
      const rawHistory = await getSaveHistory(saveId);
      const history = hydrateHistory(rawHistory, "saved");
      onSessionSwitch(state, history);
      flash("存档已加载");
    } catch (err) {
      flash(`加载失败: ${err instanceof Error ? err.message : err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (sessionId: string) => {
    if (!confirm("确认删除此团？对话记录将丢失（不影响已保存的存档）。")) return;
    try {
      await deleteSession(sessionId);
      if (currentSession?.session_id === sessionId) {
        saveSessionId(null);
      }
      flash("已删除");
      refresh();
    } catch (err) {
      flash(`删除失败: ${err instanceof Error ? err.message : err}`);
    }
  };

  const handleRename = async (sessionId: string) => {
    if (!editLabel.trim()) {
      setEditingId(null);
      return;
    }
    try {
      await updateSession(sessionId, { label: editLabel.trim() });
      setEditingId(null);
      refresh();
    } catch {
      flash("重命名失败");
    }
  };

  const handleOpenDocs = async (sessionId: string) => {
    if (managingDocs === sessionId) {
      setManagingDocs(null);
      return;
    }
    try {
      const data = await getSessionDocuments(sessionId);
      setSessionDocs(data.documents);
      setDocsMode(data.mode);
      setManagingDocs(sessionId);
    } catch {
      flash("加载资料列表失败");
    }
  };

  const handleToggleDoc = async (sessionId: string, docId: string, currentlyEnabled: boolean) => {
    setDocsSaving(true);
    try {
      const currentEnabled = sessionDocs.filter((d) => d.enabled).map((d) => d.doc_id);
      let newEnabled: string[];
      if (docsMode === "all") {
        newEnabled = currentlyEnabled
          ? sessionDocs.filter((d) => d.doc_id !== docId).map((d) => d.doc_id)
          : sessionDocs.map((d) => d.doc_id);
      } else {
        newEnabled = currentlyEnabled
          ? currentEnabled.filter((id) => id !== docId)
          : [...currentEnabled, docId];
      }
      await setSessionDocuments(sessionId, newEnabled);
      setSessionDocs((prev) =>
        prev.map((d) => ({
          ...d,
          enabled: newEnabled.includes(d.doc_id),
        })),
      );
      setDocsMode("selective");
    } catch {
      flash("更新资料设置失败");
    } finally {
      setDocsSaving(false);
    }
  };

  const handleEnableAllDocs = async (sessionId: string) => {
    setDocsSaving(true);
    try {
      await setSessionDocuments(sessionId, null);
      setSessionDocs((prev) => prev.map((d) => ({ ...d, enabled: true })));
      setDocsMode("all");
    } catch {
      flash("更新资料设置失败");
    } finally {
      setDocsSaving(false);
    }
  };

  const formatDate = (iso: string) => {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="space-y-6">
      {/* Create new campaign */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-4">
          <Plus className="h-4 w-4 text-primary" />
          新建团
        </h3>

        {!creating ? (
          <button
            onClick={() => setCreating(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 border-dashed border-border hover:border-primary/50 text-muted-foreground hover:text-primary transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span className="text-sm">开始一场新的冒险</span>
          </button>
        ) : (
          <div className="space-y-3">
            <div className="flex gap-2">
              <input
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                placeholder="团名称（可选，如「坠星之城」）"
                autoFocus
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                className="flex-1 rounded-lg bg-secondary px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground border border-border focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <button
                onClick={() => {
                  setCreating(false);
                  setNewLabel("");
                  setSelectedCharId("");
                }}
                className="p-2 rounded-lg hover:bg-secondary text-muted-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex gap-2 items-center">
              <User className="h-4 w-4 text-muted-foreground shrink-0" />
              <select
                value={selectedCharId}
                onChange={(e) => setSelectedCharId(e.target.value)}
                className="flex-1 rounded-lg bg-secondary px-3 py-2 text-sm text-foreground border border-border focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">不绑定玩家角色卡</option>
                {characters.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} — Lv.{c.level} {c.ancestry} {c.character_class}
                  </option>
                ))}
              </select>
            </div>

            {/* Teammate selection */}
            {characters.filter((c) => c.id !== selectedCharId).length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <Users className="h-4 w-4 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">选择 AI 队友（可选）</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {characters
                    .filter((c) => c.id !== selectedCharId)
                    .map((c) => {
                      const selected = selectedTeammateIds.includes(c.id);
                      return (
                        <button
                          key={c.id}
                          onClick={() =>
                            setSelectedTeammateIds((prev) =>
                              selected ? prev.filter((id) => id !== c.id) : [...prev, c.id],
                            )
                          }
                          className={cn(
                            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border transition-all",
                            selected
                              ? "border-primary bg-primary/15 text-primary"
                              : "border-border text-muted-foreground hover:border-primary/40 hover:text-foreground",
                          )}
                        >
                          {selected ? <Check className="h-3 w-3" /> : <UserPlus className="h-3 w-3" />}
                          {c.name} Lv.{c.level}
                        </button>
                      );
                    })}
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={handleCreate}
                disabled={loading}
                className="flex items-center gap-1.5 px-5 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" />
                {loading ? "创建中..." : "创建冒险"}
              </button>
            </div>
            {characters.length === 0 && (
              <p className="text-xs text-muted-foreground">
                暂无角色卡。请先在「角色卡」标签页导入 FVTT 角色。
              </p>
            )}
          </div>
        )}
      </div>

      {/* Status */}
      {statusMsg && (
        <div className="text-sm text-primary bg-primary/10 border border-primary/20 rounded-lg px-4 py-2">
          {statusMsg}
        </div>
      )}

      {/* Active sessions */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-4">
          <Swords className="h-4 w-4 text-accent" />
          进行中的团
          <span className="text-xs text-muted-foreground ml-auto">
            {sessions.length} 个
          </span>
        </h3>

        {sessions.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">
            暂无进行中的团。点击上方「新建团」开始冒险。
          </p>
        ) : (
          <div className="space-y-2">
            {sessions.map((s) => {
              const isCurrent =
                currentSession?.session_id === s.session_id;
              return (
                <div
                  key={s.session_id}
                  className={cn(
                    "border rounded-xl p-4 transition-all",
                    isCurrent
                      ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                      : "border-border hover:border-primary/30",
                  )}
                >
                  {/* Header */}
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      {editingId === s.session_id ? (
                        <div className="flex items-center gap-1.5">
                          <input
                            value={editLabel}
                            onChange={(e) => setEditLabel(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleRename(s.session_id);
                              if (e.key === "Escape") setEditingId(null);
                            }}
                            autoFocus
                            className="flex-1 rounded bg-secondary px-2 py-0.5 text-sm border border-border focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                          <button
                            onClick={() => handleRename(s.session_id)}
                            className="p-0.5 text-primary hover:bg-primary/10 rounded"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="p-0.5 text-muted-foreground hover:bg-secondary rounded"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-foreground truncate">
                            {s.label || s.session_id}
                          </span>
                          {isCurrent && (
                            <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded-full bg-primary/20 text-primary font-semibold">
                              当前
                            </span>
                          )}
                        </div>
                      )}

                      {/* Meta line */}
                      <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground flex-wrap">
                        <span className="flex items-center gap-1">
                          {PHASE_ICON[s.phase] ?? <Compass className="h-3 w-3" />}
                          {PHASE_LABEL[s.phase] ?? s.phase}
                        </span>
                        {s.player_name && (
                          <span className="flex items-center gap-1">
                            <User className="h-3 w-3" />
                            {s.player_name}
                            {s.player_class && ` · ${s.player_class}`}
                            {s.player_level > 0 && ` Lv.${s.player_level}`}
                          </span>
                        )}
                        {s.teammate_count > 0 && (
                          <span className="flex items-center gap-1 text-green-400">
                            <Users className="h-3 w-3" />
                            {s.teammate_names?.join(", ") || `${s.teammate_count} 队友`}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <MessageSquare className="h-3 w-3" />
                          {s.message_count} 消息
                        </span>
                        {s.created_at && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDate(s.created_at)}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1 shrink-0">
                      {!isCurrent && (
                        <button
                          onClick={() => handleSwitch(s.session_id)}
                          disabled={loading}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-primary/15 text-primary hover:bg-primary/25 transition-colors"
                          title="切换到此团"
                        >
                          <Play className="h-3 w-3" />
                          进入
                        </button>
                      )}
                      <button
                        onClick={() => setManagingTeammates(
                          managingTeammates === s.session_id ? null : s.session_id,
                        )}
                        className={cn(
                          "p-1.5 rounded-lg transition-colors",
                          managingTeammates === s.session_id
                            ? "text-green-400 bg-green-400/10"
                            : "text-muted-foreground hover:text-foreground hover:bg-secondary",
                        )}
                        title="管理队友"
                      >
                        <Users className="h-3 w-3" />
                      </button>
                      <button
                        onClick={() => handleOpenDocs(s.session_id)}
                        className={cn(
                          "p-1.5 rounded-lg transition-colors",
                          managingDocs === s.session_id
                            ? "text-amber-400 bg-amber-400/10"
                            : "text-muted-foreground hover:text-foreground hover:bg-secondary",
                        )}
                        title="管理参考资料"
                      >
                        <BookOpen className="h-3 w-3" />
                      </button>
                      <button
                        onClick={() => {
                          setEditingId(s.session_id);
                          setEditLabel(s.label);
                        }}
                        className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                        title="重命名"
                      >
                        <Pencil className="h-3 w-3" />
                      </button>
                      <button
                        onClick={() => handleDelete(s.session_id)}
                        className="p-1.5 rounded-lg text-muted-foreground hover:text-red-400 hover:bg-red-400/10 transition-colors"
                        title="删除"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>

                  {/* Teammate management panel */}
                  {managingTeammates === s.session_id && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <div className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-1">
                        <Users className="h-3 w-3" />
                        队友管理
                      </div>
                      {/* Current teammates */}
                      {s.teammate_names && s.teammate_names.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mb-2">
                          {s.teammate_names.map((name) => (
                            <span
                              key={name}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-green-400/10 text-green-400 text-xs"
                            >
                              {name}
                              <button
                                onClick={async () => {
                                  try {
                                    await removeTeammate(s.session_id, name);
                                    flash(`已移除队友 ${name}`);
                                    refresh();
                                  } catch { /* ignore */ }
                                }}
                                className="hover:text-red-400 transition-colors"
                                title={`移除 ${name}`}
                              >
                                <UserMinus className="h-3 w-3" />
                              </button>
                            </span>
                          ))}
                        </div>
                      )}
                      {/* Add teammate */}
                      <div className="flex flex-wrap gap-1.5">
                        {characters
                          .filter(
                            (c) =>
                              !s.teammate_names?.includes(c.name) &&
                              c.name !== s.player_name,
                          )
                          .map((c) => (
                            <button
                              key={c.id}
                              onClick={async () => {
                                try {
                                  await addTeammate(s.session_id, c.id);
                                  flash(`已添加队友 ${c.name}`);
                                  refresh();
                                } catch { /* ignore */ }
                              }}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-md border border-dashed border-border text-xs text-muted-foreground hover:border-green-400/50 hover:text-green-400 transition-colors"
                            >
                              <UserPlus className="h-3 w-3" />
                              {c.name} Lv.{c.level}
                            </button>
                          ))}
                        {characters.filter(
                          (c) => !s.teammate_names?.includes(c.name) && c.name !== s.player_name,
                        ).length === 0 && (
                          <span className="text-xs text-muted-foreground">
                            没有可添加的角色卡
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Document management panel */}
                  {managingDocs === s.session_id && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <div className="flex items-center justify-between mb-3">
                        <div className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
                          <BookOpen className="h-3 w-3" />
                          参考资料管理
                        </div>
                        {docsMode === "selective" && (
                          <button
                            onClick={() => handleEnableAllDocs(s.session_id)}
                            disabled={docsSaving}
                            className="text-[10px] px-2 py-0.5 rounded-md bg-amber-400/10 text-amber-400 hover:bg-amber-400/20 transition-colors"
                          >
                            全部启用
                          </button>
                        )}
                      </div>

                      {sessionDocs.length === 0 ? (
                        <p className="text-xs text-muted-foreground py-2">
                          暂无已上传的参考资料。请先在「参考资料」标签页上传文件。
                        </p>
                      ) : (
                        <div className="space-y-1.5">
                          <p className="text-[10px] text-muted-foreground mb-2">
                            {docsMode === "all"
                              ? "当前使用全部资料。关闭不需要的资料可减少无关内容干扰。"
                              : `已启用 ${sessionDocs.filter((d) => d.enabled).length} / ${sessionDocs.length} 份资料`}
                          </p>
                          {sessionDocs.map((doc) => (
                            <div
                              key={doc.doc_id}
                              className={cn(
                                "flex items-center gap-2 px-3 py-2 rounded-lg border transition-all",
                                doc.enabled
                                  ? "border-amber-400/30 bg-amber-400/5"
                                  : "border-border bg-secondary/30 opacity-60",
                              )}
                            >
                              <button
                                onClick={() => handleToggleDoc(s.session_id, doc.doc_id, doc.enabled)}
                                disabled={docsSaving}
                                className="shrink-0 transition-colors"
                                title={doc.enabled ? "点击禁用" : "点击启用"}
                              >
                                {doc.enabled ? (
                                  <ToggleRight className="h-5 w-5 text-amber-400" />
                                ) : (
                                  <ToggleLeft className="h-5 w-5 text-muted-foreground" />
                                )}
                              </button>
                              <div className="flex-1 min-w-0">
                                <div className="text-xs font-medium text-foreground truncate">
                                  {doc.title || doc.filename}
                                </div>
                                <div className="text-[10px] text-muted-foreground">
                                  {doc.doc_type} · {doc.chunk_count} 片段
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Saved sessions */}
      {saves.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-4">
            <FolderOpen className="h-4 w-4 text-yellow-400" />
            已保存的存档
            <span className="text-xs text-muted-foreground ml-auto">
              {saves.length} 个
            </span>
          </h3>
          <div className="space-y-2">
            {saves.map((s) => (
              <div
                key={s.save_id}
                className="flex items-center gap-3 border border-border rounded-lg px-4 py-3 hover:border-primary/30 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-foreground truncate">
                    {s.label}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDate(s.created_at)}
                    </span>
                    {s.player_name && (
                      <span className="flex items-center gap-1">
                        <User className="h-3 w-3" />
                        {s.player_name}
                      </span>
                    )}
                    <span>{s.message_count} 消息</span>
                  </div>
                </div>
                <button
                  onClick={() => handleLoadSave(s.save_id)}
                  disabled={loading}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-yellow-400/15 text-yellow-400 hover:bg-yellow-400/25 transition-colors"
                >
                  <FolderOpen className="h-3 w-3" />
                  读档
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
