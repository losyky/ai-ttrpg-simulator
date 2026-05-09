"use client";

import { useCallback, useEffect, useState } from "react";
import {
  FolderOpen,
  FileText,
  Folder,
  ChevronRight,
  ArrowLeft,
  Trash2,
  Eye,
  X,
} from "lucide-react";
import {
  listWorkspaceFiles,
  readWorkspaceFile,
  deleteWorkspaceFile,
  type WorkspaceFile,
} from "@/lib/api";
import { cn } from "@/lib/utils";

export default function WorkspacePanel({ systemId }: { systemId?: string }) {
  const [currentPath, setCurrentPath] = useState("");
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [viewFile, setViewFile] = useState<{
    path: string;
    content: string;
  } | null>(null);

  const refresh = useCallback(async () => {
    try {
      const list = await listWorkspaceFiles(currentPath, systemId);
      setFiles(list);
    } catch {
      setFiles([]);
    }
  }, [currentPath, systemId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const navigateTo = (p: string) => {
    setCurrentPath(p);
    setViewFile(null);
  };

  const goUp = () => {
    const parts = currentPath.split("/").filter(Boolean);
    parts.pop();
    setCurrentPath(parts.join("/"));
    setViewFile(null);
  };

  const handleOpen = async (f: WorkspaceFile) => {
    if (f.is_dir) {
      navigateTo(f.path);
    } else {
      try {
        const data = await readWorkspaceFile(f.path, systemId);
        setViewFile({ path: f.path, content: data.content });
      } catch {
        /* ignore */
      }
    }
  };

  const handleDelete = async (f: WorkspaceFile) => {
    const label = f.is_dir ? `目录 "${f.name}" 及其所有内容` : `文件 "${f.name}"`;
    if (!confirm(`确认删除 ${label}？`)) return;
    try {
      await deleteWorkspaceFile(f.path, systemId);
      refresh();
    } catch {
      /* ignore */
    }
  };

  const formatSize = (bytes?: number) => {
    if (bytes === undefined) return "";
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  const breadcrumbs = currentPath
    ? currentPath.split("/").filter(Boolean)
    : [];

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-foreground flex items-center gap-2 mb-1">
          <FolderOpen className="h-5 w-5 text-primary" />
          AI 工作区
        </h2>
        <p className="text-xs text-muted-foreground">
          团外 AI 助手的专属文件夹。AI 可以在此读写文件、保存笔记和规划。
        </p>
      </div>

      {/* Breadcrumbs */}
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <button
          onClick={() => navigateTo("")}
          className="hover:text-primary transition-colors font-medium"
        >
          workspace
        </button>
        {breadcrumbs.map((part, i) => (
          <span key={i} className="flex items-center gap-1">
            <ChevronRight className="h-3 w-3" />
            <button
              onClick={() =>
                navigateTo(breadcrumbs.slice(0, i + 1).join("/"))
              }
              className="hover:text-primary transition-colors"
            >
              {part}
            </button>
          </span>
        ))}
      </div>

      {/* File viewer */}
      {viewFile && (
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 bg-secondary/30 border-b border-border">
            <FileText className="h-3.5 w-3.5 text-primary" />
            <span className="text-xs font-medium text-foreground flex-1">
              {viewFile.path}
            </span>
            <button
              onClick={() => setViewFile(null)}
              className="p-0.5 rounded hover:bg-secondary text-muted-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <pre className="p-3 text-xs text-foreground/80 max-h-64 overflow-auto bg-card whitespace-pre-wrap font-mono">
            {viewFile.content}
          </pre>
        </div>
      )}

      {/* File list */}
      <div className="border border-border rounded-lg divide-y divide-border/50">
        {currentPath && (
          <button
            onClick={goUp}
            className="flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-secondary/30 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">..</span>
          </button>
        )}

        {files.length === 0 && !currentPath && (
          <div className="px-4 py-8 text-center">
            <FolderOpen className="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
            <p className="text-xs text-muted-foreground">
              工作区为空。在团外聊天中让 AI 创建文件，或上传文件到此处。
            </p>
          </div>
        )}

        {files.map((f) => (
          <div
            key={f.path}
            className="group flex items-center gap-2 px-3 py-2 hover:bg-secondary/30 transition-colors"
          >
            {f.is_dir ? (
              <Folder className="h-3.5 w-3.5 text-yellow-400" />
            ) : (
              <FileText className="h-3.5 w-3.5 text-blue-400" />
            )}
            <button
              onClick={() => handleOpen(f)}
              className="flex-1 text-left text-xs text-foreground hover:text-primary transition-colors"
            >
              {f.name}
            </button>
            {!f.is_dir && (
              <span className="text-[10px] text-muted-foreground">
                {formatSize(f.size)}
              </span>
            )}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              {!f.is_dir && (
                <button
                  onClick={() => handleOpen(f)}
                  className="p-0.5 rounded text-muted-foreground hover:text-primary"
                  title="查看"
                >
                  <Eye className="h-3 w-3" />
                </button>
              )}
              <button
                onClick={() => handleDelete(f)}
                className="p-0.5 rounded text-muted-foreground hover:text-red-400"
                title="删除"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
