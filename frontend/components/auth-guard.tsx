"use client";

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "./auth-provider";

export function AuthGuard({ children }: { children: ReactNode }) {
  const { learner, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !learner) router.replace("/signin");
  }, [loading, learner, router]);

  if (loading) {
    return (
      <main className="min-h-screen bg-background flex items-center justify-center p-6">
        <p className="text-body-md text-on-surface-variant">Restoring your session…</p>
      </main>
    );
  }
  if (!learner) return null;
  return <>{children}</>;
}
