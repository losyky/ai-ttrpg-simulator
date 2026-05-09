"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowUp,
  Heart,
  Shield,
  Star,
  Sparkles,
  Pencil,
  Check,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import DHLevelUpPanel from "@/components/charbuilder-dh/DHLevelUpPanel";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DH_TRAIT_LABELS: Record<string, string> = {
  agility: "敏捷 (Agility)",
  strength: "力量 (Strength)",
  finesse: "灵巧 (Finesse)",
  instinct: "本能 (Instinct)",
  presence: "风度 (Presence)",
  knowledge: "学识 (Knowledge)",
};

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
  items?: { _id?: string; type?: string; name?: string; system?: Record<string, unknown> }[];
}

interface Props {
  characterId: string;
  onBack: () => void;
}

export default function DHCharacterSheetEditor({ characterId, onBack }: Props) {
  const [raw, setRaw] = useState<RawActor | null>(null);
  const [loading, setLoading] = useState(true);
  const [editName, setEditName] = useState(false);
  const [nameVal, setNameVal] = useState("");
  const [showLevelUp, setShowLevelUp] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const resp = await fetch(`${API}/api/characters/${characterId}/fvtt`);
        if (resp.ok) setRaw(await resp.json());
      } catch { /* */ }
      setLoading(false);
    })();
  }, [characterId, reloadKey]);

  if (showLevelUp) {
    return <DHLevelUpPanel characterId={characterId} onBack={() => setShowLevelUp(false)}
      onComplete={() => { setShowLevelUp(false); setReloadKey(k => k + 1); }} />;
  }

  if (loading) return <div className="text-center text-muted-foreground py-12">加载中…</div>;
  if (!raw) return <div className="text-center text-red-400 py-12">无法加载角色数据</div>;

  const sys = raw.system || {};
  const resources = sys.resources || {};
  const hp = resources.hitPoints || {};
  const stress = resources.stress || {};
  const hope = resources.hope || {};
  const traits = sys.traits || {};
  const heritage = sys.heritage || {};
  const items = raw.items || [];

  const domainCards = items.filter((i) => i.type === "domainCard");
  const weapons = items.filter((i) => i.type === "weapon");
  const armor = items.filter((i) => i.type === "armor");
  const features = items.filter((i) => i.type === "feature");
  const loot = items.filter((i) => i.type === "loot" || i.type === "consumable");

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
              className="text-xl font-bold text-foreground cursor-pointer hover:text-violet-400 flex items-center gap-2"
              onClick={() => { setNameVal(raw.name || ""); setEditName(true); }}
            >
              {raw.name || "Unknown"}
              <Pencil className="h-3 w-3 opacity-40" />
            </h3>
          )}
          <p className="text-sm text-muted-foreground">
            {heritage.ancestry || ""} · {heritage.community || ""} · {sys.class || ""}{sys.subclass ? ` / ${sys.subclass}` : ""}
          </p>
        </div>
        <Sparkles className="h-6 w-6 text-violet-400" />
      </div>

      {/* Resources bar */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-center">
          <Heart className="h-4 w-4 mx-auto text-red-400 mb-1" />
          <div className="font-bold text-foreground">{hp.value ?? 0} / {hp.max ?? 0}</div>
          <div className="text-xs text-muted-foreground">HP</div>
        </div>
        <div className="p-3 rounded-xl bg-orange-500/10 border border-orange-500/30 text-center">
          <Shield className="h-4 w-4 mx-auto text-orange-400 mb-1" />
          <div className="font-bold text-foreground">{stress.value ?? 0} / {stress.max ?? 0}</div>
          <div className="text-xs text-muted-foreground">Stress</div>
        </div>
        <div className="p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-center">
          <Star className="h-4 w-4 mx-auto text-yellow-400 mb-1" />
          <div className="font-bold text-foreground">{hope.value ?? 0} / {hope.max ?? 0}</div>
          <div className="text-xs text-muted-foreground">Hope</div>
        </div>
      </div>

      {/* Level & Evasion & Armor */}
      <div className="flex items-center gap-4 text-sm flex-wrap">
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground">等级:</span>
          <span className="font-bold text-amber-300">{sys.level ?? 1}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground">闪避:</span>
          <span className="font-bold text-foreground">{sys.evasion ?? 0}</span>
        </div>
        {resources.armorSlots && (
          <div className="flex items-center gap-1">
            <span className="text-muted-foreground">护甲槽:</span>
            <span className="font-bold text-foreground">{resources.armorSlots.value ?? 0}/{resources.armorSlots.max ?? 0}</span>
          </div>
        )}
        {sys.proficiency !== undefined && (
          <div className="flex items-center gap-1">
            <span className="text-muted-foreground">熟练:</span>
            <span className="font-bold text-foreground">+{sys.proficiency}</span>
          </div>
        )}
        <button onClick={() => setShowLevelUp(true)}
          className="ml-auto flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 transition-all border border-amber-500/30">
          <ArrowUp className="h-3 w-3" /> 升级
        </button>
      </div>

      {/* Traits */}
      <div>
        <h4 className="text-sm font-semibold text-foreground mb-2">特质 (Traits)</h4>
        <div className="grid grid-cols-3 gap-2">
          {Object.entries(DH_TRAIT_LABELS).map(([key, label]) => {
            const val = traits[key]?.value ?? 0;
            return (
              <div key={key} className="text-center p-2 rounded-lg bg-secondary/50 border border-border">
                <div className="text-xs text-muted-foreground">{label}</div>
                <div className={cn(
                  "font-bold text-lg",
                  val > 0 ? "text-green-400" : val < 0 ? "text-red-400" : "text-foreground",
                )}>
                  {val >= 0 ? `+${val}` : val}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Domain Cards */}
      {domainCards.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">领域卡 (Domain Cards)</h4>
          <div className="space-y-1">
            {domainCards.map((dc) => (
              <div key={dc._id} className="px-3 py-2 rounded-lg bg-violet-500/10 border border-violet-500/30 text-sm text-foreground">
                {dc.name}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Weapons */}
      {weapons.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">武器</h4>
          <div className="space-y-1">
            {weapons.map((w) => (
              <div key={w._id} className="px-3 py-2 rounded-lg bg-secondary/50 text-sm text-foreground flex justify-between">
                <span>{w.name}</span>
                {w.system?.damage ? <span className="text-muted-foreground">{String(w.system.damage)}</span> : null}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Armor */}
      {armor.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">护甲</h4>
          <div className="space-y-1">
            {armor.map((a) => (
              <div key={a._id} className="px-3 py-2 rounded-lg bg-blue-500/10 border border-blue-500/30 text-sm text-foreground">
                {a.name}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Features */}
      {features.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">特性 (Features)</h4>
          <div className="space-y-1">
            {features.map((f) => (
              <div key={f._id} className="px-3 py-2 rounded-lg bg-secondary/50 text-sm text-foreground">
                {f.name}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Equipment */}
      {loot.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">物品</h4>
          <div className="flex flex-wrap gap-2">
            {loot.map((item) => (
              <span key={item._id} className="px-2 py-1 rounded-lg bg-secondary text-sm text-foreground">
                {item.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Experiences */}
      {sys.experiences && sys.experiences.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">经历 (Experiences)</h4>
          <div className="space-y-1">
            {sys.experiences.map((exp, i) => (
              <div key={i} className="px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-sm text-foreground">
                {exp} <span className="text-amber-400 text-xs">+2</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Background */}
      {sys.biography?.background && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">背景</h4>
          <div className="text-sm text-muted-foreground bg-secondary/50 rounded-lg p-3 whitespace-pre-wrap">
            {sys.biography.background}
          </div>
        </div>
      )}
    </div>
  );
}
