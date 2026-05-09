"use client";

import { useEffect, useState } from "react";
import { cbGetSkills } from "@/lib/api";
import type { CharacterBuildState } from "../CharBuilderWizard";

interface Props {
  build: CharacterBuildState;
  updateBuild: (partial: Partial<CharacterBuildState>) => void;
}

const RANK_LABELS = ["未受训", "受训", "专家", "大师", "传奇"];

export default function StepSkills({ build, updateBuild }: Props) {
  const [skills, setSkills] = useState<any[]>([]);

  useEffect(() => {
    cbGetSkills().then((data) => setSkills(data.skills)).catch(() => {});
  }, []);

  const classTrainedSlugs = build.class_?.trainedSkills || [];
  const bgTrainedSlugs = build.background?.trainedSkills || [];
  const maxAdditional = build.class_?.additionalSkillCount || 0;
  const userTrained = build.trainedSkills;

  const toggleSkill = (slug: string) => {
    if (classTrainedSlugs.includes(slug) || bgTrainedSlugs.includes(slug)) return;
    if (userTrained.includes(slug)) {
      updateBuild({ trainedSkills: userTrained.filter((s) => s !== slug) });
    } else if (userTrained.length < maxAdditional) {
      updateBuild({ trainedSkills: [...userTrained, slug] });
    }
  };

  return (
    <div className="p-4 overflow-y-auto h-full">
      <h3 className="text-lg font-bold mb-2">技能分配</h3>
      <p className="text-sm text-gray-400 mb-4">
        额外可训练技能: {userTrained.length}/{maxAdditional}
        {classTrainedSlugs.length > 0 && (
          <span className="ml-2">(职业固定受训: {classTrainedSlugs.join(", ")})</span>
        )}
      </p>

      <div className="grid grid-cols-2 gap-2">
        {skills.map((skill) => {
          const isClassTrained = classTrainedSlugs.includes(skill.slug);
          const isBgTrained = bgTrainedSlugs.includes(skill.slug);
          const isUserTrained = userTrained.includes(skill.slug);
          const isTrained = isClassTrained || isBgTrained || isUserTrained;
          const isLocked = isClassTrained || isBgTrained;

          return (
            <div
              key={skill.slug}
              onClick={() => toggleSkill(skill.slug)}
              className={`flex items-center justify-between p-2 rounded text-sm cursor-pointer transition-colors ${
                isTrained
                  ? isLocked
                    ? "bg-green-900/30 border border-green-800"
                    : "bg-blue-900/30 border border-blue-700"
                  : "bg-gray-800 border border-gray-700 hover:border-gray-500"
              } ${isLocked ? "cursor-default" : ""}`}
            >
              <div className="flex items-center gap-2">
                <span className="text-gray-300">{skill.name_cn}</span>
                <span className="text-xs text-gray-500">{skill.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 uppercase">{skill.attribute}</span>
                {isTrained && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-green-800 text-green-200">
                    {isClassTrained ? "职业" : isBgTrained ? "背景" : "选择"}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
