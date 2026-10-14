const labels: Record<string, string> = {
  NEW: "New note",
  REVIEWING: "Review needed",
  LEARNING: "Learning",
  MASTERED: "Mastered",
};

export function noteReviewLabel(state: string): string {
  return labels[state.toUpperCase()] ?? state.replaceAll("_", " ").toLowerCase().replace(/^./, character => character.toUpperCase());
}
