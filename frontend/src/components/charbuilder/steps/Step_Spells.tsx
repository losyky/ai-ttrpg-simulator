"use client";

import { useCallback, useState } from "react";
import OptionBrowser from "../shared/OptionBrowser";
import PF2eDescription from "../shared/PF2eDescription";
import { cbSearchSpells } from "@/lib/api";
import type { CharacterBuildState } from "../CharBuilderWizard";

interface Props {
  build: CharacterBuildState;
  updateBuild: (partial: Partial<CharacterBuildState>) => void;
}

export default function StepSpells({ build, updateBuild }: Props) {
  const [detail, setDetail] = useState<any>(null);
  const [tradition, setTradition] = useState("");

  const isSpellcaster = (build.class_?.spellcasting || 0) > 0;

  const fetchFn = useCallback(
    async (q: string) => cbSearchSpells({ tradition, rank_max: build.level > 1 ? Math.ceil(build.level / 2) : 1, q, limit: 50 }),
    [tradition, build.level],
  );

  const handleSelect = (item: any) => {
    setDetail(item);
    const existing = build.spells.find((s) => s.slug === item.slug);
    if (!existing) {
      updateBuild({
        spells: [...build.spells, { rank: item.rank, slug: item.slug, name: item.display_name || item.name }],
      });
    }
  };

  const removeSpell = (slug: string) => {
    updateBuild({ spells: build.spells.filter((s) => s.slug !== slug) });
  };

  if (!isSpellcaster) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        当前职业不是施法者，可跳过此步
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <div className="w-1/3 border-r border-gray-700 flex flex-col">
        <div className="p-3 border-b border-gray-700">
          <select
            value={tradition}
            onChange={(e) => setTradition(e.target.value)}
            className="w-full bg-gray-800 text-sm text-white border border-gray-600 rounded px-2 py-1"
          >
            <option value="">全部传统</option>
            <option value="arcane">奥术</option>
            <option value="divine">神术</option>
            <option value="occult">秘术</option>
            <option value="primal">原能</option>
          </select>
        </div>
        <div className="flex-1">
          <OptionBrowser
            title="选择法术"
            fetchFn={fetchFn}
            onSelect={handleSelect}
            getSlug={(item: any) => item.slug}
            getDisplayName={(item: any) => item.display_name || item.name}
            renderItem={(item: any) => (
              <div>
                <div className="font-medium text-sm">{item.display_name || item.name}</div>
                <div className="text-xs text-gray-500">
                  {item.rank === 0 ? "戏法" : `${item.rank}环`} | {(item.traditions || []).join(", ")}
                </div>
              </div>
            )}
          />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {/* Selected spells list */}
        {build.spells.length > 0 && (
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-gray-300 mb-2">已选法术 ({build.spells.length})</h4>
            <div className="space-y-1">
              {build.spells.map((s) => (
                <div key={s.slug} className="flex items-center justify-between bg-gray-800 rounded px-3 py-1.5 text-sm">
                  <span>{s.name} ({s.rank === 0 ? "戏法" : `${s.rank}环`})</span>
                  <button onClick={() => removeSpell(s.slug)} className="text-red-400 hover:text-red-300 text-xs">移除</button>
                </div>
              ))}
            </div>
          </div>
        )}

        {detail ? (
          <div className="space-y-3">
            <h3 className="text-lg font-bold">{detail.display_name || detail.name}</h3>
            <div className="flex gap-2 flex-wrap text-xs">
              <span className="bg-gray-800 px-2 py-0.5 rounded">{detail.rank === 0 ? "戏法" : `${detail.rank}环`}</span>
              {detail.action_cost && <span className="bg-gray-800 px-2 py-0.5 rounded">{detail.action_cost}动作</span>}
              {detail.range && <span className="bg-gray-800 px-2 py-0.5 rounded">射程 {detail.range}</span>}
              {detail.duration && <span className="bg-gray-800 px-2 py-0.5 rounded">持续 {detail.duration}</span>}
              {detail.defense && <span className="bg-gray-800 px-2 py-0.5 rounded">豁免 {detail.defense}</span>}
            </div>
            <PF2eDescription html={detail.description_cn || detail.description || ""} />
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            从左侧选择法术查看详情
          </div>
        )}
      </div>
    </div>
  );
}
