"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { PaletteSwitcher } from "./palette-switcher";
import { useHydrated } from "@/lib/use-hydrated";

export function AuthShell({ children, title, subtitle }: { children: ReactNode; title: string; subtitle?: string }) {
  const hydrated = useHydrated();
  return (
    <main className="auth-wrap">
      <div style={{ position: "absolute", top: 24, left: 28, display: "flex", alignItems: "center", gap: 12 }}>
        <Link href="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 12 }}>
          <div
            className="logo-mark"
            style={{
              width: 38,
              height: 38,
              borderRadius: 12,
              background: "var(--accent-grad)",
              color: "#fff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 17,
              fontWeight: 800,
              boxShadow: "var(--shadow-2)",
            }}
          >
            A
          </div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: "-.5px", lineHeight: 1 }}>ARIA</div>
            <div style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1.6, color: "var(--text-3)" }}>AI Learning System</div>
          </div>
        </Link>
      </div>
      <div style={{ position: "absolute", top: 24, right: 28 }}>
        <PaletteSwitcher />
      </div>
      <div className="auth-card">
        <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-.5px" }}>{title}</h1>
        {subtitle && <p style={{ fontSize: 14, color: "var(--text-2)", margin: "6px 0 22px" }}>{subtitle}</p>}
        <fieldset disabled={!hydrated} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
          {children}
        </fieldset>
      </div>
    </main>
  );
}
