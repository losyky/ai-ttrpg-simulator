interface RarityBadgeProps {
  rarity?: string;
}

const RARITY_COLORS: Record<string, string> = {
  common: "bg-gray-600 text-gray-200",
  uncommon: "bg-orange-700 text-orange-100",
  rare: "bg-blue-700 text-blue-100",
  unique: "bg-purple-700 text-purple-100",
};

const RARITY_LABELS: Record<string, string> = {
  common: "普通",
  uncommon: "罕见",
  rare: "稀有",
  unique: "独特",
};

export default function RarityBadge({ rarity = "common" }: RarityBadgeProps) {
  const color = RARITY_COLORS[rarity] ?? RARITY_COLORS.common;
  const label = RARITY_LABELS[rarity] ?? rarity;
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {label}
    </span>
  );
}
