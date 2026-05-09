"use client";

import { useCallback, useState, useMemo } from "react";
import OptionBrowser from "../shared/OptionBrowser";
import PF2eDescription from "../shared/PF2eDescription";
import FeatSlotList from "../shared/FeatSlotList";
import { cbSearchFeats } from "@/lib/api";
import type { CharacterBuildState } from "../CharBuilderWizard";

interface Props {
  build: CharacterBuildState;
  updateBuild: (partial: Partial<CharacterBuildState>) => void;
}

type FeatSlot = { slotType: string; level: number; slug: string; name: string };

export default function StepFeats({ build, updateBuild }: Props) {
  const [selectedSlotIdx, setSelectedSlotIdx] = useState(0);
  const [detail, setDetail] = useState<any>(null);

  const slots = useMemo(() => {
    const result: FeatSlot[] = [];
    const classData = build.class_;
    if (!classData) return result;

    const addSlots = (levels: number[] | undefined, type: string) => {
      (levels || []).filter((l) => l <= build.level).forEach((l) => {
        const existing = build.feats.find((f) => f.slotType === type && f.level === l);
        result.push(existing || { slotType: type, level: l, slug: "", name: "" });
      });
    };

    // We don't have the feat levels directly on build.class_, so generate defaults
    addSlots([1, 5, 9, 13, 17].filter((l) => l <= build.level), "ancestry");
    addSlots(Array.from({ length: 20 }, (_, i) => i + 1).filter((l) => l % 2 === 0 || l === 1).filter((l) => l <= build.level), "class");
    addSlots([3, 7, 11, 15, 19].filter((l) => l <= build.level), "general");
    addSlots(Array.from({ length: 20 }, (_, i) => i + 1).filter((l) => l % 2 === 0).filter((l) => l <= build.level), "skill");

    return result;
  }, [build.level, build.class_, build.feats]);

  const currentSlot = slots[selectedSlotIdx];

  const fetchFn = useCallback(
    async (q: string) => {
      if (!currentSlot) return { count: 0, results: [] };
      return cbSearchFeats({
        category: currentSlot.slotType,
        level_max: currentSlot.level,
        class_slug: currentSlot.slotType === "class" ? build.class_?.slug : undefined,
        ancestry_slug: currentSlot.slotType === "ancestry" ? build.ancestry?.slug : undefined,
        q,
        limit: 50,
      });
    },
    [currentSlot, build.class_?.slug, build.ancestry?.slug],
  );

  const handleSelectFeat = (item: any) => {
    setDetail(item);
    if (!currentSlot) return;
    const newFeats = build.feats.filter(
      (f) => !(f.slotType === currentSlot.slotType && f.level === currentSlot.level),
    );
    newFeats.push({
      slotType: currentSlot.slotType,
      level: currentSlot.level,
      slug: item.slug,
      name: item.display_name || item.name,
    });
    updateBuild({ feats: newFeats });
  };

  return (
    <div className="flex h-full">
      {/* Slot list */}
      <div className="w-1/4 border-r border-gray-700 overflow-y-auto p-3">
        <h4 className="text-sm font-semibold text-gray-300 mb-2">专长槽</h4>
        <FeatSlotList
          slots={slots}
          onSelectSlot={setSelectedSlotIdx}
          selectedIndex={selectedSlotIdx}
        />
      </div>

      {/* Feat browser */}
      <div className="w-1/3 border-r border-gray-700">
        <OptionBrowser
          title={currentSlot ? `${currentSlot.slotType} Lv.${currentSlot.level}` : "选择专长"}
          fetchFn={fetchFn}
          onSelect={handleSelectFeat}
          selectedSlug={currentSlot?.slug}
          getSlug={(item: any) => item.slug}
          getDisplayName={(item: any) => item.display_name || item.name}
          renderItem={(item: any) => (
            <div>
              <div className="font-medium text-sm">{item.display_name || item.name}</div>
              <div className="text-xs text-gray-500">
                Lv.{item.level} {item.traits?.join(", ")}
              </div>
            </div>
          )}
        />
      </div>

      {/* Detail */}
      <div className="flex-1 overflow-y-auto p-4">
        {detail ? (
          <div className="space-y-3">
            <h3 className="text-lg font-bold">{detail.display_name || detail.name}</h3>
            <div className="flex gap-2 text-xs">
              <span className="bg-gray-800 px-2 py-0.5 rounded">Lv.{detail.level}</span>
              <span className="bg-gray-800 px-2 py-0.5 rounded">{detail.category}</span>
              {detail.action_type && <span className="bg-gray-800 px-2 py-0.5 rounded">{detail.action_type}</span>}
            </div>
            {detail.prerequisites?.length > 0 && (
              <p className="text-sm text-yellow-400">前提: {detail.prerequisites.join("; ")}</p>
            )}
            <PF2eDescription html={detail.description_cn || detail.description || ""} />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            选择一个专长槽，然后从中间列表选择专长
          </div>
        )}
      </div>
    </div>
  );
}
