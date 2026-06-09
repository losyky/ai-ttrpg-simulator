"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  ArrowLeft, Swords, Pencil, Check, X, Plus, Trash2,
  Minus, ChevronDown, ChevronUp, Flame, ImageIcon, Loader2,
} from "lucide-react";
import { cn, toImageUrl } from "@/lib/utils";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ATTR_LABELS: Record<string, string> = {
  dexterity: "灵巧", smarts: "聪慧", spirit: "心魂",
  strength: "力量", vigor: "活力",
};
const ATTR_KEYS = ["dexterity", "smarts", "spirit", "strength", "vigor"];
const DIE_STEPS = [4, 6, 8, 10, 12];
const DIE_COLOR: Record<number, string> = {
  4: "text-muted-foreground", 6: "text-blue-400",
  8: "text-green-400", 10: "text-yellow-400", 12: "text-red-400",
};

const ELEMENTS = ["fire", "ice", "earth", "wind", "thunder", "light", "dark"];
const ELEMENT_LABELS: Record<string, string> = {
  fire: "火", ice: "冰", earth: "土", wind: "风",
  thunder: "雷", light: "光", dark: "暗",
};
const ELEMENT_COLORS: Record<string, string> = {
  fire: "text-red-400", ice: "text-cyan-400", earth: "text-amber-600",
  wind: "text-emerald-400", thunder: "text-yellow-400",
  light: "text-yellow-200", dark: "text-purple-400",
};
const RESIST_OPTIONS = [
  { value: "weakness", label: "弱点", color: "text-red-400", bg: "bg-red-500/20 border-red-500/50" },
  { value: "normal",   label: "正常", color: "text-muted-foreground", bg: "bg-secondary border-border" },
  { value: "resistance", label: "抗性", color: "text-blue-400", bg: "bg-blue-500/20 border-blue-500/50" },
  { value: "immunity", label: "免疫", color: "text-green-400", bg: "bg-green-500/20 border-green-500/50" },
];

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
    details?: { species?: string; biography?: string | { value?: string; backstory?: string } };
    attributes?: Record<string, { die?: { sides?: number; modifier?: number } }>;
    stats?: {
      toughness?: { value?: number; armor?: number };
      parry?: { value?: number };
      speed?: { value?: number };
    };
    resources?: { mp?: { value?: number; max?: number }; ip?: { value?: number; max?: number } };
    wounds?: { value?: number; max?: number } | number;
    fatigue?: { value?: number; max?: number } | number;
    advances?: { value?: number };
    elementalResistances?: Record<string, string>;
    bonds?: { target?: string; type?: string; description?: string }[];
    pending_levelup?: boolean;
  };
  items?: RawItem[];
}

function gn(f: unknown, sub: "value" | "max", fb: number): number {
  if (typeof f === "number") return f;
  if (typeof f === "object" && f !== null) return (f as Record<string, number>)[sub] ?? fb;
  return fb;
}

// ── Inline editable number ──────────────────────────────────────────────────
function NumEdit({ value, min = 0, max = 9999, className = "", onSave }: {
  value: number; min?: number; max?: number; className?: string;
  onSave: (v: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value));
  const ref = useRef<HTMLInputElement>(null);

  const commit = () => {
    const n = parseInt(draft);
    if (!isNaN(n) && n >= min && n <= max) onSave(n);
    else setDraft(String(value));
    setEditing(false);
  };

  if (editing) {
    return (
      <input
        ref={ref}
        type="number"
        value={draft}
        min={min}
        max={max}
        title="数值"
        placeholder="0"
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") setEditing(false); }}
        className={cn("w-14 text-center bg-secondary border border-primary rounded px-1 py-0.5 text-sm font-bold focus:outline-none", className)}
        autoFocus
      />
    );
  }
  return (
    <span
      className={cn("font-bold cursor-pointer hover:text-amber-400 transition-colors underline-offset-2 hover:underline", className)}
      onClick={() => { setDraft(String(value)); setEditing(true); }}
      title="点击编辑"
    >
      {value}
    </span>
  );
}

// ── Inline editable text ────────────────────────────────────────────────────
function TextEdit({ value, placeholder = "点击编辑…", className = "", onSave }: {
  value: string; placeholder?: string; className?: string;
  onSave: (v: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  const commit = () => { onSave(draft.trim()); setEditing(false); };

  if (editing) {
    return (
      <div className="flex items-center gap-1">
        <input
          value={draft}
          title="文本内容"
          placeholder={placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") setEditing(false); }}
          className={cn("flex-1 bg-secondary border border-primary rounded px-2 py-1 text-sm focus:outline-none", className)}
          autoFocus
        />
        <button title="确认" onClick={commit}><Check className="h-3.5 w-3.5 text-green-400" /></button>
        <button title="取消" onClick={() => setEditing(false)}><X className="h-3.5 w-3.5 text-muted-foreground" /></button>
      </div>
    );
  }
  return (
    <span
      className={cn("cursor-pointer hover:text-amber-400 transition-colors flex items-center gap-1 group", className)}
      onClick={() => { setDraft(value); setEditing(true); }}
    >
      {value || <span className="text-muted-foreground">{placeholder}</span>}
      <Pencil className="h-3 w-3 opacity-0 group-hover:opacity-40" />
    </span>
  );
}

// ── Attribute die selector ──────────────────────────────────────────────────
function DieSelector({ sides, onSave }: { sides: number; onSave: (s: number) => void }) {
  const idx = DIE_STEPS.indexOf(sides);
  return (
    <div className="flex items-center gap-1 justify-center">
      <button
        onClick={() => { if (idx > 0) onSave(DIE_STEPS[idx - 1]); }}
        disabled={idx <= 0}
        className="w-6 h-6 rounded flex items-center justify-center hover:bg-secondary disabled:opacity-30 transition-colors"
        title="降低骰阶"
      >
        <Minus className="h-3 w-3" />
      </button>
      <select
        value={sides}
        onChange={(e) => onSave(parseInt(e.target.value))}
        title="选择骰阶"
        className={cn(
          "font-bold text-base bg-transparent border-b border-transparent hover:border-primary cursor-pointer focus:outline-none text-center appearance-none w-10",
          DIE_COLOR[sides] || "text-foreground",
        )}
      >
        {DIE_STEPS.map((s) => (
          <option key={s} value={s} className="bg-background text-foreground">d{s}</option>
        ))}
      </select>
      <button
        onClick={() => { if (idx < DIE_STEPS.length - 1) onSave(DIE_STEPS[idx + 1]); }}
        disabled={idx >= DIE_STEPS.length - 1}
        className="w-6 h-6 rounded flex items-center justify-center hover:bg-secondary disabled:opacity-30 transition-colors"
        title="提升骰阶"
      >
        <Plus className="h-3 w-3" />
      </button>
    </div>
  );
}

// ── ±1 counter ──────────────────────────────────────────────────────────────
function Counter({ value, min = 0, max = 99, color = "text-foreground", onSave }: {
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

// ── Wound dot tracker ───────────────────────────────────────────────────────
function DotTracker({ value, max, dotColor, emptyColor, onChange }: {
  value: number; max: number; dotColor: string; emptyColor: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center gap-1.5 justify-center">
      <button title="减少" onClick={() => onChange(Math.max(0, value - 1))} disabled={value <= 0}
        className="p-0.5 rounded hover:bg-secondary disabled:opacity-30">
        <Minus className="h-3 w-3 text-muted-foreground" />
      </button>
      <div className="flex gap-1">
        {Array.from({ length: max }).map((_, i) => (
          <button key={i} title={`设为 ${i + 1}`} onClick={() => onChange(i < value ? i : i + 1)}
            className={cn("w-4 h-4 rounded-full border transition-colors",
              i < value ? `${dotColor} border-transparent` : `${emptyColor} border-border`)} />
        ))}
      </div>
      <button title="增加" onClick={() => onChange(Math.min(max, value + 1))} disabled={value >= max}
        className="p-0.5 rounded hover:bg-secondary disabled:opacity-30">
        <Plus className="h-3 w-3 text-muted-foreground" />
      </button>
    </div>
  );
}

// ── Main editor ─────────────────────────────────────────────────────────────
interface Props { characterId: string; onBack: () => void; }

export default function SWADECharacterSheetEditor({ characterId, onBack }: Props) {
  const [raw, setRaw] = useState<RawActor | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [expandBio, setExpandBio] = useState(false);
  const [generatingPortrait, setGeneratingPortrait] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/characters/${characterId}/fvtt`);
        if (r.ok) setRaw(await r.json());
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, [characterId]);

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

  // ── Portrait generation ────────────────────────────────────────────────────
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

  if (loading) return <div className="text-center text-muted-foreground py-12">加载中…</div>;
  if (!raw) return <div className="text-center text-red-400 py-12">无法加载角色数据</div>;

  const sys = raw.system ?? {};
  const attrs = sys.attributes ?? {};
  const stats = sys.stats ?? {};
  const res = sys.resources ?? {};
  const elemResist = sys.elementalResistances ?? {};
  const bonds = sys.bonds ?? [];
  const items = raw.items ?? [];
  const edges = items.filter((i) => i.type === "edge");
  const hindrances = items.filter((i) => i.type === "hindrance");
  const weapons = items.filter((i) => i.type === "weapon");
  const armors = items.filter((i) => ["armor", "shield"].includes(i.type ?? ""));
  const consumables = items.filter((i) => i.type === "consumable");
  const generalGear = items.filter((i) => i.type === "gear");
  const powers = items.filter((i) => i.type === "power");
  const abilities = items.filter((i) => i.type === "ability");
  const otherItems = items.filter((i) => !["edge","hindrance","gear","weapon","armor","shield","consumable","power","ability"].includes(i.type ?? ""));

  const woundsVal = gn(sys.wounds, "value", 0);
  const woundsMax = gn(sys.wounds, "max", 3);
  const fatigueVal = gn(sys.fatigue, "value", 0);
  const fatigueMax = gn(sys.fatigue, "max", 2);
  const mp = res.mp ?? {};
  const ip = res.ip ?? {};
  const species = sys.details?.species ?? "";
  const advances = sys.advances?.value ?? 0;
  const bio = typeof sys.details?.biography === "string"
    ? sys.details.biography
    : (sys.details?.biography as { backstory?: string; value?: string } | undefined)?.backstory
      ?? (sys.details?.biography as { value?: string } | undefined)?.value
      ?? "";

  // ── Item helpers ──────────────────────────────────────────────────────────
  const patchItems = (next: RawItem[]) => patch({ items: next });

  const addItem = (type: string, extra: Record<string, unknown> = {}) => {
    const newItem: RawItem = {
      _id: Math.random().toString(36).slice(2, 14),
      type,
      name: "",
      system: extra,
    };
    patchItems([...items, newItem]);
  };

  const updateItem = (id: string, updates: Partial<RawItem>) => {
    patchItems(items.map((it) => it._id === id ? { ...it, ...updates } : it));
  };

  const removeItem = (id: string) => {
    patchItems(items.filter((it) => it._id !== id));
  };

  // ── Section header helper ─────────────────────────────────────────────────
  const SectionHeader = ({ title, onAdd }: { title: string; onAdd?: () => void }) => (
    <div className="flex items-center justify-between mb-2">
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      {onAdd && (
        <button onClick={onAdd} title="添加"
          className="flex items-center gap-0.5 text-xs text-amber-400 hover:text-amber-300 transition-colors">
          <Plus className="h-3.5 w-3.5" /> 添加
        </button>
      )}
    </div>
  );

  return (
    <div className="space-y-5 pb-8">
      {/* ── Header ── */}
      <div className="flex items-start gap-3">
        <button title="返回" onClick={onBack} className="mt-1 text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1 min-w-0">
          <TextEdit
            value={raw.name ?? ""}
            className="text-xl font-bold text-foreground"
            onSave={(v) => patch({ name: v })}
          />
          <div className="flex items-center gap-2 mt-0.5 text-sm text-muted-foreground flex-wrap">
            <TextEdit value={species} placeholder="种族" onSave={(v) => patch({ details: { species: v } })} />
            <span>·</span>
            <span className="flex items-center gap-1">
              Adv.
              <NumEdit value={advances} min={0} max={99} onSave={(v) => patch({ advances: { value: v } })} />
            </span>
            {sys.pending_levelup && (
              <span className="text-xs text-amber-400 font-medium">⬆ 可升级</span>
            )}
          </div>
        </div>
        <div className="flex flex-col items-center gap-1.5">
          {/* Portrait thumbnail */}
          {(raw as Record<string, unknown>).img ? (
            <img
              src={toImageUrl((raw as Record<string, unknown>).img as string)}
              alt="立绘"
              className="w-14 h-14 rounded-full object-cover border-2 border-amber-400/50 shadow"
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
            />
          ) : (
            <div className="w-14 h-14 rounded-full bg-secondary border-2 border-border flex items-center justify-center">
              <Swords className="h-5 w-5 text-amber-400" />
            </div>
          )}
          <button
            onClick={generatePortrait}
            disabled={generatingPortrait}
            title="生成立绘"
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-amber-400 transition-colors disabled:opacity-50"
          >
            {generatingPortrait
              ? <Loader2 className="h-3 w-3 animate-spin" />
              : <ImageIcon className="h-3 w-3" />}
            {generatingPortrait ? "生成中…" : "生成立绘"}
          </button>
          {saving && <span className="text-xs text-muted-foreground animate-pulse">保存中…</span>}
        </div>
      </div>

      {/* ── Attributes ── */}
      <div>
        <SectionHeader title="属性" />
        <div className="grid grid-cols-5 gap-2">
          {ATTR_KEYS.map((key) => {
            const d = attrs[key] ?? (key === "dexterity" ? attrs["agility"] : undefined);
            const sides = d?.die?.sides ?? 4;
            return (
              <div key={key} className="text-center p-2 rounded-lg bg-secondary/50 border border-border">
                <div className="text-xs text-muted-foreground mb-1">{ATTR_LABELS[key]}</div>
                <DieSelector
                  sides={sides}
                  onSave={(s) => patch({ attributes: { [key]: { die: { sides: s, modifier: 0 } } } })}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Derived stats ── */}
      <div>
        <SectionHeader title="衍生数据" />
        <div className="grid grid-cols-3 gap-2 text-sm text-center">
          {[
            {
              label: "坚韧", sub: "护甲",
              main: stats.toughness?.value ?? 5,
              sub2: stats.toughness?.armor ?? 0,
              onMain: (v: number) => patch({ stats: { toughness: { value: v } } }),
              onSub: (v: number) => patch({ stats: { toughness: { armor: v } } }),
            },
            {
              label: "格挡", main: stats.parry?.value ?? 4,
              onMain: (v: number) => patch({ stats: { parry: { value: v } } }),
            },
            {
              label: "移速", main: stats.speed?.value ?? 6,
              onMain: (v: number) => patch({ stats: { speed: { value: v } } }),
            },
          ].map(({ label, sub, main, sub2, onMain, onSub }) => (
            <div key={label} className="p-2 rounded-lg bg-secondary/50 border border-border">
              <div className="text-muted-foreground text-xs mb-1">{label}</div>
              <NumEdit value={main} onSave={onMain} />
              {sub && onSub !== undefined && (
                <div className="text-xs text-muted-foreground mt-0.5">
                  {sub}: <NumEdit value={sub2 ?? 0} onSave={onSub} className="text-xs" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ── Resources ── */}
      <div>
        <SectionHeader title="资源" />
        <div className="grid grid-cols-2 gap-2 text-sm text-center">
          {[
            { label: "MP", val: mp.value ?? 0, max: mp.max ?? 0, color: "text-blue-400",
              onVal: (v: number) => patch({ resources: { mp: { value: v } } }),
              onMax: (v: number) => patch({ resources: { mp: { max: v } } }) },
            { label: "IP", val: ip.value ?? 0, max: ip.max ?? 0, color: "text-orange-400",
              onVal: (v: number) => patch({ resources: { ip: { value: v } } }),
              onMax: (v: number) => patch({ resources: { ip: { max: v } } }) },
          ].map(({ label, val, max, color, onVal, onMax }) => (
            <div key={label} className="p-3 rounded-xl bg-secondary/50 border border-border">
              <div className="text-muted-foreground text-xs mb-1">{label}</div>
              <div className="flex items-center justify-center gap-1">
                <Counter value={val} min={0} max={max} color={color} onSave={onVal} />
                <span className="text-muted-foreground">/</span>
                <NumEdit value={max} min={0} onSave={onMax} className="text-muted-foreground text-xs" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Wounds / Fatigue ── */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-center">
          <div className="text-muted-foreground text-xs mb-1.5 flex items-center justify-center gap-1">
            负伤 (max:
            <NumEdit value={woundsMax} min={1} max={10} className="text-xs"
              onSave={(v) => patch({ wounds: { value: woundsVal, max: v } })} />
            )
          </div>
          <DotTracker value={woundsVal} max={woundsMax} dotColor="bg-red-500" emptyColor="bg-red-500/20"
            onChange={(v) => patch({ wounds: { value: v } })} />
        </div>
        <div className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/30 text-center">
          <div className="text-muted-foreground text-xs mb-1.5 flex items-center justify-center gap-1">
            疲劳 (max:
            <NumEdit value={fatigueMax} min={1} max={10} className="text-xs"
              onSave={(v) => patch({ fatigue: { value: fatigueVal, max: v } })} />
            )
          </div>
          <DotTracker value={fatigueVal} max={fatigueMax} dotColor="bg-orange-500" emptyColor="bg-orange-500/20"
            onChange={(v) => patch({ fatigue: { value: v } })} />
        </div>
      </div>

      {/* ── Edges ── */}
      <div>
        <SectionHeader title="专长 (Edges)" onAdd={() => addItem("edge", { description: "", rank: "novice" })} />
        <div className="space-y-1.5">
          {edges.length === 0 && <p className="text-xs text-muted-foreground">暂无专长</p>}
          {edges.map((e) => (
            <div key={e._id} className="flex gap-2 items-start p-2.5 rounded-lg bg-green-500/10 border border-green-500/20">
              <div className="flex-1 min-w-0 space-y-1">
                <TextEdit value={e.name ?? ""} placeholder="专长名称"
                  onSave={(v) => updateItem(e._id!, { name: v })} />
                <TextEdit value={String(e.system?.description ?? "")} placeholder="描述（可选）"
                  className="text-xs text-muted-foreground"
                  onSave={(v) => updateItem(e._id!, { system: { ...e.system, description: v } })} />
              </div>
              <button onClick={() => removeItem(e._id!)} title="删除"
                className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Hindrances ── */}
      <div>
        <SectionHeader title="负赘 (Hindrances)" onAdd={() => addItem("hindrance", { description: "", major: false })} />
        <div className="space-y-1.5">
          {hindrances.length === 0 && <p className="text-xs text-muted-foreground">暂无负赘</p>}
          {hindrances.map((h) => (
            <div key={h._id} className="flex gap-2 items-center p-2.5 rounded-lg bg-red-500/10 border border-red-500/20">
              <TextEdit value={h.name ?? ""} placeholder="负赘名称" className="flex-1"
                onSave={(v) => updateItem(h._id!, { name: v })} />
              <button
                onClick={() => updateItem(h._id!, { system: { ...h.system, major: !h.system?.major } })}
                className={cn("px-2 py-0.5 rounded text-xs border shrink-0 transition-colors",
                  h.system?.major ? "border-red-500/50 bg-red-500/20 text-red-400" : "border-border bg-secondary text-muted-foreground")}
              >
                {h.system?.major ? "主要" : "次要"}
              </button>
              <button onClick={() => removeItem(h._id!)} title="删除"
                className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Weapons ── */}
      <div>
        <SectionHeader title="武器" onAdd={() => addItem("weapon", { damage: "", description: "" })} />
        <div className="space-y-2">
          {weapons.length === 0 && <p className="text-xs text-muted-foreground">暂无武器</p>}
          {weapons.map((g) => (
            <div key={g._id} className="p-2.5 rounded-lg bg-secondary/50 border border-border space-y-1.5">
              <div className="flex gap-2 items-center">
                <TextEdit value={g.name ?? ""} placeholder="武器名称" className="flex-1 font-medium"
                  onSave={(v) => updateItem(g._id!, { name: v })} />
                <TextEdit value={String(g.system?.damage ?? "")} placeholder="伤害"
                  className="w-20 text-xs text-muted-foreground"
                  onSave={(v) => updateItem(g._id!, { system: { ...g.system, damage: v } })} />
                <button onClick={() => removeItem(g._id!)} title="删除"
                  className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <TextEdit value={String(g.system?.description ?? g.system?.notes ?? "")}
                placeholder="描述/备注（点击编辑）"
                className="text-xs text-muted-foreground w-full"
                onSave={(v) => updateItem(g._id!, { system: { ...g.system, description: v, notes: v } })} />
            </div>
          ))}
        </div>
      </div>

      {/* ── Armor / Shield ── */}
      <div>
        <SectionHeader title="护甲 / 盾牌" onAdd={() => addItem("armor", { armor: 0, description: "" })} />
        <div className="space-y-2">
          {armors.length === 0 && <p className="text-xs text-muted-foreground">暂无护甲</p>}
          {armors.map((g) => (
            <div key={g._id} className="p-2.5 rounded-lg bg-secondary/50 border border-border space-y-1.5">
              <div className="flex gap-2 items-center">
                <TextEdit value={g.name ?? ""} placeholder="护甲名称" className="flex-1 font-medium"
                  onSave={(v) => updateItem(g._id!, { name: v })} />
                <span className="text-xs text-muted-foreground shrink-0">护甲</span>
                <NumEdit value={Number(g.system?.armor ?? g.system?.toughness ?? 0)} min={0} max={20}
                  onSave={(v) => updateItem(g._id!, { system: { ...g.system, armor: v } })} />
                <button onClick={() => removeItem(g._id!)} title="删除"
                  className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <TextEdit value={String(g.system?.description ?? g.system?.notes ?? "")}
                placeholder="描述/备注（点击编辑）"
                className="text-xs text-muted-foreground w-full"
                onSave={(v) => updateItem(g._id!, { system: { ...g.system, description: v, notes: v } })} />
            </div>
          ))}
        </div>
      </div>

      {/* ── Consumables ── */}
      <div>
        <SectionHeader title="消耗品" onAdd={() => addItem("consumable", { quantity: 1, damage: "", description: "" })} />
        <div className="space-y-2">
          {consumables.length === 0 && <p className="text-xs text-muted-foreground">暂无消耗品</p>}
          {consumables.map((g) => (
            <div key={g._id} className="p-2.5 rounded-lg bg-secondary/50 border border-border space-y-1.5">
              <div className="flex gap-2 items-center">
                <TextEdit value={g.name ?? ""} placeholder="消耗品名称" className="flex-1 font-medium"
                  onSave={(v) => updateItem(g._id!, { name: v })} />
                <TextEdit value={String(g.system?.damage ?? "")} placeholder="效果/伤害"
                  className="w-20 text-xs text-muted-foreground"
                  onSave={(v) => updateItem(g._id!, { system: { ...g.system, damage: v } })} />
                <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                  <span>×</span>
                  <NumEdit value={Number(g.system?.quantity ?? 1)} min={0} max={999}
                    onSave={(v) => updateItem(g._id!, { system: { ...g.system, quantity: v } })} />
                </div>
                <button onClick={() => removeItem(g._id!)} title="删除"
                  className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <TextEdit value={String(g.system?.description ?? g.system?.notes ?? "")}
                placeholder="描述/备注（点击编辑）"
                className="text-xs text-muted-foreground w-full"
                onSave={(v) => updateItem(g._id!, { system: { ...g.system, description: v, notes: v } })} />
            </div>
          ))}
        </div>
      </div>

      {/* ── General Gear ── */}
      <div>
        <SectionHeader title="装备" onAdd={() => addItem("gear", { quantity: 1, description: "" })} />
        <div className="space-y-2">
          {generalGear.length === 0 && <p className="text-xs text-muted-foreground">暂无一般装备</p>}
          {generalGear.map((g) => (
            <div key={g._id} className="p-2.5 rounded-lg bg-secondary/50 border border-border space-y-1.5">
              <div className="flex gap-2 items-center">
                <TextEdit value={g.name ?? ""} placeholder="装备名称" className="flex-1 font-medium"
                  onSave={(v) => updateItem(g._id!, { name: v })} />
                <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                  <span>×</span>
                  <NumEdit value={Number(g.system?.quantity ?? 1)} min={0} max={999}
                    onSave={(v) => updateItem(g._id!, { system: { ...g.system, quantity: v } })} />
                </div>
                <button onClick={() => removeItem(g._id!)} title="删除"
                  className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <TextEdit value={String(g.system?.description ?? g.system?.notes ?? "")}
                placeholder="描述/备注（点击编辑）"
                className="text-xs text-muted-foreground w-full"
                onSave={(v) => updateItem(g._id!, { system: { ...g.system, description: v, notes: v } })} />
            </div>
          ))}
        </div>
      </div>

      {/* ── Powers ── */}
      <div>
        <SectionHeader title="异能 (Powers)" onAdd={() => addItem("power", { description: "", pp: 0 })} />
        <div className="space-y-2">
          {powers.length === 0 && <p className="text-xs text-muted-foreground">暂无异能</p>}
          {powers.map((p) => (
            <div key={p._id} className="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 space-y-1.5">
              <div className="flex gap-2 items-center">
                <TextEdit value={p.name ?? ""} placeholder="异能名称" className="flex-1 font-medium"
                  onSave={(v) => updateItem(p._id!, { name: v })} />
                <span className="text-xs text-muted-foreground shrink-0">PP</span>
                <NumEdit value={Number(p.system?.pp ?? 0)} min={0} max={99}
                  onSave={(v) => updateItem(p._id!, { system: { ...p.system, pp: v } })} />
                <button onClick={() => removeItem(p._id!)} title="删除"
                  className="text-muted-foreground hover:text-red-400 transition-colors shrink-0">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <TextEdit
                value={String(p.system?.description ?? "")}
                placeholder="描述/效果（点击编辑）"
                className="text-xs text-muted-foreground w-full"
                onSave={(v) => updateItem(p._id!, { system: { ...p.system, description: v } })}
              />
            </div>
          ))}
        </div>
      </div>

      {/* ── Abilities ── */}
      {abilities.length > 0 && (
        <div>
          <SectionHeader title="特殊能力" />
          <div className="space-y-1.5">
            {abilities.map((a) => (
              <div key={a._id} className="flex gap-2 items-start p-2.5 rounded-lg bg-purple-500/10 border border-purple-500/20">
                <div className="flex-1 space-y-0.5">
                  <TextEdit value={a.name ?? ""} className="font-medium"
                    onSave={(v) => updateItem(a._id!, { name: v })} />
                  {a.system?.description && (
                    <div className="text-xs text-muted-foreground">{String(a.system.description)}</div>
                  )}
                </div>
                <button onClick={() => removeItem(a._id!)} title="删除"
                  className="text-muted-foreground hover:text-red-400 transition-colors">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Other items ── */}
      {otherItems.length > 0 && (
        <div>
          <SectionHeader title="其他物品" />
          <div className="space-y-1.5">
            {otherItems.map((it) => (
              <div key={it._id} className="flex gap-2 items-center p-2.5 rounded-lg bg-secondary/50 border border-border">
                <TextEdit value={it.name ?? ""} className="flex-1"
                  onSave={(v) => updateItem(it._id!, { name: v })} />
                <span className="text-xs text-muted-foreground">{it.type}</span>
                <button onClick={() => removeItem(it._id!)} title="删除"
                  className="text-muted-foreground hover:text-red-400 transition-colors">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Elemental Resistances ── */}
      <div>
        <SectionHeader title="元素抗性" />
        <div className="space-y-2">
          {ELEMENTS.map((el) => {
            const cur = elemResist[el] ?? "normal";
            return (
              <div key={el} className="flex items-center justify-between">
                <span className={cn("text-sm font-medium flex items-center gap-1.5 w-12", ELEMENT_COLORS[el])}>
                  <Flame className="h-3.5 w-3.5" />
                  {ELEMENT_LABELS[el]}
                </span>
                <div className="flex gap-1">
                  {RESIST_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => patch({ elementalResistances: { ...elemResist, [el]: opt.value } })}
                      className={cn(
                        "px-2 py-0.5 rounded text-xs border transition-all",
                        cur === opt.value
                          ? `${opt.color} font-medium ${opt.bg}`
                          : "text-muted-foreground border-border hover:text-foreground",
                      )}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Bonds ── */}
      <div>
        <SectionHeader
          title="羁绊 (Bonds)"
          onAdd={() => patch({ bonds: [...bonds, { target: "", type: "loyalty", description: "" }] })}
        />
        <div className="space-y-2">
          {bonds.length === 0 && <p className="text-xs text-muted-foreground">暂无羁绊</p>}
          {bonds.map((b, i) => (
            <div key={i} className="flex gap-2 items-center p-2.5 rounded-lg bg-secondary/50 border border-border">
              <TextEdit value={b.target ?? ""} placeholder="对象"
                className="w-24 text-sm font-medium"
                onSave={(v) => { const nb = [...bonds]; nb[i] = { ...b, target: v }; patch({ bonds: nb }); }} />
              <TextEdit value={b.description ?? ""} placeholder="描述"
                className="flex-1 text-sm text-muted-foreground"
                onSave={(v) => { const nb = [...bonds]; nb[i] = { ...b, description: v }; patch({ bonds: nb }); }} />
              <button title="删除羁绊"
                onClick={() => patch({ bonds: bonds.filter((_, j) => j !== i) })}
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
          {expandBio ? <ChevronUp className="h-3.5 w-3.5 ml-auto" /> : <ChevronDown className="h-3.5 w-3.5 ml-auto" />}
        </button>
        {expandBio && (
          <BioEditor
            value={bio}
            onSave={(v) => patch({ details: { biography: { backstory: v } } })}
          />
        )}
        {!expandBio && bio && (
          <p className="text-xs text-muted-foreground line-clamp-2 cursor-pointer hover:text-foreground"
            onClick={() => setExpandBio(true)}>
            {bio}
          </p>
        )}
      </div>

      {/* ── Award Advance ── */}
      <div className="border-t border-border/50 pt-4">
        <button
          onClick={async () => {
            const r = await fetch(`${API}/api/characters/${characterId}/award_advance`, { method: "POST" });
            if (r.ok) {
              const data = await r.json();
              setRaw((prev) => prev ? {
                ...prev,
                system: {
                  ...prev.system,
                  advances: { value: data.advances },
                  pending_levelup: true,
                },
              } : prev);
            }
          }}
          className="w-full py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-sm hover:bg-amber-500/20 transition-colors"
        >
          ⬆ 授予升级机会 (Advance +1)
        </button>
        {sys.pending_levelup && (
          <button
            onClick={() => patch({ pending_levelup: false })}
            className="w-full mt-1 py-1.5 rounded-lg border border-border text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            清除升级提醒
          </button>
        )}
      </div>
    </div>
  );
}

// ── Biography textarea ───────────────────────────────────────────────────────
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
