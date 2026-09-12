"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "@/lib/api";

export type AuthUser = { id: string; email: string; display_name: string | null; verified: boolean };

type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  setUser: (u: AuthUser | null) => void;
  signout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type MeResponse = { id: string; email: string; display_name?: string | null; verified?: boolean };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

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
      .catch(() => {
        // unauthenticated — leave user null
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const signout = useCallback(async () => {
    try {
      await api("/api/v1/auth/signout", { method: "POST" });
    } catch {
      // ignore — clear locally regardless
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, setUser, signout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
