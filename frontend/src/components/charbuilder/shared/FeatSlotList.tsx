"use client";

interface FeatSlot {
  slotType: string;
  level: number;
  slug: string;
  name: string;
}

interface FeatSlotListProps {
  slots: FeatSlot[];
  onSelectSlot: (index: number) => void;
  selectedIndex?: number;
}

const SLOT_LABELS: Record<string, string> = {
  ancestry: "祖裔专长",
  class: "职业专长",
  general: "通用专长",
  skill: "技能专长",
  bonus: "额外专长",
};

export default function FeatSlotList({ slots, onSelectSlot, selectedIndex }: FeatSlotListProps) {
  if (slots.length === 0) {
    return <p className="text-sm text-gray-500 p-2">暂无可用专长槽</p>;
  }

  return (
    <div className="space-y-1">
      {slots.map((slot, i) => {
        const filled = !!slot.slug;
        const label = SLOT_LABELS[slot.slotType] ?? slot.slotType;
        return (
          <div
            key={`${slot.slotType}-${slot.level}-${i}`}
            onClick={() => onSelectSlot(i)}
            className={`flex items-center justify-between p-2 rounded cursor-pointer transition-colors text-sm ${
              i === selectedIndex
                ? "bg-blue-900/40 ring-1 ring-blue-500"
                : filled
                  ? "bg-gray-800"
                  : "bg-gray-800/50 border border-dashed border-gray-600"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Lv.{slot.level}</span>
              <span className="text-gray-400">{label}</span>
            </div>
            <span className={filled ? "text-white font-medium" : "text-gray-600"}>
              {filled ? slot.name : "— 未选择 —"}
            </span>
          </div>
        );
      })}
    </div>
  );
}
