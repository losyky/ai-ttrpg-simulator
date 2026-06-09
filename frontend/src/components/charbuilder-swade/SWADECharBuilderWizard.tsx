"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  User,
  Flame,
  Shield,
  Heart,
  Swords,
  Plus,
  Minus,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const SWADE_ATTRS = ["agility", "smarts", "spirit", "strength", "vigor"] as const;
const ATTR_LABELS: Record<string, string> = {
  agility: "灵巧 (Agility)",
  smarts: "聪慧 (Smarts)",
  spirit: "心魂 (Spirit)",
  strength: "力量 (Strength)",
  vigor: "活力 (Vigor)",
};
const DIE_STEPS = [4, 6, 8, 10, 12];
const DIE_COLORS: Record<number, string> = {
  4: "text-muted-foreground",
  6: "text-blue-400",
  8: "text-green-400",
  10: "text-yellow-400",
  12: "text-red-400",
};

const RACES = [
  { slug: "human", name: "人类", trait: "+1 自由专长" },
  { slug: "elf", name: "精灵", trait: "低光视觉，灵巧 d6 起步" },
  { slug: "dwarf", name: "矮人", trait: "活力 d6 起步，低光视觉" },
  { slug: "halfling", name: "半身人", trait: "幸运，体型-1" },
  { slug: "beastkin", name: "兽人", trait: "力量 d6 起步，坚韧+1" },
  { slug: "dragonborn", name: "龙裔", trait: "龙息，元素抗性" },
  { slug: "fairy", name: "妖精", trait: "飞行(移速4)，体型-2" },
  { slug: "undead", name: "亡灵", trait: "不死者特质" },
  { slug: "demon", name: "魔族", trait: "暗元素亲和" },
  { slug: "angel", name: "天使", trait: "光元素亲和" },
  { slug: "construct", name: "人造体", trait: "不需呼吸/进食" },
];

const ELEMENTS = [
  { slug: "fire", name: "火", color: "text-red-400" },
  { slug: "ice", name: "冰", color: "text-cyan-400" },
  { slug: "earth", name: "土", color: "text-amber-600" },
  { slug: "wind", name: "风", color: "text-emerald-400" },
  { slug: "thunder", name: "雷", color: "text-yellow-400" },
  { slug: "light", name: "光", color: "text-yellow-200" },
  { slug: "dark", name: "暗", color: "text-purple-400" },
];

const RESISTANCE_OPTIONS = [
  { value: "weakness", label: "弱点", color: "text-red-400" },
  { value: "normal", label: "正常", color: "text-muted-foreground" },
  { value: "resistance", label: "抗性", color: "text-blue-400" },
  { value: "immunity", label: "免疫", color: "text-green-400" },
];

interface SWADEBuild {
  name: string;
  race: string;
  attributes: Record<string, number>;
  edges: { name: string; description: string; rank: string }[];
  hindrances: { name: string; description: string; major: boolean }[];
  equipment: { name: string; damage: string; weight: number; notes: string }[];
  bonds: { target: string; type: string; description: string }[];
  elementalResistances: Record<string, string>;
  armor: number;
  level: number;
  pace: number;
  background: string;
}

const INITIAL: SWADEBuild = {
  name: "",
  race: "",
  attributes: Object.fromEntries(SWADE_ATTRS.map((a) => [a, 4])),
  edges: [],
  hindrances: [],
  equipment: [],
  bonds: [],
  elementalResistances: Object.fromEntries(ELEMENTS.map((e) => [e.slug, "normal"])),
  armor: 0,
  level: 0,
  pace: 6,
  background: "",
};

const STEPS = [
  { key: "basics", label: "基础" },
  { key: "attrs", label: "属性" },
  { key: "edges", label: "专长/负赘" },
  { key: "equip", label: "装备/羁绊" },
  { key: "elements", label: "元素" },
  { key: "review", label: "总览" },
];

interface Props {
  onComplete: () => void;
  onCancel: () => void;
}

export default function SWADECharBuilderWizard({ onComplete, onCancel }: Props) {
  const [step, setStep] = useState(0);
  const [build, setBuild] = useState<SWADEBuild>({ ...INITIAL });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [showCustomRace, setShowCustomRace] = useState(false);
  const [customRaceName, setCustomRaceName] = useState("");
  const [customRaceTrait, setCustomRaceTrait] = useState("");

  // Dynamic race data from API (includes custom compendium entries)
  const [raceList, setRaceList] = useState(RACES);

  useEffect(() => {
    (async () => {
      try {
        const resp = await fetch(`${API}/api/swade/charbuilder/races`);
        if (resp.ok) {
          const data = await resp.json();
          if (Array.isArray(data) && data.length > 0) {
            setRaceList(data.map((r: any) => ({
              slug: r.slug,
              name: r.name_cn || r.name || r.slug,
              trait: r.trait || "",
            })));
          }
        }
      } catch { /* use defaults */ }
    })();
  }, []);

  const update = useCallback(
    <K extends keyof SWADEBuild>(key: K, val: SWADEBuild[K]) =>
      setBuild((prev) => ({ ...prev, [key]: val })),
    [],
  );

  // Points used is shown as a reference only – no hard cap enforced.
  const pointsUsed = useMemo(
    () => SWADE_ATTRS.reduce((sum, a) => sum + DIE_STEPS.indexOf(build.attributes[a]), 0),
    [build.attributes],
  );
  const POINTS_REFERENCE = 5; // standard starting allocation (informational)

  const adjustAttr = useCallback(
    (attr: string, delta: number) => {
      setBuild((prev) => {
        const cur = prev.attributes[attr];
        const idx = DIE_STEPS.indexOf(cur);
        const newIdx = idx + delta;
        if (newIdx < 0 || newIdx >= DIE_STEPS.length) return prev;
        return { ...prev, attributes: { ...prev.attributes, [attr]: DIE_STEPS[newIdx] } };
      });
    },
    [],
  );

  const setAttrDirect = useCallback((attr: string, sides: number) => {
    const clamped = DIE_STEPS.includes(sides) ? sides : DIE_STEPS.reduce((prev, cur) =>
      Math.abs(cur - sides) < Math.abs(prev - sides) ? cur : prev
    );
    setBuild((prev) => ({ ...prev, attributes: { ...prev.attributes, [attr]: clamped } }));
  }, []);

  const calcToughness = () => {
    const vigorDie = build.attributes.vigor || 4;
    return Math.floor(vigorDie / 2) + 2 + build.armor;
  };
  const calcParry = () => {
    const agiDie = build.attributes.agility || 4;
    return Math.floor(agiDie / 2) + 2;
  };
  const calcMP = () => {
    const spiritDie = build.attributes.spirit || 4;
    const lv = build.level;
    const rank = Math.floor(lv / 4) + 1;
    return rank * 2 + spiritDie * 5;
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      const body = {
        name: build.name || "New Character",
        race: build.race,
        attributes: build.attributes,
        edges: build.edges,
        hindrances: build.hindrances,
        equipment: build.equipment,
        bonds: build.bonds,
        elemental_resistances: build.elementalResistances,
        armor: build.armor,
        level: build.level,
        pace: build.pace,
        background: build.background,
      };
      const resp = await fetch(`${API}/api/swade/charbuilder/assemble`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) throw new Error(await resp.text());
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const canNext = () => {
    switch (step) {
      case 0: return !!build.name && !!build.race;
      default: return true;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
          <Swords className="h-5 w-5 text-amber-400" />
          七物语 角色创建
        </h3>
        <button onClick={onCancel} className="text-sm text-muted-foreground hover:text-foreground">
          取消
        </button>
      </div>

      {/* Step indicators */}
      <div className="flex gap-1">
        {STEPS.map((s, i) => (
          <button
            key={s.key}
            onClick={() => i <= step && setStep(i)}
            className={cn(
              "flex-1 py-1.5 text-xs rounded-lg transition-all",
              i === step
                ? "bg-amber-500/20 text-amber-300 font-medium"
                : i < step
                  ? "bg-amber-500/10 text-amber-400/60 cursor-pointer"
                  : "bg-secondary/50 text-muted-foreground",
            )}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Step 0: Basics */}
      {step === 0 && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">角色名</label>
            <input
              value={build.name}
              onChange={(e) => update("name", e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-foreground"
              placeholder="输入角色名称…"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">等级 (Advances)</label>
              <input
                type="number"
                min={0}
                max={20}
                value={build.level}
                onChange={(e) => update("level", parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-foreground"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">移速 (Pace)</label>
              <input
                type="number"
                min={1}
                value={build.pace}
                onChange={(e) => update("pace", parseInt(e.target.value) || 6)}
                className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-foreground"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">种族</label>
            <div className="grid grid-cols-2 gap-2 max-h-60 overflow-y-auto">
              {raceList.map((r) => (
                <button
                  key={r.slug}
                  onClick={() => { update("race", r.name); setShowCustomRace(false); }}
                  className={cn(
                    "p-3 rounded-lg text-left transition-all border",
                    build.race === r.name && !showCustomRace
                      ? "border-amber-500 bg-amber-500/20"
                      : "border-border bg-secondary/50 hover:border-amber-500/50",
                  )}
                >
                  <div className="font-medium text-sm text-foreground">{r.name}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{r.trait}</div>
                </button>
              ))}
              <button
                onClick={() => { setShowCustomRace(true); update("race", customRaceName || ""); }}
                className={cn(
                  "p-3 rounded-lg text-left transition-all border border-dashed",
                  showCustomRace
                    ? "border-amber-500 bg-amber-500/20"
                    : "border-border bg-secondary/30 hover:border-amber-500/50",
                )}
              >
                <div className="font-medium text-sm text-muted-foreground">+ 自定义种族</div>
                <div className="text-xs text-muted-foreground mt-0.5">输入自定义种族及特质</div>
              </button>
            </div>
            {showCustomRace && (
              <div className="mt-2 space-y-2 p-3 rounded-lg bg-secondary/30 border border-amber-500/30">
                <input
                  value={customRaceName}
                  onChange={(e) => { setCustomRaceName(e.target.value); update("race", e.target.value); }}
                  className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm"
                  placeholder="种族名称…"
                  autoFocus
                />
                <input
                  value={customRaceTrait}
                  onChange={(e) => setCustomRaceTrait(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm"
                  placeholder="种族特质描述（可选）…"
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Step 1: Attributes */}
      {step === 1 && (
        <div className="space-y-4">
          <div className="text-sm text-muted-foreground space-y-1">
            <p>每个属性从 d4 起步，按骰阶升级 (d4→d6→d8→d10→d12)。</p>
            <p className="text-xs text-muted-foreground/70">
              标准起始 5 点分配仅供参考，可自由调整（点击骰面数字可直接输入）。
            </p>
          </div>
          <div className={cn(
            "text-xs px-3 py-1.5 rounded-lg text-center",
            pointsUsed <= POINTS_REFERENCE
              ? "bg-secondary text-muted-foreground"
              : "bg-amber-500/10 text-amber-400",
          )}>
            已使用 {pointsUsed} 档升级 · 参考基准 {POINTS_REFERENCE} 档
            {pointsUsed > POINTS_REFERENCE && ` · 已超出 ${pointsUsed - POINTS_REFERENCE} 档`}
          </div>
          <div className="space-y-3">
            {SWADE_ATTRS.map((a) => (
              <div key={a} className="flex items-center justify-between p-3 rounded-lg bg-secondary/50 border border-border">
                <span className="text-sm font-medium text-foreground">{ATTR_LABELS[a]}</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => adjustAttr(a, -1)}
                    disabled={build.attributes[a] <= 4}
                    className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground disabled:opacity-30"
                  >
                    <Minus className="h-4 w-4" />
                  </button>
                  <div className="relative w-14 text-center">
                    <input
                      type="number"
                      min={4}
                      max={12}
                      step={2}
                      value={build.attributes[a]}
                      aria-label={`${ATTR_LABELS[a]} 骰面`}
                      title={`${ATTR_LABELS[a]} 骰面（4/6/8/10/12）`}
                      onChange={(e) => {
                        const v = parseInt(e.target.value);
                        if (!isNaN(v)) setAttrDirect(a, v);
                      }}
                      className={cn(
                        "w-full text-center font-bold text-lg bg-transparent border-b border-transparent",
                        "hover:border-border focus:border-primary focus:outline-none",
                        DIE_COLORS[build.attributes[a]] || "text-foreground",
                      )}
                    />
                    <span className={cn(
                      "absolute -left-1 top-0 text-lg font-bold pointer-events-none",
                      DIE_COLORS[build.attributes[a]] || "text-foreground",
                    )}>d</span>
                  </div>
                  <button
                    onClick={() => adjustAttr(a, 1)}
                    disabled={build.attributes[a] >= 12}
                    className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground disabled:opacity-30"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-3 gap-2 text-sm text-center">
            <div className="p-2 rounded-lg bg-secondary/50">
              <div className="text-muted-foreground">坚韧</div>
              <div className="font-bold text-foreground">{calcToughness()}</div>
            </div>
            <div className="p-2 rounded-lg bg-secondary/50">
              <div className="text-muted-foreground">格挡</div>
              <div className="font-bold text-foreground">{calcParry()}</div>
            </div>
            <div className="p-2 rounded-lg bg-secondary/50">
              <div className="text-muted-foreground">MP</div>
              <div className="font-bold text-foreground">{calcMP()}</div>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">护甲值 (总计)</label>
            <input
              type="number"
              min={0}
              value={build.armor}
              onChange={(e) => update("armor", parseInt(e.target.value) || 0)}
              className="w-32 px-3 py-2 rounded-lg bg-secondary border border-border text-foreground"
            />
          </div>
        </div>
      )}

      {/* Step 2: Edges & Hindrances */}
      {step === 2 && (
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-foreground">专长 (Edges)</label>
              <button
                onClick={() => update("edges", [...build.edges, { name: "", description: "", rank: "novice" }])}
                className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1"
              >
                <Plus className="h-3 w-3" /> 添加
              </button>
            </div>
            {build.edges.map((edge, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <input
                  value={edge.name}
                  onChange={(e) => {
                    const newEdges = [...build.edges];
                    newEdges[i] = { ...edge, name: e.target.value };
                    update("edges", newEdges);
                  }}
                  className="flex-1 px-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm"
                  placeholder="专长名称"
                />
                <input
                  value={edge.description}
                  onChange={(e) => {
                    const newEdges = [...build.edges];
                    newEdges[i] = { ...edge, description: e.target.value };
                    update("edges", newEdges);
                  }}
                  className="flex-1 px-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm"
                  placeholder="描述"
                />
                <button
                  onClick={() => update("edges", build.edges.filter((_, j) => j !== i))}
                  className="text-muted-foreground hover:text-red-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-foreground">负赘 (Hindrances)</label>
              <button
                onClick={() => update("hindrances", [...build.hindrances, { name: "", description: "", major: false }])}
                className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1"
              >
                <Plus className="h-3 w-3" /> 添加
              </button>
            </div>
            {build.hindrances.map((hind, i) => (
              <div key={i} className="flex gap-2 mb-2 items-center">
                <input
                  value={hind.name}
                  onChange={(e) => {
                    const newH = [...build.hindrances];
                    newH[i] = { ...hind, name: e.target.value };
                    update("hindrances", newH);
                  }}
                  className="flex-1 px-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm"
                  placeholder="负赘名称"
                />
                <button
                  onClick={() => {
                    const newH = [...build.hindrances];
                    newH[i] = { ...hind, major: !hind.major };
                    update("hindrances", newH);
                  }}
                  className={cn(
                    "px-2 py-1.5 rounded-lg text-xs border",
                    hind.major
                      ? "border-red-500/50 bg-red-500/20 text-red-400"
                      : "border-border bg-secondary text-muted-foreground",
                  )}
                >
                  {hind.major ? "主要" : "次要"}
                </button>
                <button
                  onClick={() => update("hindrances", build.hindrances.filter((_, j) => j !== i))}
                  className="text-muted-foreground hover:text-red-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Step 3: Equipment & Bonds */}
      {step === 3 && (
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-foreground">装备</label>
              <button
                onClick={() => update("equipment", [...build.equipment, { name: "", damage: "", weight: 0, notes: "" }])}
                className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1"
              >
                <Plus className="h-3 w-3" /> 添加
              </button>
            </div>
            {build.equipment.map((eq, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <input
                  value={eq.name}
                  onChange={(e) => {
                    const newEq = [...build.equipment];
                    newEq[i] = { ...eq, name: e.target.value };
                    update("equipment", newEq);
                  }}
                  className="flex-1 px-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm"
                  placeholder="名称"
                />
                <input
                  value={eq.damage}
                  onChange={(e) => {
                    const newEq = [...build.equipment];
                    newEq[i] = { ...eq, damage: e.target.value };
                    update("equipment", newEq);
                  }}
                  className="w-24 px-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm"
                  placeholder="伤害"
                />
                <button
                  onClick={() => update("equipment", build.equipment.filter((_, j) => j !== i))}
                  className="text-muted-foreground hover:text-red-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-foreground">羁绊 (Bonds)</label>
              <button
                onClick={() => update("bonds", [...build.bonds, { target: "", type: "loyalty", description: "" }])}
                className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1"
              >
                <Plus className="h-3 w-3" /> 添加
              </button>
            </div>
            {build.bonds.map((bond, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <input
                  value={bond.target}
                  onChange={(e) => {
                    const newB = [...build.bonds];
                    newB[i] = { ...bond, target: e.target.value };
                    update("bonds", newB);
                  }}
                  className="w-28 px-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm"
                  placeholder="对象"
                />
                <input
                  value={bond.description}
                  onChange={(e) => {
                    const newB = [...build.bonds];
                    newB[i] = { ...bond, description: e.target.value };
                    update("bonds", newB);
                  }}
                  className="flex-1 px-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm"
                  placeholder="描述"
                />
                <button
                  onClick={() => update("bonds", build.bonds.filter((_, j) => j !== i))}
                  className="text-muted-foreground hover:text-red-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">背景故事</label>
            <textarea
              value={build.background}
              onChange={(e) => update("background", e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-foreground h-24 resize-none"
              placeholder="描述你的角色背景…"
            />
          </div>
        </div>
      )}

      {/* Step 4: Elemental Resistances */}
      {step === 4 && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">设置角色的元素抗性。默认为「正常」。</p>
          <div className="space-y-2">
            {ELEMENTS.map((el) => (
              <div key={el.slug} className="flex items-center justify-between p-3 rounded-lg bg-secondary/50 border border-border">
                <span className={cn("text-sm font-medium", el.color)}>
                  <Flame className="h-4 w-4 inline mr-1" />
                  {el.name}
                </span>
                <div className="flex gap-1">
                  {RESISTANCE_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() =>
                        update("elementalResistances", {
                          ...build.elementalResistances,
                          [el.slug]: opt.value,
                        })
                      }
                      className={cn(
                        "px-2 py-1 rounded text-xs transition-all",
                        build.elementalResistances[el.slug] === opt.value
                          ? cn("font-medium border", opt.color, "bg-secondary border-current")
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Step 5: Review */}
      {step === 5 && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-secondary/50 border border-border space-y-3">
            <div className="flex items-center gap-3">
              <User className="h-5 w-5 text-amber-400" />
              <div>
                <h4 className="font-bold text-foreground text-lg">{build.name || "无名角色"}</h4>
                <p className="text-sm text-muted-foreground">{build.race} · 等级 {build.level}</p>
              </div>
            </div>
            <div className="grid grid-cols-5 gap-2">
              {SWADE_ATTRS.map((a) => (
                <div key={a} className="text-center p-2 rounded-lg bg-secondary">
                  <div className="text-xs text-muted-foreground">{ATTR_LABELS[a].split(" ")[0]}</div>
                  <div className={cn("font-bold", DIE_COLORS[build.attributes[a]])}>
                    d{build.attributes[a]}
                  </div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-4 gap-2 text-sm text-center">
              <div className="p-2 rounded-lg bg-secondary/50">
                <div className="text-muted-foreground">坚韧</div>
                <div className="font-bold text-foreground">{calcToughness()}</div>
              </div>
              <div className="p-2 rounded-lg bg-secondary/50">
                <div className="text-muted-foreground">格挡</div>
                <div className="font-bold text-foreground">{calcParry()}</div>
              </div>
              <div className="p-2 rounded-lg bg-secondary/50">
                <div className="text-muted-foreground">MP</div>
                <div className="font-bold text-foreground">{calcMP()}</div>
              </div>
              <div className="p-2 rounded-lg bg-secondary/50">
                <div className="text-muted-foreground">移速</div>
                <div className="font-bold text-foreground">{build.pace}</div>
              </div>
            </div>
            {build.edges.length > 0 && (
              <div className="text-sm">
                <span className="text-muted-foreground">专长: </span>
                <span className="text-foreground">{build.edges.map((e) => e.name).filter(Boolean).join("、") || "无"}</span>
              </div>
            )}
            {build.hindrances.length > 0 && (
              <div className="text-sm">
                <span className="text-muted-foreground">负赘: </span>
                <span className="text-foreground">
                  {build.hindrances.map((h) => `${h.name}${h.major ? "(主要)" : "(次要)"}`).filter((s) => s.length > 4).join("、") || "无"}
                </span>
              </div>
            )}
            {build.bonds.length > 0 && (
              <div className="text-sm">
                <span className="text-muted-foreground">羁绊: </span>
                <span className="text-foreground">{build.bonds.map((b) => `${b.target}: ${b.description}`).filter(Boolean).join("、")}</span>
              </div>
            )}
          </div>
          {error && <div className="text-sm text-red-400 bg-red-400/10 rounded-lg px-4 py-2">{error}</div>}
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-2">
        <button
          onClick={() => (step === 0 ? onCancel() : setStep(step - 1))}
          className="flex items-center gap-1 px-4 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {step === 0 ? "取消" : "上一步"}
        </button>
        {step < STEPS.length - 1 ? (
          <button
            onClick={() => setStep(step + 1)}
            disabled={!canNext()}
            className={cn(
              "flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              canNext()
                ? "bg-amber-500 text-white hover:bg-amber-600"
                : "bg-secondary text-muted-foreground cursor-not-allowed",
            )}
          >
            下一步
            <ArrowRight className="h-4 w-4" />
          </button>
        ) : (
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium bg-amber-500 text-white hover:bg-amber-600 transition-all disabled:opacity-50"
          >
            {saving ? "创建中…" : "创建角色"}
            <Check className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
