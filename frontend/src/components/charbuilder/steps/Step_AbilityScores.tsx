"use client";

import BoostAllocator from "../shared/BoostAllocator";
import AbilityScorePreview from "../shared/AbilityScorePreview";
import type { CharacterBuildState } from "../CharBuilderWizard";

const ALL_ABILITIES = ["str", "dex", "con", "int", "wis", "cha"];

interface Props {
  build: CharacterBuildState;
  updateBuild: (partial: Partial<CharacterBuildState>) => void;
}

export default function StepAbilityScores({ build, updateBuild }: Props) {
  const ancestryBoostValues = build.ancestry
    ? Object.values(build.ancestry.boosts).map((v) => v).filter(Boolean)
    : [];
  const ancestryFlawValues = build.ancestry
    ? Object.values(build.ancestry.flaws).map((v) => v).filter(Boolean)
    : [];

  return (
    <div className="p-4 space-y-6 overflow-y-auto h-full">
      <h3 className="text-lg font-bold">属性值分配</h3>
      
      <div className="bg-gray-800/50 rounded-lg p-4">
        <AbilityScorePreview
          ancestryBoosts={ancestryBoostValues.flat()}
          ancestryFlaws={ancestryFlawValues.flat()}
          backgroundBoosts={Object.values(build.background?.boosts || {}).filter(Boolean).flat() as string[]}
          classBoost={build.class_?.keyAbility || ""}
          freeBoosts={build.freeBoosts}
          levelBoosts={Object.fromEntries(
            Object.entries(build.levelBoosts).map(([k, v]) => [k, v])
          )}
          voluntaryFlaws={build.voluntaryFlaws}
        />
      </div>

      <div className="space-y-4">
        <BoostAllocator
          label="自由属性提升 (4 个)"
          availableAbilities={ALL_ABILITIES}
          selectedBoosts={build.freeBoosts}
          maxBoosts={4}
          onChange={(boosts) => updateBuild({ freeBoosts: boosts })}
        />

        <BoostAllocator
          label="自愿缺陷 (可选, 最多 2 个)"
          availableAbilities={ALL_ABILITIES}
          selectedBoosts={build.voluntaryFlaws}
          maxBoosts={2}
          onChange={(flaws) => updateBuild({ voluntaryFlaws: flaws })}
          flawMode
        />

        {build.level >= 5 &&
          [5, 10, 15, 20]
            .filter((lv) => lv <= build.level)
            .map((lv) => (
              <BoostAllocator
                key={lv}
                label={`${lv}级属性提升 (4 个)`}
                availableAbilities={ALL_ABILITIES}
                selectedBoosts={build.levelBoosts[lv] || []}
                maxBoosts={4}
                onChange={(boosts) =>
                  updateBuild({
                    levelBoosts: { ...build.levelBoosts, [lv]: boosts },
                  })
                }
              />
            ))}
      </div>
    </div>
  );
}
