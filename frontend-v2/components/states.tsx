"use client";

import { Icon } from "./icons";

/**
 * Screen-level data hook: wraps a loader with loading/error/retry so every
 * async screen has consistent states.
 */
export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div style={{ textAlign: "center", padding: "56px 0", color: "var(--text-2)", fontSize: 14 }} role="status">
      <div className="skeleton" style={{ width: 46, height: 46, borderRadius: 14, margin: "0 auto 14px" }} />
      {label}…
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="empty-state" role="alert">
      <Icon name="alert" size={30} />
      <p style={{ margin: "10px 0 14px", fontSize: 14, color: "var(--text-1)" }}>
        {message ?? "Something went wrong while loading this screen."}
      </p>
      {onRetry && (
        <button className="btn btn-secondary" onClick={onRetry} style={{ justifyContent: "center" }}>
          <Icon name="refresh" /> Try again
        </button>
      )}
    </div>
  );
}