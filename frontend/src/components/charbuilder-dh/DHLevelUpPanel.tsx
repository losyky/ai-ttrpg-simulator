"use client";

import { useState, useEffect, useMemo } from "react";
import { ArrowLeft, ArrowUp, Check, Scroll, Star, Heart, Shield, Sparkles, Search } from "lucide-react";
import { cn } from "@/lib/utils";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DH_TRAIT_LABELS: Record<string, string> = {
  agility: "敏捷", strength: "力量", finesse: "灵巧",
  instinct: "本能", presence: "风度", knowledge: "学识",
};
const DH_DOMAIN_LABELS: Record<string, string> = {
  arcana: "奥术", blade: "利刃", bone: "骸骨", codex: "典籍",
  grace: "优雅", midnight: "午夜", sage: "贤者", splendor: "辉耀", valor: "勇气",
};

interface TierOption {
  key: string;
  label: string;
  desc: string;
}
interface TierData {
  range: number[];
  label: string;
  on_enter: string;
  pick_count: number;
  options: TierOption[];
  also_gain_domain_card: boolean;
}
interface LevelupTable { tier2: TierData; tier3: TierData; tier4: TierData }

interface DomainCard {
  slug: string; name: string; name_cn?: string;
  domain: string; domain_cn?: string; level: number;
  card_type?: string; card_type_cn?: string; description?: string;
}

interface RawActor {
  _id?: string; name?: string;
  system?: {
    class?: string; subclass?: string; level?: number; proficiency?: number;
    heritage?: { ancestry?: string; community?: string };
    traits?: Record<string, { value?: number }>;
    resources?: { hitPoints?: { value?: number; max?: number }; stress?: { value?: number; max?: number }; hope?: { value?: number; max?: number } };
    evasion?: number; experiences?: string[];
    levelup_log?: { level: number; choices: string[] }[];
  };
  items?: { type?: string; name?: string }[];
}

interface Props {
  characterId: string;
  onBack: () => void;
  onComplete: () => void;
}

export default function DHLevelUpPanel({ characterId, onBack, onComplete }: Props) {
  const [actor, setActor] = useState<RawActor | null>(null);
  const [table, setTable] = useState<LevelupTable | null>(null);
  const [domainCards, setDomainCards] = useState<DomainCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [selectedChoices, setSelectedChoices] = useState<string[]>([]);
  const [selectedDomainCard, setSelectedDomainCard] = useState("");
  const [newExperience, setNewExperience] = useState("");
  const [traitBoosts, setTraitBoosts] = useState<string[]>([]);
  const [dcSearch, setDcSearch] = useState("");

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/characters/${characterId}/fvtt`).then(r => r.json()),
      fetch(`${API}/api/daggerheart/charbuilder/levelup-table`).then(r => r.json()),
      fetch(`${API}/api/daggerheart/charbuilder/domain-cards`).then(r => r.json()),
    ]).then(([a, t, dc]) => {
      setActor(a); setTable(t);
      if (Array.isArray(dc)) setDomainCards(dc);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [characterId]);

  const currentLevel = actor?.system?.level ?? 1;
  const newLevel = currentLevel + 1;
  const tierKey = newLevel <= 4 ? "tier2" : (newLevel <= 7 ? "tier3" : "tier4");
  const tierData = table?.[tierKey as keyof LevelupTable];

  const classDomains = useMemo(() => {
    if (!actor?.items) return [];
    const classItem = actor.items.find(i => i.type === "domainCard");
    return [];
  }, [actor]);

  const existingDcNames = useMemo(() => new Set((actor?.items || []).filter(i => i.type === "domainCard").map(i => i.name)), [actor]);

  const filteredDc = useMemo(() => {
    let cards = domainCards.filter(c => c.level <= newLevel && !existingDcNames.has(c.name));
    if (dcSearch) {
      const q = dcSearch.toLowerCase();
      cards = cards.filter(c => c.name.toLowerCase().includes(q) || (c.name_cn || "").includes(q) || (c.domain_cn || "").includes(q));
    }
    return cards;
  }, [domainCards, newLevel, existingDcNames, dcSearch]);

  const toggleChoice = (key: string) => {
    setSelectedChoices(prev => {
      if (prev.includes(key)) return prev.filter(k => k !== key);
      if (prev.length >= (tierData?.pick_count || 2)) return prev;
      return [...prev, key];
    });
  };

  const toggleTraitBoost = (trait: string) => {
    setTraitBoosts(prev => {
      if (prev.includes(trait)) return prev.filter(t => t !== trait);
      if (prev.length >= 2) return prev;
      return [...prev, trait];
    });
  };

  const needsTraitSelection = selectedChoices.includes("trait");
  const needsDomainCard = tierData?.also_gain_domain_card;

  const canSubmit = selectedChoices.length === (tierData?.pick_count || 2)
    && (!needsTraitSelection || traitBoosts.length === 2)
    && (!needsDomainCard || selectedDomainCard);

  const handleSubmit = async () => {
    setSaving(true); setError("");
    try {
      const body: Record<string, any> = {
        level: newLevel,
        choices: selectedChoices,
      };
      if (selectedDomainCard) body.domain_card = selectedDomainCard;
      if (newExperience) body.experience = newExperience;
      if (traitBoosts.length > 0) body.trait_boosts = traitBoosts;

      const resp = await fetch(`${API}/api/daggerheart/charbuilder/levelup/${characterId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const result = await resp.json();
      if (result.error) throw new Error(result.error);
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="text-center text-muted-foreground py-12">加载中…</div>;
  if (!actor || !table) return <div className="text-center text-red-400 py-12">无法加载角色或升级数据</div>;
  if (newLevel > 10) return (
    <div className="space-y-4">
      <button onClick={onBack} className="flex items-center gap-1 text-muted-foreground hover:text-foreground text-sm"><ArrowLeft className="h-4 w-4" />返回</button>
      <div className="text-center text-muted-foreground py-12">角色已达最高等级 (10级)</div>
    </div>
  );

  const isNewTier = newLevel === 2 || newLevel === 5 || newLevel === 8;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-1 text-muted-foreground hover:text-foreground text-sm"><ArrowLeft className="h-4 w-4" />返回</button>
        <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
          <ArrowUp className="h-5 w-5 text-amber-400" />
          {actor.name} — 升到 {newLevel} 级
        </h3>
      </div>

      {/* Tier info */}
      <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
        <div className="text-sm font-medium text-amber-300 mb-1">{tierData?.label}</div>
        {isNewTier && tierData?.on_enter && (
          <div className="text-xs text-amber-200/80 mb-2">进入新阶位: {tierData.on_enter}</div>
        )}
        <div className="text-xs text-muted-foreground">从以下列表中选择 {tierData?.pick_count || 2} 项提升，然后选择一张领域卡。</div>
      </div>

      {/* Choices */}
      <div>
        <h4 className="text-sm font-semibold text-foreground mb-2">
          升级选项 ({selectedChoices.length}/{tierData?.pick_count || 2})
        </h4>
        <div className="space-y-2">
          {tierData?.options.map((opt) => (
            <button key={opt.key} onClick={() => toggleChoice(opt.key)}
              className={cn("w-full p-3 rounded-lg text-left transition-all border",
                selectedChoices.includes(opt.key) ? "border-amber-500 bg-amber-500/15" : "border-border bg-secondary/50 hover:border-amber-500/50")}>
              <div className="flex items-center justify-between">
                <span className={cn("font-medium text-sm", selectedChoices.includes(opt.key) ? "text-amber-300" : "text-foreground")}>{opt.label}</span>
                {selectedChoices.includes(opt.key) && <Check className="h-4 w-4 text-amber-400" />}
              </div>
              <div className="text-xs text-muted-foreground mt-1">{opt.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Trait boost selection */}
      {needsTraitSelection && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">选择2个属性提升 ({traitBoosts.length}/2)</h4>
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(DH_TRAIT_LABELS).map(([key, label]) => (
              <button key={key} onClick={() => toggleTraitBoost(key)}
                className={cn("p-2 rounded-lg text-center text-sm border transition-all",
                  traitBoosts.includes(key) ? "border-green-500 bg-green-500/15 text-green-300" : "border-border bg-secondary/50 text-muted-foreground hover:border-green-500/50")}>
                {label}
                {traitBoosts.includes(key) && <span className="ml-1 text-green-400">+1</span>}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Domain card selection */}
      {needsDomainCard && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-1">
            <Scroll className="h-4 w-4 text-violet-400" /> 选择一张领域卡 (≤{newLevel}级)
          </h4>
          <div className="relative mb-2">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <input value={dcSearch} onChange={(e) => setDcSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm" placeholder="搜索领域卡…" />
          </div>
          {selectedDomainCard && (
            <div className="mb-2 text-sm text-violet-300">已选: {selectedDomainCard}
              <button onClick={() => setSelectedDomainCard("")} className="ml-2 text-xs text-muted-foreground hover:text-red-400">清除</button>
            </div>
          )}
          <div className="grid grid-cols-1 gap-1.5 max-h-48 overflow-y-auto">
            {filteredDc.map((dc) => (
              <button key={dc.slug} onClick={() => setSelectedDomainCard(dc.name)}
                className={cn("px-3 py-2 rounded-lg text-left text-sm border transition-all",
                  selectedDomainCard === dc.name ? "border-violet-500 bg-violet-500/15 text-violet-300" : "border-border bg-secondary/50 text-muted-foreground hover:border-violet-500/50")}>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-foreground">{dc.name_cn || dc.name}{dc.name_cn ? <span className="text-xs text-muted-foreground ml-1">({dc.name})</span> : null}</span>
                  <div className="flex gap-2 text-[10px]">
                    <span className="px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-400">{dc.domain_cn || dc.domain}</span>
                    <span className="px-1.5 py-0.5 rounded bg-secondary">Lv{dc.level}</span>
                    <span className="px-1.5 py-0.5 rounded bg-secondary">{dc.card_type_cn || dc.card_type}</span>
                  </div>
                </div>
                {dc.description && <div className="text-xs text-muted-foreground mt-1 line-clamp-2">{dc.description}</div>}
              </button>
            ))}
            {filteredDc.length === 0 && <div className="text-xs text-muted-foreground text-center py-4">无匹配的领域卡</div>}
          </div>
        </div>
      )}

      {/* Optional new experience */}
      {isNewTier && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">新经历 (可选)</h4>
          <input value={newExperience} onChange={(e) => setNewExperience(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-foreground text-sm" placeholder="描述新经历…" />
        </div>
      )}

      {/* Summary */}
      <div className="p-3 rounded-lg bg-secondary/50 border border-border">
        <h4 className="text-sm font-semibold text-foreground mb-2">升级摘要</h4>
        <div className="text-xs text-muted-foreground space-y-1">
          <div>等级: {currentLevel} → <span className="text-amber-300 font-bold">{newLevel}</span></div>
          {selectedChoices.map(c => <div key={c}>✓ {tierData?.options.find(o => o.key === c)?.label}</div>)}
          {traitBoosts.length > 0 && <div>属性提升: {traitBoosts.map(t => DH_TRAIT_LABELS[t]).join(", ")}</div>}
          {selectedDomainCard && <div>新领域卡: {selectedDomainCard}</div>}
          {newExperience && <div>新经历: {newExperience}</div>}
        </div>
      </div>

      {error && <div className="text-sm text-red-400 bg-red-400/10 rounded-lg px-4 py-2">{error}</div>}

      <div className="flex justify-between">
        <button onClick={onBack} className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground">取消</button>
        <button onClick={handleSubmit} disabled={!canSubmit || saving}
          className={cn("flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium transition-all",
            canSubmit ? "bg-amber-500 text-white hover:bg-amber-600" : "bg-secondary text-muted-foreground cursor-not-allowed")}>
          {saving ? "升级中…" : "完成升级"}<ArrowUp className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
