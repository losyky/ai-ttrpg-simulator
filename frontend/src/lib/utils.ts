import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { ChatMessage } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function generateId() {
  return Math.random().toString(36).slice(2, 10);
}

/**
 * Convert raw backend history into ChatMessage[], correctly preserving
 * unresolved interactive elements on the last actionable message.
 *
 * Logic: every interactive element is marked `resolved: true` EXCEPT
 * those on the **last message that carries interactive controls** when
 * no subsequent user message exists (meaning the player hadn't acted
 * on them before saving).
 */
export function hydrateHistory(
  rawHistory: Record<string, unknown>[],
  idPrefix: string = "loaded",
): ChatMessage[] {
  // Find the index of the last message that has interactive elements
  let lastInteractiveIdx = -1;
  for (let i = rawHistory.length - 1; i >= 0; i--) {
    if (
      rawHistory[i].interactive &&
      (rawHistory[i].interactive as unknown[]).length > 0
    ) {
      lastInteractiveIdx = i;
      break;
    }
  }

  // Check whether a user message follows the last interactive message
  let userRespondedAfterLast = false;
  if (lastInteractiveIdx >= 0) {
    for (let j = lastInteractiveIdx + 1; j < rawHistory.length; j++) {
      if (rawHistory[j].role === "user") {
        userRespondedAfterLast = true;
        break;
      }
    }
  }

  return rawHistory.map((m, i) => {
    const keepUnresolved =
      i === lastInteractiveIdx && !userRespondedAfterLast;

    return {
      id: `${idPrefix}_${i}`,
      role: (m.role as ChatMessage["role"]) || "system",
      content: (m.content as string) || "",
      timestamp: Date.now() - (rawHistory.length - i) * 1000,
      ...(m.dice ? { dice: m.dice } : {}),
      ...(m.interactive
        ? {
            interactive: (
              m.interactive as Array<Record<string, unknown>>
            ).map((ie) => ({
              ...ie,
              resolved: keepUnresolved ? false : true,
              resolved_value: keepUnresolved ? "" : (ie.resolved_value ?? ""),
            })),
          }
        : {}),
    };
  }) as ChatMessage[];
}
