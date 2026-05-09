"use client";

import { useState } from "react";
import { cbValidateBuild, cbAssembleBuild } from "@/lib/api";
import type { CharacterBuildState } from "../CharBuilderWizard";

interface Props {
  build: CharacterBuildState;
  updateBuild: (partial: Partial<CharacterBuildState>) => void;
  onComplete?: () => void;
}

export default function StepReview({ build, updateBuild, onComplete }: Props) {
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<{ valid: boolean; errors: string[]; warnings: string[] } | null>(null);
  const [assembling, setAssembling] = useState(false);
  const [result, setResult] = useState("");

  const handleValidate = async () => {
    setValidating(true);
    try {
      const buildPayload = {
        level: build.level,
        ancestry_slug: build.ancestry?.slug || "",
        heritage_slug: build.heritage?.slug || "",
        background_slug: build.background?.slug || "",
        class_slug: build.class_?.slug || "",
        key_ability: build.class_?.keyAbility || "",
        free_boosts: build.freeBoosts,
        trained_skills: build.trainedSkills,
        feats: build.feats,
      };
      const res = await cbValidateBuild(buildPayload);
      setValidation(res);
    } catch (e: any) {
      setValidation({ valid: false, errors: [e.message], warnings: [] });
    }
    setValidating(false);
  };

  const handleAssemble = async () => {
    if (!build.name) {
      alert("请先填写角色名称");
      return;
    }
    setAssembling(true);
    try {
      const buildPayload = {
        level: build.level,
        name: build.name,
        ancestry_slug: build.ancestry?.slug || "",
        heritage_slug: build.heritage?.slug || "",
        background_slug: build.background?.slug || "",
        class_slug: build.class_?.slug || "",
        key_ability: build.class_?.keyAbility || "",
        free_boosts: build.freeBoosts,
        level_boosts: build.levelBoosts,
        voluntary_flaws: build.voluntaryFlaws,
        trained_skills: build.trainedSkills,
        skill_increases: build.skillIncreases,
        feats: build.feats,
        spells: build.spells,
        equipment: build.equipment.map((e) => ({ slug: e.slug, quantity: e.quantity })),
        details: build.details,
      };
      const res = await cbAssembleBuild(buildPayload, build.name);
      setResult(res.result);
    } catch (e: any) {
      setResult(`创建失败: ${e.message}`);
    }
    setAssembling(false);
  };

  return (
    <div className="p-4 overflow-y-auto h-full max-w-3xl mx-auto">
      <h3 className="text-lg font-bold mb-4">角色审核</h3>

      {/* Summary */}
      <div className="bg-gray-800 rounded-lg p-4 mb-4 space-y-2">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">名称: </span>
            <span className="text-white font-medium">{build.name || "(未命名)"}</span>
          </div>
          <div>
            <span className="text-gray-400">等级: </span>
            <span className="text-white font-medium">{build.level}</span>
          </div>
          <div>
            <span className="text-gray-400">族裔: </span>
            <span className="text-white">{build.ancestry?.name || "—"}</span>
          </div>
          <div>
            <span className="text-gray-400">传承: </span>
            <span className="text-white">{build.heritage?.name || "—"}</span>
          </div>
          <div>
            <span className="text-gray-400">背景: </span>
            <span className="text-white">{build.background?.name || "—"}</span>
          </div>
          <div>
            <span className="text-gray-400">职业: </span>
            <span className="text-white">{build.class_?.name || "—"}</span>
          </div>
        </div>

        {build.feats.length > 0 && (
          <div className="pt-2 border-t border-gray-700">
            <span className="text-xs text-gray-400">专长: </span>
            <span className="text-xs text-gray-300">{build.feats.map((f) => f.name).join(", ")}</span>
          </div>
        )}
        {build.spells.length > 0 && (
          <div className="pt-2 border-t border-gray-700">
            <span className="text-xs text-gray-400">法术: </span>
            <span className="text-xs text-gray-300">{build.spells.map((s) => s.name).join(", ")}</span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-3 mb-4">
        <button
          onClick={handleValidate}
          disabled={validating}
          className="px-4 py-2 bg-yellow-700 text-white rounded hover:bg-yellow-600 disabled:opacity-50 text-sm"
        >
          {validating ? "校验中..." : "校验构建"}
        </button>
        <button
          onClick={handleAssemble}
          disabled={assembling || !build.name}
          className="px-4 py-2 bg-green-700 text-white rounded hover:bg-green-600 disabled:opacity-50 text-sm"
        >
          {assembling ? "创建中..." : "创建角色"}
        </button>
      </div>

      {/* Validation results */}
      {validation && (
        <div className={`rounded-lg p-3 mb-4 ${validation.valid ? "bg-green-900/30 border border-green-700" : "bg-red-900/30 border border-red-700"}`}>
          <div className="font-medium text-sm mb-1">
            {validation.valid ? "✅ 构建合法" : "❌ 构建存在问题"}
          </div>
          {validation.errors.map((e, i) => (
            <p key={i} className="text-sm text-red-400">• {e}</p>
          ))}
          {validation.warnings.map((w, i) => (
            <p key={i} className="text-sm text-yellow-400">⚠ {w}</p>
          ))}
        </div>
      )}

      {/* Assembly result */}
      {result && (
        <div className="bg-gray-800 rounded-lg p-3">
          <pre className="text-sm text-gray-300 whitespace-pre-wrap">{result}</pre>
          {result.includes("成功") && onComplete && (
            <button
              onClick={onComplete}
              className="mt-3 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-500 text-sm"
            >
              完成，返回角色列表
            </button>
          )}
        </div>
      )}
    </div>
  );
}
