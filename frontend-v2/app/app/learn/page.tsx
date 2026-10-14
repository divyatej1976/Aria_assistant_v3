"use client";

/* eslint-disable react-hooks/set-state-in-effect -- LearnPage must clear stale session state synchronously on context switch to prevent cross-context sends */

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/icons";
import { api, apiFormData, apiUpload, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { toast } from "@/lib/toast";
import { TutorMarkdown } from "@/components/tutor-markdown";
import { AssistantPresence } from "@/components/assistant-presence";
import { useMotionPreference } from "@/components/motion-system";
import { RequestStatus } from "@/components/request-status";
import { ErrorState, Loading } from "@/components/states";

type Session = {
  id: string;
  context_id: string;
  mode: string;
  status: string;
  created_at: string;
  title?: string | null;
  preview?: string | null;
  message_count?: number;
  last_message_at?: string | null;
};
type Source = { resource_id: string; chunk_id: string; title: string; score: number };
type Msg = { id?: string; role: "user" | "aria"; content: string; sources?: Source[]; fallback_used?: boolean; fresh?: boolean; streaming?: boolean; fullContent?: string };
type RetryRequest = { content: string; requestId: string; sessionId?: string };

function useTypewriter(fullText: string, active: boolean, wordsPerTick = 3, intervalMs = 30): string {
  const [revealed, setRevealed] = useState(active ? "" : fullText);
  const words = useRef<string[]>([]);
  const idx = useRef(0);

  useEffect(() => {
    if (!active) { setRevealed(fullText); return; }
    words.current = fullText.split(/(\s+)/);
    idx.current = 0;
    setRevealed("");
    const timer = setInterval(() => {
      idx.current = Math.min(idx.current + wordsPerTick, words.current.length);
      setRevealed(words.current.slice(0, idx.current).join(""));
      if (idx.current >= words.current.length) clearInterval(timer);
    }, intervalMs);
    return () => clearInterval(timer);
  }, [fullText, active, wordsPerTick, intervalMs]);

  return revealed;
}

function StreamingMessage({ msg, onDone, onProgress }: { msg: Msg; onDone: () => void; onProgress: () => void }) {
  const reduced = useMotionPreference();
  const revealed = useTypewriter(msg.fullContent ?? msg.content, !reduced);
  const text = reduced ? msg.fullContent ?? msg.content : revealed;
  const done = text === (msg.fullContent ?? msg.content);

  useEffect(() => { if (done) onDone(); }, [done, onDone]);
  useEffect(() => { onProgress(); }, [text, onProgress]);

  return (
    <div className="msg msg-aria message-arrival">
      <div className="mh"><Icon name="sparkles" size={14} /> ARIA Tutor</div>
      {msg.sources && msg.sources.length > 0 ? (
        <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 700, color: "var(--success-strong)", background: "var(--bg-1)", border: "1px solid var(--border)", borderRadius: 99, padding: "2px 10px", marginBottom: 8 }}>
          <Icon name="file" size={12} /> Grounded in your material · {msg.sources.length} source{msg.sources.length === 1 ? "" : "s"}
        </div>
      ) : msg.fallback_used ? (
        <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 700, color: "var(--text-2)", background: "var(--bg-1)", border: "1px solid var(--border)", borderRadius: 99, padding: "2px 10px", marginBottom: 8 }}>
          <Icon name="sparkles" size={12} /> General guidance — add material for grounded answers
        </div>
      ) : null}
      <div style={{ whiteSpace: "pre-wrap" }}><TutorMarkdown content={text} /></div>
      {done && msg.sources && msg.sources.length > 0 && (
        <div style={{ marginTop: 10, paddingTop: 8, borderTop: "1px solid var(--border)", fontSize: 11, color: "var(--text-3)" }}>
          <b>Sources:</b>{" "}
          {msg.sources.map((s) => (
            <span key={s.chunk_id} style={{ display: "inline-flex", alignItems: "center", gap: 4, background: "var(--bg-1)", border: "1px solid var(--border)", borderRadius: 99, padding: "2px 8px", margin: "2px 4px 0 0" }}>
              <Icon name="file" size={11} /> {s.title}
            </span>
          ))}
        </div>
      )}
      {done && msg.fallback_used && (
        <div style={{ marginTop: 8, fontSize: 11, color: "var(--text-3)" }}>Answer generated without source documents.</div>
      )}
    </div>
  );
}

/** Server timestamps are UTC; SQLite drops the offset, so treat a bare ISO
 * string as UTC rather than letting the browser read it as local time. */
function serverDate(iso: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + "Z");
}

function fmtDate(iso: string): string {
  try {
    return serverDate(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

const SESSION_PARAM = "session";

/** Keep the open conversation in the URL so a reload resumes it, while
 * arriving from navigation (no param) starts a fresh chat. */
function sessionFromUrl(): string | null {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get(SESSION_PARAM);
}

function syncSessionUrl(sid: string | null): void {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  if (sid) url.searchParams.set(SESSION_PARAM, sid);
  else url.searchParams.delete(SESSION_PARAM);
  window.history.replaceState(window.history.state, "", url);
}

function lastActivity(s: Session): number {
  return serverDate(s.last_message_at ?? s.created_at).getTime();
}

function recencyGroup(s: Session, now: Date): string {
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const at = lastActivity(s);
  if (at >= startOfToday) return "Today";
  if (at >= startOfToday - 86_400_000) return "Yesterday";
  if (at >= startOfToday - 6 * 86_400_000) return "Previous 7 days";
  return "Older";
}

function groupSessions(sessions: Session[]): Array<[string, Session[]]> {
  const now = new Date();
  const groups = new Map<string, Session[]>();
  for (const s of [...sessions].sort((a, b) => lastActivity(b) - lastActivity(a))) {
    const label = recencyGroup(s, now);
    groups.set(label, [...(groups.get(label) ?? []), s]);
  }
  return [...groups.entries()];
}

export default function LearnPage() {
  const { context } = useActiveContext();
  return <ContextLearn key={context?.id ?? "no-context"} />;
}

function ContextLearn() {
  const { context, loading: ctxLoading } = useActiveContext();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [typing, setTyping] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [replyError, setReplyError] = useState(false);
  const [replyErrorText, setReplyErrorText] = useState("");
  const [retryRequest, setRetryRequest] = useState<RetryRequest | null>(null);
  const requestLock = useRef(false);
  const [responding, setResponding] = useState(false);
  const [awayFromLatest, setAwayFromLatest] = useState(false);
  const followLatest = useRef(true);
  const reducedMotion = useMotionPreference();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [finishingDay, setFinishingDay] = useState(false);
  const [dailyReview, setDailyReview] = useState<string | null>(null);
  const [attaching, setAttaching] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const conversationVersion = useRef(0);
  const topicPrefilled = useRef(false);
  const followStreamingReply = useCallback(() => {
    if (followLatest.current) bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: "instant" });
  }, []);

  useEffect(() => {
    if (!context || topicPrefilled.current) return;
    const query = new URLSearchParams(window.location.search);
    const topic = query.get("topic")?.trim().slice(0, 255);
    const subject = query.get("context");
    if (!topic || (subject && subject !== context.id)) return;
    topicPrefilled.current = true;
    setInput(`Help me learn ${topic}. Start with a clear explanation and an example.`);
  }, [context]);

  useEffect(() => () => { conversationVersion.current += 1; }, []);

  const loadList = useCallback(async (cid: string) => {
    const list = await api<Session[]>("/api/v1/study/sessions?context_id=" + cid);
    setSessions(list);
    return list;
  }, []);

  const loadMessages = useCallback(async (sid: string, version = ++conversationVersion.current) => {
    followLatest.current = true;
    setAwayFromLatest(false);
    const list = await api<
      Array<{ role: "user" | "assistant" | "aria"; content: string; sources?: Source[]; fallback_used?: boolean }>
    >("/api/v1/study/sessions/" + sid + "/messages");
    if (version !== conversationVersion.current) return;
    // Backend persists the standard "assistant" role; the UI bubble model uses "aria".
    const normalized: Msg[] = list.map((m) => ({
      role: m.role === "assistant" ? "aria" : m.role,
      content: m.content,
      sources: m.sources,
      fallback_used: m.fallback_used,
    }));
    setMsgs(normalized);
    setActiveId(sid);
    syncSessionUrl(sid);
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
        // Resume only an explicitly linked session (reload / deep link);
        // otherwise open a fresh draft. The session row is created lazily on
        // the first message, so visiting Learn never leaves empty sessions.
        const requested = sessionFromUrl();
        if (requested && list.some((s) => s.id === requested)) {
          await loadMessages(requested);
        } else {
          syncSessionUrl(null);
        }
      } catch {
        if (!cancelled) toast("Could not load your study session.", "error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [context, loadList, loadMessages]);

  useEffect(() => {
    if (followLatest.current) bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: reducedMotion ? "instant" : "smooth" });
  }, [msgs, typing, reducedMotion, loading]);

  useEffect(() => {
    if (!responding) return;
    const timer = window.setTimeout(() => setResponding(false), 900);
    return () => window.clearTimeout(timer);
  }, [responding]);

  const send = async (text: string, retry?: RetryRequest) => {
    if (loading || typing || requestLock.current || ctxLoading || !context || !text.trim()) return;
    const version = conversationVersion.current;
    // guard against stale session from previous context
    if (activeId && !sessions.some((s) => s.id === activeId && s.context_id === context.id)) return;
    const content = text.trim();
    requestLock.current = true;
    const pending: RetryRequest = retry ?? { content, requestId: crypto.randomUUID() };
    setRetryRequest(pending);
    setReplyError(false);
    setReplyErrorText("");
    if (!retry) {
      setMsgs((m) => [...m, { role: "user", content, fresh: true }]);
      setInput("");
    }
    setTyping(true);
    try {
      let sid = pending.sessionId ?? activeId;
      if (!sid) {
        const created = await api<Session>("/api/v1/study/sessions", {
          method: "POST",
          body: JSON.stringify({ context_id: context.id, mode: "BASELINE" }),
        });
        if (version !== conversationVersion.current) return;
        sid = created.id;
        setSessions((p) => [created, ...p]);
        setActiveId(sid);
        syncSessionUrl(sid);
      }
      setRetryRequest({ ...pending, sessionId: sid });
      const res = await api<Msg>("/api/v1/study/sessions/" + sid + "/messages", {
        method: "POST",
        body: JSON.stringify({ content, request_id: pending.requestId }),
      });
      if (version !== conversationVersion.current) return;
      setMsgs((m) => [
        ...m,
        { role: "aria", content: reducedMotion ? res.content : "", fullContent: res.content, sources: res.sources, fallback_used: res.fallback_used, fresh: true, streaming: !reducedMotion },
      ]);
      setRetryRequest(null);
      setResponding(true);
      // Refresh titles/previews so the sidebar describes this conversation.
      loadList(context.id).catch(() => {});
    } catch (error) {
      if (version !== conversationVersion.current) return;
      setReplyError(true);
      setReplyErrorText(error instanceof ApiError ? error.message : "Your reply could not be loaded. Please try again.");
    } finally {
      if (version === conversationVersion.current) {
        requestLock.current = false;
        setTyping(false);
      }
    }
  };

  const handleAttachFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !context) return;
    const version = conversationVersion.current;
    setAttaching(true);
    const title = file.name.replace(/\.[^/.]+$/, "");
    try {
      const isPdf = file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf";
      const endpoint = isPdf
        ? `/api/v1/resources/pdf?context_id=${context.id}&title=${encodeURIComponent(title)}`
        : `/api/v1/resources/image?context_id=${context.id}&title=${encodeURIComponent(title)}`;
      const mime = isPdf ? "application/pdf" : (file.type || "image/png");
      await apiUpload(endpoint, file, mime);
      if (version !== conversationVersion.current) return;
      toast(`Attached "${file.name}" — processed via OCR.`);
      setMsgs((m) => [
        ...m,
        {
          role: "aria",
          content: `📎 **Attached document:** \`${file.name}\` has been processed via OCR into your study materials. What would you like to explore or practice from it?`,
        },
      ]);
    } catch (err) {
      if (version === conversationVersion.current) toast(err instanceof ApiError ? err.message : "Failed to upload and process file.", "error");
    } finally {
      if (version === conversationVersion.current) setAttaching(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        try {
          mediaRecorderRef.current.stop();
        } catch {}
      }
    };
  }, []);

  const toggleRecording = async () => {
    const version = conversationVersion.current;
    if (recording) {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        try {
          mediaRecorderRef.current.stop();
        } catch {}
      }
      setRecording(false);
      return;
    }

    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      toast("Voice input is not supported in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (version !== conversationVersion.current) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
      const mimeType =
        typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        if (version !== conversationVersion.current) return;
        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || "audio/webm" });
        if (blob.size === 0) return;

        setTranscribing(true);
        try {
          const formData = new FormData();
          formData.append("file", blob, "voice-input.webm");
          const res = await apiFormData<{ text: string }>("/api/v1/audio/transcribe", formData);
          if (version !== conversationVersion.current) return;
          if (res.text && res.text.trim()) {
            setInput((prev) => (prev ? `${prev} ${res.text.trim()}` : res.text.trim()));
            toast("Voice transcribed!");
          } else {
            toast("No speech detected.");
          }
        } catch (err) {
          if (version === conversationVersion.current) toast(err instanceof ApiError ? err.message : "Voice transcription failed.", "error");
        } finally {
          if (version === conversationVersion.current) setTranscribing(false);
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
      toast("Listening... Click microphone again when finished.");
    } catch {
      if (version === conversationVersion.current) toast("Microphone access was denied or unavailable.", "error");
    }
  };

  const newChat = () => {
    if (!context) return;
    ++conversationVersion.current;
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    setRecording(false);
    setAttaching(false);
    setTranscribing(false);
    setInput("");
    setTyping(false);
    setResponding(false);
    setReplyError(false);
    setRetryRequest(null);
    requestLock.current = false;
    setActiveId(null);
    setMsgs([]);
    syncSessionUrl(null);
  };

  const selectSession = async (sid: string) => {
    const version = ++conversationVersion.current;
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    setRecording(false);
    setAttaching(false);
    setTranscribing(false);
    setInput("");
    setTyping(false);
    setResponding(false);
    setReplyError(false);
    setRetryRequest(null);
    requestLock.current = false;
    setLoading(true);
    try {
      await loadMessages(sid, version);
    } catch {
      if (version === conversationVersion.current) toast("Could not load this session.", "error");
    } finally {
      if (version === conversationVersion.current) setLoading(false);
    }
  };

  // Empty sessions (legacy rows, or a chat abandoned before its first reply)
  // stay hidden unless they are the one currently open.
  const visibleSessions = sessions.filter((s) => (s.message_count ?? 0) > 0 || s.id === activeId);

  const finishDay = async () => {
    if (!context || finishingDay || typing || attaching || transcribing || recording) return;
    const version = conversationVersion.current;
    setFinishingDay(true);
    try {
      const review = await api<{ assessment_id: string }>(
        `/api/v1/study/contexts/${context.id}/finish-day`, { method: "POST" },
      );
      if (version === conversationVersion.current) {
        setDailyReview(review.assessment_id);
        toast("Your daily review is ready in Assessments.");
      }
    } catch (error) {
      if (version === conversationVersion.current) toast(error instanceof Error ? error.message : "Could not create your daily review. Try again.", "error");
    } finally {
      setFinishingDay(false);
    }
  };

  if (loading || ctxLoading) {
    return <div className="chat-shell"><Loading label="your tutor" /></div>;
  }

  return (
    <div className={`chat-sidebar-layout${focusMode ? " study-focus" : ""}`}>
      <aside className="learn-side">
        <button className="btn btn-primary btn-block" onClick={newChat}>
          <Icon name="plus" size={16} /> New chat
        </button>
        {visibleSessions.length === 0 ? (
          <>
            <div className="nav-sec">History</div>
            <div className="session-empty">Your conversations will appear here, titled by what you explored.</div>
          </>
        ) : (
          groupSessions(visibleSessions).map(([label, group]) => (
            <div key={label} className="session-group">
              <div className="nav-sec">{label}</div>
              {group.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className={`session-item${activeId === s.id ? " active" : ""}`}
                  onClick={() => selectSession(s.id)}
                  aria-current={activeId === s.id ? "page" : undefined}
                  title={`${s.title ?? "New conversation"}${s.preview ? "\n" + s.preview : ""}`}
                >
                  <span className="session-title">{(s.title ?? "New conversation").replace(new RegExp("^[\\p{Extended_Pictographic}\\p{Emoji_Presentation}\\uFE0F\\u200D\\s]+", "u"), "") || s.title}</span>
                  <span className="session-preview">
                    {s.preview ?? "Waiting for ARIA's reply…"}
                  </span>
                  <span className="session-meta">
                    {fmtDate(s.last_message_at ?? s.created_at)}
                    {s.message_count ? ` · ${Math.ceil(s.message_count / 2)} exchange${s.message_count > 2 ? "s" : ""}` : ""}
                  </span>
                </button>
              ))}
            </div>
          ))
        )}
      </aside>

      <div className="chat-shell">
        <div className="chat-head">
          <div>
            <h1 style={{ fontSize: 16, fontWeight: 800 }}>{context?.title ?? "Learn"}</h1>
            <AssistantPresence state={recording ? "listening" : typing || transcribing ? "thinking" : replyError ? "error" : responding ? "responding" : "idle"} />
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button className="btn btn-secondary daily-finish" onClick={() => void finishDay()}
              disabled={!context || finishingDay || typing || attaching || transcribing || recording || !visibleSessions.length}
              title="Create a review of today's learning in this subject">
              <Icon name="check" size={15} /> {finishingDay ? "Preparing review…" : "Done for today"}
            </button>
            <button className="btn btn-ghost focus-toggle" title={focusMode ? "Restore your conversation list and navigation" : "Hide the conversation list and navigation to focus on learning"} aria-pressed={focusMode} onClick={() => setFocusMode(value => !value)}><Icon name="target" size={15} /> {focusMode ? "Exit focus" : "Focus"}</button>
            <button
              className="btn btn-ghost"
              style={{ padding: "6px 12px", borderRadius: 99, fontSize: 12, display: "inline-flex", alignItems: "center", gap: 6 }}
              onClick={() => fileInputRef.current?.click()}
              disabled={!context || attaching}
              title="Attach a PDF or image (PNG, JPG, WEBP) to transcribe with OCR"
            >
              <Icon name="image" size={14} />
              <span>{attaching ? "Processing OCR…" : "Attach document / image"}</span>
            </button>
          </div>
        </div>

        {dailyReview && <div className="banner daily-review-ready" role="status">
          <Icon name="check" size={20} />
          <div><b>Your daily review is ready.</b><p>Practise what you discussed today. Questions grounded in your material also update your knowledge map.</p></div>
          <Link className="btn btn-primary" href={`/app/assess?review=${dailyReview}`}>Start review <Icon name="arrow" size={15} /></Link>
        </div>}

        <div className="chat-body" ref={bodyRef} role="region" aria-label="Conversation" tabIndex={0} onScroll={() => {
          const body = bodyRef.current;
          if (!body) return;
          const away = body.scrollHeight - body.scrollTop - body.clientHeight > 90;
          followLatest.current = !away;
          setAwayFromLatest(away);
        }}>
          {msgs.length === 0 && (
            <div style={{ textAlign: "center", padding: "32px 20px", color: "var(--text-2)", maxWidth: 580, margin: "0 auto" }}>
              <div style={{ display: "inline-flex", padding: 12, borderRadius: "50%", background: "var(--bg-2)", marginBottom: 12, color: "var(--primary)" }}>
                <Icon name="sparkles" size={32} />
              </div>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-1)", margin: "0 0 6px" }}>
                Meet ARIA, your AI learning agent
              </h3>
              <p style={{ fontSize: 13, color: "var(--text-3)", margin: "0 0 24px" }}>
                Ask anything about <b>{context?.title ?? "your topic"}</b>, explore ideas, or practice concepts. Upload materials whenever you want grounded source citations.
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
                {[
                  `Explain the core concepts of ${context?.title ?? "this topic"}`,
                  "Give me a practical, real-world example",
                  "Quiz me on key concepts with 3 questions",
                  "What are common pitfalls to watch out for?",
                ].map((prompt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => send(prompt)}
                    disabled={ctxLoading || loading || typing}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      fontSize: 12,
                      fontWeight: 500,
                      padding: "8px 14px",
                      borderRadius: 99,
                      border: "1px solid var(--border)",
                      background: "var(--bg-1)",
                      color: "var(--text-1)",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = "var(--primary)";
                      e.currentTarget.style.background = "var(--bg-2)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = "var(--border)";
                      e.currentTarget.style.background = "var(--bg-1)";
                    }}
                  >
                    <Icon name="sparkles" size={12} />
                    <span>{prompt}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {msgs.map((m, i) =>
            m.role === "aria" ? (
              m.streaming ? (
                <StreamingMessage key={i} msg={m} onProgress={followStreamingReply} onDone={() => setMsgs(prev => prev.map((pm, pi) => pi === i ? { ...pm, streaming: false, content: pm.fullContent ?? pm.content } : pm))} />
              ) : (
                <div className={`msg msg-aria${m.fresh ? " message-arrival" : ""}`} key={i}>
                  <div className="mh"><Icon name="sparkles" size={14} /> ARIA Tutor</div>
                  {m.sources && m.sources.length > 0 ? (
                    <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 700, color: "var(--success-strong)", background: "var(--bg-1)", border: "1px solid var(--border)", borderRadius: 99, padding: "2px 10px", marginBottom: 8 }}>
                      <Icon name="file" size={12} /> Grounded in your material · {m.sources.length} source{m.sources.length === 1 ? "" : "s"}
                    </div>
                  ) : m.fallback_used ? (
                    <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 700, color: "var(--text-2)", background: "var(--bg-1)", border: "1px solid var(--border)", borderRadius: 99, padding: "2px 10px", marginBottom: 8 }}>
                      <Icon name="sparkles" size={12} /> General guidance — add material for grounded answers
                    </div>
                  ) : null}
                  <div style={{ whiteSpace: "pre-wrap" }}><TutorMarkdown content={m.content} /></div>
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
              )
            ) : (
              <div className={`msg msg-user${m.fresh ? " message-arrival" : ""}`} key={i}>{m.content}</div>
            ),
          )}
          {replyError && retryRequest && <ErrorState inline title="Reply unavailable" message={replyErrorText}
            retryLabel="Retry reply" retryDisabled={typing} onRetry={() => void send(retryRequest.content, retryRequest)} />}
          {typing && <RequestStatus label="ARIA is thinking…" />}
        </div>

        {awayFromLatest && <button className="btn btn-secondary jump-latest" onClick={() => {
          followLatest.current = true;
          setAwayFromLatest(false);
          bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: reducedMotion ? "instant" : "smooth" });
        }}>Jump to latest <Icon name="arrow" size={15} /></button>}
        {focusMode && msgs.length > 0 && <p className="focus-session-summary">This session · {msgs.filter(message => message.role === "user").length} questions · {msgs.filter(message => message.role === "aria").length} ARIA replies</p>}

        <div className="chat-input-row">
          <div className="bar">
            <button
              className="btn btn-secondary"
              style={{ width: 44, height: 44, padding: 0, borderRadius: 12, flexShrink: 0 }}
              aria-label="Attach document or image"
              onClick={() => fileInputRef.current?.click()}
              disabled={!context || attaching}
              title="Attach a PDF or image (PNG, JPG, WEBP)"
            >
              <Icon name="plus" size={20} />
            </button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask ARIA anything…"
              onKeyDown={(e) => e.key === "Enter" && send(input)}
              disabled={ctxLoading || loading}
            />
            <button
              type="button"
              className={`btn ${recording ? "btn-primary" : "btn-secondary"}`}
              style={{
                width: 42,
                height: 42,
                padding: 0,
                borderRadius: "50%",
                flexShrink: 0,
                transition: "all 0.2s ease",
                ...(recording ? { background: "var(--danger)", color: "var(--on-danger)", borderColor: "var(--danger)" } : {}),
              }}
              aria-label={recording ? "Stop recording voice" : "Speak question"}
              onClick={toggleRecording}
              disabled={transcribing || ctxLoading || loading}
              title={
                transcribing
                  ? "Transcribing your voice…"
                  : recording
                  ? "Recording… click to stop and transcribe"
                  : "Speak your question"
              }
            >
              <Icon name={transcribing ? "sparkles" : "mic"} size={18} />
            </button>
            <button className="btn btn-primary" style={{ width: 42, height: 42, padding: 0, borderRadius: "50%", flexShrink: 0 }} aria-label="Send" onClick={() => send(input)} disabled={ctxLoading || loading || typing}>
              <Icon name="send" size={18} />
            </button>
          </div>
        </div>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.webp"
        style={{ display: "none" }}
        onChange={handleAttachFile}
      />
    </div>
  );
}
