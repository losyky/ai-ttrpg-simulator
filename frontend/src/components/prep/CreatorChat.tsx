"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Feather, Send, BookUp, Plus, Trash2, History, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { generateId } from "@/lib/utils";
import {
  streamCreatorChat,
  ingestText,
  listCreatorSessions,
  getCreatorHistory,
  deleteCreatorSession,
  type ChatSessionInfo,
} from "@/lib/api";
import { loadLLMConfig } from "@/lib/store";
import type { ChatMessage, LLMConfig } from "@/lib/types";
import ReactMarkdown from "react-markdown";

const STORAGE_KEY = "creator_session_id";

function loadSessionId(): string | null {
  try { return localStorage.getItem(STORAGE_KEY); } catch { return null; }
}
function saveSessionIdLocal(id: string) {
  try { localStorage.setItem(STORAGE_KEY, id); } catch { /* */ }
}

interface Props {
  systemId?: string;
}

export default function CreatorChat({ systemId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [sessionId, setSessionId] = useState(() => loadSessionId() || `creator-${generateId()}`);
  const [publishingId, setPublishingId] = useState<string | null>(null);
  const [showSessions, setShowSessions] = useState(false);
  const [sessions, setSessions] = useState<ChatSessionInfo[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { saveSessionIdLocal(sessionId); }, [sessionId]);

  // Load history on mount or session switch
  useEffect(() => {
    setHistoryLoaded(false);
    (async () => {
      try {
        const hist = await getCreatorHistory(sessionId);
        if (hist && hist.length > 0) {
          setMessages(
            hist.map((m, i) => ({
              id: `restored_${i}`,
              role: m.role === "user" ? "user" : m.role === "system" ? "system" : "narrator",
              content: m.content,
              timestamp: Date.now() - (hist.length - i) * 1000,
            })),
          );
        } else {
          setMessages([]);
        }
      } catch { setMessages([]); }
      setHistoryLoaded(true);
    })();
  }, [sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const doSend = useCallback(async (text: string) => {
    if (!text.trim() || streaming) return;
    const cfg: LLMConfig = loadLLMConfig();
    if (!cfg.api_key) {
      setMessages((prev) => [...prev, { id: generateId(), role: "system", content: "请先前往「设置」页面配置 API Key。", timestamp: Date.now() }]);
      return;
    }
    setInput("");
    const userMsg: ChatMessage = { id: generateId(), role: "user", content: text, timestamp: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    const assistantId = generateId();
    setMessages((prev) => [...prev, { id: assistantId, role: "narrator", content: "", timestamp: Date.now() }]);
    setStreaming(true);
    try {
      for await (const chunk of streamCreatorChat(sessionId, text, cfg)) {
        if (chunk.type === "text") {
          setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, content: m.content + chunk.content } : m));
        } else if (chunk.type === "error") {
          setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, content: `Error: ${chunk.content}`, role: "system" } : m));
        }
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, content: `连接错误: ${errMsg}`, role: "system" } : m));
    } finally { setStreaming(false); }
  }, [streaming, sessionId]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text) return;
    await doSend(text);
  }, [input, doSend]);

  const handlePublish = useCallback(async (msgId: string, content: string) => {
    if (publishingId || !content.trim()) return;
    setPublishingId(msgId);
    const headingMatch = content.match(/^#+\s+(.+)/m);
    const title = headingMatch ? headingMatch[1].trim() : `创作内容_${new Date().toLocaleDateString("zh-CN")}`;
    try {
      const doc = await ingestText(title, content, systemId);
      setMessages((prev) => [...prev, { id: generateId(), role: "system", content: `✅ 已发布到资料库: **${title}** (${doc.chunk_count} 个片段)`, timestamp: Date.now() }]);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      setMessages((prev) => [...prev, { id: generateId(), role: "system", content: `发布失败: ${errMsg}`, timestamp: Date.now() }]);
    } finally { setPublishingId(null); }
  }, [publishingId, systemId]);

  const handleNewSession = useCallback(() => {
    const newId = `creator-${generateId()}`;
    setSessionId(newId);
    setMessages([]);
    setShowSessions(false);
  }, []);

  const handleSwitchSession = useCallback((sid: string) => {
    setSessionId(sid);
    setShowSessions(false);
  }, []);

  const handleDeleteSession = useCallback(async (sid: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("确认删除此对话？")) return;
    try {
      await deleteCreatorSession(sid);
      setSessions((prev) => prev.filter((s) => s.session_id !== sid));
      if (sid === sessionId) handleNewSession();
    } catch { /* */ }
  }, [sessionId, handleNewSession]);

  const loadSessions = useCallback(async () => {
    try { setSessions(await listCreatorSessions()); } catch { /* */ }
  }, []);

  const toggleSessions = useCallback(() => {
    if (!showSessions) loadSessions();
    setShowSessions((v) => !v);
  }, [showSessions, loadSessions]);

  return (
    <div className="flex flex-col h-full">
      {/* Session header */}
      <div className="border-b border-border px-4 py-2 flex items-center gap-2">
        <button onClick={toggleSessions} className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
          <History className="h-3.5 w-3.5" />
          历史对话
          <ChevronDown className={cn("h-3 w-3 transition-transform", showSessions && "rotate-180")} />
        </button>
        <div className="flex-1" />
        <button onClick={handleNewSession} className="flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors">
          <Plus className="h-3.5 w-3.5" />
          新对话
        </button>
      </div>

      {/* Session list dropdown */}
      {showSessions && (
        <div className="border-b border-border bg-secondary/50 max-h-48 overflow-y-auto">
          {sessions.length === 0 && (
            <div className="px-4 py-3 text-xs text-muted-foreground text-center">暂无历史对话</div>
          )}
          {sessions.map((s) => (
            <div
              key={s.session_id}
              onClick={() => handleSwitchSession(s.session_id)}
              className={cn(
                "px-4 py-2 flex items-center gap-2 cursor-pointer hover:bg-secondary transition-colors",
                s.session_id === sessionId && "bg-accent/10 border-l-2 border-accent",
              )}
            >
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-foreground truncate">
                  {s.label || s.last_message || s.session_id}
                </div>
                <div className="text-[10px] text-muted-foreground">
                  {s.count || 0} 条消息
                  {s.updated && ` · ${new Date(s.updated * 1000).toLocaleDateString("zh-CN")}`}
                </div>
              </div>
              <button
                onClick={(e) => handleDeleteSession(s.session_id, e)}
                className="text-muted-foreground hover:text-red-400 transition-colors p-1"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && historyLoaded && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Feather className="h-12 w-12 text-accent/50 mb-3" />
            <h3 className="text-sm font-semibold text-foreground mb-1">剧本创作家</h3>
            <p className="text-xs text-muted-foreground max-w-sm">
              我可以帮你创作冒险模组、设计世界观、编写 NPC 背景、设计遭遇和剧情钩子。
              创作完成的内容可以发布到资料库，供跑团中使用。
            </p>
            <div className="flex flex-wrap gap-2 mt-4 justify-center">
              {["帮我设计一个单次冒险模组", "创建一个有趣的反派 NPC", "设计一个充满谜题的地下城", "生成 10 个冒险钩子", "构建一个城市的世界设定"].map((suggestion) => (
                <button key={suggestion} onClick={() => setInput(suggestion)} className="text-xs px-3 py-1.5 rounded-full bg-secondary border border-border/50 text-muted-foreground hover:text-foreground hover:border-accent/30 transition-colors">
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => {
          const isUser = msg.role === "user";
          const isAssistant = msg.role === "narrator";
          const hasContent = isAssistant && msg.content && msg.content.length > 50;
          return (
            <div key={msg.id} className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}>
              <div className={cn(
                "max-w-[85%] rounded-2xl px-4 py-3",
                isUser ? "bg-primary/20 border border-primary/30 rounded-br-sm"
                  : msg.role === "system" ? "bg-destructive/10 border border-destructive/30 rounded-bl-sm"
                    : "bg-card border border-border rounded-bl-sm",
              )}>
                {isAssistant && (
                  <div className="text-xs font-semibold text-accent mb-1 flex items-center gap-1">
                    <Feather className="h-3 w-3" /> 创作家
                  </div>
                )}
                <div className={cn(
                  "text-sm leading-relaxed prose prose-invert prose-sm max-w-none",
                  "prose-p:my-1.5 prose-headings:my-2 prose-hr:my-3",
                  "prose-strong:text-foreground prose-em:text-foreground/90",
                  "prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5",
                  "prose-blockquote:border-l-accent prose-blockquote:text-muted-foreground",
                  "prose-code:text-accent prose-code:bg-accent/10 prose-code:px-1 prose-code:rounded",
                )}>
                  <ReactMarkdown>{msg.content || "..."}</ReactMarkdown>
                </div>
                {hasContent && !streaming && (
                  <div className="mt-2 pt-2 border-t border-border/30 flex justify-end">
                    <button
                      onClick={() => handlePublish(msg.id, msg.content)}
                      disabled={publishingId === msg.id}
                      className={cn(
                        "flex items-center gap-1.5 text-xs px-3 py-1 rounded-lg",
                        "bg-accent/10 text-accent border border-accent/20",
                        "hover:bg-accent/20 transition-colors",
                        "disabled:opacity-50 disabled:cursor-not-allowed",
                      )}
                    >
                      <BookUp className="h-3 w-3" />
                      {publishingId === msg.id ? "发布中…" : "发布到资料库"}
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Input */}
      <div className="border-t border-border px-4 py-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="描述你的创作需求..."
            disabled={streaming}
            className={cn(
              "flex-1 rounded-xl bg-secondary border border-border px-4 py-2.5 text-sm",
              "text-foreground placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-ring",
              streaming && "opacity-50",
            )}
          />
          <button
            onClick={handleSend}
            disabled={streaming || !input.trim()}
            className={cn(
              "p-2.5 rounded-xl bg-accent text-accent-foreground transition-colors",
              "hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed",
            )}
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
