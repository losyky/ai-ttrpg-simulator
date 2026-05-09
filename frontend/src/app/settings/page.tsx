"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Save, Info } from "lucide-react";
import { loadLLMConfig, saveLLMConfig } from "@/lib/store";
import type { LLMConfig } from "@/lib/types";
import { cn } from "@/lib/utils";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ReasoningStrategy = "auto" | "keep" | "strip";
type GameSystemInfo = { system_id: string; display_name: string };

export default function SettingsPage() {
  const router = useRouter();
  const [config, setConfig] = useState<LLMConfig>({
    api_key: "",
    model: "gpt-4o",
    base_url: "https://api.openai.com/v1",
  });
  const [reasoningStrategy, setReasoningStrategy] =
    useState<ReasoningStrategy>("auto");
  const [gameSystems, setGameSystems] = useState<GameSystemInfo[]>([]);
  const [selectedSystem, setSelectedSystem] = useState("pf2e");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setConfig(loadLLMConfig());
    fetch(`${API}/api/settings/reasoning-strategy`)
      .then((r) => r.json())
      .then((d) => setReasoningStrategy(d.strategy ?? "auto"))
      .catch(() => {});
    fetch(`${API}/api/systems`)
      .then((r) => r.json())
      .then((d) => setGameSystems(d.systems ?? []))
      .catch(() => {});
    fetch(`${API}/api/settings/system`)
      .then((r) => r.json())
      .then((d) => {
        setSelectedSystem(d.system_id ?? "pf2e");
        document.documentElement.setAttribute("data-system", d.system_id ?? "pf2e");
      })
      .catch(() => {});
  }, []);

  async function handleSave() {
    saveLLMConfig(config);
    try {
      await fetch(`${API}/api/settings/reasoning-strategy`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategy: reasoningStrategy }),
      });
    } catch {}
    try {
      await fetch(`${API}/api/settings/system`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ system_id: selectedSystem }),
      });
    } catch {}
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  const presets = [
    {
      label: "OpenAI",
      model: "gpt-4o",
      base_url: "https://api.openai.com/v1",
      hint: "GPT-4o / GPT-4.1 / o3 / o4-mini",
    },
    {
      label: "DeepSeek",
      model: "deepseek-chat",
      base_url: "https://api.deepseek.com/v1",
      hint: "deepseek-chat / deepseek-reasoner",
    },
    {
      label: "通义千问",
      model: "qwen-plus",
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
      hint: "qwen-plus / qwen-max / qwq-32b",
    },
    {
      label: "智谱 GLM",
      model: "glm-4-plus",
      base_url: "https://open.bigmodel.cn/api/paas/v4",
      hint: "glm-4-plus / glm-4-long",
    },
    {
      label: "月之暗面",
      model: "moonshot-v1-auto",
      base_url: "https://api.moonshot.cn/v1",
      hint: "moonshot-v1-8k / v1-32k / v1-128k",
    },
    {
      label: "豆包",
      model: "doubao-1.5-pro-256k",
      base_url: "https://ark.cn-beijing.volces.com/api/v3",
      hint: "需要在火山引擎创建接入点",
    },
    {
      label: "硅基流动",
      model: "deepseek-ai/DeepSeek-V3",
      base_url: "https://api.siliconflow.cn/v1",
      hint: "聚合多家模型的 API 平台",
    },
    {
      label: "OpenRouter",
      model: "openai/gpt-4o",
      base_url: "https://openrouter.ai/api/v1",
      hint: "聚合多家模型，用 provider/model 格式",
    },
    {
      label: "Ollama (本地)",
      model: "llama3",
      base_url: "http://localhost:11434/v1",
      hint: "本地部署，无需 API Key",
    },
  ];

  const reasoningOptions: {
    value: ReasoningStrategy;
    label: string;
    desc: string;
  }[] = [
    {
      value: "auto",
      label: "自动 (推荐)",
      desc: "智能判断：有工具调用时保留思维链，否则移除。兼容所有已知模型。",
    },
    {
      value: "keep",
      label: "始终保留",
      desc: "适用于明确要求传回 reasoning_content 的模型（如 DeepSeek thinking + 工具调用场景）。",
    },
    {
      value: "strip",
      label: "始终移除",
      desc: "适用于不支持 reasoning_content 或明确要求移除的模型（如 Qwen QwQ 纯对话）。",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto px-6 py-10">
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> 返回
        </button>

        <h1 className="text-2xl font-bold text-foreground mb-2">设置</h1>
        <p className="text-sm text-muted-foreground mb-8">
          配置你的 AI 模型和 API 密钥。支持所有兼容 OpenAI 格式的 API。
        </p>

        <div className="space-y-6">
          {/* Game System */}
          {gameSystems.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                规则系统
              </label>
              <div className="flex flex-wrap gap-2">
                {gameSystems.map((sys) => (
                  <button
                    key={sys.system_id}
                    onClick={() => {
                      setSelectedSystem(sys.system_id);
                      document.documentElement.setAttribute("data-system", sys.system_id);
                    }}
                    className={cn(
                      "px-4 py-2 rounded-lg text-sm border transition-colors",
                      selectedSystem === sys.system_id
                        ? "border-primary bg-primary/20 text-primary font-medium"
                        : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/30"
                    )}
                  >
                    {sys.display_name}
                  </button>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-1.5">
                选择默认的 TTRPG 规则系统。新建团时将使用此规则。
              </p>
            </div>
          )}

          {/* API Key */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1.5">
              API Key
            </label>
            <input
              type="password"
              value={config.api_key}
              onChange={(e) =>
                setConfig((c) => ({ ...c, api_key: e.target.value }))
              }
              placeholder="sk-..."
              className={cn(
                "w-full rounded-lg bg-secondary border border-border px-4 py-2.5 text-sm",
                "text-foreground placeholder:text-muted-foreground",
                "focus:outline-none focus:ring-2 focus:ring-ring"
              )}
            />
          </div>

          {/* Model */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1.5">
              模型名称
            </label>
            <input
              type="text"
              value={config.model}
              onChange={(e) =>
                setConfig((c) => ({ ...c, model: e.target.value }))
              }
              placeholder="gpt-4o / deepseek-chat / qwen-plus ..."
              className={cn(
                "w-full rounded-lg bg-secondary border border-border px-4 py-2.5 text-sm",
                "text-foreground placeholder:text-muted-foreground",
                "focus:outline-none focus:ring-2 focus:ring-ring"
              )}
            />
            <p className="text-xs text-muted-foreground mt-1">
              输入你希望使用的模型全名，不限定任何 AI 厂商。
            </p>
          </div>

          {/* Base URL */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1.5">
              API Base URL
            </label>
            <input
              type="text"
              value={config.base_url}
              onChange={(e) =>
                setConfig((c) => ({ ...c, base_url: e.target.value }))
              }
              placeholder="https://api.openai.com/v1"
              className={cn(
                "w-full rounded-lg bg-secondary border border-border px-4 py-2.5 text-sm",
                "text-foreground placeholder:text-muted-foreground",
                "focus:outline-none focus:ring-2 focus:ring-ring"
              )}
            />
          </div>

          {/* Presets */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              快捷预设
            </label>
            <div className="flex flex-wrap gap-2">
              {presets.map((preset) => (
                <button
                  key={preset.label}
                  title={preset.hint}
                  onClick={() =>
                    setConfig((c) => ({
                      ...c,
                      model: preset.model,
                      base_url: preset.base_url,
                    }))
                  }
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs border transition-colors",
                    config.base_url === preset.base_url
                      ? "border-primary bg-primary/20 text-primary"
                      : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/30"
                  )}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              点击预设自动填入 Base URL 和默认模型名，你仍可手动修改。鼠标悬停查看支持的模型。
            </p>
          </div>

          {/* Reasoning Strategy */}
          <div>
            <label className="flex items-center gap-1.5 text-sm font-medium text-foreground mb-2">
              推理内容 (reasoning_content) 策略
              <span
                className="inline-block"
                title="DeepSeek R1、Qwen QwQ 等推理模型会返回思维链内容。不同模型对多轮对话中是否需要传回此内容有不同要求。「自动」模式可兼容所有已知模型。"
              >
                <Info className="h-3.5 w-3.5 text-muted-foreground" />
              </span>
            </label>
            <div className="space-y-2">
              {reasoningOptions.map((opt) => (
                <label
                  key={opt.value}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                    reasoningStrategy === opt.value
                      ? "border-primary bg-primary/10"
                      : "border-border hover:border-foreground/30"
                  )}
                >
                  <input
                    type="radio"
                    name="reasoning_strategy"
                    value={opt.value}
                    checked={reasoningStrategy === opt.value}
                    onChange={() => setReasoningStrategy(opt.value)}
                    className="mt-0.5"
                  />
                  <div>
                    <span className="text-sm font-medium text-foreground">
                      {opt.label}
                    </span>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {opt.desc}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Save */}
          <button
            onClick={handleSave}
            className={cn(
              "flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-medium transition-colors",
              saved
                ? "bg-green-600 text-white"
                : "bg-primary text-primary-foreground hover:bg-primary/90"
            )}
          >
            <Save className="h-4 w-4" />
            {saved ? "已保存 ✓" : "保存设置"}
          </button>
        </div>
      </div>
    </div>
  );
}
