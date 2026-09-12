"use client";

import { useEffect, useRef } from "react";
import { Icon } from "./icons";

export type ConfirmState = {
  title: string;
  body: string;
  confirmLabel?: string;
  onConfirm: () => void;
} | null;

export function ConfirmDialog({
  state,
  onClose,
}: {
  state: ConfirmState;
  onClose: () => void;
}) {
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!state) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const focusTarget = boxRef.current?.querySelector<HTMLButtonElement>("[data-autofocus]");
    focusTarget?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [state, onClose]);

  if (!state) return null;
  return (
    <div className="modal-bg show" style={{ display: "flex" }} onClick={onClose}>
      <div
        ref={boxRef}
        className="modal"
        role="alertdialog"
        aria-modal="true"
        aria-label={state.title}
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 420 }}
      >
        <div className="m-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 12, marginBottom: 10 }}>
          <h3 className="m-title" style={{ fontSize: 18, fontWeight: 800, display: "flex", alignItems: "center", gap: 8 }}>
            <Icon name="alert" size={18} /> {state.title}
          </h3>
          <button className="btn btn-ghost" style={{ padding: 6 }} onClick={onClose} aria-label="Close">
            <Icon name="x" size={16} />
          </button>
        </div>
        <p style={{ fontSize: 14, color: "var(--text-2)", margin: "0 0 6px" }}>{state.body}</p>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, borderTop: "1px solid var(--border)", paddingTop: 14, marginTop: 14 }}>
          <button className="btn btn-ghost" data-autofocus onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            style={{ background: "var(--danger-strong)", borderColor: "var(--danger-strong)" }}
            onClick={() => {
              state.onConfirm();
              onClose();
            }}
          >
            {state.confirmLabel ?? "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}