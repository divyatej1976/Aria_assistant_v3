"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
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

function readStored(): { palette: Palette; gold: boolean } {
  // Client-only lazy initializer; server render falls back to defaults so
  // hydration matches (the theme attribute is re-applied after mount).
  if (typeof window === "undefined") return { palette: "aurora", gold: false };
  let palette: Palette = "aurora";
  const saved = window.localStorage.getItem(STORAGE_KEY);
  if (saved === "aurora" || saved === "noir") palette = saved;
  return { palette, gold: window.localStorage.getItem(GOLD_KEY) === "1" };
}

export function PaletteProvider({ children }: { children: ReactNode }) {
  const [{ palette, gold }, setState] = useState(readStored);

  useEffect(() => {
    document.documentElement.dataset.theme = palette;
    document.documentElement.classList.toggle("noir-gold", palette === "noir" && gold);
    window.localStorage.setItem(STORAGE_KEY, palette);
    window.localStorage.setItem(GOLD_KEY, gold ? "1" : "0");
  }, [palette, gold]);

  const setPalette = useCallback((p: Palette) => setState((s) => ({ ...s, palette: p })), []);
  const setGold = useCallback((on: boolean) => setState((s) => ({ ...s, gold: on })), []);
  const toggleGold = useCallback(() => setState((s) => ({ ...s, gold: !s.gold })), []);

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