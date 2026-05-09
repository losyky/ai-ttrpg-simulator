"use client";

import type { CharacterBuildState } from "../CharBuilderWizard";

interface Props {
  build: CharacterBuildState;
  updateBuild: (partial: Partial<CharacterBuildState>) => void;
}

export default function StepDetails({ build, updateBuild }: Props) {
  const update = (field: keyof CharacterBuildState["details"], value: string) => {
    updateBuild({ details: { ...build.details, [field]: value } });
  };

  return (
    <div className="p-4 overflow-y-auto h-full max-w-2xl mx-auto">
      <h3 className="text-lg font-bold mb-4">角色详情</h3>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">角色名称</label>
          <input
            type="text"
            value={build.name}
            onChange={(e) => updateBuild({ name: e.target.value })}
            placeholder="输入角色名称..."
            className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:ring-1 focus:ring-blue-500 outline-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">性别</label>
            <input
              type="text"
              value={build.details.gender}
              onChange={(e) => update("gender", e.target.value)}
              placeholder="如: 男 / 女 / 其他"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">年龄</label>
            <input
              type="text"
              value={build.details.age}
              onChange={(e) => update("age", e.target.value)}
              placeholder="如: 25"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">信仰</label>
          <input
            type="text"
            value={build.details.deity}
            onChange={(e) => update("deity", e.target.value)}
            placeholder="信仰的神明（可选）"
            className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:ring-1 focus:ring-blue-500 outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">背景故事</label>
          <textarea
            value={build.details.biography}
            onChange={(e) => update("biography", e.target.value)}
            placeholder="描述角色的背景故事、性格特点..."
            rows={6}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:ring-1 focus:ring-blue-500 outline-none resize-y"
          />
        </div>
      </div>
    </div>
  );
}
