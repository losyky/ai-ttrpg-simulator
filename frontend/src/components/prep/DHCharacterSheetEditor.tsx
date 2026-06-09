"use client";

import { useEffect, useState, useCallback } from "react";
import {
  ArrowLeft, ArrowUp, Heart, Shield, Star, Sparkles,
  Pencil, Check, X, Plus, Trash2, Minus, ChevronDown,
  ImageIcon, Loader2,
} from "lucide-react";
import { cn, toImageUrl } from "@/lib/utils";
import DHLevelUpPanel from "@/components/charbuilder-dh/DHLevelUpPanel";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DH_TRAIT_LABELS: Record<string, string> = {
  agility: "敏捷", strength: "力量", finesse: "灵巧",
  instinct: "本能", presence: "风度", knowledge: "学识",
};
const DH_TRAITS = ["agility", "strength", "finesse", "instinct", "presence", "knowledge"];

interface RawItem {
  _id?: string;
  type?: string;
  name?: string;
  system?: Record<string, unknown>;
}

interface RawActor {
  _id?: string;
  name?: string;
  system?: {
    class?: string;
    subclass?: string;
    level?: number;
    proficiency?: number;
    heritage?: { ancestry?: string; community?: string };
    traits?: Record<string, { value?: number }>;
    resources?: {
      hitPoints?: { value?: number; max?: number };
      stress?: { value?: number; max?: number };
      hope?: { value?: number; max?: number };
      armorSlots?: { value?: number; max?: number };
    };
    evasion?: number;
    experiences?: string[];
    biography?: { background?: string };
    levelup_log?: { level: number; choices: string[] }[];
  };
  items?: RawItem[];
}

// ── Inline text ──────────────────────────────────────────────────────────────
function TextEdit({ value, placeholder = "点击编辑…", className = "", onSave }: {
  value: string; placeholder?: string; className?: string;
  onSave: (v: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const commit = () => { onSave(draft.trim()); setEditing(false); };
  if (editing) {
    return (
      <span className="inline-flex items-center gap-1">
        <input
          value={draft}
          title="文本内容"
          placeholder={placeholder}
          autoFocus
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") setEditing(false); }}
          className={cn("bg-secondary border border-primary rounded px-2 py-0.5 text-sm focus:outline-none", className)}
        />
        <button title="确认" onClick={commit}><Check className="h-3.5 w-3.5 text-green-400" /></button>
        <button title="取消" onClick={() => setEditing(false)}><X className="h-3.5 w-3.5 text-muted-foreground" /></button>
      </span>
    );
  }
  return (
    <span
      className={cn("cursor-pointer hover:text-violet-400 transition-colors inline-flex items-center gap-1 group", className)}
      onClick={() => { setDraft(value); setEditing(true); }}
    >
      {value || <span className="text-muted-foreground italic">{placeholder}</span>}
      <Pencil className="h-3 w-3 opacity-0 group-hover:opacity-40" />
    </span>
  );
}

// ── Inline number ────────────────────────────────────────────────────────────
function NumEdit({ value, min = -99, max = 9999, className = "", onSave }: {
  value: number; min?: number; max?: number; className?: string;
  onSave: (v: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value));
  const commit = () => {
    const n = parseInt(draft);
    if (!isNaN(n) && n >= min && n <= max) onSave(n);
    else setDraft(String(value));
    setEditing(false);
  };
  if (editing) {
    return (
      <input
        type="number" value={draft} min={min} max={max}
        title="数值" placeholder="0"
        autoFocus
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") setEditing(false); }}
        className={cn("w-14 text-center bg-secondary border border-primary rounded px-1 py-0.5 text-sm font-bold focus:outline-none", className)}
      />
    );
  }
  return (
    <span
      className={cn("font-bold cursor-pointer hover:text-violet-400 transition-colors underline-offset-2 hover:underline", className)}
      onClick={() => { setDraft(String(value)); setEditing(true); }}
      title="点击编辑"
    >
      {value}
    </span>
  );
}

// ── Counter (+/-) ────────────────────────────────────────────────────────────
function Counter({ value, min = 0, max = 999, color = "text-foreground", onSave }: {
  value: number; min?: number; max?: number; color?: string;
  onSave: (v: number) => void;
}) {
  return (
    <div className="flex items-center gap-1 justify-center">
      <button title="减少" onClick={() => value > min && onSave(value - 1)} disabled={value <= min}
        className="p-0.5 rounded hover:bg-secondary disabled:opacity-30 transition-colors">
        <Minus className="h-3 w-3 text-muted-foreground" />
      </button>
      <NumEdit value={value} min={min} max={max} className={color} onSave={onSave} />
      <button title="增加" onClick={() => value < max && onSave(value + 1)} disabled={value >= max}
        className="p-0.5 rounded hover:bg-secondary disabled:opacity-30 transition-colors">
        <Plus className="h-3 w-3 text-muted-foreground" />
      </button>
    </div>
  );
}

// ── Section header ────────────────────────────────────────────────────────────
function SectionHeader({ title, onAdd }: { title: string; onAdd?: () => void }) {
  return (
    <div className="flex items-center justify-between mb-2">
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      {onAdd && (
        <button onClick={onAdd} title="添加"
          className="flex items-center gap-0.5 text-xs text-violet-400 hover:text-violet-300 transition-colors">
          <Plus className="h-3.5 w-3.5" /> 添加
        </button>
      )}
    </div>
  );
}

// ── Main editor ──────────────────────────────────────────────────────────────
interface Props { characterId: string; onBack: () => void; }

export default function DHCharacterSheetEditor({ characterId, onBack }: Props) {
  const [raw, setRaw] = useState<RawActor | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showLevelUp, setShowLevelUp] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [expandBio, setExpandBio] = useState(false);
  const [generatingPortrait, setGeneratingPortrait] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const r = await fetch(`${API}/api/characters/${characterId}/fvtt`);
        if (r.ok) setRaw(await r.json());
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, [characterId, reloadKey]);

  const patch = useCallback(async (updates: Record<string, unknown>) => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/characters/${characterId}/fvtt`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (r.ok) setRaw(await r.json());
    } catch { /* ignore */ }
    setSaving(false);
  }, [characterId]);

  const generatePortrait = useCallback(async () => {
    const stored = localStorage.getItem("ttrpg_image_gen_config");
    let imgCfg: Record<string, string | number> = {};
    try { if (stored) imgCfg = JSON.parse(stored); } catch {}
    if (!imgCfg.api_key) {
      alert("请先在「设置」页面配置图片生成 API Key");
      return;
    }
    setGeneratingPortrait(true);
    try {
      const r = await fetch(`${API}/api/characters/${characterId}/portrait`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: imgCfg.api_key,
          model: imgCfg.model ?? "nano-banana-2",
          base_url: imgCfg.base_url ?? "https://grsaiapi.com",
          style_prefix: imgCfg.style_prefix ?? "",
        }),
      });
      if (r.ok) {
        const data = await r.json();
        setRaw((prev) => prev ? { ...prev, img: data.portrait_url } : prev);
      } else {
        const errText = await r.text();
        let errMsg = `图片生成失败 (${r.status})`;
        try { errMsg = JSON.parse(errText).detail ?? errMsg; } catch {}
        alert(errMsg);
      }
    } catch (e) {
      alert(`网络错误：${e}`);
    }
    setGeneratingPortrait(false);
  }, [characterId]);

  if (showLevelUp) {
    return <DHLevelUpPanel characterId={characterId} onBack={() => setShowLevelUp(false)}
      onComplete={() => { setShowLevelUp(false); setReloadKey(k => k + 1); }} />;
  }

  if (loading) return <div className="text-center text-muted-foreground py-12">加载中…</div>;
  if (!raw) return <div className="text-center text-red-400 py-12">无法加载角色数据</div>;

  const sys = raw.system ?? {};
  const resources = sys.resources ?? {};
  const hp = resources.hitPoints ?? {};
  const stress = resources.stress ?? {};
  const hope = resources.hope ?? {};
  const armorSlots = resources.armorSlots ?? {};
  const traits = sys.traits ?? {};
  const heritage = sys.heritage ?? {};
  const items = raw.items ?? [];

  const domainCards = items.filter((i) => i.type === "domainCard");
  const weapons = items.filter((i) => i.type === "weapon");
  const armor = items.filter((i) => i.type === "armor");
  const features = items.filter((i) => i.type === "feature");
  const loot = items.filter((i) => i.type === "loot" || i.type === "consumable");
  const otherItems = items.filter((i) => !["domainCard","weapon","armor","feature","loot","consumable"].includes(i.type ?? ""));

  const experiences = sys.experiences ?? [];
  const bio = sys.biography?.background ?? "";

  // ── Item helpers ──────────────────────────────────────────────────────────
  const patchItems = (next: RawItem[]) => patch({ items: next });

  const addItem = (type: string, extra: Record<string, unknown> = {}) => {
    patchItems([...items, { _id: Math.random().toString(36).slice(2, 14), type, name: "", system: extra }]);
  };

  const updateItem = (id: string, updates: Partial<RawItem>) => {
    patchItems(items.map((it) => it._id === id ? { ...it, ...updates } : it));
  };

  const removeItem = (id: string) => patchItems(items.filter((it) => it._id !== id));

  return (
    <div className="space-y-5 pb-8">
      {/* ── Header ── */}
      <div className="flex items-start gap-3">
        <button title="返回" onClick={onBack} className="mt-1 text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1 min-w-0 space-y-0.5">
          <TextEdit
            value={raw.name ?? ""}
            className="text-xl font-bold text-foreground"
            onSave={(v) => patch({ name: v })}
          />
          <div className="flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
            <TextEdit value={heritage.ancestry ?? ""} placeholder="族裔"
              onSave={(v) => patch({ heritage: { ...heritage, ancestry: v } })} />
            <span>·</span>
            <TextEdit value={heritage.community ?? ""} placeholder="社群"
              onSave={(v) => patch({ heritage: { ...heritage, community: v } })} />
            <span>·</span>
            <TextEdit value={sys.class ?? ""} placeholder="职业"
              onSave={(v) => patch({ class: v })} />
            {sys.subclass !== undefined && (
              <><span>/</span>
              <TextEdit value={sys.subclass ?? ""} placeholder="子职业"
                onSave={(v) => patch({ subclass: v })} /></>
            )}
          </div>
        </div>
        <div className="flex flex-col items-center gap-1.5">
          {/* Portrait thumbnail */}
          {(raw as Record<string, unknown>).img ? (
            <img
              src={toImageUrl((raw as Record<string, unknown>).img as string)}
              alt="立绘"
              className="w-14 h-14 rounded-full object-cover border-2 border-violet-400/50 shadow"
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
            />
          ) : (
            <div className="w-14 h-14 rounded-full bg-secondary border-2 border-border flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-violet-400" />
            </div>
          )}
          <button
            onClick={generatePortrait}
            disabled={generatingPortrait}
            title="生成立绘"
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-violet-400 transition-colors disabled:opacity-50"
          >
            {generatingPortrait
              ? <Loader2 className="h-3 w-3 animate-spin" />
              : <ImageIcon className="h-3 w-3" />}
            {generatingPortrait ? "生成中…" : "生成立绘"}
          </button>
          {saving && <span className="text-xs text-muted-foreground animate-pulse">保存中…</span>}
        </div>
      </div>

      {/* ── Meta row ── */}
      <div className="flex items-center gap-4 text-sm flex-wrap p-3 rounded-xl bg-secondary/30 border border-border">
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground text-xs">等级</span>
          <NumEdit value={sys.level ?? 1} min={1} max={20} className="text-amber-300"
            onSave={(v) => patch({ level: v })} />
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground text-xs">熟练</span>
          <NumEdit value={sys.proficiency ?? 0} min={0} max={10}
            onSave={(v) => patch({ proficiency: v })} />
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground text-xs">闪避</span>
          <NumEdit value={sys.evasion ?? 0} min={0} max={99}
            onSave={(v) => patch({ evasion: v })} />
        </div>
        <button onClick={() => setShowLevelUp(true)}
          className="ml-auto flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 transition-all border border-amber-500/30">
          <ArrowUp className="h-3 w-3" /> 升级向导
        </button>
      </div>

      {/* ── Resources ── */}
      <div>
        <SectionHeader title="资源" />
        <div className="grid grid-cols-2 gap-2">
          {[
            { label: "HP", icon: Heart, iconColor: "text-red-400", bg: "bg-red-500/10 border-red-500/30",
              val: hp.value ?? 0, max: hp.max ?? 0, color: "text-red-400",
              onVal: (v: number) => patch({ resources: { hitPoints: { value: v } } }),
              onMax: (v: number) => patch({ resources: { hitPoints: { max: v } } }) },
            { label: "Stress", icon: Shield, iconColor: "text-orange-400", bg: "bg-orange-500/10 border-orange-500/30",
              val: stress.value ?? 0, max: stress.max ?? 0, color: "text-orange-400",
              onVal: (v: number) => patch({ resources: { stress: { value: v } } }),
              onMax: (v: number) => patch({ resources: { stress: { max: v } } }) },
            { label: "Hope", icon: Star, iconColor: "text-yellow-400", bg: "bg-yellow-500/10 border-yellow-500/30",
              val: hope.value ?? 0, max: hope.max ?? 0, color: "text-yellow-400",
              onVal: (v: number) => patch({ resources: { hope: { value: v } } }),
              onMax: (v: number) => patch({ resources: { hope: { max: v } } }) },
            { label: "护甲槽", icon: Shield, iconColor: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/30",
              val: armorSlots.value ?? 0, max: armorSlots.max ?? 0, color: "text-blue-400",
              onVal: (v: number) => patch({ resources: { armorSlots: { value: v } } }),
              onMax: (v: number) => patch({ resources: { armorSlots: { max: v } } }) },
          ].map(({ label, icon: Icon, iconColor, bg, val, max, color, onVal, onMax }) => (
            <div key={label} className={cn("p-3 rounded-xl border text-center", bg)}>
              <Icon className={cn("h-4 w-4 mx-auto mb-1", iconColor)} />
              <div className="flex items-center justify-center gap-1">
                <Counter value={val} min={0} max={max} color={color} onSave={onVal} />
                <span className="text-muted-foreground text-xs">/</span>
                <NumEdit value={max} min={0} className="text-xs text-muted-foreground" onSave={onMax} />
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Traits ── */}
      <div>
        <SectionHeader title="特质 (Traits)" />
        <div className="grid grid-cols-3 gap-2">
          {DH_TRAITS.map((key) => {
            const val = traits[key]?.value ?? 0;
            return (
              <div key={key} className="text-center p-2 rounded-lg bg-secondary/50 border border-border">
                <div className="text-xs text-muted-foreground mb-1">{DH_TRAIT_LABELS[key]}</div>
                <Counter
                  value={val}
                  min={-5}
                  max={10}
                  color={val > 0 ? "text-green-400" : val < 0 ? "text-red-400" : "text-foreground"}
                  onSave={(v) => patch({ traits: { [key]: { value: v } } })}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Domain Cards ── */}
      <div>
        <SectionHeader title="领域卡 (Domain Cards)"
          onAdd={() => addItem("domainCard", { description: "", type: "" })} />
        <div className="space-y-1.5">
          {domainCards.length === 0 && <p className="text-xs text-muted-foreground">暂无领域卡</p>}
          {domainCards.map((dc) => (
            <div key={dc._id} className="flex gap-2 items-start p-2.5 rounded-lg bg-violet-500/10 border border-violet-500/30">
              <div className="flex-1 min-w-0 space-y-0.5">
                <TextEdit value={dc.name ?? ""} placeholder="领域卡名称"
                  className="font-medium text-foreground"
                  onSave={(v) => updateItem(dc._id!, { name: v })} />
                {dc.system?.description && (
                  <div className="text-xs text-muted-foreground">{String(dc.system.description)}</div>
                )}
              </div>
              <button title="删除" onClick={() => removeItem(dc._id!)}
                className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Weapons ── */}
      <div>
        <SectionHeader title="武器" onAdd={() => addItem("weapon", { damage: "", trait: "", description: "" })} />
        <div className="space-y-2">
          {weapons.length === 0 && <p className="text-xs text-muted-foreground">暂无武器</p>}
          {weapons.map((w) => (
            <div key={w._id} className="p-2.5 rounded-lg bg-secondary/50 border border-border space-y-1.5">
              <div className="flex gap-2 items-center">
                <TextEdit value={w.name ?? ""} placeholder="武器名称" className="flex-1 font-medium"
                  onSave={(v) => updateItem(w._id!, { name: v })} />
                <TextEdit value={String(w.system?.damage ?? "")} placeholder="伤害"
                  className="w-20 text-xs text-muted-foreground"
                  onSave={(v) => updateItem(w._id!, { system: { ...w.system, damage: v } })} />
                <button title="删除" onClick={() => removeItem(w._id!)}
                  className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <TextEdit
                value={String(w.system?.description ?? w.system?.trait ?? "")}
                placeholder="特性/描述（点击编辑）"
                className="text-xs text-muted-foreground w-full"
                onSave={(v) => updateItem(w._id!, { system: { ...w.system, description: v, trait: v } })}
              />
            </div>
          ))}
        </div>
      </div>

      {/* ── Armor ── */}
      <div>
        <SectionHeader title="护甲" onAdd={() => addItem("armor", { armorSlots: 1, feature: "", description: "" })} />
        <div className="space-y-2">
          {armor.length === 0 && <p className="text-xs text-muted-foreground">暂无护甲</p>}
          {armor.map((a) => (
            <div key={a._id} className="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/30 space-y-1.5">
              <div className="flex gap-2 items-center">
                <TextEdit value={a.name ?? ""} placeholder="护甲名称" className="flex-1 font-medium"
                  onSave={(v) => updateItem(a._id!, { name: v })} />
                <span className="text-xs text-muted-foreground shrink-0">
                  槽: <NumEdit value={Number(a.system?.armorSlots ?? 1)} min={0} max={10} className="text-xs"
                    onSave={(v) => updateItem(a._id!, { system: { ...a.system, armorSlots: v } })} />
                </span>
                <button title="删除" onClick={() => removeItem(a._id!)}
                  className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <TextEdit
                value={String(a.system?.description ?? a.system?.feature ?? "")}
                placeholder="特性/描述（点击编辑）"
                className="text-xs text-muted-foreground w-full"
                onSave={(v) => updateItem(a._id!, { system: { ...a.system, description: v, feature: v } })}
              />
            </div>
          ))}
        </div>
      </div>

      {/* ── Features ── */}
      <div>
        <SectionHeader title="特性 (Features)" onAdd={() => addItem("feature", { description: "" })} />
        <div className="space-y-1.5">
          {features.length === 0 && <p className="text-xs text-muted-foreground">暂无特性</p>}
          {features.map((f) => (
            <div key={f._id} className="flex gap-2 items-start p-2.5 rounded-lg bg-secondary/50 border border-border">
              <div className="flex-1 space-y-0.5">
                <TextEdit value={f.name ?? ""} placeholder="特性名称" className="font-medium"
                  onSave={(v) => updateItem(f._id!, { name: v })} />
                {f.system?.description && (
                  <div className="text-xs text-muted-foreground">{String(f.system.description)}</div>
                )}
              </div>
              <button title="删除" onClick={() => removeItem(f._id!)}
                className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Loot / Consumables ── */}
      <div>
        <SectionHeader title="物品 / 消耗品" onAdd={() => addItem("loot", { quantity: 1 })} />
        <div className="flex flex-wrap gap-2">
          {loot.length === 0 && <p className="text-xs text-muted-foreground">暂无物品</p>}
          {loot.map((item) => (
            <div key={item._id}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-secondary border border-border group">
              <TextEdit value={item.name ?? ""} placeholder="物品名称" className="text-sm"
                onSave={(v) => updateItem(item._id!, { name: v })} />
              <button title="删除" onClick={() => removeItem(item._id!)}
                className="text-muted-foreground hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Other items ── */}
      {otherItems.length > 0 && (
        <div>
          <SectionHeader title="其他" />
          <div className="space-y-1.5">
            {otherItems.map((it) => (
              <div key={it._id} className="flex gap-2 items-center p-2.5 rounded-lg bg-secondary/50 border border-border">
                <TextEdit value={it.name ?? ""} className="flex-1"
                  onSave={(v) => updateItem(it._id!, { name: v })} />
                <span className="text-xs text-muted-foreground">{it.type}</span>
                <button title="删除" onClick={() => removeItem(it._id!)}
                  className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Experiences ── */}
      <div>
        <SectionHeader title="经历 (Experiences)"
          onAdd={() => patch({ experiences: [...experiences, ""] })} />
        <div className="space-y-1.5">
          {experiences.length === 0 && <p className="text-xs text-muted-foreground">暂无经历</p>}
          {experiences.map((exp, i) => (
            <div key={i} className="flex gap-2 items-center p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30">
              <TextEdit value={exp} placeholder="经历描述" className="flex-1"
                onSave={(v) => {
                  const ne = [...experiences]; ne[i] = v;
                  patch({ experiences: ne });
                }} />
              <span className="text-amber-400 text-xs shrink-0">+2</span>
              <button title="删除" onClick={() => patch({ experiences: experiences.filter((_, j) => j !== i) })}
                className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Biography ── */}
      <div>
        <button
          onClick={() => setExpandBio((v) => !v)}
          className="flex items-center gap-2 text-sm font-semibold text-foreground w-full hover:text-primary transition-colors mb-2"
        >
          背景故事
          <ChevronDown className={cn("h-3.5 w-3.5 ml-auto transition-transform", expandBio && "rotate-180")} />
        </button>
        {expandBio && (
          <BioEditor
            value={bio}
            onSave={(v) => patch({ biography: { background: v } })}
          />
        )}
        {!expandBio && bio && (
          <p className="text-xs text-muted-foreground line-clamp-2 cursor-pointer hover:text-foreground"
            onClick={() => setExpandBio(true)}>
            {bio}
          </p>
        )}
      </div>
    </div>
  );
}

// ── Biography textarea ────────────────────────────────────────────────────────
function BioEditor({ value, onSave }: { value: string; onSave: (v: string) => void }) {
  const [draft, setDraft] = useState(value);
  const dirty = draft !== value;
  return (
    <div className="space-y-2">
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={5}
        className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground resize-y focus:outline-none focus:border-primary"
        placeholder="描述你的角色背景故事…"
      />
      {dirty && (
        <div className="flex gap-2">
          <button onClick={() => onSave(draft)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:opacity-90">
            <Check className="h-3.5 w-3.5" /> 保存
          </button>
          <button onClick={() => setDraft(value)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-muted-foreground text-xs hover:text-foreground">
            <X className="h-3.5 w-3.5" /> 还原
          </button>
        </div>
      )}
    </div>
  );
}
