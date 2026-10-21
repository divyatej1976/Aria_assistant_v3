"use client";

/* eslint-disable react-hooks/set-state-in-effect -- LearnPage must clear stale session state synchronously on context switch to prevent cross-context sends */

import { useCallback, useEffect, useRef, useState } from "react";
import { MicWaveform } from "@/components/mic-waveform";
import { CameraCapture } from "@/components/camera-capture";
import { PageGuide } from "@/components/page-guide";
import { useAuth } from "@/components/auth-provider";
import { Icon } from "@/components/icons";
import { api, apiFormData, apiStream, apiUpload, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { toast } from "@/lib/toast";
import { TutorReply, DEPTH_LABEL, type Depth, type RequestedDepth, type Source } from "@/components/tutor-reply";
import { AssistantPresence } from "@/components/assistant-presence";
import { useMotionPreference } from "@/components/motion-system";
import { RequestStatus } from "@/components/request-status";
import { ErrorState, Loading } from "@/components/states";
import { ActionCard, type ChatAction } from "@/components/action-card";

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
type Msg = { id?: string; action?: ChatAction | null; role: "user" | "aria"; content: string; sources?: Source[]; fallback_used?: boolean; depth?: Depth | null; fresh?: boolean; streaming?: boolean; fullContent?: string; files?: SentFile[]; stopped?: boolean; live?: boolean };
/** A file sent with a message: shown inside the learner's bubble. */
type SentFile = { name: string; id?: string; failed?: boolean };
type RetryRequest = { content: string; requestId: string; sessionId?: string; depth: RequestedDepth };

type ChatFile = { id: string; title: string; processing_status: string; error_detail?: string | null };

const DEPTH_KEY = "aria.reply-depth";
const DEPTH_OPTIONS: RequestedDepth[] = ["auto", "quick", "balanced", "deep"];

/** Phones get shorter replies; the backend uses this with the chosen depth. */
function screenSize(): "compact" | "regular" | "wide" {
  if (typeof window === "undefined") return "regular";
  return window.innerWidth < 640 ? "compact" : window.innerWidth >= 1280 ? "wide" : "regular";
}

function savedDepth(): RequestedDepth {
  try {
    const value = window.localStorage.getItem(DEPTH_KEY);
    return DEPTH_OPTIONS.includes(value as RequestedDepth) ? (value as RequestedDepth) : "auto";
  } catch {
    return "auto";
  }
}

/** Reveal a reply as if typed; long replies type faster so none takes more than ~4 seconds. */
function useTypewriter(fullText: string, active: boolean, intervalMs = 40, maxMs = 4000): string {
  const [revealed, setRevealed] = useState(active ? "" : fullText);
  const words = useRef<string[]>([]);
  const idx = useRef(0);

  useEffect(() => {
    if (!active) { setRevealed(fullText); return; }
    words.current = fullText.split(/(\s+)/);
    idx.current = 0;
    setRevealed("");
    const wordsPerTick = Math.max(3, Math.ceil(words.current.length / (maxMs / intervalMs)));
    const timer = setInterval(() => {
      idx.current = Math.min(idx.current + wordsPerTick, words.current.length);
      setRevealed(words.current.slice(0, idx.current).join(""));
      if (idx.current >= words.current.length) clearInterval(timer);
    }, intervalMs);
    return () => clearInterval(timer);
  }, [fullText, active, intervalMs, maxMs]);

  return revealed;
}

function StreamingMessage({ msg, onDone, onProgress }: { msg: Msg; onDone: () => void; onProgress: (shown: string) => void }) {
  const reduced = useMotionPreference();
  const revealed = useTypewriter(msg.fullContent ?? msg.content, !reduced);
  const text = reduced ? msg.fullContent ?? msg.content : revealed;
  const done = text === (msg.fullContent ?? msg.content);

  useEffect(() => { if (done) onDone(); }, [done, onDone]);
  useEffect(() => { onProgress(text); }, [text, onProgress]);

  return <TutorReply content={text} depth={msg.depth} sources={msg.sources} fallback={msg.fallback_used} done={done} fresh />;
}

/** Server timestamps are UTC; SQLite drops the offset, so treat a bare ISO
 * string as UTC rather than letting the browser read it as local time. */


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


export default function LearnPage() {
  const { context } = useActiveContext();
  return <ContextLearn key={context?.id ?? "no-context"} />;
}

function ContextLearn() {
  const { context, loading: ctxLoading } = useActiveContext();
  const [sessions, setSessions] = useState<Session[]>([]);
  // Chats with a reply on the way; nothing is saved until it lands, so keep them listed meanwhile.
  const [waitingIds, setWaitingIds] = useState<string[]>([]);
  const { user } = useAuth();
  const firstName = (user?.display_name || user?.email?.split("@")[0] || "there").trim().split(/\s+/)[0];
  const [activeId, setActiveId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [typing, setTyping] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  // Phones hide the chat list beside the conversation; this slides it in.
  const [chatsOpen, setChatsOpen] = useState(false);
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
  const [depth, setDepthState] = useState<RequestedDepth>("auto");
  const [attaching, setAttaching] = useState(false);
  const [attachingName, setAttachingName] = useState("");
  const [attachMenu, setAttachMenu] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  // Files wait in the input bar (like ChatGPT/Claude) and go with the next message.
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  // The reply being prepared, so Stop can abort it and tell the server to discard it.
  const inflight = useRef<{ controller: AbortController; sessionId?: string; requestId: string } | null>(null);
  const shownSoFar = useRef("");
  const [micStream, setMicStream] = useState<MediaStream | null>(null);
  const [chatFiles, setChatFiles] = useState<ChatFile[]>([]);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const conversationVersion = useRef(0);
  const topicPrefilled = useRef(false);
  const pendingAsk = useRef<string | null>(null);
  const followStreamingReply = useCallback((shown?: string) => {
    if (shown !== undefined) shownSoFar.current = shown;
    if (followLatest.current) bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: "instant" });
  }, []);

  useEffect(() => {
    if (!context || topicPrefilled.current) return;
    const query = new URLSearchParams(window.location.search);
    // "Explain this in chat" from a quiz result arrives with the exact question to ask.
    const ask = query.get("ask")?.trim().slice(0, 2000);
    if (ask) {
      topicPrefilled.current = true;
      // A question typed on Home is sent straight away; a quiz follow-up waits for review.
      if (query.get("autosend") === "1") pendingAsk.current = ask;
      else setInput(ask);
      return;
    }
    const topic = query.get("topic")?.trim().slice(0, 255);
    const subject = query.get("context");
    if (!topic || (subject && subject !== context.id)) return;
    topicPrefilled.current = true;
    setInput(`Help me learn ${topic}. Start with a clear explanation and an example.`);
  }, [context]);

  useEffect(() => () => { conversationVersion.current += 1; }, []);

  useEffect(() => { setDepthState(savedDepth()); }, []);

  // A newer upload or chat switch makes an in-flight file list stale.
  const filesVersion = useRef(0);
  const loadChatFiles = useCallback(async (sid: string) => {
    if (!context) return;
    const version = ++filesVersion.current;
    const files = await api<ChatFile[]>(`/api/v1/resources?context_id=${context.id}&session_id=${sid}`);
    if (version === filesVersion.current) setChatFiles(files);
  }, [context]);

  useEffect(() => {
    setChatFiles([]);
    if (activeId) loadChatFiles(activeId).catch(() => {});
  }, [activeId, loadChatFiles]);

  const addToLibrary = async (file: ChatFile) => {
    try {
      await api(`/api/v1/resources/${file.id}/library`, { method: "POST" });
      setChatFiles((files) => files.filter((f) => f.id !== file.id));
      toast(`"${file.title}" is now in your library, so every chat can use it.`, "success");
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Could not add the file to your library.", "error");
    }
  };

  const setDepth = (value: RequestedDepth) => {
    setDepthState(value);
    try { window.localStorage.setItem(DEPTH_KEY, value); } catch {}
  };

  const loadList = useCallback(async (cid: string) => {
    const list = await api<Session[]>("/api/v1/study/sessions?context_id=" + cid);
    setSessions(list);
    return list;
  }, []);

  const loadMessages = useCallback(async (sid: string, version = ++conversationVersion.current) => {
    followLatest.current = true;
    setAwayFromLatest(false);
    const list = await api<
      Array<{ id: string; action?: ChatAction | null; role: "user" | "assistant" | "aria"; content: string; sources?: Source[]; fallback_used?: boolean; depth?: Depth | null }>
    >("/api/v1/study/sessions/" + sid + "/messages");
    if (version !== conversationVersion.current) return;
    // Backend persists the standard "assistant" role; the UI bubble model uses "aria".
    const normalized: Msg[] = list.map((m) => ({
      id: m.id,
      action: m.action,
      role: m.role === "assistant" ? "aria" : m.role,
      content: m.content,
      sources: m.sources,
      fallback_used: m.fallback_used,
      depth: m.depth,
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

  /** Upload one staged file into this chat; null when the upload itself failed. */
  const uploadToChat = async (file: File, sid: string): Promise<ChatFile | null> => {
    if (!context) return null;
    const version = conversationVersion.current;
    setAttachingName(file.name);
    const title = file.name.replace(/\.[^/.]+$/, "") || "Photo";
    try {
      const isPdf = file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf";
      const query = `context_id=${context.id}&session_id=${sid}&title=${encodeURIComponent(title)}`;
      const endpoint = isPdf ? `/api/v1/resources/pdf?${query}` : `/api/v1/resources/image?${query}`;
      const mime = isPdf ? "application/pdf" : (file.type || "image/png");
      const saved = await apiUpload<ChatFile>(endpoint, file, mime);
      if (version !== conversationVersion.current) return saved;
      filesVersion.current += 1;
      setChatFiles((files) => [...files.filter((f) => f.id !== saved.id), saved]);
      if (saved.processing_status !== "READY") toast(saved.error_detail ?? `"${file.name}" could not be read. Try a clearer PDF or image.`, "error");
      return saved;
    } catch (err) {
      if (version === conversationVersion.current) toast(err instanceof ApiError ? err.message : `"${file.name}" could not be uploaded.`, "error");
      return null;
    }
  };

  const send = async (text: string, retry?: RetryRequest, depthOverride?: RequestedDepth) => {
    const files = retry ? [] : pendingFiles;
    if (loading || typing || requestLock.current || ctxLoading || !context || !(text.trim() || files.length)) return;
    const version = conversationVersion.current;
    // guard against stale session from previous context
    if (activeId && !sessions.some((s) => s.id === activeId && s.context_id === context.id)) return;
    const content = text.trim() || (files.length > 1 ? "Summarize these files" : "Summarize this file");
    requestLock.current = true;
    const pending: RetryRequest = retry ?? { content, requestId: crypto.randomUUID(), depth: depthOverride ?? depth };
    setRetryRequest(pending);
    setReplyError(false);
    setReplyErrorText("");
    if (!retry) {
      setMsgs((m) => [...m, { role: "user", content, fresh: true, files: files.map((file) => ({ name: file.name })) }]);
      setInput("");
      setPendingFiles([]);
    }
    const controller = new AbortController();
    inflight.current = { controller, requestId: pending.requestId };
    setTyping(true);
    let waitingOn: string | null = null;
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
      inflight.current = { controller, sessionId: sid, requestId: pending.requestId };
      if (files.length) {
        setAttaching(true);
        const sent: SentFile[] = [];
        for (const file of files) {
          const saved = await uploadToChat(file, sid);
          sent.push({ name: file.name, id: saved?.id, failed: !saved || saved.processing_status !== "READY" });
        }
        setAttaching(false);
        if (version !== conversationVersion.current || controller.signal.aborted) return;
        setMsgs((m) => m.map((msg) => msg.role === "user" && msg.files && msg.content === content && !msg.files.some((f) => f.id)
          ? { ...msg, files: sent } : msg));
      }
      waitingOn = sid;
      setWaitingIds((ids) => [...ids, sid]);
      // The reply streams in as ARIA writes it, like ChatGPT or Claude.
      let res: Msg | null = null;
      let streamed = false;
      await apiStream("/api/v1/study/sessions/" + sid + "/messages/stream",
        { content, request_id: pending.requestId, depth: pending.depth, screen: screenSize() },
        (event) => {
          if (version !== conversationVersion.current) return;
          if (event.type === "delta") {
            const piece = String(event.text ?? "");
            const first = !streamed; // read now: React may run the update after `streamed` changes
            setMsgs((m) => !first
              ? m.map((msg, index) => index === m.length - 1 && msg.live ? { ...msg, content: msg.content + piece } : msg)
              : [...m, { role: "aria", content: piece, fresh: true, live: true, depth: pending.depth === "auto" ? null : pending.depth }]);
            streamed = true;
            requestAnimationFrame(() => followStreamingReply());
          } else if (event.type === "done") {
            res = event.message as Msg;
          } else if (event.type === "error") {
            throw new ApiError(Number(event.status ?? 500), String(event.detail ?? "Your reply could not be loaded. Please try again."));
          }
        }, controller.signal);
      // Refresh the sidebar even if the learner has moved to another chat, or this
      // chat (still listed with no messages) would vanish from the list.
      loadList(context.id).catch(() => {});
      if (version !== conversationVersion.current || !res) return;
      const reply: Msg = res;
      setMsgs((m) => {
        const kept = streamed && m[m.length - 1]?.live ? m.slice(0, -1) : m;
        // Streamed text is already on screen; a reply that did not stream (a fallback or an action) types out.
        const typed = !streamed && !reducedMotion && !reply.action;
        return [...kept, { id: reply.id, action: reply.action, role: "aria", content: typed ? "" : reply.content, fullContent: reply.content,
          sources: reply.sources, fallback_used: reply.fallback_used, depth: reply.depth, fresh: true, streaming: typed }];
      });
      setRetryRequest(null);
      setResponding(true);
    } catch (error) {
      if (version !== conversationVersion.current || controller.signal.aborted) return;
      setReplyError(true);
      setReplyErrorText(error instanceof ApiError ? error.message : "Your reply could not be loaded. Please try again.");
    } finally {
      if (waitingOn) setWaitingIds((ids) => ids.filter((id) => id !== waitingOn));
      if (inflight.current?.controller === controller) inflight.current = null;
      if (version === conversationVersion.current) {
        requestLock.current = false;
        setTyping(false);
      }
    }
  };

  const stop = () => {
    const current = inflight.current;
    if (current) {
      current.controller.abort();
      inflight.current = null;
      if (current.sessionId) {
        void api(`/api/v1/study/sessions/${current.sessionId}/messages/${current.requestId}/stop`, { method: "POST" }).catch(() => {});
      }
      requestLock.current = false;
      setTyping(false);
      setAttaching(false);
      setRetryRequest(null);
      setMsgs((m) => m[m.length - 1]?.live
        ? m.map((msg, index) => index === m.length - 1 ? { ...msg, live: false, stopped: true } : msg)
        : [...m, { role: "aria", content: "", stopped: true }]);
      return;
    }
    setMsgs((m) => m.map((msg) => msg.streaming
      ? { ...msg, streaming: false, content: shownSoFar.current, stopped: true } : msg));
  };
  const replying = typing || msgs.some((m) => m.streaming || m.live);
  const writing = msgs[msgs.length - 1]?.live === true;
  const sentIds = new Set(msgs.flatMap((m) => m.files?.flatMap((f) => (f.id ? [f.id] : [])) ?? []));

  useEffect(() => {
    if (!pendingAsk.current || loading || ctxLoading || !context) return;
    const question = pendingAsk.current;
    pendingAsk.current = null;
    // Start a fresh chat for it and drop the parameters so a reload does not resend.
    window.history.replaceState(window.history.state, "", window.location.pathname);
    void send(question);
  }); // Runs after each render until the page is ready; the ref ensures it sends once.

  /** The + menu: one hidden input for documents and photos; the camera gets a live preview. */
  const pickAttachment = (kind: "file" | "photo" | "camera") => {
    const input = fileInputRef.current;
    setAttachMenu(false);
    if (kind === "camera") { setCameraOpen(true); return; }
    if (!input) return;
    input.accept = kind === "file" ? ".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/*" : "image/*";
    input.click();
  };

  const stageFile = (file: File) => {
    const isPdf = file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf";
    if (file.size > (isPdf ? 50 : 25) * 1024 * 1024) {
      toast(isPdf ? "This PDF is over 50 MB." : "This photo is over 25 MB.", "error");
      return;
    }
    setPendingFiles((files) => [...files, file]);
  };

  const handleAttachFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    Array.from(e.target.files ?? []).forEach(stageFile);
    e.target.value = "";
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

    if (typeof MediaRecorder === "undefined") {
      toast("This browser cannot record audio. Open ARIA in Chrome or Edge to use voice input.", "error");
      return;
    }

    let stream: MediaStream | null = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recordingStream = stream;
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
        recordingStream.getTracks().forEach((track) => track.stop());
        setMicStream(null);
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
      setMicStream(stream);
      setRecording(true);
    } catch (error) {
      stream?.getTracks().forEach((track) => track.stop());
      if (version !== conversationVersion.current) return;
      const name = error instanceof Error ? error.name : "";
      const message = name === "NotAllowedError" || name === "SecurityError"
        ? "Microphone access is blocked. Allow microphone access for this site and in Windows privacy settings, then retry. If the in-app browser cannot request access, open ARIA in Chrome or Edge."
        : name === "NotFoundError" || name === "DevicesNotFoundError"
          ? "No microphone was found. Connect a microphone or select an input device in Windows sound settings, then retry."
          : name === "NotReadableError" || name === "TrackStartError"
            ? "Your microphone could not be opened. Check Windows microphone access and close other apps using the device, then retry."
            : "Audio recording could not start. Check your microphone, or open ARIA in Chrome or Edge and retry.";
      toast(message, "error");
    }
  };

  const newChat = () => {
    setChatsOpen(false);
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
    setChatsOpen(false);
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
  const lastReply = msgs.reduce((last, m, i) => (m.role === "aria" && !m.action ? i : last), -1);
  const visibleSessions = sessions.filter((s) => (s.message_count ?? 0) > 0 || s.id === activeId || waitingIds.includes(s.id));

  if (loading || ctxLoading) {
    return <div className="chat-shell"><Loading label="your tutor" /></div>;
  }

  return (
    <div className={`chat-sidebar-layout${focusMode ? " study-focus" : ""}${chatsOpen ? " chats-open" : ""}`}>
      {chatsOpen && <button type="button" className="chats-backdrop" aria-label="Close chats" onClick={() => setChatsOpen(false)} />}
      <aside className="learn-side" id="learn-chats">
        <button className="btn btn-primary btn-block" onClick={newChat}>
          <Icon name="plus" size={16} /> New chat
        </button>
        {visibleSessions.length === 0 ? (
          <>
            <div className="nav-sec">Recents</div>
            <div className="session-empty">Your conversations will appear here, titled by what you explored.</div>
          </>
        ) : (
          <div className="session-group">
            <div className="nav-sec">Recents</div>
            {visibleSessions.map((s) => (
              <button
                key={s.id}
                type="button"
                className={`session-item${activeId === s.id ? " active" : ""}`}
                onClick={() => selectSession(s.id)}
                aria-current={activeId === s.id ? "page" : undefined}
                title={s.title ?? "New conversation"}
              >
                <span className="session-title">{(s.title ?? "New conversation").replace(new RegExp("^[\\p{Extended_Pictographic}\\p{Emoji_Presentation}\\uFE0F\\u200D\\s]+", "u"), "") || s.title}</span>
                {waitingIds.includes(s.id) && <span className="session-meta">ARIA is replying…</span>}
              </button>
            ))}
          </div>
        )}
      </aside>

      <div className="chat-shell">
        <div className="chat-head">
          <button type="button" className="icon-btn chats-toggle" aria-label="Your chats" aria-controls="learn-chats" aria-expanded={chatsOpen} onClick={() => setChatsOpen(true)}><Icon name="list" size={18} /></button>
          <div className="chat-title">
            <h1>{sessions.find((s) => s.id === activeId)?.title ?? "New chat"}</h1>
            <span className="chat-subject">{context?.title ?? "Learn"}</span>
            <AssistantPresence state={recording ? "listening" : typing || transcribing ? "thinking" : replyError ? "error" : responding ? "responding" : "idle"} />
          </div>
          <button className="icon-btn focus-toggle" aria-label={focusMode ? "Exit focus mode" : "Focus mode"} title={focusMode ? "Show the chat list and navigation again" : "Hide the chat list and navigation"} aria-pressed={focusMode} onClick={() => setFocusMode(value => !value)}><Icon name="target" size={17} /></button>
        </div>


        <div className="chat-body" ref={bodyRef} role="region" aria-label="Conversation" tabIndex={0} onScroll={() => {
          const body = bodyRef.current;
          if (!body) return;
          const away = body.scrollHeight - body.scrollTop - body.clientHeight > 90;
          followLatest.current = !away;
          setAwayFromLatest(away);
        }}>
          {chatFiles.some((file) => !sentIds.has(file.id)) && <div className="chat-files" aria-label="Files in this chat">
            {chatFiles.filter((file) => !sentIds.has(file.id)).map((file) => (
              <div key={file.id} className={`chat-file${file.processing_status === "READY" ? "" : " failed"}`}>
                <span className="chat-file-icon"><Icon name="file" size={18} /></span>
                <span className="chat-file-text">
                  <b>{file.title}</b>
                  <small>{file.processing_status === "READY" ? "Attached · ARIA can read it in this chat" : file.error_detail ?? "Could not read this file"}</small>
                </span>
                {file.processing_status === "READY"
                  ? <button type="button" onClick={() => void addToLibrary(file)} aria-label={`Add ${file.title} to library`}>Add to library</button>
                  : <em>could not read</em>}
              </div>
            ))}
          </div>}
          {msgs.length === 0 && <PageGuide page="learn" />}
          {msgs.length === 0 && (
            <div style={{ textAlign: "center", padding: "32px 20px", color: "var(--text-2)", maxWidth: 580, margin: "0 auto" }}>
              <div style={{ display: "inline-flex", padding: 12, borderRadius: "50%", background: "var(--bg-2)", marginBottom: 12, color: "var(--primary)" }}>
                <Icon name="sparkles" size={32} />
              </div>
              <h3 style={{ fontSize: 22, fontWeight: 800, color: "var(--text-1)", margin: "0 0 20px" }}>
                Hey {firstName}, what do you want to learn?
              </h3>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
                {/* Starters fill the box for the learner to finish: sent bare, the AI has to guess a topic. */}
                {[
                  ["Explain a hard idea to me simply", "Explain this to me simply: "],
                  ["Quiz me with 3 questions", "Quiz me with 3 questions on "],
                  ["Help me plan my study for this week", "Help me plan my study this week. My goal is "],
                  ["Teach me something new in 5 minutes", "Teach me in 5 minutes about "],
                ].map(([prompt, starter], idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setInput(starter);
                      const box = document.querySelector<HTMLInputElement>('input[placeholder="Ask ARIA anything…"]');
                      box?.focus();
                    }}
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
            m.role === "aria" && m.stopped && !m.content ? <p key={i} className="msg-stopped">You stopped this reply.</p> : m.role === "aria" ? (
              m.action ? <ActionCard key={m.action.id} initial={m.action} /> : m.live ? (
                <TutorReply key={i} content={m.content} depth={m.depth} done={false} fresh />
              ) : m.streaming ? (
                <StreamingMessage key={i} msg={m} onProgress={followStreamingReply} onDone={() => setMsgs(prev => prev.map((pm, pi) => pi === i ? { ...pm, streaming: false, content: pm.fullContent ?? pm.content } : pm))} />
              ) : (
                m.stopped ? (
                  // A stopped reply is not saved, so nothing can build on it.
                  <div key={i}>
                    <TutorReply content={m.content} depth={m.depth} done={false} fresh={m.fresh} />
                    <p className="msg-stopped">You stopped this reply.</p>
                  </div>
                ) : <TutorReply key={i} content={m.content} depth={m.depth} sources={m.sources} fallback={m.fallback_used} fresh={m.fresh}
                  onDeeper={i === lastReply && !typing ? () => void send("Explain that in more depth, with an example.", undefined, "deep") : undefined}
                  onShorter={i === lastReply && !typing ? () => void send("Give me a shorter version of that.", undefined, "quick") : undefined}
                  quickCheckHref={i === lastReply && !typing && activeId ? `/app/assess?${new URLSearchParams({ quiz_chat: activeId })}` : undefined} />
              )
            ) : (
              <div className={`msg-user-wrap${m.fresh ? " message-arrival" : ""}`} key={i}>
                {m.files && m.files.length > 0 && <div className="msg-files">
                  {m.files.map((file, fi) => <span key={fi} className={`msg-file${file.failed ? " failed" : ""}`}>
                    <Icon name={/\.pdf$/i.test(file.name) ? "file" : "image"} size={15} />{file.name}
                    {file.failed && <small> · could not read</small>}
                  </span>)}
                </div>}
                <div className="msg msg-user">{m.content}</div>
              </div>
            ),
          )}
          {replyError && retryRequest && <ErrorState inline title="Reply unavailable" message={replyErrorText}
            retryLabel="Retry reply" retryDisabled={typing} onRetry={() => void send(retryRequest.content, retryRequest)} />}
          {typing && !writing && <RequestStatus label={attaching ? `Reading ${attachingName || "your file"}…` : "ARIA is thinking…"} />}
        </div>

        {awayFromLatest && <button type="button" className="jump-latest" aria-label="Scroll to the latest message" title="Latest message" onClick={() => {
          followLatest.current = true;
          setAwayFromLatest(false);
          bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: reducedMotion ? "instant" : "smooth" });
        }}><Icon name="chevron-down" size={18} /></button>}
        {focusMode && msgs.length > 0 && <p className="focus-session-summary">This session · {msgs.filter(message => message.role === "user").length} questions · {msgs.filter(message => message.role === "aria").length} ARIA replies</p>}

        <div className="chat-input-row">
          <div className="depth-meter" role="radiogroup" aria-label="Answer depth">
            <span className="depth-meter-label">Depth</span>
            {DEPTH_OPTIONS.map((option) => (
              <button key={option} type="button" role="radio" aria-checked={depth === option}
                className={`depth-option${depth === option ? " active" : ""}`} onClick={() => setDepth(option)}
                title={option === "auto" ? "ARIA matches the length to how you ask" : `${DEPTH_LABEL[option]} answers`}>
                {option === "auto" ? "Auto" : DEPTH_LABEL[option]}
              </button>
            ))}
          </div>
          {pendingFiles.length > 0 && <div className="pending-files" aria-label="Files to send">
            {pendingFiles.map((file, fi) => (
              <span key={`${file.name}-${fi}`} className="pending-file">
                <Icon name={/\.pdf$/i.test(file.name) ? "file" : "image"} size={15} />
                <span>{file.name}</span>
                <button type="button" aria-label={`Remove ${file.name}`} onClick={() => setPendingFiles((files) => files.filter((_, index) => index !== fi))}><Icon name="x" size={13} /></button>
              </span>
            ))}
          </div>}
          <div className="bar">
            <div className="attach-wrap">
              <button
                className="btn btn-secondary"
                style={{ width: 44, height: 44, padding: 0, borderRadius: 12, flexShrink: 0 }}
                aria-label="Attach document or image"
                aria-haspopup="menu"
                aria-expanded={attachMenu}
                onClick={() => setAttachMenu((open) => !open)}
                onKeyDown={(e) => { if (e.key === "Escape") setAttachMenu(false); }}
                disabled={!context || attaching}
                title="Add files, photos or a camera picture"
              >
                <Icon name="plus" size={20} />
              </button>
              {attachMenu && <>
                <div className="attach-backdrop" onClick={() => setAttachMenu(false)} />
                <div className="attach-menu" role="menu" aria-label="Add to this chat">
                  <button type="button" role="menuitem" onClick={() => pickAttachment("file")}><Icon name="file" size={17} /><span><b>Upload a file</b><small>PDFs up to 50 MB · photos up to 25 MB</small></span></button>
                  <button type="button" role="menuitem" onClick={() => pickAttachment("photo")}><Icon name="image" size={17} /><span><b>Photos</b><small>Notes, slides, a whiteboard</small></span></button>
                  <button type="button" role="menuitem" onClick={() => pickAttachment("camera")}><Icon name="camera" size={17} /><span><b>Take a photo</b><small>Use your camera</small></span></button>
                </div>
              </>}
            </div>
            {recording && micStream ? <MicWaveform stream={micStream} /> : <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={transcribing ? "Turning your voice into text…" : "Ask ARIA anything…"}
              onKeyDown={(e) => { if (e.key === "Enter" && !replying) void send(input); }}
              disabled={ctxLoading || loading}
            />}
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
            {replying
              ? <button className="btn btn-primary" style={{ width: 42, height: 42, padding: 0, borderRadius: "50%", flexShrink: 0 }} aria-label="Stop" title="Stop the reply" onClick={stop}>
                  <Icon name="stop" size={16} />
                </button>
              : <button className="btn btn-primary" style={{ width: 42, height: 42, padding: 0, borderRadius: "50%", flexShrink: 0 }} aria-label="Send" onClick={() => send(input)} disabled={ctxLoading || loading || !(input.trim() || pendingFiles.length)}>
                  <Icon name="send" size={18} />
                </button>}
          </div>
        </div>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.webp"
        multiple
        style={{ display: "none" }}
        onChange={handleAttachFile}
      />
      {cameraOpen && <CameraCapture onClose={() => setCameraOpen(false)} onCapture={stageFile} />}
    </div>
  );
}
