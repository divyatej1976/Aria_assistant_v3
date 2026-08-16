"use client";

import { ReactNode, createContext, useCallback, useContext, useEffect, useState } from "react";

import { ApiError, api, clearToken } from "../lib/api";

export type Learner = { id: string; email: string; display_name: string | null; verified: boolean };

type AuthContextValue = {
  learner: Learner | null;
  loading: boolean;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue>({
  learner: null,
  loading: true,
  signOut: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [learner, setLearner] = useState<Learner | null>(null);
  const [loading, setLoading] = useState(true);

  const signOut = useCallback(async () => {
    try {
      await api("/api/v1/auth/signout", { method: "POST" });
    } catch {
      // Session may already be expired; local cleanup below is still required.
    }
    clearToken();
    setLearner(null);
    window.location.assign("/signin");
  }, []);

  useEffect(() => {
    let active = true;
    async function restore() {
      try {
        const me = await api<Learner>("/api/v1/auth/me");
        if (active) setLearner(me);
      } catch (error) {
        // Only treat an explicit 401 as a real sign-out; transient network
        // errors must not log the user out or redirect them.
        if (error instanceof ApiError && error.status === 401) clearToken();
      } finally {
        if (active) setLoading(false);
      }
    }
    void restore();
    return () => {
      active = false;
    };
  }, []);

  return <AuthContext.Provider value={{ learner, loading, signOut }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}
