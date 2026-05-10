"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ChatBubble from "@/components/ChatBubble";
import ChatInput from "@/components/ChatInput";
import Sidebar from "@/components/Sidebar";
import MaterialsPanel from "@/components/prep/MaterialsPanel";
import CharactersPanel from "@/components/prep/CharactersPanel";
import SkillsPanel from "@/components/prep/SkillsPanel";
import ToolsPanel from "@/components/prep/ToolsPanel";
import PrepChat from "@/components/prep/PrepChat";
import CreatorChat from "@/components/prep/CreatorChat";
import InteractiveRenderer from "@/components/interactive/InteractiveRenderer";
import SaveLoadPanel from "@/components/SaveLoadPanel";
import CampaignManager from "@/components/CampaignManager";
import MemoryPanel from "@/components/MemoryPanel";
import BackupPanel from "@/components/BackupPanel";
import WorkspacePanel from "@/components/WorkspacePanel";
import DataManagementPanel from "@/components/prep/DataManagementPanel";
import { createSession, streamChat, getCurrentSystem } from "@/lib/api";
import { loadLLMConfig, loadSessionId, saveSessionId } from "@/lib/store";
import { generateId } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { ChatMessage, SessionState, LLMConfig, DiceResult } from "@/lib/types";
import {
  Swords,
  BookOpen,
  FileText,
  UserCircle,
  Zap,
  Wrench,
  MessageCircle,
  Save,
  Download,
  ScrollText,
  Brain,
  Archive,
  FolderOpen,
  Feather,
  Database,
} from "lucide-react";

type AppMode = "prep" | "game";
type PrepTab = "campaigns" | "chat" | "creator" | "materials" | "characters" | "skills" | "tools" | "saves" | "workspace" | "backup" | "data";

export default function Home() {
  const [mode, setMode] = useState<AppMode>("prep");
  const [prepTab, setPrepTab] = useState<PrepTab>("campaigns");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [session, setSession] = useState<SessionState | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [thinkingStep, setThinkingStep] = useState<string | null>(null);
  const [showMemory, setShowMemory] = useState(false);
  const [llmConfig, setLlmConfig] = useState<LLMConfig | null>(null);
  const [systemId, setSystemId] = useState<string>("pf2e");
  const [saveStatus, setSaveStatus] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLlmConfig(loadLLMConfig());
    getCurrentSystem().then(setSystemId).catch(() => {});
  }, []);

  // Apply theme based on current system
  useEffect(() => {
    document.documentElement.setAttribute("data-system", systemId);
  }, [systemId]);

  // Listen for tab switch requests from child components
  useEffect(() => {
    const handler = (e: Event) => {
      const tab = (e as CustomEvent).detail as PrepTab;
      if (tab) {
        setMode("prep");
        setPrepTab(tab);
      }
    };
    window.addEventListener("switch-prep-tab", handler);
    return () => window.removeEventListener("switch-prep-tab", handler);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, thinkingStep]);

  const ensureSession = useCallback(async () => {
    if (session) return session;
    const cfg = llmConfig ?? loadLLMConfig();
    if (!cfg.api_key) {
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          role: "system",
          content:
            "请先前往「设置」页面配置你的 API Key 和模型信息，然后刷新本页。",
          timestamp: Date.now(),
        },
      ]);
      return null;
    }
    let systemId: string | undefined;
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/settings/system`);
      const data = await res.json();
      systemId = data.system_id;
    } catch {}
    const s = await createSession(cfg, undefined, undefined, undefined, systemId);
    setSession(s);
    saveSessionId(s.session_id);
    return s;
  }, [session, llmConfig]);

  const handleSend = useCallback(
    async (text: string) => {
      const cfg = llmConfig ?? loadLLMConfig();
      const s = await ensureSession();
      if (!s) return;

      const userMsg: ChatMessage = {
        id: generateId(),
        role: "user",
        content: text,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMsg]);

      const assistantId = generateId();
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "narrator", content: "", timestamp: Date.now() },
      ]);
      setStreaming(true);
      setThinkingStep("分析意图...");

      const seenInteractiveIds = new Set<string>();

      try {
        for await (const chunk of streamChat(s.session_id, text, cfg)) {
          if (chunk.type === "thinking") {
            setThinkingStep(chunk.thinking_step || null);
            continue;
          }
          if (chunk.type === "text") {
            setThinkingStep(null);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + chunk.content }
                  : m,
              ),
            );
          } else if (chunk.type === "dice") {
            if (chunk.dice) {
              const diceMsg: ChatMessage = {
                id: generateId(),
                role: "referee",
                content: "",
                dice: chunk.dice,
                timestamp: Date.now(),
              };
              setMessages((prev) => {
                const idx = prev.findIndex((m) => m.id === assistantId);
                const copy = [...prev];
                copy.splice(idx, 0, diceMsg);
                return copy;
              });
            }
          } else if (chunk.type === "interactive" && chunk.interactive) {
            const ie = chunk.interactive;
            if (!seenInteractiveIds.has(ie.id)) {
              seenInteractiveIds.add(ie.id);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, interactive: [...(m.interactive || []), ie] }
                    : m,
                ),
              );
            }
          } else if (chunk.type === "state_update" && chunk.state) {
            setSession(chunk.state);
          } else if (chunk.type === "error") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: `Error: ${chunk.content}`, role: "system" }
                  : m,
              ),
            );
          }
        }
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : String(err);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: `Connection error: ${errMsg}`, role: "system" }
              : m,
          ),
        );
      } finally {
        setStreaming(false);
        setThinkingStep(null);
      }
    },
    [llmConfig, ensureSession],
  );

  const handleResolveInteractive = useCallback(
    (elementId: string, value: string, dice?: DiceResult) => {
      setMessages((prev) =>
        prev.map((m) => {
          if (!m.interactive) return m;
          const updated = m.interactive.map((ie) =>
            ie.id === elementId
              ? { ...ie, resolved: true, resolved_value: value, ...(dice ? { resolved_dice: dice } : {}) }
              : ie,
          );
          const changed = updated.some((ie, idx) => ie !== m.interactive![idx]);
          return changed ? { ...m, interactive: updated } : m;
        }),
      );
    },
    [],
  );

  const handleSessionLoaded = useCallback(
    (state: SessionState, history: ChatMessage[]) => {
      setSession(state);
      saveSessionId(state.session_id);
      setMessages(history);
      setMode("game");
    },
    [],
  );

  const handleNewSession = useCallback(
    (state: SessionState) => {
      setSession(state);
      saveSessionId(state.session_id);
      setMessages([]);
      setMode("game");
    },
    [],
  );

  const handleQuickSave = useCallback(async () => {
    if (!session) return;
    try {
      const { createSave } = await import("@/lib/api");
      await createSave(session.session_id);
      setSaveStatus("已保存");
      setTimeout(() => setSaveStatus(""), 2000);
    } catch {
      setSaveStatus("保存失败");
      setTimeout(() => setSaveStatus(""), 2000);
    }
  }, [session]);

  const handleExportLog = useCallback(async () => {
    if (!session) return;
    const { getExportLogUrl } = await import("@/lib/api");
    window.open(getExportLogUrl(session.session_id), "_blank");
  }, [session]);

  const prepTabs: { key: PrepTab; label: string; icon: typeof FileText }[] = [
    { key: "campaigns", label: "团管理", icon: ScrollText },
    { key: "chat", label: "助手", icon: MessageCircle },
    { key: "creator", label: "创作家", icon: Feather },
    { key: "materials", label: "资料库", icon: FileText },
    { key: "characters", label: "角色卡", icon: UserCircle },
    { key: "skills", label: "Skills", icon: Zap },
    { key: "tools", label: "工具", icon: Wrench },
    { key: "workspace", label: "工作区", icon: FolderOpen },
    { key: "saves", label: "存档", icon: Save },
    { key: "backup", label: "备份", icon: Archive },
    { key: "data", label: "数据", icon: Database },
  ];

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        session={session}
        systemId={systemId}
        onSendMessage={handleSend}
        onStoryPointsChanged={(pts) => setSession((prev) => prev ? { ...prev, story_points: pts } : prev)}
      />

      <main className="flex-1 flex flex-col min-w-0">
        {/* Mode switcher */}
        <div className="border-b border-border bg-card/80 backdrop-blur-sm">
          <div className="flex items-center max-w-5xl mx-auto">
            <button
              onClick={() => setMode("prep")}
              className={cn(
                "flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors border-b-2",
                mode === "prep"
                  ? "text-primary border-primary"
                  : "text-muted-foreground border-transparent hover:text-foreground",
              )}
            >
              <BookOpen className="h-4 w-4" />
              团外准备
            </button>
            <button
              onClick={() => setMode("game")}
              className={cn(
                "flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors border-b-2",
                mode === "game"
                  ? "text-accent border-accent"
                  : "text-muted-foreground border-transparent hover:text-foreground",
              )}
            >
              <Swords className="h-4 w-4" />
              团内游戏
            </button>
          </div>
        </div>

        {/* PREP mode */}
        {mode === "prep" && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Prep sub-tabs */}
            <div className="border-b border-border/50 bg-card/40">
              <div className="flex items-center gap-1 px-6 py-2 max-w-5xl mx-auto">
                {prepTabs.map(({ key, label, icon: Icon }) => (
                  <button
                    key={key}
                    onClick={() => setPrepTab(key)}
                    className={cn(
                      "flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium transition-colors",
                      prepTab === key
                        ? "bg-primary/20 text-primary"
                        : "text-muted-foreground hover:text-foreground hover:bg-secondary",
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Prep content */}
            {prepTab === "chat" ? (
              <div className="flex-1 overflow-hidden">
                <div className="h-full max-w-4xl mx-auto">
                  <PrepChat />
                </div>
              </div>
            ) : prepTab === "creator" ? (
              <div className="flex-1 overflow-hidden">
                <div className="h-full max-w-4xl mx-auto">
                  <CreatorChat systemId={systemId} />
                </div>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto px-6 py-6">
                <div className="max-w-4xl mx-auto">
                  {prepTab === "campaigns" && (
                    <CampaignManager
                      currentSession={session}
                      onSessionSwitch={handleSessionLoaded}
                      onNewSession={handleNewSession}
                      systemId={systemId}
                    />
                  )}
                  {prepTab === "materials" && <MaterialsPanel systemId={systemId} />}
                  {prepTab === "characters" && <CharactersPanel systemId={systemId} />}
                  {prepTab === "skills" && <SkillsPanel systemId={systemId} />}
                  {prepTab === "tools" && <ToolsPanel systemId={systemId} />}
                  {prepTab === "saves" && (
                    <SaveLoadPanel
                      session={session}
                      onSessionLoaded={handleSessionLoaded}
                      systemId={systemId}
                    />
                  )}
                  {prepTab === "workspace" && <WorkspacePanel systemId={systemId} />}
                  {prepTab === "backup" && <BackupPanel />}
                  {prepTab === "data" && <DataManagementPanel systemId={systemId} />}
                </div>
              </div>
            )}
          </div>
        )}

        {/* GAME mode */}
        {mode === "game" && (
          <>
            {/* Game toolbar */}
            {session && (
              <div className="border-b border-border/50 bg-card/40 px-6 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground mr-auto">
                    <span className="text-foreground font-medium">{session.label || "未命名"}</span>
                    {" · "}
                    <code className="text-primary/60 text-[10px]">{session.session_id}</code>
                    {" · "}
                    {messages.length} 消息
                  </span>
                  {saveStatus && (
                    <span className="text-xs text-primary animate-pulse">
                      {saveStatus}
                    </span>
                  )}
                  <button
                    onClick={handleQuickSave}
                    disabled={streaming}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                    title="快速存档"
                  >
                    <Save className="h-3 w-3" />
                    存档
                  </button>
                  <button
                    onClick={handleExportLog}
                    disabled={streaming}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                    title="导出团 Log"
                  >
                    <Download className="h-3 w-3" />
                    导出 Log
                  </button>
                  <button
                    onClick={() => setShowMemory((v) => !v)}
                    className={cn(
                      "flex items-center gap-1 px-2.5 py-1 rounded-md text-xs transition-colors",
                      showMemory
                        ? "bg-primary/20 text-primary"
                        : "text-muted-foreground hover:text-foreground hover:bg-secondary",
                    )}
                    title="记忆面板"
                  >
                    <Brain className="h-3 w-3" />
                    记忆
                  </button>
                </div>
              </div>
            )}
            <div className="flex-1 flex overflow-hidden">
              {/* Chat area */}
              <div className="flex-1 flex flex-col overflow-hidden">
                <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4">
                  {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                      <div className="text-6xl mb-4">&#x1F3F0;</div>
                      <h2 className="text-xl font-semibold text-foreground mb-2">
                        欢迎来到 AI 跑团模拟器
                      </h2>
                      <p className="text-sm text-muted-foreground max-w-md">
                        输入任何内容开始你的冒险。你可以描述你的角色、选择一个模组，或者直接说「开始冒险」。
                      </p>
                      <p className="text-xs text-muted-foreground mt-3 max-w-md">
                        提示：先在「团外准备」中上传模组资料和角色卡，AI 会自动参考这些内容。
                      </p>
                    </div>
                  )}

                  <div className="flex flex-col gap-3 max-w-3xl mx-auto">
                    {messages.map((msg, i) => (
                      <div key={msg.id}>
                        <ChatBubble
                          msg={msg}
                          isStreaming={
                            streaming && i === messages.length - 1 && msg.role !== "user"
                          }
                        />
                        {msg.interactive && msg.interactive.length > 0 && (
                          <div className="max-w-[80%] ml-0">
                            <InteractiveRenderer
                              elements={msg.interactive}
                              sessionId={session?.session_id || ""}
                              onSendMessage={handleSend}
                              onResolve={handleResolveInteractive}
                              disabled={streaming}
                              storyPoints={session?.story_points ?? 0}
                              pointName={session?.system_id === "swade" ? "物语点" : session?.system_id === "pf2e" ? "英雄点" : "叙事点"}
                              onStoryPointsChanged={(pts) => setSession((prev) => prev ? { ...prev, story_points: pts } : prev)}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                    {streaming && thinkingStep && (
                      <div className="flex items-center gap-3 px-4 py-3 max-w-3xl mx-auto">
                        <div className="thinking-dots flex items-center gap-1">
                          <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "0ms" }} />
                          <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "150ms" }} />
                          <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "300ms" }} />
                        </div>
                        <span className="text-sm text-muted-foreground italic">{thinkingStep}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="px-6 py-4 border-t border-border max-w-3xl mx-auto w-full">
                  <ChatInput onSend={handleSend} disabled={streaming} />
                </div>
              </div>

              {/* Memory side panel */}
              {showMemory && session && (
                <div className="w-80 shrink-0 border-l border-border overflow-y-auto bg-background/50">
                  <MemoryPanel sessionId={session.session_id} />
                </div>
              )}
            </div>
          </>
        )}
      </main>

    </div>
  );
}
