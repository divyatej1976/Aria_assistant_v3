"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Icon } from "@/components/icons";

export type ChatAction = {
  id: string;
  capability: string;
  status: "proposed" | "running" | "done" | "failed" | "cancelled";
  artifact_id: string | null;
  error_code: string | null;
  message: string;
  auto_run: boolean;
};

export function ActionCard({ initial }: { initial: ChatAction }) {
  const [action, setAction] = useState(initial);
  const [connectionError, setConnectionError] = useState("");
  const mounted = useRef(false);
  const started = useRef(false);
  const pending = useRef(false);
  const path = `/api/v1/orchestration/actions/${initial.id}`;
  const refresh = useCallback(async () => {
    try {
      const result = await api<ChatAction>(path);
      if (mounted.current) { setAction(result); setConnectionError(""); }
    } catch {
      if (mounted.current) setConnectionError("Could not check this action. Refresh its status before trying again.");
    }
  }, [path]);
  const run = useCallback(async () => {
    if (pending.current) return;
    pending.current = true;
    setConnectionError("");
    setAction(prev => ({ ...prev, status: "running", message: "Creating your conversation audio…" }));
    try {
      const result = await api<ChatAction>(`${path}/run`, { method: "POST" });
      if (mounted.current) setAction(result);
    } catch {
      // A lost response does not mean execution failed. Recover the saved state.
      await refresh();
    } finally { pending.current = false; }
  }, [path, refresh]);
  useEffect(() => {
    mounted.current = true;
    if (initial.status === "proposed" && initial.auto_run && !started.current) {
      started.current = true;
      void run();
    }
    return () => { mounted.current = false; };
  }, [initial.status, initial.auto_run, run]);
  useEffect(() => {
    if (action.status !== "running") return;
    let polls = 0;
    const timer = setInterval(() => {
      if (++polls > 60) {
        clearInterval(timer);
        setConnectionError("This is taking longer than expected. Your action is saved; refresh its status to check again.");
      } else void refresh();
    }, 2000);
    return () => clearInterval(timer);
  }, [action.status, refresh]);
  const cancel = async () => {
    try {
      const result = await api<ChatAction>(`${path}/cancel`, { method: "POST" });
      if (mounted.current) setAction(result);
    } catch { await refresh(); }
  };
  return <section className="card card-pad chat-action-card" aria-label="Conversation audio action" data-action-status={action.status}>
    <div className="ui-row ui-gap-12"><Icon name="headphones" size={20} /><b>Conversation audio</b></div>
    <p role="status">{action.message}</p>
    <div className="ui-row ui-gap-12">
      {action.status === "done" && action.artifact_id && <Link className="btn btn-primary" href={`/app/audio#episode-${action.artifact_id}`}>Listen in Audio</Link>}
      {action.status === "failed" && <button className="btn btn-primary" onClick={() => void run()}>Retry audio</button>}
      {action.status === "proposed" && <button className="btn btn-primary" disabled={!action.auto_run} onClick={() => void run()}>Create audio</button>}
      {(action.status === "proposed" || action.status === "failed") && <button className="btn btn-ghost" onClick={() => void cancel()}>Cancel audio</button>}
      {action.status === "running" && <button className="btn btn-ghost" onClick={() => void refresh()}>Refresh status</button>}
    </div>
    {connectionError && <p role="alert">{connectionError} <button className="btn btn-ghost" onClick={() => void refresh()}>Refresh status</button></p>}
  </section>;
}
