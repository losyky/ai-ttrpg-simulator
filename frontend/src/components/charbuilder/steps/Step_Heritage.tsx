"use client";

import { useCallback, useState } from "react";
import OptionBrowser from "../shared/OptionBrowser";
import PF2eDescription from "../shared/PF2eDescription";
import { cbSearchHeritages } from "@/lib/api";
import type { CharacterBuildState } from "../CharBuilderWizard";

interface Props {
  build: CharacterBuildState;
  updateBuild: (partial: Partial<CharacterBuildState>) => void;
}

export default function StepHeritage({ build, updateBuild }: Props) {
  const [detail, setDetail] = useState<any>(null);
  const ancestrySlug = build.ancestry?.slug || "";

  const fetchFn = useCallback(
    async (q: string) => cbSearchHeritages(ancestrySlug, q),
    [ancestrySlug],
  );

  const handleSelect = (item: any) => {
    setDetail(item);
    updateBuild({
      heritage: { slug: item.slug, name: item.display_name || item.name },
    });
  };

  if (!ancestrySlug) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        请先选择族裔
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <div className="w-1/3 border-r border-gray-700">
        <OptionBrowser
          title={`选择传承 (${build.ancestry?.name || ""})`}
          fetchFn={fetchFn}
          onSelect={handleSelect}
          selectedSlug={build.heritage?.slug}
          getSlug={(item: any) => item.slug}
          getDisplayName={(item: any) => item.display_name || item.name}
          renderItem={(item: any) => (
            <div>
              <div className="font-medium text-sm">{item.display_name || item.name}</div>
              <div className="text-xs text-gray-500 line-clamp-2">{item.rules_summary || ""}</div>
            </div>
          )}
        />
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {detail ? (
          <div className="space-y-4">
            <h3 className="text-xl font-bold">{detail.display_name || detail.name}</h3>
            {detail.description_cn || detail.description ? (
              <PF2eDescription html={detail.description_cn || detail.description} />
            ) : (
              <p className="text-gray-400">{detail.rules_summary}</p>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            从左侧选择一个传承
          </div>
        )}
      </div>
    </div>
  );
}
