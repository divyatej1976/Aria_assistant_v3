"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api } from "@/lib/api";
import { useAuth } from "./auth-provider";

export type ActiveContext = {
  id: string;
  title: string;
  description: string | null;
  status: string;
};

type ActiveContextValue = {
  contexts: ActiveContext[];
  context: ActiveContext | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
  createContext: (input: {
    title: string;
    description?: string;
    masteryLevel: string;
  }) => Promise<ActiveContext>;
  selectContext: (id: string) => void;
  removeContext: (id: string) => void;
};

const Ctx = createContext<ActiveContextValue | null>(null);

const STORAGE_KEY = "aria_active_context";

function readActiveContext(): string | null {
  try { return typeof window === "undefined" ? null : window.localStorage.getItem(STORAGE_KEY); }
  catch { return null; }
}
function writeActiveContext(id: string | null): void {
  try {
    if (typeof window !== "undefined") {
      if (id) window.localStorage.setItem(STORAGE_KEY, id);
      else window.localStorage.removeItem(STORAGE_KEY);
    }
  }
  catch { /* The selected subject remains available in memory. */ }
}


/**
 * Mounted once inside AuthProvider. Owns active-context state for the whole
 * app (header switcher + every screen), refetching whenever authentication
 * changes and resetting on sign-out.
 */
export function ActiveContextProvider({ children }: { children: ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [contexts, setContexts] = useState<ActiveContext[]>([]);
  const [context, setContext] = useState<ActiveContext | null>(null);
  const [fetchedFor, setFetchedFor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);

  // "loading" means auth is resolving or contexts haven't loaded for the
  // current user yet. Derived so the effect never calls setState synchronously.
  const loading = authLoading || (user != null && fetchedFor !== user.id);

  useEffect(() => {
    if (authLoading) return;
    const uid = user?.id ?? null;
    let cancelled = false;

    if (!uid) {
      // signed out — reset asynchronously (keeps the effect pure)
      void Promise.resolve().then(() => {
        if (cancelled) return;
        setContexts([]);
        setContext(null);
        setFetchedFor(null);
        setError(null);
      });
      return () => {
        cancelled = true;
      };
    }

    api<ActiveContext[]>("/api/v1/contexts")
      .then((list) => {
        if (cancelled) return;
        setContexts(list);
        const saved =
          readActiveContext();
        const match = saved ? list.find((c) => c.id === saved) : undefined;
        setContext(match ?? list[0] ?? null);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load your learning contexts.");
      })
      .finally(() => {
        if (!cancelled) setFetchedFor(uid);
      });
    return () => {
      cancelled = true;
    };
  }, [user?.id, authLoading, retryNonce]);

  const createContextFn = useCallback(
    async (input: { title: string; description?: string; masteryLevel: string }) => {
      const created = await api<ActiveContext>("/api/v1/contexts", {
        method: "POST",
        body: JSON.stringify({
          title: input.title,
          description: input.description || undefined,
          configuration: { mastery_level: input.masteryLevel.toLowerCase() },
        }),
      });
      setContexts((prev) => [...prev.filter((c) => c.id !== created.id), created]);
      setContext(created);
      writeActiveContext(created.id);
      return created;
    },
    [],
  );

  const selectContext = useCallback((id: string) => {
    setContexts((prev) => {
      const match = prev.find((c) => c.id === id);
      if (match) {
        setContext(match);
        writeActiveContext(id);
      }
      return prev;
    });
  }, []);

  const retry = useCallback(() => {
    setError(null);
    setFetchedFor(null);
    setRetryNonce((n) => n + 1);
  }, []);

  const removeContext = useCallback((id: string) => {
    const remaining = contexts.filter((c) => c.id !== id);
    setContexts(remaining);
    // if the deleted context was the active one, switch to survivor synchronously
    if (context?.id === id) {
      const survivor = remaining[0] ?? null;
      setContext(survivor);
      writeActiveContext(survivor?.id ?? null);
    }
  }, [contexts, context?.id]);

  const value: ActiveContextValue = {
    contexts,
    context,
    loading,
    error,
    retry,
    createContext: createContextFn,
    selectContext,
    removeContext,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useActiveContext(): ActiveContextValue {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useActiveContext must be used within ActiveContextProvider");
  return ctx;
}