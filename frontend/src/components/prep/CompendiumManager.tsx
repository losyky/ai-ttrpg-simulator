"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Database, Plus, Trash2, ChevronRight, ArrowLeft, Lock, Upload, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  getCompendiumCollections,
  getCompendiumEntries,
  addCompendiumEntry,
  deleteCompendiumEntry,
  type CompendiumEntry,
} from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const COLLECTION_FIELDS: Record<string, { key: string; label: string; required?: boolean }[]> = {
  classes: [
    { key: "slug", label: "标识 (slug)", required: true },
    { key: "name", label: "英文名", required: true },
    { key: "name_cn", label: "中文名" },
    { key: "base_hp", label: "HP" },
    { key: "base_evasion", label: "闪避" },
    { key: "domains", label: "领域 (逗号分隔)" },
  ],
  _default: [
    { key: "slug", label: "标识", required: true },
    { key: "name", label: "名称", required: true },
    { key: "name_cn", label: "中文名" },
    { key: "description", label: "描述" },
  ],
};

interface CollectionInfo {
  id: string;
  label: string;
}

interface Props {
  systemId: string;
}

export default function CompendiumManager({ systemId }: Props) {
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [selectedCol, setSelectedCol] = useState<string | null>(null);
  const [entries, setEntries] = useState<CompendiumEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newEntry, setNewEntry] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");
  const [importMsg, setImportMsg] = useState("");
  const importRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const resp = await getCompendiumCollections(systemId);
        setCollections(resp.collections);
      } catch { setCollections([]); }
    })();
    setSelectedCol(null);
  }, [systemId]);

  const loadEntries = useCallback(async (col: string) => {
    setLoading(true);
    setError("");
    try {
      const data = await getCompendiumEntries(systemId, col);
      setEntries(data);
    } catch { setEntries([]); }
    setLoading(false);
  }, [systemId]);

  const handleSelectCol = useCallback((col: string) => {
    setSelectedCol(col);
    setShowAddForm(false);
    setNewEntry({});
    setFilter("");
    loadEntries(col);
  }, [loadEntries]);

  const handleAdd = useCallback(async () => {
    if (!selectedCol) return;
    setError("");
    const fields = COLLECTION_FIELDS[selectedCol] || COLLECTION_FIELDS._default;
    const missing = fields.filter(f => f.required && !newEntry[f.key]?.trim());
    if (missing.length) {
      setError(`请填写: ${missing.map(f => f.label).join("、")}`);
      return;
    }
    const entry: Record<string, unknown> = { ...newEntry };
    if (entry.domains && typeof entry.domains === "string") {
      entry.domains = (entry.domains as string).split(",").map(s => s.trim()).filter(Boolean);
    }
    if (entry.base_hp) entry.base_hp = parseInt(entry.base_hp as string) || 6;
    if (entry.base_evasion) entry.base_evasion = parseInt(entry.base_evasion as string) || 8;

    try {
      await addCompendiumEntry(systemId, selectedCol, entry);
      setShowAddForm(false);
      setNewEntry({});
      loadEntries(selectedCol);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [selectedCol, newEntry, systemId, loadEntries]);

  const handleDelete = useCallback(async (slug: string) => {
    if (!selectedCol || !confirm("确认删除此条目？")) return;
    try {
      await deleteCompendiumEntry(systemId, selectedCol, slug);
      loadEntries(selectedCol);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [selectedCol, systemId, loadEntries]);

  const handleImportFVTT = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;
    setImportMsg("导入中…");

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    try {
      const resp = await fetch(`${API}/api/compendium/${systemId}/import-fvtt-batch`, {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) throw new Error(await resp.text());
      const result = await resp.json();
      const details = Object.entries(result.by_collection || {})
        .map(([col, cnt]) => `${col}: ${cnt}`)
        .join(", ");
      setImportMsg(`导入成功! 共 ${result.total_imported} 条 (${details})`);
      if (selectedCol) loadEntries(selectedCol);
    } catch (err) {
      setImportMsg(`导入失败: ${err instanceof Error ? err.message : String(err)}`);
    }
    e.target.value = "";
  }, [systemId, selectedCol, loadEntries]);

  const filteredEntries = filter
    ? entries.filter(e =>
      (e.name || "").toLowerCase().includes(filter.toLowerCase()) ||
      (e.name_cn || "").toLowerCase().includes(filter.toLowerCase()) ||
      (e.slug || "").includes(filter.toLowerCase())
    )
    : entries;

  if (!selectedCol) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <Database className="h-5 w-5 text-primary" />
          <h3 className="text-sm font-bold text-foreground">合集数据管理</h3>
        </div>
        <p className="text-xs text-muted-foreground mb-1">
          管理车卡器和 AI 所用的合集数据。内置条目不可删除，可添加自定义条目或从 FVTT JSON 导入。
        </p>

        {/* FVTT Import */}
        <div className="flex gap-2">
          <button
            onClick={() => importRef.current?.click()}
            className={cn(
              "flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg",
              "bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-colors",
            )}
          >
            <Upload className="h-3.5 w-3.5" />
            从 FVTT JSON 导入
          </button>
          <input
            ref={importRef}
            type="file"
            accept=".json"
            multiple
            className="hidden"
            onChange={handleImportFVTT}
          />
        </div>
        {importMsg && (
          <div className={cn(
            "text-xs px-3 py-2 rounded-lg",
            importMsg.startsWith("导入成功") ? "bg-green-500/10 text-green-400" : importMsg.startsWith("导入中") ? "bg-blue-500/10 text-blue-400" : "bg-red-500/10 text-red-400",
          )}>
            {importMsg}
          </div>
        )}

        {collections.length === 0 && (
          <p className="text-xs text-muted-foreground text-center py-6">当前规则暂无可管理的合集</p>
        )}
        <div className="space-y-1.5">
          {collections.map((col) => (
            <button
              key={col.id}
              onClick={() => handleSelectCol(col.id)}
              className="w-full flex items-center justify-between p-3 rounded-lg bg-secondary/50 border border-border hover:border-primary/50 transition-colors"
            >
              <span className="text-sm font-medium text-foreground">{col.label}</span>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </button>
          ))}
        </div>
      </div>
    );
  }

  const colLabel = collections.find(c => c.id === selectedCol)?.label || selectedCol;
  const fields = COLLECTION_FIELDS[selectedCol] || COLLECTION_FIELDS._default;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <button onClick={() => setSelectedCol(null)} className="text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <h3 className="text-sm font-bold text-foreground">{colLabel}</h3>
        <span className="text-xs text-muted-foreground">({entries.length})</span>
        <div className="flex-1" />
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="flex items-center gap-1 text-xs text-primary hover:text-primary/80"
        >
          <Plus className="h-3.5 w-3.5" /> 新增
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-secondary border border-border text-foreground text-sm"
          placeholder="搜索…"
        />
      </div>

      {showAddForm && (
        <div className="p-3 rounded-lg bg-primary/5 border border-primary/20 space-y-2">
          {fields.map((f) => (
            <div key={f.key}>
              <label className="block text-xs text-muted-foreground mb-0.5">
                {f.label}
                {f.required && <span className="text-red-400 ml-0.5">*</span>}
              </label>
              <input
                value={newEntry[f.key] || ""}
                onChange={(e) => setNewEntry(prev => ({ ...prev, [f.key]: e.target.value }))}
                className="w-full px-2.5 py-1.5 rounded-lg bg-secondary border border-border text-foreground text-sm"
                placeholder={f.label}
              />
            </div>
          ))}
          {error && <p className="text-xs text-red-400">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button onClick={() => { setShowAddForm(false); setNewEntry({}); setError(""); }} className="text-xs text-muted-foreground hover:text-foreground px-3 py-1 rounded-lg">
              取消
            </button>
            <button onClick={handleAdd} className="text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:bg-primary/90">
              添加
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-xs text-muted-foreground text-center py-4">加载中…</div>
      ) : (
        <div className="space-y-1 max-h-[60vh] overflow-y-auto">
          {filteredEntries.map((entry) => (
            <div
              key={entry.slug + (entry.fvtt_id || "")}
              className={cn(
                "flex items-center gap-2 p-2 rounded-lg border text-sm",
                entry._default
                  ? "bg-secondary/30 border-border"
                  : "bg-primary/5 border-primary/20",
              )}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-medium text-foreground truncate">{entry.name_cn || entry.name || entry.slug}</span>
                  {entry.name && entry.name_cn && (
                    <span className="text-xs text-muted-foreground">({entry.name})</span>
                  )}
                  {entry._default && <Lock className="h-3 w-3 text-muted-foreground/50 flex-shrink-0" />}
                </div>
                {(entry.description || entry.trait) && (
                  <div className="text-xs text-muted-foreground truncate mt-0.5">{String(entry.description || entry.trait).slice(0, 100)}</div>
                )}
              </div>
              {!entry._default && (
                <button
                  onClick={() => handleDelete(entry.slug)}
                  className="text-muted-foreground hover:text-red-400 transition-colors p-1 flex-shrink-0"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          ))}
          {filteredEntries.length === 0 && (
            <div className="text-xs text-muted-foreground text-center py-4">
              {filter ? "没有匹配的条目" : "暂无条目"}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
