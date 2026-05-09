/**
 * Minimal client-side store backed by localStorage.
 * Holds the user's LLM config and session id across page reloads.
 */

import type { LLMConfig } from "./types";

const CONFIG_KEY = "ttrpg_llm_config";
const SESSION_KEY = "ttrpg_session_id";

export function loadLLMConfig(): LLMConfig {
  if (typeof window === "undefined")
    return { api_key: "", model: "gpt-4o", base_url: "https://api.openai.com/v1" };
  try {
    const raw = localStorage.getItem(CONFIG_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { api_key: "", model: "gpt-4o", base_url: "https://api.openai.com/v1" };
}

export function saveLLMConfig(config: LLMConfig) {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
}

export function loadSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(SESSION_KEY);
}

export function saveSessionId(id: string | null) {
  if (id) localStorage.setItem(SESSION_KEY, id);
  else localStorage.removeItem(SESSION_KEY);
}
