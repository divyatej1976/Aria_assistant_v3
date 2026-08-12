"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = resolvedTheme === "dark";

  return (
    <button
      type="button"
      aria-label="Toggle color theme"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="w-10 h-10 rounded-full shadow-extruded bg-surface flex items-center justify-center text-on-surface-variant hover:opacity-80 transition-opacity"
    >
      {mounted ? (isDark ? "☀" : "☾") : ""}
    </button>
  );
}
