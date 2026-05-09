"use client";

import { useCallback, useState } from "react";
import OptionBrowser from "../shared/OptionBrowser";
import PF2eDescription from "../shared/PF2eDescription";
import { cbSearchClasses, cbGetClass } from "@/lib/api";
import type { CharacterBuildState } from "../CharBuilderWizard";

interface Props {
  build: CharacterBuildState;
  updateBuild: (partial: Partial<CharacterBuildState>) => void;
}

export default function StepClass({ build, updateBuild }: Props) {
  const [detail, setDetail] = useState<any>(null);
  const [selectedKey, setSelectedKey] = useState("");

  const fetchFn = useCallback(async (q: string) => cbSearchClasses(q), []);

  const handleSelect = async (item: any) => {
    try {
      const full = await cbGetClass(item.slug);
      setDetail(full);
      const firstKey = full.key_ability?.[0] || "";
      setSelectedKey(firstKey);
      updateBuild({
        class_: {
          slug: full.slug,
          name: full.display_name || full.name,
          keyAbility: firstKey,
          hp: full.hp_per_level,
          trainedSkills: full.trained_skills || [],
          additionalSkillCount: full.additional_skill_count || 0,
          spellcasting: full.spellcasting || 0,
        },
      });
    } catch {}
  };

  return (
    <div className="flex h-full">
      <div className="w-1/3 border-r border-gray-700">
        <OptionBrowser
          title="选择职业"
          fetchFn={fetchFn}
          onSelect={handleSelect}
          selectedSlug={build.class_?.slug}
          getSlug={(item: any) => item.slug}
          getDisplayName={(item: any) => item.display_name || item.name}
          renderItem={(item: any) => (
            <div>
              <div className="font-medium text-sm">{item.display_name || item.name}</div>
              <div className="text-xs text-gray-500">
                HP/级 {item.hp_per_level} | 关键属性 {(item.key_ability || []).join("/")}
              </div>
            </div>
          )}
        />
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {detail ? (
          <div className="space-y-4">
            <h3 className="text-xl font-bold">{detail.display_name || detail.name}</h3>
            
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-800/50 rounded p-2">
                <span className="text-xs text-gray-500">每级 HP</span>
                <div className="text-lg font-bold">{detail.hp_per_level}</div>
              </div>
              <div className="bg-gray-800/50 rounded p-2">
                <span className="text-xs text-gray-500">施法能力</span>
                <div className="text-lg font-bold">{detail.spellcasting ? "是" : "否"}</div>
              </div>
            </div>

            {/* Key ability selector */}
            {detail.key_ability?.length > 1 && (
              <div className="bg-gray-800/50 rounded-lg p-3">
                <h4 className="text-sm font-semibold text-gray-300 mb-2">关键属性</h4>
                <div className="flex gap-2">
                  {detail.key_ability.map((ability: string) => (
                    <button
                      key={ability}
                      onClick={() => {
                        setSelectedKey(ability);
                        if (build.class_) {
                          updateBuild({ class_: { ...build.class_, keyAbility: ability } });
                        }
                      }}
                      className={`px-3 py-1 rounded text-sm font-medium ${
                        selectedKey === ability
                          ? "bg-blue-700 text-white"
                          : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                      }`}
                    >
                      {ability.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {detail.description_rendered || detail.description_cn || detail.description ? (
              <PF2eDescription html={detail.description_rendered || detail.description_cn || detail.description} />
            ) : null}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            从左侧选择一个职业
          </div>
        )}
      </div>
    </div>
  );
}
