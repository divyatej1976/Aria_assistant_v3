"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "../lib/api";

export type ActiveContext = {
  id: string;
  title: string;
  description: string | null;
  status: string;
};

const STORAGE_KEY = "aria_active_context";

export function useActiveContext() {
  const [contexts, setContexts] = useState<ActiveContext[]>([]);
  const [context, setContext] = useState<ActiveContext | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<ActiveContext[]>("/api/v1/contexts")
      .then((list) => {
        setContexts(list);
        const saved = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
        const selected = list.find((item) => item.id === saved) || list[list.length - 1] || null;
        setContext(selected);
        if (selected && typeof window !== "undefined") {
          localStorage.setItem(STORAGE_KEY, selected.id);
        }
      })
      .catch(() => setContext(null))
      .finally(() => setLoading(false));
  }, []);

  const setActiveContextId = useCallback((id: string) => {
    setContexts((items) => {
      const selected = items.find((item) => item.id === id) || null;
      setContext(selected);
      return items;
    });
    localStorage.setItem(STORAGE_KEY, id);
  }, []);

  return { context, contexts, loading, setActiveContextId };
}
