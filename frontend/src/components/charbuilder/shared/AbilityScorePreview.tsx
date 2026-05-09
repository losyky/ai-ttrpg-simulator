"use client";

import { useEffect, useState } from "react";
import { cbComputeAbilities } from "@/lib/api";

interface AbilityScorePreviewProps {
  ancestryBoosts: string[];
  ancestryFlaws: string[];
  backgroundBoosts: string[];
  classBoost: string;
  freeBoosts: string[];
  levelBoosts: Record<string, string[]>;
  voluntaryFlaws: string[];
}

const ABILITY_LABELS: Record<string, string> = {
  str: "力量", dex: "敏捷", con: "体质",
  int: "智力", wis: "感知", cha: "魅力",
};

export default function AbilityScorePreview(props: AbilityScorePreviewProps) {
  const [scores, setScores] = useState<Record<string, number>>({
    str: 0, dex: 0, con: 0, int: 0, wis: 0, cha: 0,
  });

  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const result = await cbComputeAbilities({
          ancestry_boosts: props.ancestryBoosts,
          ancestry_flaws: props.ancestryFlaws,
          background_boosts: props.backgroundBoosts,
          class_boost: props.classBoost,
          free_boosts: props.freeBoosts,
          level_boosts: props.levelBoosts,
          voluntary_flaws: props.voluntaryFlaws,
        });
        setScores(result.abilities);
      } catch {
        // Keep current scores on error
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [
    props.ancestryBoosts, props.ancestryFlaws,
    props.backgroundBoosts, props.classBoost,
    props.freeBoosts, props.levelBoosts, props.voluntaryFlaws,
  ]);

  return (
    <div className="flex gap-3 flex-wrap">
      {Object.entries(ABILITY_LABELS).map(([key, label]) => {
        const val = scores[key] ?? 0;
        const mod = Math.floor((val - 10) / 2);
        const modStr = mod >= 0 ? `+${mod}` : `${mod}`;
        return (
          <div
            key={key}
            className="flex flex-col items-center bg-gray-800 rounded-lg p-2 min-w-[60px]"
          >
            <span className="text-xs text-gray-400 uppercase">{label}</span>
            <span className="text-lg font-bold text-white">{val || 10}</span>
            <span className={`text-sm font-medium ${mod >= 0 ? "text-green-400" : "text-red-400"}`}>
              {modStr}
            </span>
          </div>
        );
      })}
    </div>
  );
}
