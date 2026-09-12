"use client";

/* eslint-disable react-hooks/set-state-in-effect -- LearnPage must clear stale session state synchronously on context switch to prevent cross-context sends */

import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icons";
import { api, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { toast } from "@/lib/toast";
import { TutorMarkdown } from "@/components/tutor-markdown";

type Session = { id: string; context_id: string; mode: string; status: string; created_at: string };
type Source = { resource_id: string; chunk_id: string; title: string; score: number };
type Msg = { id?: string; role: "user" | "aria"; content: string; sources?: Source[]; fallback_used?: boolean };

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

export default function LearnPage() {
  const { context, loading: ctxLoading } = useActiveContext();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [typing, setTyping] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const bodyRef = useRef<HTMLDivElement>(null);

  const loadList = useCallback(async (cid: string) => {
    const list = await api<Session[]>("/api/v1/study/sessions?context_id=" + cid);
    setSessions(list);
    return list;
  }, []);

  const loadMessages = useCallback(async (sid: string) => {
    const list = await api<
      Array<{ role: "user" | "assistant" | "aria"; content: string; sources?: Source[]; fallback_used?: boolean }>
    >("/api/v1/study/sessions/" + sid + "/messages");
    // Backend persists the standard "assistant" role; the UI bubble model uses "aria".
    const normalized: Msg[] = list.map((m) => ({
      role: m.role === "assistant" ? "aria" : m.role,
      content: m.content,
      sources: m.sources,
      fallback_used: m.fallback_used,
    }));
    setMsgs(normalized);
    setActiveId(sid);
  }, []);

  useEffect(() => {
    if (!context) {
      setSessions([]);
      setMsgs([]);
      setActiveId(null);
      setLoading(false);
      return;
    }
    // clear stale context data immediately so no message can be sent to the wrong context
    setSessions([]);
    setMsgs([]);
    setActiveId(null);
    setLoading(true);
    let cancelled = false;
    (async () => {
      try {
        const list = await loadList(context.id);
        if (cancelled) return;
        if (list.length > 0) {
          await loadMessages(list[0].id);
        } else {
          const created = await api<Session>("/api/v1/study/sessions", {
            method: "POST",
            body: JSON.stringify({ context_id: context.id, mode: "BASELINE" }),
          });
          if (cancelled) return;
          setSessions((p) => [created, ...p]);
          setActiveId(created.id);
        }
      } catch {
        if (!cancelled) toast("Could not load your study session.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [context, loadList, loadMessages]);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs, typing]);

  const send = async (text: string) => {
    if (ctxLoading || !context || !text.trim() || !activeId) return;
    // guard against stale session from previous context
    if (sessions.length > 0 && !sessions.some((s) => s.id === activeId && s.context_id === context.id)) return;
    const content = text.trim();
    setMsgs((m) => [...m, { role: "user", content }]);
    setInput("");
    setTyping(true);
    try {
      const res = await api<Msg>("/api/v1/study/sessions/" + activeId + "/messages", {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      setMsgs((m) => [
        ...m,
        { role: "aria", content: res.content, sources: res.sources, fallback_used: res.fallback_used },
      ]);
    } catch {
      toast("Could not get a reply.");
    } finally {
      setTyping(false);
    }
  };

  const newChat = async () => {
    if (!context) return;
    try {
      const created = await api<Session>("/api/v1/study/sessions", {
        method: "POST",
        body: JSON.stringify({ context_id: context.id, mode: "BASELINE" }),
      });
      setSessions((p) => [created, ...p]);
      setActiveId(created.id);
      setMsgs([]);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not start a new chat.");
    }
  };

  const selectSession = async (sid: string) => {
    setLoading(true);
    try {
      await loadMessages(sid);
    } catch {
      toast("Could not load this session.");
    } finally {
      setLoading(false);
    }
  };

  if (loading || ctxLoading) {
    return (
      <div className="chat-shell">
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "80vh", color: "var(--text-2)" }}>
          Loading your tutor…
        </div>
      </div>
    );
  }

  return (
    <div className="chat-sidebar-layout">
      <aside className="learn-side">
        <button className="btn btn-primary btn-block" onClick={newChat}>
          <Icon name="plus" size={16} /> New Chat
        </button>
        <div className="nav-sec">Sessions</div>
        {sessions.length === 0 ? (
          <div style={{ fontSize: 12, color: "var(--text-3)", padding: "8px 12px" }}>No sessions yet. Start one above, or ask ARIA below.</div>
        ) : (
          sessions.map((s, i) => (
            <button
              key={s.id}
              type="button"
              className={`nav-link${activeId === s.id ? " active" : ""}`}
              onClick={() => selectSession(s.id)}
              aria-current={activeId === s.id ? "page" : undefined}
              style={{ width: "100%", textAlign: "left" }}
            >
              <Icon name={i === 0 ? SM_CURRENT : "message"} size={15} />
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {i === 0 ? "Current session" : "Session " + fmtDate(s.created_at)}
              </span>
            </button>
          ))
        )}
      </aside>

      <div className="chat-shell">
        <div className="chat-head">
          <div>
            <div style={{ fontSize: 16, fontWeight: 800 }}>{context?.title ?? "Learn"}</div>
            <div style={{ fontSize: 11, color: "var(--text-3)" }}>ARIA Tutor · Adaptive</div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button className="btn btn-ghost" style={{ padding: "6px 12px", borderRadius: 99, fontSize: 12 }} disabled title="Document attachment is coming soon — add them in Materials.">
              Attach a document
            </button>
          </div>
        </div>

        <div className="chat-body" ref={bodyRef}>
          {msgs.length === 0 && (
            <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-2)" }}>
              <Icon name="sparkles" size={34} />
              <p style={{ marginTop: 10, fontSize: 14 }}>Ask ARIA anything about <b>{context?.title ?? "your topic"}</b>.</p>
            </div>
          )}
          {msgs.map((m, i) =>
            m.role === "aria" ? (
              <div className="msg msg-aria" key={i}>
                <div className="mh"><Icon name="sparkles" size={14} /> ARIA Tutor</div>
                <div style={{ whiteSpace: "pre-wrap" }}>{m.role === "aria" ? <TutorMarkdown content={m.content} /> : m.content}</div>
                {m.sources && m.sources.length > 0 && (
                  <div style={{ marginTop: 10, paddingTop: 8, borderTop: "1px solid var(--border)", fontSize: 11, color: "var(--text-3)" }}>
                    <b>Sources:</b>{" "}
                    {m.sources.map((s) => (
                      <span key={s.chunk_id} style={{ display: "inline-flex", alignItems: "center", gap: 4, background: "var(--bg-1)", border: "1px solid var(--border)", borderRadius: 99, padding: "2px 8px", margin: "2px 4px 0 0" }}>
                        <Icon name="file" size={11} /> {s.title}
                      </span>
                    ))}
                  </div>
                )}
                {m.fallback_used && (
                  <div style={{ marginTop: 8, fontSize: 11, color: "var(--text-3)" }}>Answer generated without source documents.</div>
                )}
              </div>
            ) : (
              <div className="msg msg-user" key={i}>{m.content}</div>
            ),
          )}
          {typing && <div className="typing"><b /><b /><b /></div>}
        </div>

        <div className="chat-input-row">
          <div className="bar">
            <button className="btn btn-secondary" style={{ width: 44, height: 44, padding: 0, borderRadius: 12, flexShrink: 0 }} aria-label="Attach" disabled title="Document attachment is coming soon.">
              <Icon name="plus" size={20} />
            </button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask ARIA anything..."
              onKeyDown={(e) => e.key === "Enter" && send(input)}
              disabled={!activeId || ctxLoading || loading}
            />
            <button className="btn btn-secondary" style={{ width: 42, height: 42, padding: 0, borderRadius: "50%", flexShrink: 0 }} aria-label="Voice" disabled title="Voice input is coming soon.">
              <Icon name="mic" size={18} />
            </button>
            <button className="btn btn-primary" style={{ width: 42, height: 42, padding: 0, borderRadius: "50%", flexShrink: 0 }} aria-label="Send" onClick={() => send(input)} disabled={!activeId || ctxLoading || loading}>
              <Icon name="send" size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const SM_CURRENT = "terminal" as const;
