"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  UserCircle,
  Trash2,
  RefreshCw,
  Heart,
  Shield,
  ExternalLink,
  Plus,
  Wand2,
  PenTool,
  Database,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  listCharacters,
  importCharacter,
  deleteCharacter,
  type CharacterListItem,
} from "@/lib/api";
import CharacterSheetEditor from "./CharacterSheetEditor";
import DHCharacterSheetEditor from "./DHCharacterSheetEditor";
import SWADECharacterSheetEditor from "./SWADECharacterSheetEditor";
import CharBuilderWizard from "../charbuilder/CharBuilderWizard";
import DHCharBuilderWizard from "../charbuilder-dh/DHCharBuilderWizard";
import SWADECharBuilderWizard from "../charbuilder-swade/SWADECharBuilderWizard";
import CompendiumManager from "./CompendiumManager";

type ViewMode = "list" | "editor" | "wizard" | "mode-select";

export default function CharactersPanel({ systemId }: { systemId?: string }) {
  const [characters, setCharacters] = useState<CharacterListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [showCompendium, setShowCompendium] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const chars = await listCharacters(systemId);
      setCharacters(chars);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [systemId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleImport = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setMsg("");
      try {
        const char = await importCharacter(file, systemId);
        setMsg(`角色「${char.name}」已导入`);
        refresh();
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : String(err);
        setMsg(`导入失败: ${errMsg}`);
      }
      e.target.value = "";
    },
    [refresh, systemId],
  );

  const handleDelete = useCallback(
    async (charId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      if (!confirm("确认删除此角色卡？")) return;
      try {
        await deleteCharacter(charId);
        if (selectedId === charId) setSelectedId(null);
        setCharacters((prev) => prev.filter((c) => c.id !== charId));
        setMsg("角色卡已删除");
        setTimeout(() => setMsg(""), 2000);
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : String(err);
        setMsg(`删除失败: ${errMsg}`);
      }
    },
    [selectedId],
  );

  // Show character editor (routed by system)
  if (selectedId && viewMode === "list") {
    const editorProps = {
      characterId: selectedId,
      onBack: () => { setSelectedId(null); refresh(); },
    };
    if (systemId === "daggerheart") {
      return <DHCharacterSheetEditor {...editorProps} />;
    }
    if (systemId === "swade") {
      return <SWADECharacterSheetEditor {...editorProps} />;
    }
    return <CharacterSheetEditor {...editorProps} />;
  }

  // Show character builder wizard (routed by system)
  if (viewMode === "wizard") {
    const wizardProps = {
      onComplete: () => { setViewMode("list"); refresh(); },
      onCancel: () => setViewMode("list"),
    };
    if (systemId === "daggerheart") {
      return <DHCharBuilderWizard {...wizardProps} />;
    }
    if (systemId === "swade") {
      return <SWADECharBuilderWizard {...wizardProps} />;
    }
    return <CharBuilderWizard {...wizardProps} />;
  }

  // Mode selection dialog
  if (viewMode === "mode-select") {
    return (
      <div className="space-y-6 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-foreground">新建角色</h3>
          <button
            onClick={() => setViewMode("list")}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            取消
          </button>
        </div>
        <div className="grid grid-cols-1 gap-4">
          <button
            onClick={() => setViewMode("wizard")}
            className={cn(
              "flex items-start gap-4 p-6 rounded-xl border-2 border-border",
              "hover:border-primary/50 hover:bg-secondary/50 transition-all text-left",
            )}
          >
            <PenTool className="h-8 w-8 text-blue-400 mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-foreground mb-1">手动创建</h4>
              <p className="text-sm text-muted-foreground">
                {systemId === "daggerheart"
                  ? "通过分步向导选择族裔、社群、职业、特质，创建 Daggerheart 角色"
                  : systemId === "swade"
                    ? "通过分步向导设置属性骰、专长、负赘，创建七物语角色"
                    : "通过分步向导手动选择族裔、职业、专长等，类似 FVTT 的角色创建流程"}
              </p>
            </div>
          </button>
          <button
            onClick={() => {
              setViewMode("list");
              // Store intent globally so PrepChat can pick it up on mount
              (window as any).__pendingAiCharbuilder = true;
              // Switch to chat tab
              window.dispatchEvent(new CustomEvent("switch-prep-tab", { detail: "chat" }));
            }}
            className={cn(
              "flex items-start gap-4 p-6 rounded-xl border-2 border-border",
              "hover:border-primary/50 hover:bg-secondary/50 transition-all text-left",
            )}
          >
            <Wand2 className="h-8 w-8 text-purple-400 mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-foreground mb-1">AI 引导创建</h4>
              <p className="text-sm text-muted-foreground">
                通过和团外 AI 对话，由 AI 引导你完成建卡流程，适合新手或想偷懒的冒险者
              </p>
            </div>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* New Character + Import */}
      <div className="flex gap-3">
        <button
          onClick={() => setViewMode("mode-select")}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 py-3 rounded-xl",
            "bg-primary/10 border-2 border-primary/30 text-primary",
            "hover:bg-primary/20 hover:border-primary/50 transition-all",
          )}
        >
          <Plus className="h-5 w-5" />
          <span className="text-sm font-medium">新建角色</span>
        </button>
        <button
          onClick={() => fileRef.current?.click()}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 py-3 rounded-xl",
            "border-2 border-dashed border-border text-muted-foreground",
            "hover:border-primary/50 hover:text-foreground transition-all",
          )}
        >
          <UserCircle className="h-5 w-5" />
          <span className="text-sm font-medium">导入 FVTT JSON</span>
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".json"
          multiple
          className="hidden"
          onChange={handleImport}
        />
      </div>

      {msg && (
        <div className="text-sm text-accent bg-accent/10 rounded-lg px-4 py-2">
          {msg}
        </div>
      )}

      {/* Character list */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-foreground">
            角色卡 ({characters.length})
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

        {characters.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            还没有角色卡，点击上方按钮新建或导入
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {characters.map((char) => (
              <div
                key={char.id}
                onClick={() => setSelectedId(char.id)}
                className={cn(
                  "bg-secondary/50 rounded-xl p-4 border border-border/50",
                  "cursor-pointer hover:border-primary/40 hover:bg-secondary/70 transition-all group",
                )}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-foreground flex items-center gap-1.5">
                      {char.name}
                      <ExternalLink className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {char.ancestry} · {char.character_class} · Lv.{char.level}
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(char.id, e)}
                    className="p-1 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="flex items-center gap-1 text-red-400">
                    <Heart className="h-3 w-3" />
                    {char.hp}/{char.max_hp}
                  </span>
                  <span className="flex items-center gap-1 text-blue-400">
                    <Shield className="h-3 w-3" />
                    Lv.{char.level}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Compendium Data Management */}
      {systemId && (
        <div className="border-t border-border/50 pt-4">
          <button
            onClick={() => setShowCompendium((v) => !v)}
            className="flex items-center gap-2 text-sm font-semibold text-foreground hover:text-primary transition-colors w-full"
          >
            <Database className="h-4 w-4" />
            合集数据管理
            <ChevronDown className={cn("h-3.5 w-3.5 transition-transform ml-auto", showCompendium && "rotate-180")} />
          </button>
          {showCompendium && (
            <div className="mt-3 p-4 rounded-xl bg-card border border-border">
              <CompendiumManager systemId={systemId} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
