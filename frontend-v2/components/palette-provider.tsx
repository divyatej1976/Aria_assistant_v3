"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useSyncExternalStore,
  type ReactNode,
} from "react";

export type Palette = "aurora" | "noir";

type PaletteContextValue = {
  palette: Palette;
  gold: boolean;
  setPalette: (p: Palette) => void;
  setGold: (on: boolean) => void;
  toggleGold: () => void;
};

const PaletteContext = createContext<PaletteContextValue | null>(null);

const STORAGE_KEY = "aria.palette";
const GOLD_KEY = "aria.gold";

const DEFAULT_SNAPSHOT = "aurora|0";
let fallbackSnapshot = DEFAULT_SNAPSHOT;
let storageUnavailable = false;
const listeners = new Set<() => void>();

function subscribe(callback: () => void) {
  listeners.add(callback);
  window.addEventListener("storage", callback);
  return () => {
    listeners.delete(callback);
    window.removeEventListener("storage", callback);
  };
}

function snapshot() {
  if (storageUnavailable) return fallbackSnapshot;
  try {
    const palette = window.localStorage.getItem(STORAGE_KEY) === "noir" ? "noir" : "aurora";
    return `${palette}|${window.localStorage.getItem(GOLD_KEY) === "1" ? "1" : "0"}`;
  } catch { return fallbackSnapshot; }
}

function readStored(): { palette: Palette; gold: boolean } {
  const [palette, gold] = snapshot().split("|");
  return { palette: palette === "noir" ? "noir" : "aurora", gold: gold === "1" };
}

function save(state: { palette: Palette; gold: boolean }) {
  fallbackSnapshot = `${state.palette}|${state.gold ? "1" : "0"}`;
  try {
    window.localStorage.setItem(STORAGE_KEY, state.palette);
    window.localStorage.setItem(GOLD_KEY, state.gold ? "1" : "0");
  } catch { storageUnavailable = true; }
  listeners.forEach(callback => callback());
}

export function PaletteProvider({ children }: { children: ReactNode }) {
  const stored = useSyncExternalStore(subscribe, snapshot, () => DEFAULT_SNAPSHOT);
  const [name, goldValue] = stored.split("|");
  const palette: Palette = name === "noir" ? "noir" : "aurora";
  const gold = goldValue === "1";

  useEffect(() => {
    document.documentElement.dataset.theme = palette;
    document.documentElement.classList.toggle("noir-gold", palette === "noir" && gold);
  }, [palette, gold]);

  const setPalette = useCallback((p: Palette) => save({ ...readStored(), palette: p }), []);
  const setGold = useCallback((on: boolean) => save({ ...readStored(), gold: on }), []);
  const toggleGold = useCallback(() => { const state = readStored(); save({ ...state, gold: !state.gold }); }, []);

  return (
    <PaletteContext.Provider value={{ palette, gold, setPalette, setGold, toggleGold }}>
      {children}
    </PaletteContext.Provider>
  );
}

export function usePalette(): PaletteContextValue {
  const ctx = useContext(PaletteContext);
  if (!ctx) throw new Error("usePalette must be used within PaletteProvider");
  return ctx;
}
