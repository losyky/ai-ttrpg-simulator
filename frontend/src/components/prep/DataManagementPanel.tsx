"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getDataStatus,
  resetPf2eData,
  updatePf2eData,
  importFvttPacks,
} from "@/lib/api";
import {
  Database,
  RefreshCw,
  Upload,
  CheckCircle,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface DataManagementPanelProps {
  systemId: string;
}

export default function DataManagementPanel({ systemId }: DataManagementPanelProps) {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // PF2e update form
  const [pf2ePacksPath, setPf2ePacksPath] = useState("");
  const [pf2eTransPath, setPf2eTransPath] = useState("");

  // Generic FVTT import form
  const [fvttSystemPath, setFvttSystemPath] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getDataStatus();
      setStatus(data);
    } catch {
      setMessage({ type: "error", text: "无法获取数据状态" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleResetPf2e = async () => {
    setActionLoading("reset-pf2e");
    setMessage(null);
    try {
      const res = await resetPf2eData("all");
      setMessage({ type: "success", text: `PF2e 数据已重置: ${JSON.stringify(res.results)}` });
      refresh();
    } catch (e: unknown) {
      setMessage({ type: "error", text: `重置失败: ${e}` });
    } finally {
      setActionLoading(null);
    }
  };

  const handleUpdatePf2e = async () => {
    if (!pf2ePacksPath) {
      setMessage({ type: "error", text: "请输入 PF2e FVTT 系统路径" });
      return;
    }
    setActionLoading("update-pf2e");
    setMessage(null);
    try {
      const res = await updatePf2eData(pf2ePacksPath, pf2eTransPath || undefined);
      setMessage({ type: "success", text: `PF2e 数据已更新: ${JSON.stringify(res.results)}` });
      refresh();
    } catch (e: unknown) {
      setMessage({ type: "error", text: `更新失败: ${e}` });
    } finally {
      setActionLoading(null);
    }
  };

  const handleFvttImport = async () => {
    if (!fvttSystemPath) {
      setMessage({ type: "error", text: "请输入 FVTT 系统路径" });
      return;
    }
    setActionLoading("fvtt-import");
    setMessage(null);
    try {
      const res = await importFvttPacks(systemId, fvttSystemPath);
      setMessage({ type: "success", text: `${systemId} 数据已导入: ${JSON.stringify(res.result)}` });
      refresh();
    } catch (e: unknown) {
      setMessage({ type: "error", text: `导入失败: ${e}` });
    } finally {
      setActionLoading(null);
    }
  };

  const pf2eStatus = status?.pf2e as Record<string, unknown> | undefined;
  const dhStatus = status?.daggerheart as Record<string, unknown> | undefined;
  const swadeStatus = status?.swade as Record<string, unknown> | undefined;

  const currentStatus = systemId === "pf2e" ? pf2eStatus
    : systemId === "daggerheart" ? dhStatus
    : systemId === "swade" ? swadeStatus
    : null;

  return (
    <div className="space-y-6 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Database className="h-5 w-5" />
          数据管理
        </h2>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-md bg-muted hover:bg-muted/80 transition-colors"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          刷新状态
        </button>
      </div>

      {message && (
        <div
          className={cn(
            "flex items-center gap-2 p-3 rounded-lg text-sm",
            message.type === "success" ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400",
          )}
        >
          {message.type === "success" ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {message.text}
        </div>
      )}

      {/* Current system status */}
      {currentStatus && (
        <div className="border border-border rounded-lg p-4 space-y-3">
          <h3 className="font-medium text-sm text-muted-foreground">
            当前系统: {systemId.toUpperCase()}
          </h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {Object.entries(currentStatus).map(([key, val]) => {
              if (typeof val === "object" && val !== null) {
                return (
                  <div key={key} className="col-span-2">
                    <span className="text-muted-foreground">{key}:</span>
                    <div className="ml-4 grid grid-cols-2 gap-1 mt-1">
                      {Object.entries(val as Record<string, unknown>).map(([k, v]) => (
                        <span key={k} className="text-xs">
                          {k}: <strong>{String(v)}</strong>
                        </span>
                      ))}
                    </div>
                  </div>
                );
              }
              return (
                <div key={key}>
                  <span className="text-muted-foreground">{key}:</span>{" "}
                  <strong>{String(val)}</strong>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* PF2e specific controls */}
      {systemId === "pf2e" && (
        <div className="space-y-4">
          <div className="border border-border rounded-lg p-4 space-y-3">
            <h3 className="font-medium">重置为内置默认数据</h3>
            <p className="text-sm text-muted-foreground">
              将 PF2e 车卡器和规则数据库恢复为出厂默认状态（包含完整的中文翻译）
            </p>
            <button
              onClick={handleResetPf2e}
              disabled={actionLoading !== null}
              className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {actionLoading === "reset-pf2e" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              重置 PF2e 数据
            </button>
          </div>

          <div className="border border-border rounded-lg p-4 space-y-3">
            <h3 className="font-medium">从外部 FVTT 源更新</h3>
            <p className="text-sm text-muted-foreground">
              从本地 FVTT PF2e 系统目录重新导入数据（用于更新到新版本）
            </p>
            <div className="space-y-2">
              <input
                type="text"
                value={pf2ePacksPath}
                onChange={(e) => setPf2ePacksPath(e.target.value)}
                placeholder="PF2e 系统路径 (如 D:\FoundryVTT\Data\systems\pf2e)"
                className="w-full px-3 py-2 rounded-md bg-input border border-border text-sm"
              />
              <input
                type="text"
                value={pf2eTransPath}
                onChange={(e) => setPf2eTransPath(e.target.value)}
                placeholder="中文翻译路径 (可选，如 D:\...\pf2e_compendium_chn\compendium)"
                className="w-full px-3 py-2 rounded-md bg-input border border-border text-sm"
              />
            </div>
            <button
              onClick={handleUpdatePf2e}
              disabled={actionLoading !== null}
              className="flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-accent-foreground hover:bg-accent/90 transition-colors disabled:opacity-50"
            >
              {actionLoading === "update-pf2e" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              更新 PF2e 数据
            </button>
          </div>
        </div>
      )}

      {/* DH / SWADE import */}
      {(systemId === "daggerheart" || systemId === "swade") && (
        <div className="border border-border rounded-lg p-4 space-y-3">
          <h3 className="font-medium">从 FVTT 系统导入</h3>
          <p className="text-sm text-muted-foreground">
            从本地 FVTT {systemId === "daggerheart" ? "Daggerheart" : "SWADE"} 系统目录导入合集数据
          </p>
          <input
            type="text"
            value={fvttSystemPath}
            onChange={(e) => setFvttSystemPath(e.target.value)}
            placeholder={`FVTT 系统路径 (如 D:\\FoundryVTT\\Data\\systems\\${systemId === "swade" ? "swade" : "daggerheart"})`}
            className="w-full px-3 py-2 rounded-md bg-input border border-border text-sm"
          />
          <button
            onClick={handleFvttImport}
            disabled={actionLoading !== null}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-accent-foreground hover:bg-accent/90 transition-colors disabled:opacity-50"
          >
            {actionLoading === "fvtt-import" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            导入数据
          </button>
        </div>
      )}

      {/* All systems status overview */}
      {status && (
        <div className="border border-border rounded-lg p-4 space-y-3">
          <h3 className="font-medium text-sm text-muted-foreground">所有系统数据状态</h3>
          <div className="grid gap-3">
            {[
              { id: "pf2e", label: "Pathfinder 2e", data: pf2eStatus },
              { id: "daggerheart", label: "Daggerheart", data: dhStatus },
              { id: "swade", label: "SWADE/七物语", data: swadeStatus },
            ].map(({ id, label, data }) => (
              <div key={id} className="flex items-center justify-between text-sm">
                <span className={cn(id === systemId && "font-medium")}>{label}</span>
                <span className="text-muted-foreground">
                  {data ? (
                    Object.entries(data)
                      .filter(([, v]) => typeof v !== "object")
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(" | ")
                  ) : (
                    "加载中..."
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
