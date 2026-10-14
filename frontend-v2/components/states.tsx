"use client";

import { Icon } from "./icons";

/**
 * Screen-level data hook: wraps a loader with loading/error/retry so every
 * async screen has consistent states.
 */
export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <div className="skeleton loading-state-skeleton" />
      {/^(loading)\b/i.test(label) ? label : `Loading ${label}`}…
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
  title,
  retryLabel = "Try again",
  retryDisabled = false,
  inline = false,
}: {
  message?: string;
  onRetry?: () => void;
  title?: string;
  retryLabel?: string;
  retryDisabled?: boolean;
  inline?: boolean;
}) {
  return (
    <div className={`empty-state${inline ? " inline-error error-state-inline" : ""}`} role="alert">
      {!inline && <Icon name="alert" size={30} />}
      {title && <b>{title}</b>}
      <p className="error-state-message">
        {message ?? "Something went wrong while loading this screen."}
      </p>
      {onRetry && (
        <button type="button" className="btn btn-secondary ui-justify-center" onClick={onRetry} disabled={retryDisabled}>
          <Icon name="refresh" /> {retryLabel}
        </button>
      )}
    </div>
  );
}
