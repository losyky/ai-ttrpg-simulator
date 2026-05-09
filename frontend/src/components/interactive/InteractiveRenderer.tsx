"use client";

import type { InteractiveElement, DiceResult } from "@/lib/types";
import ChoiceCard from "./ChoiceCard";
import DiceRollButton from "./DiceRollButton";
import DualityDiceButton from "./DualityDiceButton";
import TokenUpdateCard from "./TokenUpdateCard";
import InputPrompt from "./InputPrompt";

export function formatDiceResultMessage(result: DiceResult): string {
  if (result.duality_outcome) {
    const outcomeText =
      result.duality_outcome === "critical_success"
        ? "大成功"
        : result.duality_outcome === "with_hope"
          ? "以希望成功"
          : "以恐惧成功";
    return `[二元骰结果] Hope: ${result.hope_die}, Fear: ${result.fear_die}, 总计 ${result.total} → ${outcomeText}`;
  }
  const successText = result.success_level
    ? ` → ${
        result.success_level === "critical_success"
          ? "大成功"
          : result.success_level === "success"
            ? "成功"
            : result.success_level === "failure"
              ? "失败"
              : result.success_level === "critical_failure"
                ? "大失败"
                : result.success_level
      }`
    : "";
  const raiseText = (result.raises ?? 0) > 0 ? ` (优良 ×${result.raises})` : "";
  return `[骰子结果] ${result.expression} = ${result.total}${successText}${raiseText}`;
}

interface InteractiveRendererProps {
  elements: InteractiveElement[];
  sessionId: string;
  onSendMessage: (message: string) => void;
  onDiceResult?: (result: DiceResult) => void;
  onResolve?: (elementId: string, value: string, dice?: DiceResult) => void;
  disabled?: boolean;
}

export default function InteractiveRenderer({
  elements,
  sessionId,
  onSendMessage,
  onDiceResult,
  onResolve,
  disabled,
}: InteractiveRendererProps) {
  if (!elements.length) return null;

  return (
    <div className="space-y-2">
      {elements.map((elem) => {
        switch (elem.element_type) {
          case "choices":
            return (
              <ChoiceCard
                key={elem.id}
                element={elem}
                disabled={disabled || elem.resolved}
                onSelect={(_, label) => {
                  onResolve?.(elem.id, label);
                  onSendMessage(label);
                }}
              />
            );
          case "dice_request":
            return (
              <DiceRollButton
                key={elem.id}
                element={elem}
                sessionId={sessionId}
                disabled={disabled || elem.resolved}
                onResult={(result) => {
                  const msg = formatDiceResultMessage(result);
                  onResolve?.(elem.id, msg, result);
                  onDiceResult?.(result);
                  onSendMessage(msg);
                }}
              />
            );
          case "duality_dice_request":
            return (
              <DualityDiceButton
                key={elem.id}
                element={elem}
                sessionId={sessionId}
                disabled={disabled || elem.resolved}
                onResult={(result) => {
                  const msg = formatDiceResultMessage(result);
                  onResolve?.(elem.id, msg, result);
                  onDiceResult?.(result);
                  onSendMessage(msg);
                }}
              />
            );
          case "token_update":
            return <TokenUpdateCard key={elem.id} element={elem} />;
          case "input_prompt":
            return (
              <InputPrompt
                key={elem.id}
                element={elem}
                disabled={disabled || elem.resolved}
                onSubmit={(value) => {
                  onResolve?.(elem.id, value);
                  onSendMessage(value);
                }}
              />
            );
          default:
            return null;
        }
      })}
    </div>
  );
}
