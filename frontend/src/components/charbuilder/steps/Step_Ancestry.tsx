"use client";

import { useCallback } from "react";
import OptionBrowser from "../shared/OptionBrowser";
import PF2eDescription from "../shared/PF2eDescription";
import BoostAllocator from "../shared/BoostAllocator";
import { cbSearchAncestries, cbGetAncestry } from "@/lib/api";
import { useState } from "react";
import type { CharacterBuildState } from "../CharBuilderWizard";

const ALL_ABILITIES = ["str", "dex", "con", "int", "wis", "cha"];

interface Props {
  build: CharacterBuildState;
  updateBuild: (partial: Partial<CharacterBuildState>) => void;
}

export default function StepAncestry({ build, updateBuild }: Props) {
  const [detail, setDetail] = useState<any>(null);
  const [ancestryBoosts, setAncestryBoosts] = useState<string[]>([]);

  const fetchFn = useCallback(async (q: string) => cbSearchAncestries(q), []);

  const handleSelect = async (item: any) => {
    try {
      const full = await cbGetAncestry(item.slug);
      setDetail(full);
      setAncestryBoosts([]);
      
      updateBuild({
        ancestry: {
          slug: full.slug,
          name: full.display_name || full.name,
          boosts: {},
          flaws: {},
          hp: full.hp,
          speed: full.speed,
          size: full.size,
          vision: full.vision,
        },
        heritage: null,
      });
    } catch {}
  };

  const boostSlots = detail?.boosts || {};
  const flawSlots = detail?.flaws || {};

  return (
    <div className="flex h-full">
      {/* Left: browser */}
      <div className="w-1/3 border-r border-gray-700 flex flex-col">
        <OptionBrowser
          title="选择族裔"
          fetchFn={fetchFn}
          onSelect={handleSelect}
          selectedSlug={build.ancestry?.slug}
          getSlug={(item: any) => item.slug}
          getDisplayName={(item: any) => item.display_name || item.name}
          renderItem={(item: any, isSelected: boolean) => (
            <div>
              <div className="font-medium text-sm">{item.display_name || item.name}</div>
              <div className="text-xs text-gray-500">HP {item.hp} | 速度 {item.speed}尺 | {item.size}</div>
            </div>
          )}
        />
      </div>

      {/* Right: detail */}
      <div className="flex-1 overflow-y-auto p-4">
        {detail ? (
          <div className="space-y-4">
            <h3 className="text-xl font-bold">{detail.display_name || detail.name}</h3>
            
            <div className="flex gap-4 text-sm">
              <span className="bg-gray-800 px-2 py-1 rounded">HP {detail.hp}</span>
              <span className="bg-gray-800 px-2 py-1 rounded">速度 {detail.speed}尺</span>
              <span className="bg-gray-800 px-2 py-1 rounded">体型 {detail.size}</span>
              <span className="bg-gray-800 px-2 py-1 rounded">视觉 {detail.vision}</span>
            </div>

            {/* Boosts/Flaws allocation */}
            <div className="bg-gray-800/50 rounded-lg p-3">
              <h4 className="text-sm font-semibold text-gray-300 mb-2">属性调整</h4>
              {Object.entries(boostSlots).map(([key, slot]: [string, any]) => {
                const values = slot?.value || [];
                if (values.length === 6) {
                  return (
                    <BoostAllocator
                      key={key}
                      label={`自由提升 #${Number(key) + 1}`}
                      availableAbilities={ALL_ABILITIES}
                      selectedBoosts={ancestryBoosts.filter((_, i) => i === Number(key) ? true : false)}
                      maxBoosts={1}
                      onChange={(boosts) => {
                        const newBoosts = [...ancestryBoosts];
                        newBoosts[Number(key)] = boosts[0] || "";
                        setAncestryBoosts(newBoosts.filter(Boolean));
                      }}
                    />
                  );
                }
                return (
                  <div key={key} className="mb-2">
                    <span className="text-sm text-gray-400">固定提升: </span>
                    <span className="text-sm text-blue-400">{values.join(", ").toUpperCase()}</span>
                  </div>
                );
              })}
              {Object.entries(flawSlots).map(([key, slot]: [string, any]) => {
                const values = slot?.value || [];
                return (
                  <div key={`flaw-${key}`} className="mb-2">
                    <span className="text-sm text-gray-400">缺陷: </span>
                    <span className="text-sm text-red-400">{values.join(", ").toUpperCase()}</span>
                  </div>
                );
              })}
            </div>

            {detail.description_rendered || detail.description_cn || detail.description ? (
              <PF2eDescription html={detail.description_rendered || detail.description_cn || detail.description} />
            ) : null}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            从左侧选择一个族裔
          </div>
        )}
      </div>
    </div>
  );
}
