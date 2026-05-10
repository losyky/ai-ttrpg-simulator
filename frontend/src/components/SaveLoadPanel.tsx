"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Save,
  FolderOpen,
  Download,
  Upload,
  Trash2,
  FileText,
  Clock,
  User,
  ChevronDown,
  ChevronUp,
  X,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import {
  listSaves,
  createSave,
  loadSave,
  deleteSave,
  getDownloadSaveUrl,
  getExportLogUrl,
  getLogPreview,
  importSaveFile,
  type SaveInfo,
} from "@/lib/api";
import type { SessionState, ChatMessage } from "@/lib/types";
import { cn, hydrateHistory } from "@/lib/utils";

interface SaveLoadPanelProps {
  session: SessionState | null;
  onSessionLoaded: (state: SessionState, history: ChatMessage[]) => void;
  systemId?: string;
}

export default function SaveLoadPanel({
  session,
  onSessionLoaded,
  systemId,
}: SaveLoadPanelProps) {
  const [saves, setSaves] = useState<SaveInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [label, setLabel] = useState("");
  const [expandedSave, setExpandedSave] = useState<string | null>(null);
  const [previewMd, setPreviewMd] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const importRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      const list = await listSaves(systemId);
      setSaves(list);
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

  const handleSave = async () => {
    if (!session) {
      flash("请先开始一个游戏会话");
      return;
    }
    setSaving(true);
    try {
      const info = await createSave(session.session_id, label);
      flash(`已保存: ${info.label}`);
      setLabel("");
      refresh();
    } catch (err) {
      flash(`保存失败: ${err instanceof Error ? err.message : err}`);
    } finally {
      setSaving(false);
    }
  };

  const handleLoad = async (saveId: string) => {
    if (!confirm("加载存档将替换当前会话，是否继续？")) return;
    setLoading(true);
    try {
      const state = await loadSave(saveId);
      const { getSaveHistory } = await import("@/lib/api");
      const rawHistory = await getSaveHistory(saveId);
      const history = hydrateHistory(rawHistory, "loaded");
      onSessionLoaded(state, history);
      flash("存档已加载");
    } catch (err) {
      flash(`加载失败: ${err instanceof Error ? err.message : err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (saveId: string) => {
    if (!confirm("确认删除此存档？")) return;
    try {
      await deleteSave(saveId);
      flash("已删除");
      refresh();
    } catch (err) {
      flash(`删除失败: ${err instanceof Error ? err.message : err}`);
    }
  };

  const handleExportLog = async () => {
    if (!session) {
      flash("请先开始一个游戏会话");
      return;
    }
    window.open(getExportLogUrl(session.session_id), "_blank");
  };

  const handlePreviewLog = async () => {
    if (!session) return;
    try {
      const data = await getLogPreview(session.session_id);
      setPreviewMd(data.markdown);
      setShowPreview(true);
    } catch (err) {
      flash(`预览失败: ${err instanceof Error ? err.message : err}`);
    }
  };

  const handleImportSave = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await importSaveFile(file);
      flash(`导入成功: ${result.save_id} (${result.message_count} 消息)`);
      refresh();
    } catch (err) {
      flash(`导入失败: ${err instanceof Error ? err.message : err}`);
    }
    e.target.value = "";
  };

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString("zh-CN", {
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
      {/* Save current session */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-4">
          <Save className="h-4 w-4 text-primary" />
          保存当前会话
        </h3>
        <div className="flex gap-2">
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="存档备注（可选）"
            className="flex-1 rounded-lg bg-secondary px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground border border-border focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <button
            onClick={handleSave}
            disabled={!session || saving}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
              session
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "bg-secondary text-muted-foreground cursor-not-allowed",
            )}
          >
            <Save className="h-3.5 w-3.5" />
            {saving ? "保存中..." : "存档"}
          </button>
        </div>

        {/* Export log buttons */}
        <div className="flex gap-2 mt-3">
          <button
            onClick={handlePreviewLog}
            disabled={!session}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors border border-border"
          >
            <FileText className="h-3.5 w-3.5" />
            预览团 Log
          </button>
          <button
            onClick={handleExportLog}
            disabled={!session}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors border border-border"
          >
            <Download className="h-3.5 w-3.5" />
            导出团 Log (Markdown)
          </button>
          <button
            onClick={() => importRef.current?.click()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors border border-border ml-auto"
          >
            <Upload className="h-3.5 w-3.5" />
            导入存档
          </button>
          <input
            ref={importRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleImportSave}
          />
        </div>
      </div>

      {/* Status */}
      {statusMsg && (
        <div className="text-sm text-primary bg-primary/10 border border-primary/20 rounded-lg px-4 py-2">
          {statusMsg}
        </div>
      )}

      {/* Log preview modal */}
      {showPreview && previewMd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl max-w-3xl w-full max-h-[80vh] flex flex-col m-4">
            <div className="flex items-center justify-between px-5 py-3 border-b border-border">
              <h3 className="text-sm font-semibold">团 Log 预览</h3>
              <div className="flex gap-2">
                <button
                  onClick={handleExportLog}
                  className="flex items-center gap-1 px-3 py-1 rounded-lg text-xs bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <Download className="h-3 w-3" />
                  下载
                </button>
                <button
                  onClick={() => setShowPreview(false)}
                  className="p-1 rounded-lg hover:bg-secondary"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-4 prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{previewMd}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      {/* Save list */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-4">
          <FolderOpen className="h-4 w-4 text-yellow-400" />
          存档列表
          <span className="text-xs text-muted-foreground ml-auto">
            {saves.length} 个存档
          </span>
        </h3>

        {saves.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            暂无存档。开始游戏后可以随时保存进度。
          </p>
        ) : (
          <div className="space-y-2">
            {saves.map((s) => (
              <div
                key={s.save_id}
                className="border border-border rounded-lg overflow-hidden transition-colors hover:border-primary/30"
              >
                {/* Save header */}
                <div
                  className="flex items-center gap-3 px-4 py-3 cursor-pointer"
                  onClick={() =>
                    setExpandedSave(
                      expandedSave === s.save_id ? null : s.save_id,
                    )
                  }
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-foreground truncate">
                      {s.label || s.save_id}
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
                      {s.phase && (
                        <span className="text-primary/80">{s.phase}</span>
                      )}
                    </div>
                  </div>
                  {expandedSave === s.save_id ? (
                    <ChevronUp className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>

                {/* Expanded actions */}
                {expandedSave === s.save_id && (
                  <div className="px-4 pb-3 flex gap-2 border-t border-border/50 pt-2">
                    <button
                      onClick={() => handleLoad(s.save_id)}
                      disabled={loading}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-primary/20 text-primary hover:bg-primary/30 transition-colors"
                    >
                      <FolderOpen className="h-3.5 w-3.5" />
                      {loading ? "加载中..." : "读取存档"}
                    </button>
                    <a
                      href={getDownloadSaveUrl(s.save_id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors border border-border"
                    >
                      <Download className="h-3.5 w-3.5" />
                      下载 JSON
                    </a>
                    <button
                      onClick={() => handleDelete(s.save_id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-red-400 hover:bg-red-400/10 transition-colors ml-auto border border-red-400/20"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      删除
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
