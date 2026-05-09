"use client";

import { useCallback, useState } from "react";
import OptionBrowser from "../shared/OptionBrowser";
import PF2eDescription from "../shared/PF2eDescription";
import { cbSearchBackgrounds, cbGetBackground } from "@/lib/api";
import type { CharacterBuildState } from "../CharBuilderWizard";

interface Props {
  build: CharacterBuildState;
  updateBuild: (partial: Partial<CharacterBuildState>) => void;
}

export default function StepBackground({ build, updateBuild }: Props) {
  const [detail, setDetail] = useState<any>(null);

  const fetchFn = useCallback(async (q: string) => cbSearchBackgrounds(q), []);

  const handleSelect = async (item: any) => {
    try {
      const full = await cbGetBackground(item.slug);
      setDetail(full);
      updateBuild({
        background: {
          slug: full.slug,
          name: full.display_name || full.name,
          boosts: {},
          trainedSkills: full.trained_skills || [],
          lore: full.lore || [],
        },
      });
    } catch {}
  };

  return (
    <div className="flex h-full">
      <div className="w-1/3 border-r border-gray-700">
        <OptionBrowser
          title="选择背景"
          fetchFn={fetchFn}
          onSelect={handleSelect}
          selectedSlug={build.background?.slug}
          getSlug={(item: any) => item.slug}
          getDisplayName={(item: any) => item.display_name || item.name}
          renderItem={(item: any) => (
            <div>
              <div className="font-medium text-sm">{item.display_name || item.name}</div>
              <div className="text-xs text-gray-500">
                {(item.trained_skills || []).join(", ")}
                {item.lore?.length ? ` + ${item.lore.join(", ")}` : ""}
              </div>
            </div>
          )}
        />
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {detail ? (
          <div className="space-y-4">
            <h3 className="text-xl font-bold">{detail.display_name || detail.name}</h3>
            
            <div className="bg-gray-800/50 rounded-lg p-3 space-y-2">
              {detail.trained_skills?.length > 0 && (
                <div className="text-sm">
                  <span className="text-gray-400">受训技能: </span>
                  <span className="text-green-400">{detail.trained_skills.join(", ")}</span>
                </div>
              )}
              {detail.lore?.length > 0 && (
                <div className="text-sm">
                  <span className="text-gray-400">学识: </span>
                  <span className="text-yellow-400">{detail.lore.join(", ")}</span>
                </div>
              )}
              {detail.granted_feat_names?.length > 0 && (
                <div className="text-sm">
                  <span className="text-gray-400">赠送专长: </span>
                  <span className="text-blue-400">{detail.granted_feat_names.join(", ")}</span>
                </div>
              )}
            </div>

            {detail.description_rendered || detail.description_cn || detail.description ? (
              <PF2eDescription html={detail.description_rendered || detail.description_cn || detail.description} />
            ) : null}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            从左侧选择一个背景
          </div>
        )}
      </div>
    </div>
  );
}
