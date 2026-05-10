"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeft,
  Heart,
  Shield,
  Swords,
  Flame,
  Pencil,
  Check,
  X,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ATTR_LABELS: Record<string, string> = {
  agility: "灵巧",
  smarts: "聪慧",
  spirit: "心魂",
  strength: "力量",
  vigor: "活力",
};

const ELEMENT_LABELS: Record<string, string> = {
  fire: "火", ice: "冰", earth: "土", wind: "风",
  thunder: "雷", light: "光", dark: "暗",
};
const ELEMENT_COLORS: Record<string, string> = {
  fire: "text-red-400", ice: "text-cyan-400", earth: "text-amber-600",
  wind: "text-emerald-400", thunder: "text-yellow-400", light: "text-yellow-200", dark: "text-purple-400",
};
const RESIST_LABEL: Record<string, string> = {
  weakness: "弱点", normal: "正常", resistance: "抗性", immunity: "免疫",
};
const RESIST_COLOR: Record<string, string> = {
  weakness: "text-red-400", normal: "text-muted-foreground", resistance: "text-blue-400", immunity: "text-green-400",
};

interface RawActor {
  _id?: string;
  name?: string;
  system?: {
    details?: {
      species?: string;
      biography?: string | { value?: string };
    };
    attributes?: Record<string, { die?: { sides?: number; modifier?: number } }>;
    stats?: {
      toughness?: { value?: number; armor?: number };
      parry?: { value?: number };
      speed?: { value?: number };
    };
    resources?: {
      mp?: { value?: number; max?: number };
      ip?: { value?: number; max?: number };
    };
    wounds?: { value?: number; max?: number };
    fatigue?: { value?: number; max?: number };
    bennies?: { value?: number; max?: number };
    advances?: { value?: number };
    elementalResistances?: Record<string, string>;
    bonds?: { target?: string; type?: string; description?: string }[];
  };
  items?: { _id?: string; type?: string; name?: string; system?: Record<string, unknown> }[];
}

interface Props {
  characterId: string;
  onBack: () => void;
}

export default function SWADECharacterSheetEditor({ characterId, onBack }: Props) {
  const [raw, setRaw] = useState<RawActor | null>(null);
  const [loading, setLoading] = useState(true);
  const [editName, setEditName] = useState(false);
  const [nameVal, setNameVal] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const resp = await fetch(`${API}/api/characters/${characterId}/fvtt`);
        if (resp.ok) setRaw(await resp.json());
      } catch { /* */ }
      setLoading(false);
    })();
  }, [characterId]);

  if (loading) return <div className="text-center text-muted-foreground py-12">加载中…</div>;
  if (!raw) return <div className="text-center text-red-400 py-12">无法加载角色数据</div>;

  const sys = raw.system || {};
  const attrs = sys.attributes || {};
  const stats = sys.stats || {};
  const resources = sys.resources || {};
  const mp = resources.mp || {};
  const ip = resources.ip || {};
  const wounds = sys.wounds || {};
  const fatigue = sys.fatigue || {};
  const bennies = sys.bennies || {};
  const details = sys.details || {};
  const elemResist = sys.elementalResistances || {};
  const bonds = sys.bonds || [];
  const items = raw.items || [];

  const edges = items.filter((i) => i.type === "edge");
  const hindrances = items.filter((i) => i.type === "hindrance");
  const gear = items.filter((i) => ["gear", "weapon", "armor", "shield"].includes(i.type || ""));
  const powers = items.filter((i) => i.type === "power");

  const species = details.species || "";
  const bio = typeof details.biography === "string" ? details.biography : details.biography?.value || "";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          {editName ? (
            <div className="flex items-center gap-2">
              <input
                value={nameVal}
                onChange={(e) => setNameVal(e.target.value)}
                className="text-xl font-bold bg-secondary px-2 py-1 rounded border border-border text-foreground"
                autoFocus
              />
              <button onClick={async () => {
                await fetch(`${API}/api/characters/${characterId}`, {
                  method: "PATCH",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ name: nameVal }),
                });
                setRaw({ ...raw, name: nameVal });
                setEditName(false);
              }}>
                <Check className="h-4 w-4 text-green-400" />
              </button>
              <button onClick={() => setEditName(false)}>
                <X className="h-4 w-4 text-muted-foreground" />
              </button>
            </div>
          ) : (
            <h3
              className="text-xl font-bold text-foreground cursor-pointer hover:text-amber-400 flex items-center gap-2"
              onClick={() => { setNameVal(raw.name || ""); setEditName(true); }}
            >
              {raw.name || "Unknown"}
              <Pencil className="h-3 w-3 opacity-40" />
            </h3>
          )}
          <p className="text-sm text-muted-foreground">
            {species && `${species} · `}等级 {sys.advances?.value ?? 0}
          </p>
        </div>
        <Swords className="h-6 w-6 text-amber-400" />
      </div>

      {/* Attributes */}
      <div>
        <h4 className="text-sm font-semibold text-foreground mb-2">属性</h4>
        <div className="grid grid-cols-5 gap-2">
          {Object.entries(ATTR_LABELS).map(([key, label]) => {
            const die = attrs[key]?.die;
            const sides = die?.sides ?? 4;
            return (
              <div key={key} className="text-center p-2 rounded-lg bg-secondary/50 border border-border">
                <div className="text-xs text-muted-foreground">{label}</div>
                <div className={cn(
                  "font-bold text-lg",
                  sides >= 10 ? "text-yellow-400" : sides >= 8 ? "text-green-400" : sides >= 6 ? "text-blue-400" : "text-muted-foreground",
                )}>
                  d{sides}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Derived stats + Resources */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-xl bg-secondary/50 border border-border">
          <div className="grid grid-cols-3 gap-2 text-center text-sm">
            <div>
              <div className="text-muted-foreground">坚韧</div>
              <div className="font-bold text-foreground">{stats.toughness?.value ?? 5}{(stats.toughness?.armor ?? 0) > 0 ? ` (${stats.toughness?.armor})` : ""}</div>
            </div>
            <div>
              <div className="text-muted-foreground">格挡</div>
              <div className="font-bold text-foreground">{stats.parry?.value ?? 4}</div>
            </div>
            <div>
              <div className="text-muted-foreground">移速</div>
              <div className="font-bold text-foreground">{stats.speed?.value ?? 6}</div>
            </div>
          </div>
        </div>
        <div className="p-3 rounded-xl bg-secondary/50 border border-border">
          <div className="grid grid-cols-2 gap-2 text-center text-sm">
            <div>
              <div className="text-muted-foreground flex items-center justify-center gap-1"><Zap className="h-3 w-3 text-blue-400" />MP</div>
              <div className="font-bold text-foreground">{mp.value ?? 0} / {mp.max ?? 0}</div>
            </div>
            <div>
              <div className="text-muted-foreground flex items-center justify-center gap-1"><Heart className="h-3 w-3 text-red-400" />IP</div>
              <div className="font-bold text-foreground">{ip.value ?? 0} / {ip.max ?? 0}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Wounds / Fatigue / Bennies */}
      <div className="grid grid-cols-3 gap-2 text-sm text-center">
        <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/30">
          <div className="text-muted-foreground">负伤</div>
          <div className="font-bold text-foreground">{wounds.value ?? 0} / {wounds.max ?? 3}</div>
        </div>
        <div className="p-2 rounded-lg bg-orange-500/10 border border-orange-500/30">
          <div className="text-muted-foreground">疲劳</div>
          <div className="font-bold text-foreground">{fatigue.value ?? 0} / {fatigue.max ?? 2}</div>
        </div>
        <div className="p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
          <div className="text-muted-foreground">坚毅点</div>
          <div className="font-bold text-foreground">{bennies.value ?? 3} / {bennies.max ?? 3}</div>
        </div>
      </div>

      {/* Edges & Hindrances */}
      {edges.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">专长 (Edges)</h4>
          <div className="space-y-1">
            {edges.map((e) => (
              <div key={e._id} className="px-3 py-2 rounded-lg bg-green-500/10 border border-green-500/20 text-sm text-foreground">
                {e.name}
              </div>
            ))}
          </div>
        </div>
      )}
      {hindrances.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">负赘 (Hindrances)</h4>
          <div className="space-y-1">
            {hindrances.map((h) => (
              <div key={h._id} className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-foreground flex justify-between">
                <span>{h.name}</span>
                {Boolean(h.system?.major) && <span className="text-xs text-red-400">主要</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Gear */}
      {gear.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">装备</h4>
          <div className="space-y-1">
            {gear.map((g) => (
              <div key={g._id} className="px-3 py-2 rounded-lg bg-secondary/50 text-sm text-foreground flex justify-between">
                <span>{g.name}</span>
                {Boolean(g.system?.damage) && <span className="text-muted-foreground">{String(g.system!.damage)}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Powers */}
      {powers.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">异能 (Powers)</h4>
          <div className="space-y-1">
            {powers.map((p) => (
              <div key={p._id} className="px-3 py-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-sm text-foreground">
                {p.name}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Elemental Resistances */}
      {Object.keys(elemResist).length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">元素抗性</h4>
          <div className="grid grid-cols-4 gap-2">
            {Object.entries(elemResist).map(([el, level]) => (
              <div key={el} className="text-center p-2 rounded-lg bg-secondary/50 border border-border">
                <div className={cn("text-xs font-medium", ELEMENT_COLORS[el] || "text-foreground")}>
                  {ELEMENT_LABELS[el] || el}
                </div>
                <div className={cn("text-xs", RESIST_COLOR[level] || "text-muted-foreground")}>
                  {RESIST_LABEL[level] || level}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bonds */}
      {bonds.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">羁绊 (Bonds)</h4>
          <div className="space-y-1">
            {bonds.map((b, i) => (
              <div key={i} className="px-3 py-2 rounded-lg bg-secondary/50 text-sm text-foreground">
                <span className="font-medium">{b.target}</span>
                {b.description && <span className="text-muted-foreground ml-2">{b.description}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Biography */}
      {bio && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">背景</h4>
          <div className="text-sm text-muted-foreground bg-secondary/50 rounded-lg p-3 whitespace-pre-wrap">
            {bio}
          </div>
        </div>
      )}
    </div>
  );
}
