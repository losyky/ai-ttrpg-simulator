"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Save, Info } from "lucide-react";
import { loadLLMConfig, saveLLMConfig, loadImageGenConfig, saveImageGenConfig } from "@/lib/store";
import type { LLMConfig, ImageGenConfig } from "@/lib/types";
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
  const [imageGenConfig, setImageGenConfig] = useState<ImageGenConfig>({
    api_key: "",
    model: "nano-banana-2",
    base_url: "https://grsaiapi.com",
    style_prefix: "",
    turns_per_image: 5,
  });
  const [imageGenTestStatus, setImageGenTestStatus] = useState<"idle" | "testing" | "ok" | "fail">("idle");

  useEffect(() => {
    setConfig(loadLLMConfig());
    setImageGenConfig(loadImageGenConfig());
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

  async function handleTestImageGen() {
    if (!imageGenConfig.api_key) {
      setImageGenTestStatus("fail");
      return;
    }
    setImageGenTestStatus("testing");
    try {
      const res = await fetch(`${API}/api/chat/generate-image`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: "test",
          prompt: "a simple test image, white background, minimal",
          image_gen_config: imageGenConfig,
        }),
      });
      if (res.ok) {
        setImageGenTestStatus("ok");
      } else {
        setImageGenTestStatus("fail");
      }
    } catch {
      setImageGenTestStatus("fail");
    }
    setTimeout(() => setImageGenTestStatus("idle"), 3000);
  }

  async function handleSave() {
    saveLLMConfig(config);
    saveImageGenConfig(imageGenConfig);
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

          {/* Image Generation Settings */}
          <div className="border-t border-border pt-6">
            <h2 className="text-base font-semibold text-foreground mb-4">图片生成设置</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  图片生成 API Key
                </label>
                <input
                  type="password"
                  value={imageGenConfig.api_key}
                  onChange={(e) => setImageGenConfig((c) => ({ ...c, api_key: e.target.value }))}
                  placeholder="sk-..."
                  className={cn(
                    "w-full px-3 py-2 rounded-lg border border-border bg-secondary text-sm",
                    "text-foreground placeholder:text-muted-foreground",
                    "focus:outline-none focus:ring-2 focus:ring-ring"
                  )}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  接口地址（完整 URL，直接 POST 到此地址）
                </label>
                <input
                  type="text"
                  value={imageGenConfig.base_url}
                  onChange={(e) => setImageGenConfig((c) => ({ ...c, base_url: e.target.value }))}
                  placeholder="https://grsaiapi.com/v1/api/generate"
                  className={cn(
                    "w-full px-3 py-2 rounded-lg border border-border bg-secondary text-sm",
                    "text-foreground placeholder:text-muted-foreground",
                    "focus:outline-none focus:ring-2 focus:ring-ring"
                  )}
                />
                <div className="flex flex-wrap gap-2 mt-1.5">
                  {[
                    { label: "nano-banana 全球", url: "https://grsaiapi.com/v1/api/generate" },
                    { label: "nano-banana 国内", url: "https://grsai.dakka.com.cn/v1/api/generate" },
                  ].map((n) => (
                    <button key={n.url} type="button"
                      onClick={() => setImageGenConfig((c) => ({ ...c, base_url: n.url }))}
                      className={cn(
                        "px-2.5 py-1 rounded text-xs border transition-colors",
                        imageGenConfig.base_url === n.url
                          ? "border-primary bg-primary/20 text-primary"
                          : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/30"
                      )}>
                      {n.label}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  地址原样使用，不会自动补全路径。其他图片服务填入对应的生成接口地址即可。
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  图片模型
                </label>
                <input
                  type="text"
                  value={imageGenConfig.model}
                  onChange={(e) => setImageGenConfig((c) => ({ ...c, model: e.target.value }))}
                  placeholder="nano-banana-2"
                  className={cn(
                    "w-full px-3 py-2 rounded-lg border border-border bg-secondary text-sm",
                    "text-foreground placeholder:text-muted-foreground",
                    "focus:outline-none focus:ring-2 focus:ring-ring"
                  )}
                />
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {["nano-banana", "nano-banana-fast", "nano-banana-2", "nano-banana-2-cl", "nano-banana-pro", "nano-banana-pro-cl"].map((m) => (
                    <button key={m} type="button"
                      onClick={() => setImageGenConfig((c) => ({ ...c, model: m }))}
                      className={cn(
                        "px-2 py-0.5 rounded text-xs border transition-colors",
                        imageGenConfig.model === m
                          ? "border-primary bg-primary/20 text-primary"
                          : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/30"
                      )}>
                      {m}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  画风基础提示词（style prefix）
                  <span className="text-xs text-muted-foreground ml-2">会自动拼接在所有图片 prompt 前</span>
                </label>
                <input
                  type="text"
                  value={imageGenConfig.style_prefix}
                  onChange={(e) => setImageGenConfig((c) => ({ ...c, style_prefix: e.target.value }))}
                  placeholder="例：anime fantasy art, detailed illustration"
                  className={cn(
                    "w-full px-3 py-2 rounded-lg border border-border bg-secondary text-sm",
                    "text-foreground placeholder:text-muted-foreground",
                    "focus:outline-none focus:ring-2 focus:ring-ring"
                  )}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  每 N 轮对话可生成一次图片
                </label>
                <input
                  type="number"
                  title="每N轮生成一次"
                  min={0}
                  max={50}
                  value={imageGenConfig.turns_per_image}
                  onChange={(e) => setImageGenConfig((c) => ({ ...c, turns_per_image: parseInt(e.target.value) || 0 }))}
                  className={cn(
                    "w-24 px-3 py-2 rounded-lg border border-border bg-secondary text-sm",
                    "text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  )}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  设为 0 表示无限制。超出频率时 AI 会弹出确认框询问是否继续生成。
                </p>
              </div>
              <button
                onClick={handleTestImageGen}
                disabled={imageGenTestStatus === "testing"}
                className={cn(
                  "px-4 py-2 rounded-lg text-sm font-medium border transition-colors",
                  imageGenTestStatus === "ok" && "bg-green-600 text-white border-green-600",
                  imageGenTestStatus === "fail" && "bg-red-600 text-white border-red-600",
                  imageGenTestStatus === "testing" && "opacity-60 cursor-not-allowed border-border text-muted-foreground",
                  imageGenTestStatus === "idle" && "border-border text-foreground hover:border-primary hover:text-primary"
                )}
              >
                {imageGenTestStatus === "testing" ? "测试中..." :
                 imageGenTestStatus === "ok" ? "连接成功 ✓" :
                 imageGenTestStatus === "fail" ? "连接失败 ✗" :
                 "测试图片生成连接"}
              </button>
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
