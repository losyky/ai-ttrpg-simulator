"use client";

import { useState, useEffect, useCallback } from "react";
import RarityBadge from "./RarityBadge";

interface OptionBrowserProps<T> {
  title: string;
  fetchFn: (query: string) => Promise<{ count: number; results: T[] }>;
  renderItem: (item: T, isSelected: boolean) => React.ReactNode;
  onSelect: (item: T) => void;
  selectedSlug?: string;
  getSlug: (item: T) => string;
  getDisplayName: (item: T) => string;
}

export default function OptionBrowser<T>({
  title,
  fetchFn,
  renderItem,
  onSelect,
  selectedSlug,
  getSlug,
  getDisplayName,
}: OptionBrowserProps<T>) {
  const [items, setItems] = useState<T[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (q: string) => {
    setLoading(true);
    try {
      const data = await fetchFn(q);
      setItems(data.results);
    } catch {
      setItems([]);
    }
    setLoading(false);
  }, [fetchFn]);

  useEffect(() => {
    load("");
  }, [load]);

  useEffect(() => {
    const timer = setTimeout(() => load(query), 300);
    return () => clearTimeout(timer);
  }, [query, load]);

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-gray-300 mb-2">{title}</h3>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜索..."
          className="w-full px-3 py-1.5 bg-gray-800 border border-gray-600 rounded text-sm text-white placeholder-gray-500 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none"
        />
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center text-gray-500 text-sm">加载中...</div>
        ) : items.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">无结果</div>
        ) : (
          <div className="divide-y divide-gray-800">
            {items.map((item) => {
              const slug = getSlug(item);
              const isSelected = slug === selectedSlug;
              return (
                <div
                  key={slug}
                  onClick={() => onSelect(item)}
                  className={`p-3 cursor-pointer transition-colors ${
                    isSelected
                      ? "bg-blue-900/40 border-l-2 border-blue-500"
                      : "hover:bg-gray-800/60 border-l-2 border-transparent"
                  }`}
                >
                  {renderItem(item, isSelected)}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
