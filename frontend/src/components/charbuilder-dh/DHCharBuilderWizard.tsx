"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Sword,
  Shield,
  Heart,
  Star,
  User,
  Scroll,
  Sparkles,
  Search,
  Zap,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DHBuildState {
  name: string;
  ancestry: string;
  community: string;
  className: string;
  subclass: string;
  traits: Record<string, number>;
  hp: number;
  evasion: number;
  stressMax: number;
  armorSlots: number;
  domainCards: string[];
  experiences: string[];
  equipment: string[];
  background: string;
  primaryWeapon: string;
  secondaryWeapon: string;
  armor: string;
}

const DH_TRAITS = ["agility", "strength", "finesse", "instinct", "presence", "knowledge"] as const;
const DH_TRAIT_LABELS: Record<string, string> = {
  agility: "敏捷 (Agility)",
  strength: "力量 (Strength)",
  finesse: "灵巧 (Finesse)",
  instinct: "本能 (Instinct)",
  presence: "风度 (Presence)",
  knowledge: "学识 (Knowledge)",
};

interface DHClassDef {
  slug: string;
  name: string;
  name_cn?: string;
  domains: string[];
  base_hp?: number;
  base_evasion?: number;
  base_stress?: number;
  hp?: number;
  evasion?: number;
  stress?: number;
  fvtt_id?: string;
  description?: string;
}

interface DHSubclassDef {
  slug: string;
  name: string;
  name_cn?: string;
  linked_class?: string;
  spellcasting_trait?: string;
  description?: string;
  fvtt_id?: string;
}

interface DHWeaponDef {
  slug: string;
  name: string;
  name_cn?: string;
  tier: number;
  burden?: string;
  damage_die?: string;
  damage_type?: string;
  range?: string;
  description?: string;
}

interface DHArmorDef {
  slug: string;
  name: string;
  name_cn?: string;
  tier: number;
  base_score?: number;
  description?: string;
}

interface DHDomainCardDef {
  slug: string;
  name: string;
  name_cn?: string;
  domain: string;
  domain_cn?: string;
  level: number;
  card_type?: string;
  card_type_cn?: string;
  recall_cost?: number;
  description?: string;
}

interface Recommended {
  traits?: Record<string, number>;
  primary_weapon?: string;
  secondary_weapon?: string | null;
  armor?: string;
}

const DH_DOMAIN_LABELS: Record<string, string> = {
  arcana: "奥术 (Arcana)", blade: "利刃 (Blade)", bone: "骸骨 (Bone)",
  codex: "典籍 (Codex)", grace: "优雅 (Grace)", midnight: "午夜 (Midnight)",
  sage: "贤者 (Sage)", splendor: "辉耀 (Splendor)", valor: "勇气 (Valor)",
};

const VALID_DISTRIBUTIONS = [[-1, 0, 0, 1, 1, 2]];

const STEPS = [
  { key: "basics", label: "基础信息" },
  { key: "class", label: "职业与子职业" },
  { key: "traits", label: "特质" },
  { key: "equipment", label: "装备与领域卡" },
  { key: "review", label: "总览" },
];

const INITIAL: DHBuildState = {
  name: "",
  ancestry: "",
  community: "",
  className: "",
  subclass: "",
  traits: Object.fromEntries(DH_TRAITS.map((t) => [t, 0])),
  hp: 6,
  evasion: 8,
  stressMax: 6,
  armorSlots: 0,
  domainCards: [],
  experiences: ["", ""],
  equipment: [],
  background: "",
  primaryWeapon: "",
  secondaryWeapon: "",
  armor: "",
};

interface Props {
  onComplete: () => void;
  onCancel: () => void;
}

export default function DHCharBuilderWizard({ onComplete, onCancel }: Props) {
  const [step, setStep] = useState(0);
  const [build, setBuild] = useState<DHBuildState>({ ...INITIAL });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [equipInput, setEquipInput] = useState("");

  // custom entry states
  const [showCustomAncestry, setShowCustomAncestry] = useState(false);
  const [customAncestry, setCustomAncestry] = useState("");
  const [showCustomCommunity, setShowCustomCommunity] = useState(false);
  const [customCommunity, setCustomCommunity] = useState("");
  const [showCustomClass, setShowCustomClass] = useState(false);
  const [customClassName, setCustomClassName] = useState("");

  // data from API
  const [dhClasses, setDhClasses] = useState<DHClassDef[]>([]);
  const [dhAncestries, setDhAncestries] = useState<string[]>([]);
  const [dhCommunities, setDhCommunities] = useState<string[]>([]);
  const [dhSubclasses, setDhSubclasses] = useState<DHSubclassDef[]>([]);
  const [dhWeapons, setDhWeapons] = useState<DHWeaponDef[]>([]);
  const [dhArmors, setDhArmors] = useState<DHArmorDef[]>([]);
  const [dhDomainCards, setDhDomainCards] = useState<DHDomainCardDef[]>([]);
  const [recommended, setRecommended] = useState<Recommended>({});

  // search / filter
  const [weaponSearch, setWeaponSearch] = useState("");
  const [armorSearch, setArmorSearch] = useState("");
  const [dcSearch, setDcSearch] = useState("");
  const [dcDomainFilter, setDcDomainFilter] = useState<string>("all");
  const [weaponTierFilter, setWeaponTierFilter] = useState<number>(1);
  const [showSubclassDesc, setShowSubclassDesc] = useState<string | null>(null);

  useEffect(() => {
    const f = (url: string) => fetch(`${API}${url}`).then(r => r.json()).catch(() => []);
    Promise.all([
      f("/api/daggerheart/charbuilder/classes"),
      f("/api/daggerheart/charbuilder/ancestries"),
      f("/api/daggerheart/charbuilder/communities"),
      f("/api/daggerheart/charbuilder/subclasses"),
      f("/api/daggerheart/charbuilder/weapons"),
      f("/api/daggerheart/charbuilder/armors"),
      f("/api/daggerheart/charbuilder/domain-cards"),
    ]).then(([cls, anc, com, sub, wpn, arm, dc]) => {
      if (Array.isArray(cls)) setDhClasses(cls.map((c: any) => ({
        ...c,
        hp: c.base_hp ?? c.hp ?? 6,
        evasion: c.base_evasion ?? c.evasion ?? 8,
        stress: c.base_stress ?? c.stress ?? 6,
      })));
      if (Array.isArray(anc)) setDhAncestries(anc.map((a: any) => a.name_cn ? `${a.name_cn} (${a.name})` : a.name));
      if (Array.isArray(com)) setDhCommunities(com.map((c: any) => c.name_cn ? `${c.name_cn} (${c.name})` : c.name));
      if (Array.isArray(sub)) setDhSubclasses(sub);
      if (Array.isArray(wpn)) setDhWeapons(wpn);
      if (Array.isArray(arm)) setDhArmors(arm);
      if (Array.isArray(dc)) setDhDomainCards(dc);
    });
  }, []);

  // fetch recommended when class changes
  useEffect(() => {
    if (!build.className || build.className === "__custom__") { setRecommended({}); return; }
    fetch(`${API}/api/daggerheart/charbuilder/recommended/${build.className}`)
      .then(r => r.json()).then(setRecommended).catch(() => setRecommended({}));
  }, [build.className]);

  const update = useCallback(
    <K extends keyof DHBuildState>(key: K, val: DHBuildState[K]) =>
      setBuild((prev) => ({ ...prev, [key]: val })),
    [],
  );

  const selectedClass = dhClasses.find((c) => c.slug === build.className);
  const classDomains = selectedClass?.domains || [];

  // filter subclasses by selected class fvtt_id
  const filteredSubclasses = useMemo(() => {
    if (!selectedClass) return dhSubclasses;
    return dhSubclasses.filter(s => {
      if (!s.linked_class) return true;
      return s.linked_class.includes(selectedClass.fvtt_id || "NOMATCH");
    });
  }, [dhSubclasses, selectedClass]);

  // filter domain cards by class domains and level 1 for creation
  const filteredDomainCards = useMemo(() => {
    let cards = dhDomainCards;
    if (dcDomainFilter !== "all") {
      cards = cards.filter(c => c.domain === dcDomainFilter);
    } else if (classDomains.length > 0) {
      cards = cards.filter(c => classDomains.includes(c.domain));
    }
    cards = cards.filter(c => c.level <= 1);
    if (dcSearch) {
      const q = dcSearch.toLowerCase();
      cards = cards.filter(c => c.name.toLowerCase().includes(q) || (c.name_cn || "").includes(q));
    }
    return cards;
  }, [dhDomainCards, classDomains, dcDomainFilter, dcSearch]);

  const filteredWeapons = useMemo(() => {
    let w = dhWeapons.filter(wp => wp.tier <= weaponTierFilter);
    if (weaponSearch) {
      const q = weaponSearch.toLowerCase();
      w = w.filter(wp => wp.name.toLowerCase().includes(q) || (wp.name_cn || "").includes(q));
    }
    return w;
  }, [dhWeapons, weaponSearch, weaponTierFilter]);

  const filteredArmors = useMemo(() => {
    let a = dhArmors.filter(ar => ar.tier <= 1);
    if (armorSearch) {
      const q = armorSearch.toLowerCase();
      a = a.filter(ar => ar.name.toLowerCase().includes(q) || (ar.name_cn || "").includes(q));
    }
    return a;
  }, [dhArmors, armorSearch]);

  const handleClassSelect = useCallback((cls: DHClassDef) => {
    setBuild((prev) => ({
      ...prev,
      className: cls.slug,
      subclass: "",
      hp: cls.hp ?? cls.base_hp ?? 6,
      evasion: cls.evasion ?? cls.base_evasion ?? 8,
      stressMax: cls.stress ?? cls.base_stress ?? 6,
      domainCards: [],
    }));
    setShowCustomClass(false);
  }, []);

  const applyRecommended = useCallback(() => {
    if (!recommended) return;
    setBuild(prev => ({
      ...prev,
      traits: recommended.traits ? { ...recommended.traits } : prev.traits,
      primaryWeapon: recommended.primary_weapon || prev.primaryWeapon,
      secondaryWeapon: recommended.secondary_weapon || prev.secondaryWeapon,
      armor: recommended.armor || prev.armor,
    }));
  }, [recommended]);

  const traitValues = DH_TRAITS.map((t) => build.traits[t]);
  const traitValid = [...traitValues].sort((a, b) => a - b).join(",") === VALID_DISTRIBUTIONS[0].join(",");

  const cycleTrait = useCallback((trait: string) => {
    setBuild((prev) => {
      const cur = prev.traits[trait];
      const cycle = [-1, 0, 1, 2];
      const nextIdx = (cycle.indexOf(cur) + 1) % cycle.length;
      return { ...prev, traits: { ...prev.traits, [trait]: cycle[nextIdx] } };
    });
  }, []);

  const toggleDomainCard = useCallback((cardName: string) => {
    setBuild(prev => {
      const has = prev.domainCards.includes(cardName);
      return { ...prev, domainCards: has ? prev.domainCards.filter(n => n !== cardName) : [...prev.domainCards, cardName] };
    });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      const eq = [...build.equipment];
      if (build.primaryWeapon) eq.push(build.primaryWeapon);
      if (build.secondaryWeapon) eq.push(build.secondaryWeapon);
      if (build.armor) eq.push(build.armor);
      const body = {
        name: build.name || "New Hero",
        class: build.className,
        subclass: build.subclass,
        ancestry: build.ancestry,
        community: build.community,
        traits: build.traits,
        hp: build.hp,
        evasion: build.evasion,
        stress_max: build.stressMax,
        armor_slots: build.armorSlots,
        domain_cards: build.domainCards,
        experiences: build.experiences.filter(Boolean),
        equipment: eq,
        background: build.background,
      };
      const resp = await fetch(`${API}/api/daggerheart/charbuilder/assemble`, {
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
      case 0: return !!build.name && !!build.ancestry && !!build.community;
      case 1: return !!build.className;
      case 2: return traitValid;
      default: return true;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-violet-400" />
          Daggerheart 角色创建
        </h3>
        <button onClick={onCancel} className="text-sm text-muted-foreground hover:text-foreground">取消</button>
      </div>

      {/* Step indicators */}
      <div className="flex gap-1">
        {STEPS.map((s, i) => (
          <button
            key={s.key}
            onClick={() => i <= step && setStep(i)}
            className={cn(
              "flex-1 py-1.5 text-xs rounded-lg transition-all",
              i === step ? "bg-violet-500/20 text-violet-300 font-medium"
                : i < step ? "bg-violet-500/10 text-violet-400/60 cursor-pointer"
                : "bg-secondary/50 text-muted-foreground",
            )}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* ── Step 0: Basics ── */}
      {step === 0 && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">角色名</label>
            <input value={build.name} onChange={(e) => update("name", e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-foreground" placeholder="输入角色名称…" />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">族裔 (Ancestry)</label>
            <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
              {dhAncestries.map((a) => (
                <button key={a} onClick={() => { update("ancestry", a); setShowCustomAncestry(false); }}
                  className={cn("px-3 py-2 rounded-lg text-sm text-left transition-all border",
                    build.ancestry === a && !showCustomAncestry ? "border-violet-500 bg-violet-500/20 text-violet-300" : "border-border bg-secondary/50 text-muted-foreground hover:border-violet-500/50")}>{a}</button>
              ))}
              <button onClick={() => setShowCustomAncestry(true)} className={cn("px-3 py-2 rounded-lg text-sm text-left transition-all border border-dashed",
                showCustomAncestry ? "border-violet-500 bg-violet-500/20 text-violet-300" : "border-border bg-secondary/30 text-muted-foreground hover:border-violet-500/50")}>+ 自定义族裔</button>
            </div>
            {showCustomAncestry && (
              <input value={customAncestry} onChange={(e) => { setCustomAncestry(e.target.value); update("ancestry", e.target.value); }}
                className="w-full mt-2 px-3 py-2 rounded-lg bg-secondary border border-violet-500/50 text-foreground text-sm" placeholder="输入自定义族裔名称…" autoFocus />
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">社群 (Community)</label>
            <div className="grid grid-cols-2 gap-2">
              {dhCommunities.map((c) => (
                <button key={c} onClick={() => { update("community", c); setShowCustomCommunity(false); }}
                  className={cn("px-3 py-2 rounded-lg text-sm text-left transition-all border",
                    build.community === c && !showCustomCommunity ? "border-violet-500 bg-violet-500/20 text-violet-300" : "border-border bg-secondary/50 text-muted-foreground hover:border-violet-500/50")}>{c}</button>
              ))}
              <button onClick={() => setShowCustomCommunity(true)} className={cn("px-3 py-2 rounded-lg text-sm text-left transition-all border border-dashed",
                showCustomCommunity ? "border-violet-500 bg-violet-500/20 text-violet-300" : "border-border bg-secondary/30 text-muted-foreground hover:border-violet-500/50")}>+ 自定义社群</button>
            </div>
            {showCustomCommunity && (
              <input value={customCommunity} onChange={(e) => { setCustomCommunity(e.target.value); update("community", e.target.value); }}
                className="w-full mt-2 px-3 py-2 rounded-lg bg-secondary border border-violet-500/50 text-foreground text-sm" placeholder="输入自定义社群名称…" autoFocus />
            )}
          </div>
        </div>
      )}

      {/* ── Step 1: Class + Subclass ── */}
      {step === 1 && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">选择你的职业和子职业。职业决定基础数值和可用领域。</p>
          <div className="grid grid-cols-1 gap-3 max-h-[350px] overflow-y-auto">
            {dhClasses.map((cls) => (
              <button key={cls.slug} onClick={() => handleClassSelect(cls)}
                className={cn("p-4 rounded-xl text-left transition-all border-2",
                  build.className === cls.slug ? "border-violet-500 bg-violet-500/10" : "border-border bg-secondary/30 hover:border-violet-500/50")}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-foreground">{cls.name_cn ? `${cls.name_cn} (${cls.name})` : cls.name}</span>
                  <div className="flex gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1"><Heart className="h-3 w-3 text-red-400" />{cls.hp ?? cls.base_hp}</span>
                    <span className="flex items-center gap-1"><Shield className="h-3 w-3 text-blue-400" />{cls.evasion ?? cls.base_evasion}</span>
                  </div>
                </div>
                <div className="flex gap-2 mt-2">
                  {(cls.domains || []).map((d) => (
                    <span key={d} className="text-xs px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300">{DH_DOMAIN_LABELS[d] || d}</span>
                  ))}
                </div>
              </button>
            ))}
            <button onClick={() => { setShowCustomClass(true); setBuild(p => ({ ...p, className: "__custom__", hp: 6, evasion: 8, domainCards: [] })); }}
              className={cn("p-4 rounded-xl text-left transition-all border-2 border-dashed",
                showCustomClass ? "border-violet-500 bg-violet-500/10" : "border-border bg-secondary/30 hover:border-violet-500/50")}>
              <span className="font-semibold text-muted-foreground">+ 自定义职业</span>
            </button>
          </div>
          {showCustomClass && (
            <div className="space-y-3 p-3 rounded-lg bg-secondary/30 border border-violet-500/30">
              <input value={customClassName} onChange={(e) => { setCustomClassName(e.target.value); update("className", e.target.value); }}
                className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm" placeholder="自定义职业名称…" autoFocus />
              <div className="flex gap-4">
                <div><label className="block text-xs text-muted-foreground mb-1">HP</label>
                  <input type="number" value={build.hp} onChange={(e) => update("hp", parseInt(e.target.value) || 6)}
                    className="w-20 px-2 py-1 rounded-lg bg-secondary border border-border text-foreground text-sm" /></div>
                <div><label className="block text-xs text-muted-foreground mb-1">闪避</label>
                  <input type="number" value={build.evasion} onChange={(e) => update("evasion", parseInt(e.target.value) || 8)}
                    className="w-20 px-2 py-1 rounded-lg bg-secondary border border-border text-foreground text-sm" /></div>
              </div>
            </div>
          )}

          {/* Subclass selection */}
          {(selectedClass || showCustomClass) && (
            <div className="mt-2">
              <label className="block text-sm font-medium text-foreground mb-2">子职业 (Subclass)</label>
              {filteredSubclasses.length > 0 ? (
                <div className="space-y-2">
                  {filteredSubclasses.map((sc) => (
                    <div key={sc.slug}>
                      <div className="flex items-stretch">
                        <button onClick={() => update("subclass", sc.name)}
                          className={cn("flex-1 p-3 rounded-l-lg text-left transition-all border border-r-0",
                            build.subclass === sc.name ? "border-violet-500 bg-violet-500/15 text-violet-300" : "border-border bg-secondary/50 text-muted-foreground hover:border-violet-500/50")}>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-foreground">{sc.name_cn ? `${sc.name_cn} (${sc.name})` : sc.name}</span>
                            {sc.spellcasting_trait && (
                              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300">
                                施法: {DH_TRAIT_LABELS[sc.spellcasting_trait]?.split(" ")[0] || sc.spellcasting_trait}
                              </span>
                            )}
                          </div>
                        </button>
                        {sc.description && (
                          <button onClick={() => setShowSubclassDesc(showSubclassDesc === sc.slug ? null : sc.slug)}
                            className={cn("px-2 rounded-r-lg border transition-all flex items-center",
                              build.subclass === sc.name ? "border-violet-500 bg-violet-500/10" : "border-border bg-secondary/50",
                              "text-muted-foreground hover:text-foreground")}>
                            {showSubclassDesc === sc.slug ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </button>
                        )}
                      </div>
                      {showSubclassDesc === sc.slug && sc.description && (
                        <div className="mt-1 px-3 py-2 rounded-lg bg-secondary/30 text-xs text-muted-foreground max-h-24 overflow-y-auto">{sc.description}</div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <input value={build.subclass} onChange={(e) => update("subclass", e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-foreground" placeholder="输入子职业名称…" />
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Step 2: Traits ── */}
      {step === 2 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              分配六项特质。标准分配为 <b>+2 / +1 / +1 / +0 / +0 / -1</b>。
            </p>
            {Object.keys(recommended.traits || {}).length > 0 && (
              <button onClick={applyRecommended}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 transition-all border border-amber-500/30">
                <Zap className="h-3 w-3" /> 应用推荐配置
              </button>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            {DH_TRAITS.map((t) => {
              const isRecommended = recommended.traits?.[t] !== undefined;
              return (
                <div key={t} className="flex items-center justify-between p-3 rounded-lg bg-secondary/50 border border-border">
                  <div>
                    <span className="text-sm font-medium text-foreground">{DH_TRAIT_LABELS[t]}</span>
                    {isRecommended && (
                      <span className="ml-2 text-xs text-amber-400/70">推荐 {(recommended.traits![t] >= 0 ? "+" : "")}{recommended.traits![t]}</span>
                    )}
                  </div>
                  <button onClick={() => cycleTrait(t)}
                    className={cn("w-10 h-10 rounded-lg font-bold text-lg transition-all",
                      build.traits[t] > 0 ? "bg-green-500/20 text-green-400 border border-green-500/40"
                        : build.traits[t] < 0 ? "bg-red-500/20 text-red-400 border border-red-500/40"
                        : "bg-secondary border border-border text-muted-foreground")}>
                    {build.traits[t] > 0 ? `+${build.traits[t]}` : build.traits[t]}
                  </button>
                </div>
              );
            })}
          </div>
          <div className={cn("text-sm p-3 rounded-lg",
            traitValid ? "bg-green-500/10 text-green-400" : "bg-yellow-500/10 text-yellow-400")}>
            {traitValid ? "✓ 特质分配正确 (+2/+1/+1/+0/+0/-1)"
              : `当前: ${DH_TRAITS.map((t) => `${build.traits[t] >= 0 ? "+" : ""}${build.traits[t]}`).join(", ")} — 需要 +2/+1/+1/+0/+0/-1`}
          </div>
        </div>
      )}

      {/* ── Step 3: Equipment + Domain Cards ── */}
      {step === 3 && (
        <div className="space-y-5">
          {/* Recommended equipment banner */}
          {(recommended.primary_weapon || recommended.armor) && (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-amber-300 flex items-center gap-1"><Zap className="h-4 w-4" /> 推荐装备</span>
                <button onClick={() => {
                  setBuild(prev => ({
                    ...prev,
                    primaryWeapon: recommended.primary_weapon || prev.primaryWeapon,
                    secondaryWeapon: recommended.secondary_weapon || prev.secondaryWeapon,
                    armor: recommended.armor || prev.armor,
                  }));
                }} className="text-xs px-2 py-1 rounded bg-amber-500/20 text-amber-300 hover:bg-amber-500/30">一键应用</button>
              </div>
              <div className="text-xs text-muted-foreground space-y-1">
                {recommended.primary_weapon && <div>主武器: <span className="text-foreground">{recommended.primary_weapon}</span></div>}
                {recommended.secondary_weapon && <div>副武器: <span className="text-foreground">{recommended.secondary_weapon}</span></div>}
                {recommended.armor && <div>护甲: <span className="text-foreground">{recommended.armor}</span></div>}
              </div>
            </div>
          )}

          {/* Primary Weapon */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1 flex items-center gap-1"><Sword className="h-4 w-4 text-red-400" /> 主武器</label>
            <div className="flex gap-2 mb-2">
              <div className="relative flex-1">
                <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                <input value={weaponSearch} onChange={(e) => setWeaponSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm" placeholder="搜索武器…" />
              </div>
              <select value={weaponTierFilter} onChange={(e) => setWeaponTierFilter(Number(e.target.value))}
                className="px-2 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm">
                <option value={1}>阶位1</option><option value={2}>≤阶位2</option><option value={3}>≤阶位3</option><option value={4}>全部</option>
              </select>
            </div>
            {build.primaryWeapon && (
              <div className="mb-2 flex items-center gap-2">
                <span className="text-sm text-violet-300">已选: {build.primaryWeapon}</span>
                <button onClick={() => update("primaryWeapon", "")} className="text-xs text-muted-foreground hover:text-red-400">清除</button>
              </div>
            )}
            <div className="grid grid-cols-2 gap-1.5 max-h-32 overflow-y-auto">
              {filteredWeapons.slice(0, 30).map((w) => (
                <button key={w.slug} onClick={() => update("primaryWeapon", w.name)}
                  className={cn("px-2 py-1.5 rounded text-xs text-left border transition-all",
                    build.primaryWeapon === w.name ? "border-violet-500 bg-violet-500/15 text-violet-300" : "border-border bg-secondary/50 text-muted-foreground hover:border-violet-500/50")}>
                  <div className="truncate font-medium">{w.name_cn ? `${w.name_cn}` : w.name}</div>
                  <div className="text-[10px] opacity-70">{w.name_cn ? w.name : ""}{w.name_cn ? " · " : ""}{w.range || ""} · {w.burden || ""} · T{w.tier}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Secondary Weapon */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">副武器 <span className="text-muted-foreground font-normal">(可选)</span></label>
            {build.secondaryWeapon && (
              <div className="mb-1 flex items-center gap-2">
                <span className="text-sm text-violet-300">已选: {build.secondaryWeapon}</span>
                <button onClick={() => update("secondaryWeapon", "")} className="text-xs text-muted-foreground hover:text-red-400">清除</button>
              </div>
            )}
            <div className="grid grid-cols-2 gap-1.5 max-h-24 overflow-y-auto">
              {filteredWeapons.filter(w => w.burden === "oneHanded").slice(0, 20).map((w) => (
                <button key={w.slug} onClick={() => update("secondaryWeapon", w.name)}
                  className={cn("px-2 py-1.5 rounded text-xs text-left border transition-all",
                    build.secondaryWeapon === w.name ? "border-violet-500 bg-violet-500/15 text-violet-300" : "border-border bg-secondary/50 text-muted-foreground hover:border-violet-500/50")}>
                  <div className="truncate font-medium">{w.name_cn ? `${w.name_cn}` : w.name}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Armor */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1 flex items-center gap-1"><Shield className="h-4 w-4 text-blue-400" /> 护甲</label>
            <div className="relative mb-2">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
              <input value={armorSearch} onChange={(e) => setArmorSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm" placeholder="搜索护甲…" />
            </div>
            {build.armor && (
              <div className="mb-1 flex items-center gap-2">
                <span className="text-sm text-violet-300">已选: {build.armor}</span>
                <button onClick={() => update("armor", "")} className="text-xs text-muted-foreground hover:text-red-400">清除</button>
              </div>
            )}
            <div className="grid grid-cols-2 gap-1.5 max-h-28 overflow-y-auto">
              {filteredArmors.map((a) => (
                <button key={a.slug} onClick={() => { update("armor", a.name); update("armorSlots", a.base_score || 0); }}
                  className={cn("px-2 py-1.5 rounded text-xs text-left border transition-all",
                    build.armor === a.name ? "border-violet-500 bg-violet-500/15 text-violet-300" : "border-border bg-secondary/50 text-muted-foreground hover:border-violet-500/50")}>
                  <div className="truncate font-medium">{a.name_cn ? `${a.name_cn}` : a.name}</div>
                  <div className="text-[10px] opacity-70">{a.name_cn ? `${a.name} · ` : ""}护甲值 {a.base_score ?? 0}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Domain Cards */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1 flex items-center gap-1"><Scroll className="h-4 w-4 text-violet-400" /> 领域卡 (选择2张基础领域卡)</label>
            <div className="flex gap-2 mb-2">
              <div className="relative flex-1">
                <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                <input value={dcSearch} onChange={(e) => setDcSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm" placeholder="搜索领域卡…" />
              </div>
              <select value={dcDomainFilter} onChange={(e) => setDcDomainFilter(e.target.value)}
                className="px-2 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm">
                <option value="all">职业领域</option>
                {Object.entries(DH_DOMAIN_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            {build.domainCards.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {build.domainCards.map((dc, i) => (
                  <span key={i} className="px-2 py-1 rounded-lg bg-violet-500/20 text-xs text-violet-300 flex items-center gap-1">
                    {dc}
                    <button onClick={() => update("domainCards", build.domainCards.filter((_, j) => j !== i))} className="text-violet-400 hover:text-red-400">×</button>
                  </span>
                ))}
              </div>
            )}
            <div className="grid grid-cols-1 gap-1.5 max-h-40 overflow-y-auto">
              {filteredDomainCards.map((dc) => (
                <button key={dc.slug} onClick={() => toggleDomainCard(dc.name)}
                  className={cn("px-3 py-2 rounded-lg text-left text-sm border transition-all",
                    build.domainCards.includes(dc.name) ? "border-violet-500 bg-violet-500/15 text-violet-300" : "border-border bg-secondary/50 text-muted-foreground hover:border-violet-500/50")}>
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-foreground">{dc.name_cn ? `${dc.name_cn}` : dc.name}{dc.name_cn ? <span className="text-xs text-muted-foreground ml-1">({dc.name})</span> : null}</span>
                    <div className="flex gap-2 text-[10px]">
                      <span className="px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-400">{dc.domain_cn || dc.domain}</span>
                      <span className="px-1.5 py-0.5 rounded bg-secondary">{dc.card_type_cn || dc.card_type}</span>
                    </div>
                  </div>
                  {dc.description && <div className="text-xs text-muted-foreground mt-1 line-clamp-2">{dc.description}</div>}
                </button>
              ))}
              {filteredDomainCards.length === 0 && <div className="text-xs text-muted-foreground text-center py-4">无匹配的领域卡</div>}
            </div>
          </div>

          {/* Experiences */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">经历 (Experiences)</label>
            {build.experiences.map((exp, i) => (
              <input key={i} value={exp} onChange={(e) => {
                const newExps = [...build.experiences]; newExps[i] = e.target.value; update("experiences", newExps);
              }} className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-foreground mb-2" placeholder={`经历 ${i + 1}… (相关检定+2)`} />
            ))}
          </div>

          {/* Extra equipment */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">额外物品</label>
            <div className="flex gap-2 mb-2">
              <input value={equipInput} onChange={(e) => setEquipInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && equipInput.trim()) { update("equipment", [...build.equipment, equipInput.trim()]); setEquipInput(""); } }}
                className="flex-1 px-3 py-2 rounded-lg bg-secondary border border-border text-foreground" placeholder="添加装备（回车确认）…" />
            </div>
            <div className="flex flex-wrap gap-2">
              {build.equipment.map((eq, i) => (
                <span key={i} className="px-2 py-1 rounded-lg bg-secondary text-sm text-foreground flex items-center gap-1">
                  {eq}
                  <button onClick={() => update("equipment", build.equipment.filter((_, j) => j !== i))} className="text-muted-foreground hover:text-red-400">×</button>
                </span>
              ))}
            </div>
          </div>

          {/* Background */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">背景故事</label>
            <textarea value={build.background} onChange={(e) => update("background", e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-foreground h-20 resize-none" placeholder="描述你的角色背景…" />
          </div>
        </div>
      )}

      {/* ── Step 4: Review ── */}
      {step === 4 && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-secondary/50 border border-border space-y-3">
            <div className="flex items-center gap-3">
              <User className="h-5 w-5 text-violet-400" />
              <div>
                <h4 className="font-bold text-foreground text-lg">{build.name || "无名英雄"}</h4>
                <p className="text-sm text-muted-foreground">{build.ancestry} · {build.community}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="text-muted-foreground">职业:</span> <span className="text-foreground">{selectedClass?.name_cn ? `${selectedClass.name_cn}` : build.className}</span></div>
              {build.subclass && <div><span className="text-muted-foreground">子职业:</span> <span className="text-foreground">{build.subclass}</span></div>}
              <div className="flex items-center gap-1"><Heart className="h-3 w-3 text-red-400" /><span className="text-foreground">HP {build.hp}</span></div>
              <div className="flex items-center gap-1"><Shield className="h-3 w-3 text-blue-400" /><span className="text-foreground">闪避 {build.evasion}</span></div>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {DH_TRAITS.map((t) => (
                <div key={t} className="text-center p-2 rounded-lg bg-secondary">
                  <div className="text-xs text-muted-foreground">{DH_TRAIT_LABELS[t]}</div>
                  <div className={cn("font-bold", build.traits[t] > 0 ? "text-green-400" : build.traits[t] < 0 ? "text-red-400" : "text-foreground")}>
                    {build.traits[t] > 0 ? `+${build.traits[t]}` : build.traits[t]}
                  </div>
                </div>
              ))}
            </div>
            {/* Equipment summary */}
            <div className="space-y-1 text-sm">
              {build.primaryWeapon && <div><span className="text-muted-foreground">主武器:</span> <span className="text-foreground">{build.primaryWeapon}</span></div>}
              {build.secondaryWeapon && <div><span className="text-muted-foreground">副武器:</span> <span className="text-foreground">{build.secondaryWeapon}</span></div>}
              {build.armor && <div><span className="text-muted-foreground">护甲:</span> <span className="text-foreground">{build.armor} (护甲值 {build.armorSlots})</span></div>}
            </div>
            {build.domainCards.length > 0 && (
              <div>
                <span className="text-sm text-muted-foreground">领域卡: </span>
                {build.domainCards.map((dc, i) => (
                  <span key={i} className="text-sm text-violet-300">{dc}{i < build.domainCards.length - 1 ? "、" : ""}</span>
                ))}
              </div>
            )}
            {build.experiences.filter(Boolean).length > 0 && (
              <div className="text-sm"><span className="text-muted-foreground">经历: </span><span className="text-foreground">{build.experiences.filter(Boolean).join("、")}</span></div>
            )}
          </div>
          {error && <div className="text-sm text-red-400 bg-red-400/10 rounded-lg px-4 py-2">{error}</div>}
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-2">
        <button onClick={() => (step === 0 ? onCancel() : setStep(step - 1))}
          className="flex items-center gap-1 px-4 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="h-4 w-4" />{step === 0 ? "取消" : "上一步"}
        </button>
        {step < STEPS.length - 1 ? (
          <button onClick={() => setStep(step + 1)} disabled={!canNext()}
            className={cn("flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              canNext() ? "bg-violet-500 text-white hover:bg-violet-600" : "bg-secondary text-muted-foreground cursor-not-allowed")}>
            下一步<ArrowRight className="h-4 w-4" />
          </button>
        ) : (
          <button onClick={handleSave} disabled={saving}
            className="flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium bg-violet-500 text-white hover:bg-violet-600 transition-all disabled:opacity-50">
            {saving ? "创建中…" : "创建角色"}<Check className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
