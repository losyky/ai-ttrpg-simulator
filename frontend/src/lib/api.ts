import type {
  LLMConfig,
  SessionState,
  SessionListItem,
  ChatResponseChunk,
  DocumentInfo,
  CharacterSummary,
  DiceResult,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── Sessions ──

export async function listSessions(systemId?: string): Promise<SessionListItem[]> {
  const params = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  return request<SessionListItem[]>(`/api/sessions${params}`);
}

export async function createSession(
  llmConfig: LLMConfig,
  player?: CharacterSummary,
  label?: string,
  teammateIds?: string[],
  systemId?: string,
): Promise<SessionState> {
  return request<SessionState>("/api/sessions", {
    method: "POST",
    body: JSON.stringify({
      llm_config: llmConfig,
      player_character: player ?? null,
      teammate_ids: teammateIds ?? [],
      label: label ?? "",
      system_id: systemId ?? null,
    }),
  });
}

export async function getGameSystems(): Promise<{ system_id: string; display_name: string }[]> {
  const res = await request<{ systems: { system_id: string; display_name: string }[] }>("/api/systems");
  return res.systems;
}

export async function getCurrentSystem(): Promise<string> {
  const res = await request<{ system_id: string }>("/api/settings/system");
  return res.system_id;
}

export async function addTeammate(sessionId: string, characterId: string): Promise<{ status: string; teammates: string[] }> {
  return request(`/api/sessions/${sessionId}/teammates/add`, {
    method: "POST",
    body: JSON.stringify({ character_id: characterId }),
  });
}

export async function removeTeammate(sessionId: string, name: string): Promise<{ status: string; teammates: string[] }> {
  return request(`/api/sessions/${sessionId}/teammates/remove`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function getSession(sessionId: string): Promise<SessionState> {
  return request<SessionState>(`/api/sessions/${sessionId}`);
}

export async function updateSession(
  sessionId: string,
  data: { label?: string },
): Promise<SessionState> {
  return request<SessionState>(`/api/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteSession(sessionId: string): Promise<void> {
  await request(`/api/sessions/${sessionId}`, { method: "DELETE" });
}

// ── Session document settings ──

export interface SessionDocumentItem {
  doc_id: string;
  title: string;
  filename: string;
  doc_type: string;
  chunk_count: number;
  enabled: boolean;
}

export async function getSessionDocuments(sessionId: string): Promise<{
  session_id: string;
  documents: SessionDocumentItem[];
  mode: "all" | "selective";
}> {
  return request(`/api/sessions/${sessionId}/documents`);
}

export async function setSessionDocuments(
  sessionId: string,
  enabledDocIds: string[] | null,
): Promise<{ session_id: string; enabled_doc_ids: string[] | null }> {
  return request(`/api/sessions/${sessionId}/documents`, {
    method: "PUT",
    body: JSON.stringify({ enabled_doc_ids: enabledDocIds }),
  });
}

export async function* streamChat(
  sessionId: string,
  message: string,
  llmConfig: LLMConfig,
): AsyncGenerator<ChatResponseChunk> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      llm_config: llmConfig,
    }),
  });

  if (!res.ok) {
    throw new Error(`Chat API ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("data:")) {
        const raw = trimmed.slice(5).trim();
        if (raw) {
          try {
            yield JSON.parse(raw) as ChatResponseChunk;
          } catch {
            // skip malformed chunks
          }
        }
      }
    }
  }
}

export async function uploadDocument(file: File, systemId?: string): Promise<DocumentInfo> {
  const form = new FormData();
  form.append("file", file);

  const qs = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  const res = await fetch(`${BASE}/api/documents${qs}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Upload ${res.status}`);
  return res.json() as Promise<DocumentInfo>;
}

// ── Documents / Knowledge Base ──

export async function listDocuments(systemId?: string): Promise<DocumentInfo[]> {
  const qs = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  return request<DocumentInfo[]>(`/api/documents${qs}`);
}

export async function deleteDocument(docId: string): Promise<void> {
  await request(`/api/documents/${docId}`, { method: "DELETE" });
}

export async function ingestText(
  title: string,
  content: string,
  systemId?: string,
): Promise<DocumentInfo> {
  return request<DocumentInfo>("/api/documents/ingest-text", {
    method: "POST",
    body: JSON.stringify({
      title,
      content,
      system_id: systemId || undefined,
    }),
  });
}

export async function searchDocuments(
  q: string,
  docId?: string,
  systemId?: string,
): Promise<unknown[]> {
  const params = new URLSearchParams({ q });
  if (docId) params.set("doc_id", docId);
  if (systemId) params.set("system_id", systemId);
  return request<unknown[]>(`/api/documents/search?${params}`);
}

// ── Skills ──

export interface SkillInfo {
  skill_id: string;
  title: string;
  description: string;
  filename: string;
  shared?: boolean;
}

export interface SkillDetail {
  skill_id: string;
  content: string;
  filename: string;
}

export async function listSkills(systemId?: string): Promise<SkillInfo[]> {
  const qs = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  return request<SkillInfo[]>(`/api/skills${qs}`);
}

export async function getSkill(skillId: string, systemId?: string): Promise<SkillDetail> {
  const qs = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  return request<SkillDetail>(`/api/skills/${skillId}${qs}`);
}

export async function createSkill(data: {
  skill_id: string;
  title: string;
  description: string;
  instructions: string;
  examples?: string;
  shared?: boolean;
}, systemId?: string): Promise<SkillInfo> {
  const qs = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  return request<SkillInfo>(`/api/skills${qs}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteSkill(skillId: string, systemId?: string): Promise<void> {
  const qs = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  await request(`/api/skills/${skillId}${qs}`, { method: "DELETE" });
}

// ── Characters ──

export interface CharacterListItem {
  id: string;
  name: string;
  level: number;
  ancestry: string;
  character_class: string;
  hp: number;
  max_hp: number;
}

export async function listCharacters(systemId?: string): Promise<CharacterListItem[]> {
  const qs = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  return request<CharacterListItem[]>(`/api/characters${qs}`);
}

export async function importCharacter(file: File, systemId?: string): Promise<CharacterListItem> {
  const form = new FormData();
  form.append("file", file);

  const qs = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  const res = await fetch(`${BASE}/api/characters/import${qs}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Import ${res.status}`);
  return res.json() as Promise<CharacterListItem>;
}

export async function deleteCharacter(charId: string): Promise<void> {
  await request(`/api/characters/${charId}`, { method: "DELETE" });
}

export async function getCharacterSummary(charId: string): Promise<CharacterSummary> {
  return request<CharacterSummary>(`/api/characters/${charId}/as_session_character`);
}

export interface CharacterFull {
  id: string;
  name: string;
  level: number;
  ancestry: string;
  heritage: string;
  background: string;
  character_class: string;
  key_ability: string;
  deity: string;
  hp: number;
  max_hp: number;
  temp_hp: number;
  hero_points: number;
  abilities: { str: number; dex: number; con: number; int: number; wis: number; cha: number };
  skills: { slug: string; rank: number; label: string }[];
  saves: { slug: string; rank: number }[];
  feats: { name: string; item_type: string; category: string; description: string }[];
  spells: { name: string; rank: number; tradition: string; description: string }[];
  inventory: { name: string; item_type: string; quantity: number; description: string }[];
  lore_skills: { slug: string; rank: number }[];
  backstory: string;
  gender: string;
  perception_rank?: number;
  summary: string;
}

export async function getCharacter(charId: string): Promise<CharacterFull> {
  return request<CharacterFull>(`/api/characters/${charId}`);
}

export async function updateCharacter(charId: string, updates: Record<string, unknown>): Promise<CharacterFull> {
  return request<CharacterFull>(`/api/characters/${charId}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

// ── Tools ──

export interface ToolInfo {
  tool_id: string;
  name: string;
  name_en: string;
  description: string;
  category: string;
  builtin: boolean;
  shared?: boolean;
  parameters: Record<string, string>;
  instructions?: string;
}

export async function listTools(systemId?: string): Promise<ToolInfo[]> {
  const qs = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  return request<ToolInfo[]>(`/api/tools${qs}`);
}

export async function createTool(data: {
  tool_id: string;
  name: string;
  description: string;
  parameters?: Record<string, string>;
  instructions?: string;
  category?: string;
  shared?: boolean;
}, systemId?: string): Promise<ToolInfo> {
  const qs = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  return request<ToolInfo>(`/api/tools${qs}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteTool(toolId: string, systemId?: string): Promise<void> {
  const qs = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  await request(`/api/tools/${toolId}${qs}`, { method: "DELETE" });
}

// ── Player Dice Roll ──

export async function rollDice(data: {
  session_id: string;
  expression: string;
  dc?: number;
  label?: string;
  modifier?: number;
}): Promise<DiceResult> {
  return request<DiceResult>("/api/dice/roll", {
    method: "POST",
    body: JSON.stringify({
      session_id: data.session_id,
      expression: data.expression,
      dc: data.dc ?? 0,
      label: data.label ?? "",
      modifier: data.modifier ?? 0,
    }),
  });
}

export async function rerollDice(data: {
  session_id: string;
  expression: string;
  dc?: number;
  label?: string;
  modifier?: number;
  original_total: number;
}): Promise<DiceResult> {
  return request<DiceResult>("/api/dice/reroll", {
    method: "POST",
    body: JSON.stringify({
      session_id: data.session_id,
      expression: data.expression,
      dc: data.dc ?? 0,
      label: data.label ?? "",
      modifier: data.modifier ?? 0,
      original_total: data.original_total,
    }),
  });
}

export async function updateStoryPoints(
  sessionId: string,
  delta: number,
  reason: string = "",
): Promise<{ story_points: number; max_story_points: number }> {
  return request(`/api/sessions/${sessionId}/story-points`, {
    method: "PATCH",
    body: JSON.stringify({ delta, reason }),
  });
}

// ── Save / Load ──

export interface SaveInfo {
  save_id: string;
  label: string;
  created_at: string;
  session_id: string;
  system_id?: string;
  message_count: number;
  player_name?: string;
  phase?: string;
}

export async function listSaves(systemId?: string): Promise<SaveInfo[]> {
  const params = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
  return request<SaveInfo[]>(`/api/saves${params}`);
}

export async function createSave(
  sessionId: string,
  label?: string,
): Promise<SaveInfo> {
  return request<SaveInfo>("/api/saves", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, label: label ?? "" }),
  });
}

export async function loadSave(saveId: string): Promise<SessionState> {
  return request<SessionState>(`/api/saves/${saveId}/load`, {
    method: "POST",
  });
}

export async function deleteSave(saveId: string): Promise<void> {
  await request(`/api/saves/${saveId}`, { method: "DELETE" });
}

export async function getSaveHistory(
  saveId: string,
): Promise<Record<string, unknown>[]> {
  return request<Record<string, unknown>[]>(`/api/saves/${saveId}/history`);
}

export function getDownloadSaveUrl(saveId: string): string {
  return `${BASE}/api/saves/${saveId}/download`;
}

export function getExportLogUrl(sessionId: string): string {
  return `${BASE}/api/saves/export/log/${sessionId}`;
}

export async function getLogPreview(
  sessionId: string,
): Promise<{ session_id: string; markdown: string; message_count: number }> {
  return request(`/api/saves/export/log-preview/${sessionId}`);
}

export async function importSaveFile(
  file: File,
): Promise<{ save_id: string; session_id: string; message_count: number }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/saves/import`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Import ${res.status}`);
  return res.json();
}

// ── Memories ──

export interface MemoryItem {
  key: string;
  category: string;
  text: string;
  [k: string]: unknown;
}

export async function listMemories(
  sessionId: string,
  category?: string,
): Promise<MemoryItem[]> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  params.set("limit", "100");
  return request<MemoryItem[]>(
    `/api/memories/${sessionId}?${params}`,
  );
}

export async function addMemory(
  sessionId: string,
  text: string,
  category: string = "facts",
): Promise<{ key: string }> {
  return request<{ key: string }>("/api/memories", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      text,
      category,
    }),
  });
}

export async function deleteMemory(
  sessionId: string,
  category: string,
  key: string,
): Promise<void> {
  await request(`/api/memories/${sessionId}/${category}/${key}`, {
    method: "DELETE",
  });
}

export async function clearMemories(
  sessionId: string,
): Promise<{ cleared: number }> {
  return request<{ cleared: number }>(`/api/memories/${sessionId}`, {
    method: "DELETE",
  });
}

// ── Prep Chat ──

export async function* streamPrepChat(
  sessionId: string,
  message: string,
  llmConfig: LLMConfig,
): AsyncGenerator<ChatResponseChunk> {
  const res = await fetch(`${BASE}/api/prep-chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      llm_config: llmConfig,
    }),
  });

  if (!res.ok) {
    throw new Error(`Prep Chat API ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("data:")) {
        const raw = trimmed.slice(5).trim();
        if (raw) {
          try {
            yield JSON.parse(raw) as ChatResponseChunk;
          } catch {
            /* skip */
          }
        }
      }
    }
  }
}

// ── Creator Chat ──

export async function* streamCreatorChat(
  sessionId: string,
  message: string,
  llmConfig: LLMConfig,
): AsyncGenerator<ChatResponseChunk> {
  const res = await fetch(`${BASE}/api/creator-chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      llm_config: llmConfig,
    }),
  });

  if (!res.ok) {
    throw new Error(`Creator Chat API ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("data:")) {
        const raw = trimmed.slice(5).trim();
        if (raw) {
          try {
            yield JSON.parse(raw) as ChatResponseChunk;
          } catch {
            /* skip */
          }
        }
      }
    }
  }
}

// ── Prep / Creator Chat Session Management ──

export interface ChatSessionInfo {
  session_id: string;
  label?: string;
  created?: number;
  updated?: number;
  count?: number;
  last_message?: string;
}

export interface ChatHistoryMessage {
  role: string;
  content: string;
}

export async function listPrepSessions(): Promise<ChatSessionInfo[]> {
  return request<ChatSessionInfo[]>("/api/prep-chat/sessions");
}

export async function getPrepHistory(sessionId: string): Promise<ChatHistoryMessage[]> {
  return request<ChatHistoryMessage[]>(`/api/prep-chat/sessions/${encodeURIComponent(sessionId)}`);
}

export async function deletePrepSession(sessionId: string): Promise<void> {
  await request(`/api/prep-chat/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
}

export async function listCreatorSessions(): Promise<ChatSessionInfo[]> {
  return request<ChatSessionInfo[]>("/api/creator-chat/sessions");
}

export async function getCreatorHistory(sessionId: string): Promise<ChatHistoryMessage[]> {
  return request<ChatHistoryMessage[]>(`/api/creator-chat/sessions/${encodeURIComponent(sessionId)}`);
}

export async function deleteCreatorSession(sessionId: string): Promise<void> {
  await request(`/api/creator-chat/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
}

// ── Compendium Management ──

export interface CompendiumEntry {
  slug: string;
  name?: string;
  name_cn?: string;
  _default?: boolean;
  [key: string]: unknown;
}

export async function getCompendiumCollections(system: string): Promise<{ system: string; collections: { id: string; label: string }[] }> {
  return request(`/api/compendium/${system}`);
}

export async function getCompendiumEntries(system: string, collection: string): Promise<CompendiumEntry[]> {
  return request(`/api/compendium/${system}/${collection}`);
}

export async function addCompendiumEntry(system: string, collection: string, entry: Record<string, unknown>): Promise<{ ok: boolean; entry: CompendiumEntry }> {
  return request(`/api/compendium/${system}/${collection}`, { method: "POST", body: JSON.stringify(entry) });
}

export async function deleteCompendiumEntry(system: string, collection: string, slug: string): Promise<void> {
  await request(`/api/compendium/${system}/${collection}/${encodeURIComponent(slug)}`, { method: "DELETE" });
}

// ── Backup / Restore ──

export interface BackupStats {
  [folder: string]: { count: number; size_mb: number } | { exists: boolean; size_mb: number };
}

export async function getBackupStats(): Promise<BackupStats> {
  return request<BackupStats>("/api/backup/stats");
}

export function getBackupDownloadUrl(): string {
  return `${BASE}/api/backup/export`;
}

export async function importBackup(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<{ restored: Record<string, number>; errors: string[] }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/api/backup/import`);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(`Import failed: ${xhr.status} ${xhr.responseText}`));
      }
    });
    xhr.addEventListener("error", () => reject(new Error("Network error")));

    const fd = new FormData();
    fd.append("file", file);
    xhr.send(fd);
  });
}

// ── Workspace ──

export interface WorkspaceFile {
  name: string;
  path: string;
  is_dir: boolean;
  size?: number;
}

export async function listWorkspaceFiles(path: string = "", systemId?: string): Promise<WorkspaceFile[]> {
  const p = new URLSearchParams();
  if (path) p.set("path", path);
  if (systemId) p.set("system_id", systemId);
  const qs = p.toString() ? `?${p}` : "";
  return request<WorkspaceFile[]>(`/api/workspace/list${qs}`);
}

export async function readWorkspaceFile(
  path: string,
  systemId?: string,
): Promise<{ path: string; content: string; size: number }> {
  const p = new URLSearchParams({ path });
  if (systemId) p.set("system_id", systemId);
  return request(`/api/workspace/read?${p}`);
}

export async function writeWorkspaceFile(path: string, content: string, systemId?: string): Promise<void> {
  await request("/api/workspace/write", {
    method: "POST",
    body: JSON.stringify({ path, content, system_id: systemId }),
  });
}

export async function deleteWorkspaceFile(path: string, systemId?: string): Promise<void> {
  const p = new URLSearchParams({ path });
  if (systemId) p.set("system_id", systemId);
  await request(`/api/workspace/delete?${p}`, {
    method: "DELETE",
  });
}

export async function uploadDocumentWithProgress(
  file: File,
  onProgress?: (pct: number) => void,
  systemId?: string,
): Promise<DocumentInfo> {
  return new Promise((resolve, reject) => {
    const qs = systemId ? `?system_id=${encodeURIComponent(systemId)}` : "";
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/api/documents${qs}`);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`));
      }
    });
    xhr.addEventListener("error", () => reject(new Error("Network error")));

    const fd = new FormData();
    fd.append("file", file);
    xhr.send(fd);
  });
}

// ── Character Builder API ──

const CB_PREFIX = "/api/pf2e/charbuilder";

export async function cbSearchAncestries(q = "", lang = "cn") {
  return request<{ count: number; results: any[] }>(
    `${CB_PREFIX}/ancestries?q=${encodeURIComponent(q)}&lang=${lang}`,
  );
}

export async function cbGetAncestry(slug: string, lang = "cn") {
  return request<any>(`${CB_PREFIX}/ancestries/${slug}?lang=${lang}`);
}

export async function cbSearchHeritages(ancestrySlug = "", q = "", lang = "cn") {
  return request<{ count: number; results: any[] }>(
    `${CB_PREFIX}/heritages?ancestry_slug=${encodeURIComponent(ancestrySlug)}&q=${encodeURIComponent(q)}&lang=${lang}`,
  );
}

export async function cbSearchBackgrounds(q = "", lang = "cn") {
  return request<{ count: number; results: any[] }>(
    `${CB_PREFIX}/backgrounds?q=${encodeURIComponent(q)}&lang=${lang}`,
  );
}

export async function cbGetBackground(slug: string, lang = "cn") {
  return request<any>(`${CB_PREFIX}/backgrounds/${slug}?lang=${lang}`);
}

export async function cbSearchClasses(q = "", lang = "cn") {
  return request<{ count: number; results: any[] }>(
    `${CB_PREFIX}/classes?q=${encodeURIComponent(q)}&lang=${lang}`,
  );
}

export async function cbGetClass(slug: string, lang = "cn") {
  return request<any>(`${CB_PREFIX}/classes/${slug}?lang=${lang}`);
}

export async function cbSearchFeats(params: {
  category?: string;
  level_max?: number;
  class_slug?: string;
  ancestry_slug?: string;
  q?: string;
  limit?: number;
  lang?: string;
} = {}) {
  const qs = new URLSearchParams();
  if (params.category) qs.set("category", params.category);
  if (params.level_max) qs.set("level_max", String(params.level_max));
  if (params.class_slug) qs.set("class_slug", params.class_slug);
  if (params.ancestry_slug) qs.set("ancestry_slug", params.ancestry_slug);
  if (params.q) qs.set("q", params.q);
  if (params.limit) qs.set("limit", String(params.limit));
  qs.set("lang", params.lang ?? "cn");
  return request<{ count: number; results: any[] }>(`${CB_PREFIX}/feats?${qs}`);
}

export async function cbSearchSpells(params: {
  tradition?: string;
  rank_max?: number;
  q?: string;
  limit?: number;
  lang?: string;
} = {}) {
  const qs = new URLSearchParams();
  if (params.tradition) qs.set("tradition", params.tradition);
  if (params.rank_max) qs.set("rank_max", String(params.rank_max));
  if (params.q) qs.set("q", params.q);
  if (params.limit) qs.set("limit", String(params.limit));
  qs.set("lang", params.lang ?? "cn");
  return request<{ count: number; results: any[] }>(`${CB_PREFIX}/spells?${qs}`);
}

export async function cbSearchEquipment(params: {
  item_type?: string;
  category?: string;
  q?: string;
  limit?: number;
  lang?: string;
} = {}) {
  const qs = new URLSearchParams();
  if (params.item_type) qs.set("item_type", params.item_type);
  if (params.category) qs.set("category", params.category);
  if (params.q) qs.set("q", params.q);
  if (params.limit) qs.set("limit", String(params.limit));
  qs.set("lang", params.lang ?? "cn");
  return request<{ count: number; results: any[] }>(`${CB_PREFIX}/equipment?${qs}`);
}

export async function cbGetSkills() {
  return request<{ skills: any[] }>(`${CB_PREFIX}/skills`);
}

export async function cbComputeAbilities(body: {
  ancestry_boosts: string[];
  ancestry_flaws: string[];
  background_boosts: string[];
  class_boost: string;
  free_boosts: string[];
  level_boosts: Record<string, string[]>;
  voluntary_flaws: string[];
}) {
  return request<{ abilities: Record<string, number> }>(`${CB_PREFIX}/compute-abilities`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function cbValidateBuild(build: Record<string, unknown>) {
  return request<{ valid: boolean; errors: string[]; warnings: string[] }>(
    `${CB_PREFIX}/validate`,
    { method: "POST", body: JSON.stringify({ build }) },
  );
}

export async function cbAssembleBuild(build: Record<string, unknown>, name: string) {
  return request<{ result: string }>(
    `${CB_PREFIX}/assemble`,
    { method: "POST", body: JSON.stringify({ build, name, save: true }) },
  );
}

export async function cbGetStats() {
  return request<Record<string, number>>(`${CB_PREFIX}/stats`);
}

// ── Data Management ──

export async function getDataStatus() {
  return request<Record<string, unknown>>("/api/data/status");
}

export async function resetPf2eData(target: string = "all") {
  return request<{ status: string; results: Record<string, string> }>(
    "/api/data/pf2e/reset",
    { method: "POST", body: JSON.stringify({ system_id: "pf2e", target }) },
  );
}

export async function updatePf2eData(packsPath?: string, translationsPath?: string) {
  return request<{ status: string; results: Record<string, string> }>(
    "/api/data/pf2e/update",
    { method: "POST", body: JSON.stringify({ packs_path: packsPath, translations_path: translationsPath }) },
  );
}

export async function importFvttPacks(systemId: string, systemPath: string) {
  return request<{ status: string; result: Record<string, string> }>(
    "/api/data/fvtt-import",
    { method: "POST", body: JSON.stringify({ system_id: systemId, system_path: systemPath }) },
  );
}
