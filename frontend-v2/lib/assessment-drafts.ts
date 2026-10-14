export function clearLearnerDrafts(learnerId: string): boolean {
  if (typeof window === "undefined") return true;
  const prefix = `aria_assess_draft:${learnerId}:`;
  try {
    const keys = Object.keys(window.localStorage).filter(key => key === "aria_assess_draft" || key.startsWith(prefix));
    let cleared = true;
    for (const key of keys) {
      try { window.localStorage.removeItem(key); }
      catch { cleared = false; }
    }
    return cleared;
  } catch { return false; }
}
