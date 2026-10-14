"use client";

import { useEffect, useId, useRef } from "react";
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
  const dialogRef = useRef<HTMLDialogElement>(null);
  const descriptionId = useId();
  const open = state !== null;

  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog?.showModal();
    const focusTarget = boxRef.current?.querySelector<HTMLButtonElement>("[data-autofocus]");
    focusTarget?.focus();
    return () => {
      dialog?.close();
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, [open]);

  if (!state) return null;
  return (
    <dialog
      ref={dialogRef}
      className="modal-bg show"
      role="alertdialog"
      aria-label={state.title}
      aria-describedby={descriptionId}
      aria-modal="true"
      style={{ display: "flex", width: "100vw", height: "100dvh", maxWidth: "none", maxHeight: "none", margin: 0, border: 0, color: "var(--text-1)" }}
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const buttons = boxRef.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)");
        if (!buttons?.length) return;
        const first = buttons[0];
        const last = buttons[buttons.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault(); first.focus();
        }
      }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}
    >
      <div
        ref={boxRef}
        className="modal"
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
        <p id={descriptionId} style={{ fontSize: 14, color: "var(--text-2)", margin: "0 0 6px" }}>{state.body}</p>
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
    </dialog>
  );
}
