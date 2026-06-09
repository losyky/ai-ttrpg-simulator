/**
 * Minimal client-side store backed by localStorage.
 * Holds the user's LLM config and session id across page reloads.
 */

import type { LLMConfig, ImageGenConfig } from "./types";

const CONFIG_KEY = "ttrpg_llm_config";
const SESSION_KEY = "ttrpg_session_id";
const IMAGE_GEN_KEY = "ttrpg_image_gen_config";

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

const DEFAULT_IMAGE_GEN: ImageGenConfig = {
  api_key: "",
  model: "nano-banana-2",
  base_url: "https://grsaiapi.com/v1/api/generate",
  style_prefix: "",
  turns_per_image: 5,
};

export function loadImageGenConfig(): ImageGenConfig {
  if (typeof window === "undefined") return DEFAULT_IMAGE_GEN;
  try {
    const raw = localStorage.getItem(IMAGE_GEN_KEY);
    if (raw) return { ...DEFAULT_IMAGE_GEN, ...JSON.parse(raw) };
  } catch {}
  return DEFAULT_IMAGE_GEN;
}

export function saveImageGenConfig(config: ImageGenConfig) {
  localStorage.setItem(IMAGE_GEN_KEY, JSON.stringify(config));
}
