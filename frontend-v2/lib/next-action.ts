import type { IconName } from "@/components/icons";

export type NextActionInput = {
  overdueTask?: { id: string; title: string } | null;
  dueNotesCount?: number;
  focusDecision?: { reason: string; concept?: string } | null;
  nearestExamDaysLeft?: number | null;
  nearestExamTitle?: string | null;
  hasLastSession?: boolean;
};

export type NextAction = {
  kind: "task" | "review" | "focus" | "exam" | "study";
  icon: IconName;
  title: string;
  why: string;
  cta: string;
  href: string;
};

/**
 * Single "what should I do next" recommendation for the dashboard.
 * Priority: overdue task -> due reviews -> weak-concept focus -> nearest exam
 * -> continue studying.
 */
export function pickNextAction(input: NextActionInput): NextAction {
  if (input.overdueTask) {
    return {
      kind: "task",
      icon: "check",
      title: `Complete “${input.overdueTask.title}”`,
      why: "This task is past its due date — clearing it keeps your plan on track.",
      cta: "Open planner",
      href: "/app/planner",
    };
  }
  if ((input.dueNotesCount ?? 0) > 0) {
    return {
      kind: "review",
      icon: "refresh",
      title: `Review ${input.dueNotesCount} due note${input.dueNotesCount === 1 ? "" : "s"}`,
      why: "Spaced review at the right moment is what makes knowledge stick.",
      cta: "Start review",
      href: "/app/materials",
    };
  }
  if (input.focusDecision) {
    return {
      kind: "focus",
      icon: "target",
      title: input.focusDecision.concept
        ? `Focus study: ${input.focusDecision.concept}`
        : "Focus study on your weakest concept",
      why: input.focusDecision.reason,
      cta: "Start now",
      href: "/app/learn",
    };
  }
  if (input.nearestExamDaysLeft != null && input.nearestExamDaysLeft <= 3) {
    return {
      kind: "exam",
      icon: "calendar",
      title: `Prepare for ${input.nearestExamTitle ?? "your exam"} (${input.nearestExamDaysLeft}d left)`,
      why: "Your exam is close — a focused session now pays off.",
      cta: "Study for it",
      href: "/app/learn",
    };
  }
  return {
    kind: input.hasLastSession ? "study" : "study",
    icon: "message",
    title: input.hasLastSession ? "Continue your study session" : "Start your first study session",
    why: "Small, regular sessions are how topics become strong.",
    cta: "Open ARIA tutor",
    href: "/app/learn",
  };
}