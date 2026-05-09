"use client";

interface BoostAllocatorProps {
  label: string;
  availableAbilities: string[];
  selectedBoosts: string[];
  maxBoosts: number;
  onChange: (boosts: string[]) => void;
  flawMode?: boolean;
}

const ABILITY_LABELS: Record<string, string> = {
  str: "力量", dex: "敏捷", con: "体质",
  int: "智力", wis: "感知", cha: "魅力",
};

export default function BoostAllocator({
  label,
  availableAbilities,
  selectedBoosts,
  maxBoosts,
  onChange,
  flawMode = false,
}: BoostAllocatorProps) {
  const toggle = (ability: string) => {
    if (selectedBoosts.includes(ability)) {
      onChange(selectedBoosts.filter((a) => a !== ability));
    } else if (selectedBoosts.length < maxBoosts) {
      onChange([...selectedBoosts, ability]);
    }
  };

  const color = flawMode ? "red" : "blue";

  return (
    <div className="mb-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm font-medium text-gray-300">{label}</span>
        <span className="text-xs text-gray-500">
          ({selectedBoosts.length}/{maxBoosts})
        </span>
      </div>
      <div className="flex gap-2 flex-wrap">
        {availableAbilities.map((ability) => {
          const selected = selectedBoosts.includes(ability);
          return (
            <button
              key={ability}
              onClick={() => toggle(ability)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors
                ${selected
                  ? flawMode
                    ? "bg-red-700 text-red-100 ring-1 ring-red-500"
                    : "bg-blue-700 text-blue-100 ring-1 ring-blue-500"
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                }
                ${!selected && selectedBoosts.length >= maxBoosts ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}
              `}
              disabled={!selected && selectedBoosts.length >= maxBoosts}
            >
              {ABILITY_LABELS[ability] ?? ability}
            </button>
          );
        })}
      </div>
    </div>
  );
}
