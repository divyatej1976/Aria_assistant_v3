"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./auth-provider";
import { useActiveContext } from "./use-active-context";
import { ErrorState } from "./states";

/**
 * Redirects authed users to onboarding when they have no learning context yet.
 * Signed-out visitors are never redirected here — sign-out navigates home.
 */
export function ContextGuard({ children }: { children: React.ReactNode }) {
  const { loading, context, error, retry } = useActiveContext();
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading || authLoading) return;
    if (error) return; // don't redirect on load failure — show retry UI instead
    if (!user) return; // signed out — landing/signin handle their own routing
    if (!context) {
      router.replace("/onboarding");
    }
  }, [loading, authLoading, user, context, error, router]);

  if (error) {
    return <ErrorState message={error} onRetry={retry} />;
  }

  if (authLoading || loading || (user && !context)) {
    return (
      <div style={{ padding: 60, textAlign: "center", color: "var(--text-2)" }}>
        Loading your learning workspace…
      </div>
    );
  }
  return <>{children}</>;
}
