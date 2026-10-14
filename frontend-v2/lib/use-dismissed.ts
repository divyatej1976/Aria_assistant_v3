"use client";

import { useCallback, useSyncExternalStore } from "react";

const fallback = new Set<string>();
const eventName = "aria:display-preference";
function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(eventName, callback);
  return () => { window.removeEventListener("storage", callback); window.removeEventListener(eventName, callback); };
}

export function useDismissed(key: string) {
  const snapshot = useCallback(() => {
    try { return localStorage.getItem(key) === "1" || fallback.has(key); }
    catch { return fallback.has(key); }
  }, [key]);
  const dismissed = useSyncExternalStore(subscribe, snapshot, () => false);
  const dismiss = () => {
    fallback.add(key);
    try { localStorage.setItem(key, "1"); } catch { /* Still dismiss for this visit. */ }
    window.dispatchEvent(new Event(eventName));
  };
  return { dismissed, dismiss };
}
