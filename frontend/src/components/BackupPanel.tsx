"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Archive,
  Download,
  Upload,
  FolderOpen,
  FileText,
  Users,
  Zap,
  Wrench,
  Save,
  HardDrive,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import {
  getBackupStats,
  getBackupDownloadUrl,
  importBackup,
  type BackupStats,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const FOLDER_META: Record<string, { label: string; icon: typeof FileText }> = {
  uploads: { label: "上传资料", icon: FileText },
  characters: { label: "角色卡", icon: Users },
  skills: { label: "Skills", icon: Zap },
  custom_tools: { label: "自定义工具", icon: Wrench },
  saves: { label: "存档", icon: Save },
  workspace: { label: "工作区", icon: FolderOpen },
  game_db: { label: "数据库", icon: HardDrive },
};

export default function BackupPanel() {
  const [stats, setStats] = useState<BackupStats | null>(null);
  const [importing, setImporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadStats = useCallback(async () => {
    try {
      const s = await getBackupStats();
      setStats(s);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const handleExport = () => {
    window.open(getBackupDownloadUrl(), "_blank");
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setProgress(0);
    setResult(null);

    try {
      const res = await importBackup(file, (pct) => setProgress(pct));
      const totalRestored = Object.values(res.restored).reduce(
        (sum, v) => sum + (typeof v === "number" ? v : 1),
        0,
      );
      setResult({
        type: "success",
        message: `成功恢复 ${totalRestored} 个文件${res.errors.length > 0 ? `（${res.errors.length} 个错误）` : ""}`,
      });
      loadStats();
    } catch (err) {
      setResult({
        type: "error",
        message: err instanceof Error ? err.message : "导入失败",
      });
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground flex items-center gap-2 mb-1">
          <Archive className="h-5 w-5 text-primary" />
          数据备份管理
        </h2>
        <p className="text-xs text-muted-foreground">
          导出/导入所有用户数据（资料、角色卡、Skills、工具、工作区、存档）
        </p>
      </div>

      {/* Current data stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {Object.entries(stats).map(([key, val]) => {
            const meta = FOLDER_META[key];
            if (!meta) return null;
            const Icon = meta.icon;
            const info = val as { count?: number; size_mb?: number; exists?: boolean };
            return (
              <div
                key={key}
                className="bg-secondary/30 rounded-lg p-3 border border-border/50"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Icon className="h-3.5 w-3.5 text-primary" />
                  <span className="text-xs font-medium text-foreground">
                    {meta.label}
                  </span>
                </div>
                <div className="text-lg font-semibold text-foreground">
                  {info.count ?? (info.exists ? "✓" : "—")}
                </div>
                {info.size_mb !== undefined && (
                  <div className="text-[10px] text-muted-foreground">
                    {info.size_mb} MB
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          onClick={handleExport}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 font-medium text-sm transition-colors"
        >
          <Download className="h-4 w-4" />
          导出完整备份
        </button>

        <button
          onClick={() => fileRef.current?.click()}
          disabled={importing}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border font-medium text-sm transition-colors",
            importing
              ? "border-primary/30 text-muted-foreground cursor-wait"
              : "border-border text-foreground hover:bg-secondary hover:border-primary/30",
          )}
        >
          <Upload className="h-4 w-4" />
          {importing ? "导入中..." : "导入备份"}
        </button>

        <input
          ref={fileRef}
          type="file"
          accept=".zip"
          className="hidden"
          onChange={handleImport}
        />
      </div>

      {/* Progress bar */}
      {importing && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>上传进度</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Result message */}
      {result && (
        <div
          className={cn(
            "flex items-start gap-2 px-4 py-3 rounded-lg text-sm",
            result.type === "success"
              ? "bg-green-500/10 text-green-400 border border-green-500/20"
              : "bg-red-500/10 text-red-400 border border-red-500/20",
          )}
        >
          {result.type === "success" ? (
            <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          )}
          {result.message}
        </div>
      )}

      <div className="text-[10px] text-muted-foreground border-t border-border/50 pt-3">
        备份包含：上传的资料文件、角色卡 JSON、AI Skills、自定义工具定义、
        游戏存档、工作区文件，以及知识库数据库。导入时会覆盖同名文件。
      </div>
    </div>
  );
}
