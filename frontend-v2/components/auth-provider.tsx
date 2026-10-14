"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api, ApiError } from "@/lib/api";
import { clearLearnerDrafts } from "@/lib/assessment-drafts";
import { toast } from "@/lib/toast";

export type AuthUser = { id: string; email: string; display_name: string | null; verified: boolean };

type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  error: string | null;
  signedOut: boolean;
  setUser: (u: AuthUser | null) => void;
  signout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type MeResponse = { id: string; email: string; display_name?: string | null; verified?: boolean };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [signedOut, setSignedOut] = useState(false);
  const currentLearner = useRef<string | null>(null);

  const setUser = useCallback((next: AuthUser | null) => {
    const previous = currentLearner.current;
    if (previous && previous !== next?.id && !clearLearnerDrafts(previous)) {
      toast("Your account session changed, but saved assessment drafts could not be removed from this device.", "error");
    }
    currentLearner.current = next?.id ?? null;
    if (next) setSignedOut(false);
    setError(null);
    setUserState(next);
  }, []);

  useEffect(() => {
    let cancelled = false;
    api<MeResponse>("/api/v1/auth/me")
      .then((me) => {
        if (cancelled) return;
        setUser({
          id: me.id,
          email: me.email,
          display_name: me.display_name ?? null,
          verified: me.verified ?? false,
        });
      })
      .catch((err: unknown) => {
        if (!cancelled && !(err instanceof ApiError && err.status === 401)) {
          setError("Could not check your sign-in status. Please try again.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [setUser]);

  const signout = useCallback(async () => {
    await api("/api/v1/auth/signout", { method: "POST" });
    setSignedOut(true);
    setUser(null);
  }, [setUser]);

  return (
    <AuthContext.Provider value={{ user, loading, error, signedOut, setUser, signout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
