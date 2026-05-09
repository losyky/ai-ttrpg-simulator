"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Upload,
  FileText,
  Trash2,
  Search,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import {
  listDocuments,
  uploadDocumentWithProgress,
  deleteDocument,
  searchDocuments,
} from "@/lib/api";
import type { DocumentInfo } from "@/lib/types";

export default function MaterialsPanel({ systemId }: { systemId?: string }) {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<
    { section: string; content: string }[]
  >([]);
  const [msg, setMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const docs = await listDocuments(systemId);
      setDocuments(docs);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [systemId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setUploading(true);
      setUploadProgress(0);
      setMsg("");
      try {
        const info = await uploadDocumentWithProgress(file, (pct) =>
          setUploadProgress(pct), systemId,
        );
        setMsg(
          `「${info.filename}」已上传（${info.chunk_count} 个片段，类型: ${info.doc_type}）`,
        );
        refresh();
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : String(err);
        setMsg(`上传失败: ${errMsg}`);
      } finally {
        setUploading(false);
        setUploadProgress(0);
        e.target.value = "";
      }
    },
    [refresh, systemId],
  );

  const handleDelete = useCallback(
    async (docId: string) => {
      try {
        await deleteDocument(docId);
        refresh();
      } catch {
        /* ignore */
      }
    },
    [refresh],
  );

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;
    try {
      const results = (await searchDocuments(searchQuery, undefined, systemId)) as {
        section: string;
        content: string;
      }[];
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    }
  }, [searchQuery, systemId]);

  return (
    <div className="space-y-6">
      {/* Upload area */}
      <div
        className={cn(
          "border-2 border-dashed border-border rounded-xl p-8 text-center",
          "hover:border-primary/50 transition-colors cursor-pointer",
          uploading && "opacity-50 pointer-events-none",
        )}
        onClick={() => fileRef.current?.click()}
      >
        <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-3" />
        <p className="text-sm text-muted-foreground">
          点击或拖放上传文件（JSON / MD / PDF / TXT）
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          支持 FVTT JournalEntry、模组剧本、规则资料等
        </p>
        <input
          ref={fileRef}
          type="file"
          accept=".json,.md,.markdown,.pdf,.txt"
          className="hidden"
          onChange={handleUpload}
        />
        {uploading && (
          <div className="mt-3 w-64 mx-auto">
            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
              <span>上传中...</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {msg && (
        <div className="text-sm text-accent bg-accent/10 rounded-lg px-4 py-2">
          {msg}
        </div>
      )}

      {/* Document list */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-foreground">
            已上传资料 ({documents.length})
          </h3>
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

        {documents.length === 0 ? (
          <p className="text-sm text-muted-foreground">还没有上传任何资料</p>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.doc_id}
                className="flex items-center gap-3 bg-secondary/50 rounded-lg px-4 py-3"
              >
                <FileText className="h-4 w-4 text-primary shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-foreground truncate">
                    {doc.filename}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {doc.doc_type} · {doc.chunk_count} 片段
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(doc.doc_id)}
                  className="p-1.5 rounded-lg hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Search */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-3">搜索资料</h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="搜索关键词..."
            className={cn(
              "flex-1 rounded-lg bg-secondary border border-border px-4 py-2 text-sm",
              "text-foreground placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-ring",
            )}
          />
          <button
            onClick={handleSearch}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm hover:bg-primary/90 transition-colors"
          >
            <Search className="h-4 w-4" />
          </button>
        </div>

        {searchResults.length > 0 && (
          <div className="mt-3 space-y-2">
            {searchResults.map((r, i) => (
              <div
                key={i}
                className="bg-secondary/50 rounded-lg px-4 py-3 text-sm"
              >
                <div className="text-xs text-primary mb-1">{r.section}</div>
                <div className="text-muted-foreground prose prose-invert prose-sm max-w-none prose-p:my-1">
                  <ReactMarkdown>{r.content}</ReactMarkdown>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
