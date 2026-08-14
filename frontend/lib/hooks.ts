import { useCallback, useEffect, useState } from "react";

import { api } from "./api";

type UseApiState<T> = {
  data: T | null;
  loading: boolean;
  error: string;
  reload: () => void;
};

/**
 * Shared fetch hook: consistent loading/error/data/reload for one GET endpoint.
 *
 * Example:
 *   const { data, loading, error, reload } = useApi<Context[]>(
 *     "/api/v1/contexts",
 *   );
 */
export function useApi<T>(
  path: string,
  deps: ReadonlyArray<unknown> = [],
  options: { skip?: boolean } = {},
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);

  const reload = useCallback(() => setTick((value) => value + 1), []);

  useEffect(() => {
    if (options.skip) {
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    setError("");
    api<T>(path)
      .then((payload) => {
        if (active) setData(payload);
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error ? requestError.message : "Request failed",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, options.skip, ...deps]);

  return { data, loading, error, reload };
}

export type ContextSummary = { id: string; title: string };

export function useContexts(): UseApiState<ContextSummary[]> {
  return useApi<ContextSummary[]>("/api/v1/contexts");
}
