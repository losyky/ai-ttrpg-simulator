"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  Save,
  Heart,
  Shield,
  Swords,
  Star,
  BookOpen,
  Sparkles,
  Backpack,
  Scroll,
  User,
  Pencil,
  Check,
  X,
  ChevronDown,
  ChevronRight,
  Flame,
  Eye,
  Plus,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getCharacter, updateCharacter, type CharacterFull } from "@/lib/api";

const ABILITY_LABELS: Record<string, string> = {
  str: "力量", dex: "敏捷", con: "体质",
  int: "智力", wis: "感知", cha: "魅力",
};

const ABILITY_COLORS: Record<string, string> = {
  str: "text-red-400 border-red-400/30 bg-red-400/10",
  dex: "text-green-400 border-green-400/30 bg-green-400/10",
  con: "text-orange-400 border-orange-400/30 bg-orange-400/10",
  int: "text-blue-400 border-blue-400/30 bg-blue-400/10",
  wis: "text-purple-400 border-purple-400/30 bg-purple-400/10",
  cha: "text-pink-400 border-pink-400/30 bg-pink-400/10",
};

const RANK_NAMES: Record<number, string> = {
  0: "未受训", 1: "受训", 2: "专家", 3: "大师", 4: "传奇",
};
const RANK_COLORS: Record<number, string> = {
  0: "text-muted-foreground",
  1: "text-blue-400",
  2: "text-purple-400",
  3: "text-yellow-400",
  4: "text-red-400",
};

const SKILL_LABELS: Record<string, string> = {
  acrobatics: "特技", arcana: "奥秘", athletics: "运动",
  crafting: "制造", deception: "欺骗", diplomacy: "交涉",
  intimidation: "威吓", medicine: "医药", nature: "自然",
  occultism: "神秘学", performance: "表演", religion: "宗教",
  society: "社会", stealth: "隐匿", survival: "求生", thievery: "盗窃",
};

const SAVE_LABELS: Record<string, string> = {
  fortitude: "强韧", reflex: "反射", will: "意志",
};

type SheetTab = "overview" | "skills" | "feats" | "spells" | "inventory" | "bio";

interface Props {
  characterId: string;
  onBack: () => void;
}

export default function CharacterSheetEditor({ characterId, onBack }: Props) {
  const [char, setChar] = useState<CharacterFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState<SheetTab>("overview");
  const [dirty, setDirty] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getCharacter(characterId);
      setChar(data);
      setDirty(false);
    } catch (err) {
      setStatusMsg(`加载失败: ${err instanceof Error ? err.message : err}`);
    } finally {
      setLoading(false);
    }
  }, [characterId]);

  useEffect(() => { load(); }, [load]);

  const flash = (msg: string) => {
    setStatusMsg(msg);
    setTimeout(() => setStatusMsg(""), 3000);
  };

  const updateField = useCallback((field: string, value: unknown) => {
    setChar(prev => prev ? { ...prev, [field]: value } : prev);
    setDirty(true);
  }, []);

  const updateAbility = useCallback((key: string, value: number) => {
    setChar(prev => {
      if (!prev) return prev;
      return { ...prev, abilities: { ...prev.abilities, [key]: value } };
    });
    setDirty(true);
  }, []);

  const handleSave = useCallback(async () => {
    if (!char || !dirty) return;
    setSaving(true);
    try {
      const updates: Record<string, unknown> = {
        name: char.name,
        level: char.level,
        ancestry: char.ancestry,
        heritage: char.heritage,
        background: char.background,
        character_class: char.character_class,
        key_ability: char.key_ability,
        deity: char.deity,
        hp: char.hp,
        max_hp: char.max_hp,
        temp_hp: char.temp_hp,
        hero_points: char.hero_points,
        abilities: char.abilities,
        skills: char.skills,
        saves: char.saves,
        feats: char.feats,
        spells: char.spells,
        inventory: char.inventory,
        lore_skills: char.lore_skills,
        backstory: char.backstory,
        gender: char.gender,
      };
      const updated = await updateCharacter(characterId, updates);
      setChar(updated);
      setDirty(false);
      flash("已保存");
    } catch (err) {
      flash(`保存失败: ${err instanceof Error ? err.message : err}`);
    } finally {
      setSaving(false);
    }
  }, [char, dirty, characterId]);

  if (loading || !char) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground">
        {loading ? "加载中..." : "角色未找到"}
      </div>
    );
  }

  const tabs: { key: SheetTab; label: string; icon: typeof Star }[] = [
    { key: "overview", label: "总览", icon: User },
    { key: "skills", label: "技能", icon: Eye },
    { key: "feats", label: "专长", icon: Star },
    { key: "spells", label: "法术", icon: Sparkles },
    { key: "inventory", label: "物品", icon: Backpack },
    { key: "bio", label: "传记", icon: Scroll },
  ];

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="p-2 rounded-lg hover:bg-secondary text-muted-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="flex-1 min-w-0">
          <EditableText
            value={char.name}
            onChange={(v) => updateField("name", v)}
            className="text-lg font-bold text-foreground"
          />
          <div className="text-xs text-muted-foreground mt-0.5">
            {char.ancestry} ({char.heritage}) · {char.character_class} · Lv.{char.level}
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={!dirty || saving}
          className={cn(
            "flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
            dirty
              ? "bg-primary text-primary-foreground hover:bg-primary/90"
              : "bg-secondary text-muted-foreground cursor-not-allowed",
          )}
        >
          <Save className="h-3.5 w-3.5" />
          {saving ? "保存中..." : dirty ? "保存更改" : "已保存"}
        </button>
      </div>

      {statusMsg && (
        <div className="text-sm text-primary bg-primary/10 border border-primary/20 rounded-lg px-4 py-2">
          {statusMsg}
        </div>
      )}

      {/* Tab bar */}
      <div className="flex items-center gap-1 border-b border-border pb-px">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2",
              tab === key
                ? "text-primary border-primary bg-primary/5"
                : "text-muted-foreground border-transparent hover:text-foreground hover:bg-secondary/50",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="min-h-[400px]">
        {tab === "overview" && <OverviewTab char={char} updateField={updateField} updateAbility={updateAbility} />}
        {tab === "skills" && <SkillsTab char={char} updateField={updateField} />}
        {tab === "feats" && <FeatsTab char={char} updateField={updateField} />}
        {tab === "spells" && <SpellsTab char={char} updateField={updateField} />}
        {tab === "inventory" && <InventoryTab char={char} updateField={updateField} />}
        {tab === "bio" && <BioTab char={char} updateField={updateField} />}
      </div>
    </div>
  );
}


/* ─── Inline editable text ─── */

function EditableText({
  value,
  onChange,
  className,
  placeholder,
  type = "text",
}: {
  value: string | number;
  onChange: (v: string) => void;
  className?: string;
  placeholder?: string;
  type?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value));

  useEffect(() => { setDraft(String(value)); }, [value]);

  if (!editing) {
    return (
      <span
        className={cn("cursor-pointer hover:bg-secondary/50 rounded px-1 -mx-1 transition-colors group inline-flex items-center gap-1", className)}
        onClick={() => setEditing(true)}
        title="点击编辑"
      >
        {value || <span className="text-muted-foreground italic">{placeholder || "—"}</span>}
        <Pencil className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1">
      <input
        type={type}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") { onChange(draft); setEditing(false); }
          if (e.key === "Escape") { setDraft(String(value)); setEditing(false); }
        }}
        autoFocus
        className={cn(
          "bg-secondary border border-border rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-primary",
          type === "number" ? "w-16 text-center" : "w-auto",
          className,
        )}
      />
      <button onClick={() => { onChange(draft); setEditing(false); }} className="p-0.5 text-primary hover:bg-primary/10 rounded">
        <Check className="h-3 w-3" />
      </button>
      <button onClick={() => { setDraft(String(value)); setEditing(false); }} className="p-0.5 text-muted-foreground hover:bg-secondary rounded">
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}


/* ─── Number stepper ─── */

function NumberStepper({
  value,
  onChange,
  min = -999,
  max = 999,
  label,
  colorClass,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  label?: string;
  colorClass?: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1">
      {label && <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</span>}
      <div className={cn("flex items-center gap-0.5 border rounded-lg px-1 py-0.5", colorClass)}>
        <button
          onClick={() => onChange(Math.max(min, value - 1))}
          className="w-5 h-5 flex items-center justify-center rounded hover:bg-secondary/80 text-xs"
        >−</button>
        <span className="text-sm font-bold w-8 text-center tabular-nums">{value}</span>
        <button
          onClick={() => onChange(Math.min(max, value + 1))}
          className="w-5 h-5 flex items-center justify-center rounded hover:bg-secondary/80 text-xs"
        >+</button>
      </div>
    </div>
  );
}


/* ─── Collapsible section ─── */

function Section({ title, icon: Icon, defaultOpen = true, count, children }: {
  title: string;
  icon: typeof Star;
  defaultOpen?: boolean;
  count?: number;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-4 py-3 bg-secondary/30 hover:bg-secondary/50 transition-colors"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
        <Icon className="h-3.5 w-3.5 text-primary" />
        <span className="text-sm font-semibold text-foreground">{title}</span>
        {count !== undefined && (
          <span className="text-xs text-muted-foreground ml-auto">{count}</span>
        )}
      </button>
      {open && <div className="p-4">{children}</div>}
    </div>
  );
}


/* ─── Rank selector ─── */

function RankSelector({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex items-center gap-0.5">
      {[0, 1, 2, 3, 4].map((r) => (
        <button
          key={r}
          onClick={() => onChange(r)}
          className={cn(
            "w-5 h-5 rounded-full border text-[9px] font-bold flex items-center justify-center transition-all",
            value >= r
              ? cn("border-current", RANK_COLORS[r], r > 0 ? "bg-current/20" : "")
              : "border-border text-muted-foreground/30",
          )}
          title={RANK_NAMES[r]}
        >
          {r}
        </button>
      ))}
    </div>
  );
}


/* ─── Tab: Overview ─── */

function OverviewTab({
  char,
  updateField,
  updateAbility,
}: {
  char: CharacterFull;
  updateField: (f: string, v: unknown) => void;
  updateAbility: (k: string, v: number) => void;
}) {
  return (
    <div className="space-y-5">
      {/* Identity grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <FieldCard label="种族" value={char.ancestry} onChange={(v) => updateField("ancestry", v)} />
        <FieldCard label="传承" value={char.heritage} onChange={(v) => updateField("heritage", v)} />
        <FieldCard label="职业" value={char.character_class} onChange={(v) => updateField("character_class", v)} />
        <FieldCard label="背景" value={char.background} onChange={(v) => updateField("background", v)} />
        <FieldCard label="等级" value={String(char.level)} onChange={(v) => updateField("level", parseInt(v) || 1)} />
        <FieldCard label="信仰" value={char.deity} onChange={(v) => updateField("deity", v)} />
        <FieldCard label="关键属性" value={char.key_ability} onChange={(v) => updateField("key_ability", v)} />
        <FieldCard label="性别" value={char.gender} onChange={(v) => updateField("gender", v)} />
      </div>

      {/* Vitals */}
      <Section title="生命值与资源" icon={Heart}>
        <div className="flex items-center gap-6 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-center">
              <span className="text-[10px] text-muted-foreground mb-1">当前 HP</span>
              <div className="relative">
                <NumberStepper value={char.hp} onChange={(v) => updateField("hp", v)} min={0} max={char.max_hp} colorClass="border-red-400/30 bg-red-400/5" />
              </div>
            </div>
            <span className="text-muted-foreground text-lg">/</span>
            <div className="flex flex-col items-center">
              <span className="text-[10px] text-muted-foreground mb-1">最大 HP</span>
              <NumberStepper value={char.max_hp} onChange={(v) => updateField("max_hp", v)} min={1} colorClass="border-red-400/30 bg-red-400/5" />
            </div>
          </div>
          <NumberStepper value={char.temp_hp} onChange={(v) => updateField("temp_hp", v)} min={0} label="临时 HP" colorClass="border-orange-400/30 bg-orange-400/5" />
          <NumberStepper value={char.hero_points} onChange={(v) => updateField("hero_points", v)} min={0} max={3} label="英雄点" colorClass="border-yellow-400/30 bg-yellow-400/5" />
        </div>

        {/* HP bar */}
        <div className="mt-3">
          <div className="h-3 rounded-full bg-secondary overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-red-500 to-red-400 transition-all duration-300"
              style={{ width: `${char.max_hp > 0 ? Math.min(100, (char.hp / char.max_hp) * 100) : 0}%` }}
            />
          </div>
        </div>
      </Section>

      {/* Ability scores */}
      <Section title="属性调整值" icon={Flame}>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          {(["str", "dex", "con", "int", "wis", "cha"] as const).map((key) => (
            <div
              key={key}
              className={cn("flex flex-col items-center p-3 rounded-xl border transition-colors", ABILITY_COLORS[key])}
            >
              <span className="text-[10px] font-semibold uppercase tracking-wider mb-1">{ABILITY_LABELS[key]}</span>
              <span className="text-2xl font-bold tabular-nums">
                {char.abilities[key] >= 0 ? "+" : ""}{char.abilities[key]}
              </span>
              <div className="flex items-center gap-1 mt-1.5">
                <button
                  onClick={() => updateAbility(key, char.abilities[key] - 1)}
                  className="w-5 h-5 rounded bg-background/50 flex items-center justify-center text-xs hover:bg-background"
                >−</button>
                <button
                  onClick={() => updateAbility(key, char.abilities[key] + 1)}
                  className="w-5 h-5 rounded bg-background/50 flex items-center justify-center text-xs hover:bg-background"
                >+</button>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Saves */}
      <Section title="豁免检定" icon={Shield}>
        <div className="grid grid-cols-3 gap-3">
          {char.saves.map((save, i) => (
            <div key={save.slug} className="flex items-center justify-between p-3 rounded-xl bg-secondary/30 border border-border">
              <div>
                <div className="text-sm font-semibold text-foreground">{SAVE_LABELS[save.slug] || save.slug}</div>
                <div className={cn("text-xs", RANK_COLORS[save.rank])}>{RANK_NAMES[save.rank]}</div>
              </div>
              <RankSelector
                value={save.rank}
                onChange={(r) => {
                  const newSaves = [...char.saves];
                  newSaves[i] = { ...save, rank: r };
                  updateField("saves", newSaves);
                }}
              />
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}


/* ─── Field card ─── */

function FieldCard({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="bg-secondary/30 border border-border rounded-xl p-3">
      <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">{label}</div>
      <EditableText value={value} onChange={onChange} className="text-sm font-medium text-foreground" placeholder="未设置" />
    </div>
  );
}


/* ─── Tab: Skills ─── */

function SkillsTab({ char, updateField }: { char: CharacterFull; updateField: (f: string, v: unknown) => void }) {
  const updateSkillRank = (idx: number, rank: number) => {
    const newSkills = [...char.skills];
    newSkills[idx] = { ...newSkills[idx], rank, label: RANK_NAMES[rank] || "" };
    updateField("skills", newSkills);
  };

  const updateLoreRank = (idx: number, rank: number) => {
    const newLore = [...char.lore_skills];
    newLore[idx] = { ...newLore[idx], rank };
    updateField("lore_skills", newLore);
  };

  const addLore = () => {
    updateField("lore_skills", [...char.lore_skills, { slug: "新学识", rank: 1 }]);
  };

  const removeLore = (idx: number) => {
    updateField("lore_skills", char.lore_skills.filter((_, i) => i !== idx));
  };

  const abilityForSkill: Record<string, string> = {
    acrobatics: "dex", arcana: "int", athletics: "str",
    crafting: "int", deception: "cha", diplomacy: "cha",
    intimidation: "cha", medicine: "wis", nature: "wis",
    occultism: "int", performance: "cha", religion: "wis",
    society: "int", stealth: "dex", survival: "wis", thievery: "dex",
  };

  return (
    <div className="space-y-5">
      {/* Perception */}
      <Section title="感知" icon={Eye} defaultOpen>
        <div className="flex items-center justify-between p-3 bg-secondary/30 rounded-xl border border-border">
          <div>
            <span className="text-sm font-semibold">感知 Perception</span>
            <span className={cn("text-xs ml-2", RANK_COLORS[char.perception_rank ?? 0])}>
              {RANK_NAMES[char.perception_rank ?? 0]}
            </span>
          </div>
          <RankSelector
            value={char.perception_rank ?? 0}
            onChange={(r) => updateField("perception_rank", r)}
          />
        </div>
      </Section>

      {/* Skills */}
      <Section title="技能" icon={BookOpen} count={char.skills.filter(s => s.rank > 0).length}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {char.skills.map((skill, i) => {
            const ab = abilityForSkill[skill.slug] || "";
            const mod = ab ? char.abilities[ab as keyof typeof char.abilities] : 0;
            const profBonus = skill.rank > 0 ? char.level + skill.rank * 2 : 0;
            const total = mod + profBonus;
            return (
              <div
                key={skill.slug}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors",
                  skill.rank > 0 ? "border-border bg-secondary/20" : "border-transparent bg-secondary/10",
                )}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium text-foreground">
                      {SKILL_LABELS[skill.slug] || skill.slug}
                    </span>
                    <span className="text-[10px] text-muted-foreground uppercase">
                      {skill.slug}
                    </span>
                    {ab && (
                      <span className={cn("text-[10px]", ABILITY_COLORS[ab]?.split(" ")[0])}>
                        ({ABILITY_LABELS[ab]})
                      </span>
                    )}
                  </div>
                </div>
                {skill.rank > 0 && (
                  <span className="text-xs font-bold text-foreground tabular-nums w-8 text-right">
                    {total >= 0 ? "+" : ""}{total}
                  </span>
                )}
                <RankSelector value={skill.rank} onChange={(r) => updateSkillRank(i, r)} />
              </div>
            );
          })}
        </div>
      </Section>

      {/* Lore skills */}
      <Section title="学识 Lore" icon={BookOpen} count={char.lore_skills.length}>
        <div className="space-y-2">
          {char.lore_skills.map((lore, i) => (
            <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-secondary/20">
              <EditableText
                value={lore.slug}
                onChange={(v) => {
                  const newLore = [...char.lore_skills];
                  newLore[i] = { ...lore, slug: v };
                  updateField("lore_skills", newLore);
                }}
                className="text-sm font-medium flex-1"
              />
              <RankSelector value={lore.rank} onChange={(r) => updateLoreRank(i, r)} />
              <button onClick={() => removeLore(i)} className="p-1 hover:bg-destructive/20 rounded text-muted-foreground hover:text-destructive">
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          ))}
          <button
            onClick={addLore}
            className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg border-2 border-dashed border-border hover:border-primary/50 text-muted-foreground hover:text-primary text-xs transition-colors"
          >
            <Plus className="h-3 w-3" /> 添加学识
          </button>
        </div>
      </Section>
    </div>
  );
}


/* ─── Tab: Feats ─── */

function FeatsTab({ char, updateField }: { char: CharacterFull; updateField: (f: string, v: unknown) => void }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const categories = new Map<string, typeof char.feats>();
  for (const feat of char.feats) {
    const cat = feat.category || "other";
    if (!categories.has(cat)) categories.set(cat, []);
    categories.get(cat)!.push(feat);
  }

  const catLabels: Record<string, string> = {
    classfeature: "职业特性",
    class: "职业专长",
    ancestry: "族裔专长",
    general: "通用专长",
    skill: "技能专长",
    bonus: "奖励专长",
    other: "其他",
  };

  const removeFeat = (idx: number) => {
    updateField("feats", char.feats.filter((_, i) => i !== idx));
  };

  const addFeat = () => {
    updateField("feats", [...char.feats, { name: "新专长", item_type: "feat", category: "other", description: "" }]);
  };

  let globalIdx = 0;

  return (
    <div className="space-y-4">
      {Array.from(categories.entries()).map(([cat, feats]) => {
        const startIdx = globalIdx;
        globalIdx += feats.length;
        return (
          <Section key={cat} title={catLabels[cat] || cat} icon={Star} count={feats.length}>
            <div className="space-y-1.5">
              {feats.map((feat, fi) => {
                const realIdx = startIdx + fi;
                const isExpanded = expanded === `${cat}_${fi}`;
                return (
                  <div
                    key={fi}
                    className="border border-border rounded-lg overflow-hidden"
                  >
                    <div
                      className="flex items-center gap-2 px-3 py-2 hover:bg-secondary/30 cursor-pointer transition-colors"
                      onClick={() => setExpanded(isExpanded ? null : `${cat}_${fi}`)}
                    >
                      {isExpanded ? <ChevronDown className="h-3 w-3 text-muted-foreground" /> : <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                      <span className="text-sm font-medium text-foreground flex-1">{feat.name}</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); removeFeat(realIdx); }}
                        className="p-1 hover:bg-destructive/20 rounded text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                    {isExpanded && feat.description && (
                      <div className="px-4 py-2 bg-secondary/10 border-t border-border text-xs text-muted-foreground leading-relaxed">
                        {feat.description}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </Section>
        );
      })}
      <button
        onClick={addFeat}
        className="w-full flex items-center justify-center gap-1.5 py-3 rounded-xl border-2 border-dashed border-border hover:border-primary/50 text-muted-foreground hover:text-primary text-sm transition-colors"
      >
        <Plus className="h-3.5 w-3.5" /> 添加专长
      </button>
    </div>
  );
}


/* ─── Tab: Spells ─── */

function SpellsTab({ char, updateField }: { char: CharacterFull; updateField: (f: string, v: unknown) => void }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  const byRank = new Map<number, { spell: typeof char.spells[0]; idx: number }[]>();
  char.spells.forEach((spell, idx) => {
    const r = spell.rank;
    if (!byRank.has(r)) byRank.set(r, []);
    byRank.get(r)!.push({ spell, idx });
  });

  const sortedRanks = Array.from(byRank.keys()).sort((a, b) => a - b);

  const removeSpell = (idx: number) => {
    updateField("spells", char.spells.filter((_, i) => i !== idx));
  };

  const addSpell = () => {
    updateField("spells", [...char.spells, { name: "新法术", rank: 1, tradition: "", description: "" }]);
  };

  const rankLabel = (r: number) => r === 0 ? "戏法" : `${r} 环`;

  return (
    <div className="space-y-4">
      {char.spells.length === 0 ? (
        <div className="text-center py-10 text-sm text-muted-foreground">此角色没有法术</div>
      ) : (
        sortedRanks.map((rank) => (
          <Section
            key={rank}
            title={rankLabel(rank)}
            icon={Sparkles}
            count={byRank.get(rank)!.length}
          >
            <div className="space-y-1.5">
              {byRank.get(rank)!.map(({ spell, idx }) => (
                <div key={idx} className="border border-border rounded-lg overflow-hidden">
                  <div
                    className="flex items-center gap-2 px-3 py-2 hover:bg-secondary/30 cursor-pointer transition-colors"
                    onClick={() => setExpanded(expanded === idx ? null : idx)}
                  >
                    {expanded === idx ? <ChevronDown className="h-3 w-3 text-muted-foreground" /> : <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                    <span className="text-sm font-medium text-foreground flex-1">{spell.name}</span>
                    {spell.tradition && (
                      <span className="text-[10px] text-muted-foreground px-1.5 py-0.5 bg-secondary rounded-full">{spell.tradition}</span>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); removeSpell(idx); }}
                      className="p-1 hover:bg-destructive/20 rounded text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                  {expanded === idx && spell.description && (
                    <div className="px-4 py-2 bg-secondary/10 border-t border-border text-xs text-muted-foreground leading-relaxed">
                      {spell.description}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Section>
        ))
      )}
      <button
        onClick={addSpell}
        className="w-full flex items-center justify-center gap-1.5 py-3 rounded-xl border-2 border-dashed border-border hover:border-primary/50 text-muted-foreground hover:text-primary text-sm transition-colors"
      >
        <Plus className="h-3.5 w-3.5" /> 添加法术
      </button>
    </div>
  );
}


/* ─── Tab: Inventory ─── */

function InventoryTab({ char, updateField }: { char: CharacterFull; updateField: (f: string, v: unknown) => void }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  const typeLabels: Record<string, string> = {
    weapon: "武器",
    armor: "护甲",
    shield: "盾牌",
    equipment: "装备",
    consumable: "消耗品",
    treasure: "财宝",
    backpack: "容器",
  };

  const typeGroups = new Map<string, { item: typeof char.inventory[0]; idx: number }[]>();
  char.inventory.forEach((item, idx) => {
    const t = item.item_type || "equipment";
    if (!typeGroups.has(t)) typeGroups.set(t, []);
    typeGroups.get(t)!.push({ item, idx });
  });

  const removeItem = (idx: number) => {
    updateField("inventory", char.inventory.filter((_, i) => i !== idx));
  };

  const updateQty = (idx: number, qty: number) => {
    const newInv = [...char.inventory];
    newInv[idx] = { ...newInv[idx], quantity: Math.max(0, qty) };
    updateField("inventory", newInv);
  };

  const addItem = () => {
    updateField("inventory", [...char.inventory, { name: "新物品", item_type: "equipment", quantity: 1, description: "" }]);
  };

  return (
    <div className="space-y-4">
      {char.inventory.length === 0 ? (
        <div className="text-center py-10 text-sm text-muted-foreground">背包是空的</div>
      ) : (
        Array.from(typeGroups.entries()).map(([type, items]) => (
          <Section
            key={type}
            title={typeLabels[type] || type}
            icon={type === "weapon" ? Swords : Backpack}
            count={items.length}
          >
            <div className="space-y-1.5">
              {items.map(({ item, idx }) => (
                <div key={idx} className="border border-border rounded-lg overflow-hidden">
                  <div
                    className="flex items-center gap-2 px-3 py-2 hover:bg-secondary/30 cursor-pointer transition-colors"
                    onClick={() => setExpanded(expanded === idx ? null : idx)}
                  >
                    {expanded === idx ? <ChevronDown className="h-3 w-3 text-muted-foreground" /> : <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                    <span className="text-sm font-medium text-foreground flex-1">{item.name}</span>
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-muted-foreground">×</span>
                      <NumberStepper
                        value={item.quantity}
                        onChange={(v) => updateQty(idx, v)}
                        min={0}
                        colorClass="border-border bg-secondary/30"
                      />
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); removeItem(idx); }}
                      className="p-1 hover:bg-destructive/20 rounded text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                  {expanded === idx && item.description && (
                    <div className="px-4 py-2 bg-secondary/10 border-t border-border text-xs text-muted-foreground leading-relaxed">
                      {item.description}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Section>
        ))
      )}
      <button
        onClick={addItem}
        className="w-full flex items-center justify-center gap-1.5 py-3 rounded-xl border-2 border-dashed border-border hover:border-primary/50 text-muted-foreground hover:text-primary text-sm transition-colors"
      >
        <Plus className="h-3.5 w-3.5" /> 添加物品
      </button>
    </div>
  );
}


/* ─── Tab: Biography ─── */

function BioTab({ char, updateField }: { char: CharacterFull; updateField: (f: string, v: unknown) => void }) {
  return (
    <div className="space-y-5">
      <Section title="角色信息" icon={User}>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <FieldCard label="种族" value={char.ancestry} onChange={(v) => updateField("ancestry", v)} />
          <FieldCard label="传承" value={char.heritage} onChange={(v) => updateField("heritage", v)} />
          <FieldCard label="性别" value={char.gender} onChange={(v) => updateField("gender", v)} />
        </div>
      </Section>

      <Section title="背景故事" icon={BookOpen}>
        <textarea
          value={char.backstory}
          onChange={(e) => updateField("backstory", e.target.value)}
          placeholder="在此输入角色的背景故事..."
          className="w-full h-48 rounded-xl bg-secondary/30 border border-border p-4 text-sm text-foreground placeholder:text-muted-foreground resize-y focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </Section>

      {/* Summary (read-only) */}
      <Section title="角色摘要 (AI 使用)" icon={Scroll} defaultOpen={false}>
        <pre className="text-xs text-muted-foreground whitespace-pre-wrap bg-secondary/30 rounded-lg p-4 border border-border">
          {char.summary}
        </pre>
      </Section>
    </div>
  );
}
