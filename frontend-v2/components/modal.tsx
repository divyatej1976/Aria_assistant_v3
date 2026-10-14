"use client";

import { useEffect, useRef, type ReactNode } from "react";

export function Modal({ open, title, onClose, children }: {
  open: boolean; title: string; onClose: () => void; children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (!open) return;
    const dialog = ref.current;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog?.showModal();
    const initial = dialog?.querySelector<HTMLElement>("input:not(:disabled), select:not(:disabled), textarea:not(:disabled)")
      ?? dialog?.querySelector<HTMLElement>("button:not(:disabled)");
    initial?.focus();
    return () => {
      dialog?.close();
      if (trigger?.isConnected) trigger.focus();
    };
  }, [open]);
  if (!open) return null;
  return <dialog ref={ref} className="modal-bg show" aria-label={title} aria-modal="true"
    style={{ display: "flex", width: "100vw", height: "100dvh", maxWidth: "none", maxHeight: "none", margin: 0, border: 0, color: "var(--text-1)" }}
    onCancel={event => { event.preventDefault(); onClose(); }}
    onClick={event => { if (event.target === event.currentTarget) onClose(); }}
    onKeyDown={event => {
      if (event.key !== "Tab") return;
      const controls = Array.from(ref.current?.querySelectorAll<HTMLElement>("button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex='0']") ?? [])
        .filter(element => element.getClientRects().length > 0);
      const first = controls[0], last = controls[controls.length - 1];
      if (first && event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (last && !event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }}>
    {children}
  </dialog>;
}
