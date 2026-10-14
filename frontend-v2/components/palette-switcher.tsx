"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useHydrated } from "@/lib/use-hydrated";
import { usePalette, type Palette } from "./palette-provider";
import { Icon } from "./icons";

export function PaletteSwitcher() {
  const hydrated = useHydrated();
  const { palette, gold, setPalette, toggleGold } = usePalette();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    panelRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const outside = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", outside);
    rootRef.current?.addEventListener("keydown", escape);
    const root = rootRef.current;
    return () => {
      document.removeEventListener("pointerdown", outside);
      root?.removeEventListener("keydown", escape);
    };
  }, [open]);

  const pick = (p: Palette) => {
    setPalette(p);
    setOpen(false);
    triggerRef.current?.focus();
  };

  return (
    <div ref={rootRef} className="relative" onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
    }}>
      <button
        ref={triggerRef}
        disabled={!hydrated}
        type="button"
        className="btn btn-secondary"
        style={{ width: 40, height: 40, padding: 0, borderRadius: 9999 }}
        onClick={() => setOpen((o) => !o)}
        aria-label="Palette settings"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
      >
        <Icon name="palette" size={19} />
      </button>

      {open && (
        <div
          ref={panelRef}
          id={panelId}
          role="group"
          aria-label="Color palette"
          className="card card-pad"
          style={{
            position: "absolute",
            top: "calc(100% + 10px)",
            right: 0,
            zIndex: 60,
            width: 250,
            padding: 12,
          }}
        >
          <button
            type="button"
            className="chip"
            aria-pressed={palette === "aurora"}
            aria-label="Select Aurora palette"
            style={{
              width: "100%",
              justifyContent: "space-between",
              background: palette === "aurora" ? "var(--accent-grad-soft)" : undefined,
              border: palette === "aurora" ? "1px solid var(--accent)" : "1px solid transparent",
            }}
            onClick={() => pick("aurora")}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: "50%",
                  background: "linear-gradient(135deg,#2DD4BF,#A78BFA)",
                }}
              />
              Aurora
            </span>
            {palette === "aurora" && <Icon name="check" size={15} />}
          </button>

          <button
            type="button"
            className="chip"
            aria-pressed={palette === "noir"}
            aria-label="Select Noir Silk palette"
            style={{
              width: "100%",
              justifyContent: "space-between",
              marginTop: 8,
              background: palette === "noir" ? "var(--accent-grad-soft)" : undefined,
              border: palette === "noir" ? "1px solid var(--accent)" : "1px solid transparent",
            }}
            onClick={() => pick("noir")}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: "50%",
                  background: "linear-gradient(135deg,#111,#E4E6EB)",
                }}
              />
              Noir Silk
            </span>
            {palette === "noir" && <Icon name="check" size={15} />}
          </button>

          <button
            type="button"
            className="chip"
            aria-pressed={gold}
            aria-label="Toggle gold accents"
            style={{
              width: "100%",
              justifyContent: "space-between",
              marginTop: 8,
              borderTop: "1px solid var(--border)",
              borderRadius: 10,
              opacity: palette === "noir" ? 1 : 0.5,
            }}
            onClick={toggleGold}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ color: "var(--accent-gold)" }}>◆</span> Gold accents
            </span>
            <span
              style={{
                width: 34,
                height: 20,
                borderRadius: 99,
                background: gold && palette === "noir" ? "var(--accent-grad)" : "var(--bg-4)",
                position: "relative",
                transition: "background .3s",
              }}
            >
              <span
                style={{
                  position: "absolute",
                  top: 2,
                  left: gold && palette === "noir" ? 16 : 2,
                  width: 16,
                  height: 16,
                  borderRadius: "50%",
                  background: "var(--text-1)",
                  transition: "left .3s var(--spring)",
                }}
              />
            </span>
          </button>
        </div>
      )}
    </div>
  );
}
