"use client";

import { useState, useCallback, useMemo } from "react";
import StepAncestry from "./steps/Step_Ancestry";
import StepHeritage from "./steps/Step_Heritage";
import StepBackground from "./steps/Step_Background";
import StepClass from "./steps/Step_Class";
import StepAbilityScores from "./steps/Step_AbilityScores";
import StepSkills from "./steps/Step_Skills";
import StepFeats from "./steps/Step_Feats";
import StepSpells from "./steps/Step_Spells";
import StepEquipment from "./steps/Step_Equipment";
import StepDetails from "./steps/Step_Details";
import StepReview from "./steps/Step_Review";

export interface CharacterBuildState {
  level: number;
  name: string;
  ancestry: { slug: string; name: string; boosts: Record<string, string>; flaws: Record<string, string>; hp: number; speed: number; size: string; vision: string } | null;
  heritage: { slug: string; name: string } | null;
  background: { slug: string; name: string; boosts: Record<string, string>; trainedSkills: string[]; lore: string[] } | null;
  class_: { slug: string; name: string; keyAbility: string; hp: number; trainedSkills: string[]; additionalSkillCount: number; spellcasting: number } | null;
  freeBoosts: string[];
  levelBoosts: Record<number, string[]>;
  voluntaryFlaws: string[];
  trainedSkills: string[];
  skillIncreases: Record<number, string>;
  feats: { slotType: string; level: number; slug: string; name: string }[];
  spells: { rank: number; slug: string; name: string }[];
  equipment: { slug: string; name: string; quantity: number; price_cp: number }[];
  details: { deity: string; gender: string; age: string; biography: string };
}

const INITIAL_BUILD: CharacterBuildState = {
  level: 1,
  name: "",
  ancestry: null,
  heritage: null,
  background: null,
  class_: null,
  freeBoosts: [],
  levelBoosts: {},
  voluntaryFlaws: [],
  trainedSkills: [],
  skillIncreases: {},
  feats: [],
  spells: [],
  equipment: [],
  details: { deity: "", gender: "", age: "", biography: "" },
};

const STEPS = [
  { key: "ancestry", label: "族裔", shortLabel: "族裔" },
  { key: "heritage", label: "传承", shortLabel: "传承" },
  { key: "background", label: "背景", shortLabel: "背景" },
  { key: "class", label: "职业", shortLabel: "职业" },
  { key: "abilities", label: "属性", shortLabel: "属性" },
  { key: "skills", label: "技能", shortLabel: "技能" },
  { key: "feats", label: "专长", shortLabel: "专长" },
  { key: "spells", label: "法术", shortLabel: "法术" },
  { key: "equipment", label: "装备", shortLabel: "装备" },
  { key: "details", label: "详情", shortLabel: "详情" },
  { key: "review", label: "审核", shortLabel: "审核" },
];

interface CharBuilderWizardProps {
  onComplete?: () => void;
  onCancel?: () => void;
}

export default function CharBuilderWizard({ onComplete, onCancel }: CharBuilderWizardProps) {
  const [step, setStep] = useState(0);
  const [build, setBuild] = useState<CharacterBuildState>({ ...INITIAL_BUILD });

  const updateBuild = useCallback((partial: Partial<CharacterBuildState>) => {
    setBuild((prev) => ({ ...prev, ...partial }));
  }, []);

  const canAdvance = useMemo(() => {
    switch (step) {
      case 0: return build.ancestry !== null;
      case 1: return build.heritage !== null;
      case 2: return build.background !== null;
      case 3: return build.class_ !== null;
      default: return true;
    }
  }, [step, build]);

  const next = () => setStep((s) => Math.min(s + 1, STEPS.length - 1));
  const prev = () => setStep((s) => Math.max(s - 1, 0));

  const renderStep = () => {
    const props = { build, updateBuild };
    switch (step) {
      case 0: return <StepAncestry {...props} />;
      case 1: return <StepHeritage {...props} />;
      case 2: return <StepBackground {...props} />;
      case 3: return <StepClass {...props} />;
      case 4: return <StepAbilityScores {...props} />;
      case 5: return <StepSkills {...props} />;
      case 6: return <StepFeats {...props} />;
      case 7: return <StepSpells {...props} />;
      case 8: return <StepEquipment {...props} />;
      case 9: return <StepDetails {...props} />;
      case 10: return <StepReview build={build} updateBuild={updateBuild} onComplete={onComplete} />;
      default: return null;
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Header with level selector */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold">角色创建</h2>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-400">等级:</label>
            <select
              value={build.level}
              onChange={(e) => updateBuild({ level: Number(e.target.value) })}
              className="bg-gray-700 text-white border border-gray-600 rounded px-2 py-0.5 text-sm"
            >
              {Array.from({ length: 20 }, (_, i) => (
                <option key={i + 1} value={i + 1}>{i + 1}</option>
              ))}
            </select>
          </div>
        </div>
        <button
          onClick={onCancel}
          className="text-sm text-gray-400 hover:text-white transition-colors"
        >
          取消
        </button>
      </div>

      {/* Step navigation */}
      <div className="flex items-center gap-1 px-4 py-2 bg-gray-850 border-b border-gray-700 overflow-x-auto">
        {STEPS.map((s, i) => (
          <button
            key={s.key}
            onClick={() => setStep(i)}
            className={`px-3 py-1 rounded text-xs font-medium whitespace-nowrap transition-colors ${
              i === step
                ? "bg-blue-600 text-white"
                : i < step
                  ? "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  : "bg-gray-800 text-gray-500 hover:bg-gray-700"
            }`}
          >
            {s.shortLabel}
          </button>
        ))}
      </div>

      {/* Step content */}
      <div className="flex-1 overflow-hidden">
        {renderStep()}
      </div>

      {/* Bottom navigation */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-t border-gray-700">
        <button
          onClick={prev}
          disabled={step === 0}
          className="px-4 py-1.5 text-sm rounded bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          上一步
        </button>

        <span className="text-sm text-gray-500">
          {step + 1} / {STEPS.length}
        </span>

        {step < STEPS.length - 1 ? (
          <button
            onClick={next}
            disabled={!canAdvance}
            className="px-4 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            下一步
          </button>
        ) : (
          <span />
        )}
      </div>
    </div>
  );
}
