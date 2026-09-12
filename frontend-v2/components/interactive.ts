import type { KeyboardEvent } from "react";

/** Props that make a non-button element keyboard-activatable (Enter/Space). */
export function interactiveProps(onActivate: () => void): {
  role: "button";
  tabIndex: 0;
  onKeyDown: (e: KeyboardEvent<HTMLElement>) => void;
} {
  return {
    role: "button",
    tabIndex: 0,
    onKeyDown: (e: KeyboardEvent<HTMLElement>) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onActivate();
      }
    },
  };
}