"use client";

import { usePageVisible } from "./motion-system";

export type AssistantState = "idle" | "thinking" | "responding" | "listening" | "error";
const LABELS: Record<AssistantState, string> = { idle: "Ready to explore", thinking: "Thinking", responding: "Reply ready", listening: "Listening", error: "Reply unavailable" };

export function AssistantPresence({ state = "idle" }: { state?: AssistantState }) {
  const visible = usePageVisible();
  return <span className={`assistant-presence assistant-${state}`}><span className="assistant-orb" style={{ animationPlayState: visible ? "running" : "paused" }} aria-hidden="true"><i /><i /><i /></span><span role="status" className="assistant-status">{LABELS[state]}</span></span>;
}
