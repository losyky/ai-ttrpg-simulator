"use client";

import { useCallback, useState } from "react";
import OptionBrowser from "../shared/OptionBrowser";
import { cbSearchEquipment } from "@/lib/api";
import type { CharacterBuildState } from "../CharBuilderWizard";

interface Props {
  build: CharacterBuildState;
  updateBuild: (partial: Partial<CharacterBuildState>) => void;
}

function formatPrice(cp: number): string {
  if (cp >= 100) return `${Math.floor(cp / 100)} gp`;
  if (cp >= 10) return `${Math.floor(cp / 10)} sp`;
  return `${cp} cp`;
}

export default function StepEquipment({ build, updateBuild }: Props) {
  const [itemType, setItemType] = useState("");
  const [detail, setDetail] = useState<any>(null);

  const fetchFn = useCallback(
    async (q: string) => cbSearchEquipment({ item_type: itemType, q, limit: 50 }),
    [itemType],
  );

  const handleSelect = (item: any) => {
    setDetail(item);
    const existing = build.equipment.find((e) => e.slug === item.slug);
    if (existing) {
      updateBuild({
        equipment: build.equipment.map((e) =>
          e.slug === item.slug ? { ...e, quantity: e.quantity + 1 } : e,
        ),
      });
    } else {
      updateBuild({
        equipment: [
          ...build.equipment,
          { slug: item.slug, name: item.display_name || item.name, quantity: 1, price_cp: item.price_cp },
        ],
      });
    }
  };

  const removeItem = (slug: string) => {
    updateBuild({ equipment: build.equipment.filter((e) => e.slug !== slug) });
  };

  const totalCost = build.equipment.reduce((sum, e) => sum + e.price_cp * e.quantity, 0);

  return (
    <div className="flex h-full">
      <div className="w-1/3 border-r border-gray-700 flex flex-col">
        <div className="p-3 border-b border-gray-700">
          <select
            value={itemType}
            onChange={(e) => setItemType(e.target.value)}
            className="w-full bg-gray-800 text-sm text-white border border-gray-600 rounded px-2 py-1"
          >
            <option value="">全部类型</option>
            <option value="weapon">武器</option>
            <option value="armor">护甲</option>
            <option value="shield">盾牌</option>
            <option value="equipment">装备</option>
            <option value="consumable">消耗品</option>
          </select>
        </div>
        <div className="flex-1">
          <OptionBrowser
            title="选择装备"
            fetchFn={fetchFn}
            onSelect={handleSelect}
            getSlug={(item: any) => item.slug}
            getDisplayName={(item: any) => item.display_name || item.name}
            renderItem={(item: any) => (
              <div>
                <div className="font-medium text-sm">{item.display_name || item.name}</div>
                <div className="text-xs text-gray-500">
                  {formatPrice(item.price_cp)} | {item.item_type}
                  {item.damage ? ` | ${item.damage}` : ""}
                </div>
              </div>
            )}
          />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-semibold text-gray-300">已选装备</h4>
            <span className="text-sm text-yellow-400">总计: {formatPrice(totalCost)}</span>
          </div>
          {build.equipment.length === 0 ? (
            <p className="text-sm text-gray-500">尚未选择装备</p>
          ) : (
            <div className="space-y-1">
              {build.equipment.map((e) => (
                <div key={e.slug} className="flex items-center justify-between bg-gray-800 rounded px-3 py-1.5 text-sm">
                  <span>{e.name} x{e.quantity}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-500">{formatPrice(e.price_cp * e.quantity)}</span>
                    <button onClick={() => removeItem(e.slug)} className="text-red-400 hover:text-red-300 text-xs">移除</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
