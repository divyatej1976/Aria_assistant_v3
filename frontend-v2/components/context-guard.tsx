"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./auth-provider";
import { useActiveContext } from "./use-active-context";
import { ErrorState } from "./states";

/**
 * Resolves authentication and subject selection before rendering workspace data.
 */
export function ContextGuard({ children }: { children: React.ReactNode }) {
  const { loading, context, error, retry } = useActiveContext();
  const { user, signedOut, loading: authLoading, error: authError } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading || authLoading) return;
    if (error || authError) return;
    if (!user) {
      router.replace(signedOut ? "/" : "/signin?next=" + encodeURIComponent(pathname));
      return;
    }
    if (!context) {
      router.replace("/onboarding");
    }
  }, [loading, authLoading, user, signedOut, context, error, authError, router, pathname]);

  if (authError) {
    return <ErrorState message={authError} onRetry={() => window.location.reload()} />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={retry} />;
  }

  if (authLoading || loading || !user || !context) {
    return (
      <div style={{ padding: 60, textAlign: "center", color: "var(--text-2)" }}>
        Loading your learning workspace…
      </div>
    );
  }
  return <>{children}</>;
}
