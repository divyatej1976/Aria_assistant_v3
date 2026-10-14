export function assessmentTypeLabel(mode: string): string {
  const labels: Record<string, string> = {
    DAILY_REVIEW: "Daily Review", BASELINE: "Practice", TARGETED: "Targeted Practice",
    RETEST_TARGETED: "Targeted Review",
  };
  return labels[mode] ?? mode.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());
}

export function assessmentTypeClass(mode: string): string {
  return ({ DAILY_REVIEW: "daily", BASELINE: "practice", TARGETED: "targeted", RETEST_TARGETED: "retest" } as Record<string, string>)[mode] ?? "";
}
