const DATE_OPTS: Intl.DateTimeFormatOptions = {
  year: "numeric",
  month: "short",
  day: "numeric",
};

const DATE_TIME_OPTS: Intl.DateTimeFormatOptions = {
  ...DATE_OPTS,
  hour: "numeric",
  minute: "2-digit",
};

const DAY_MS = 86_400_000;

function toDate(value: string | Date): Date | null {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Consistent date (e.g. "Aug 14, 2026"). Uses the browser's local timezone by default. */
export function formatDate(value: string | Date, tz?: string): string {
  const date = toDate(value);
  if (!date) return "";
  return new Intl.DateTimeFormat("en-US", {
    ...DATE_OPTS,
    ...(tz ? { timeZone: tz } : {}),
  }).format(date);
}

/** Consistent date + time (e.g. "Aug 14, 2026, 5:24 PM"). */
export function formatDateTime(value: string | Date, tz?: string): string {
  const date = toDate(value);
  if (!date) return "";
  return new Intl.DateTimeFormat("en-US", {
    ...DATE_TIME_OPTS,
    ...(tz ? { timeZone: tz } : {}),
  }).format(date);
}

/** Relative label: "Today", "Tomorrow", "In 3 days", "2 days ago", else a date. */
export function formatRelative(value: string | Date, now: Date = new Date()): string {
  const date = toDate(value);
  if (!date) return "";
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfTarget = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDays = Math.round((startOfTarget.getTime() - startOfToday.getTime()) / DAY_MS);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  if (diffDays === -1) return "Yesterday";
  if (diffDays > 1) return `In ${diffDays} days`;
  if (diffDays < -1) return `${Math.abs(diffDays)} days ago`;
  return formatDate(date);
}
