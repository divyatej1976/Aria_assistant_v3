"use client";

import { Modal } from "@/components/modal";
import { PageGuide } from "@/components/page-guide";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icons";
import { api, apiBlob, apiUpload, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { toast } from "@/lib/toast";
import { ErrorState, Loading } from "@/components/states";
import { ConfirmDialog, type ConfirmState } from "@/components/confirm";

type Note = {
  id: string;
  title: string;
};
type Resource = {
  id: string;
  title: string;
  resource_type: string;
};
type Artifact = {
  id: string;
  source_type: string;
  source_id: string;
  text: string;
  status: string;
  error_detail: string | null;
  content_type: string | null;
  duration_seconds: number | null;
  created_at: string;
  title?: string;
  parts?: EpisodePart[];
};
type EpisodePart = { part: number; start_seconds: number };
type Progress = { position_seconds: number; completed: boolean };
type Chat = { id: string; title?: string | null; message_count?: number };
type AudioListItem = {
  id: string;
  source_type: string;
  source_id: string;
  title: string;
  status: string;
  content_type: string | null;
  duration_seconds: number | null;
  position_seconds: number;
  completed: boolean;
  created_at: string;
  parts: EpisodePart[];
};

function fmtDur(seconds: number | null | undefined): string {
  if (!seconds) return "";
  const mins = Math.floor(seconds / 60);
  const secs = String(seconds % 60).padStart(2, "0");
  return `${mins}:${secs}`;
}

export default function AudioPage() {
  const { context } = useActiveContext();
  return <AudioPageWorkspace key={context?.id ?? "no-subject"} />;
}

function AudioPageWorkspace() {
  const { context } = useActiveContext();
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [notes, setNotes] = useState<Note[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [chats, setChats] = useState<Chat[]>([]);
  const [chatId, setChatId] = useState("");
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [progress, setProgress] = useState<Record<string, Progress>>({});
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState(""); // "note:<id>" | "resource:<id>"
  const [sourceMode, setSourceMode] = useState("text");
  // One tutor explaining, or a tutor answering a curious learner (two voices).
  const [audioStyle, setAudioStyle] = useState<"explainer" | "conversation">("explainer");
  const [draftTitle, setDraftTitle] = useState("");
  const [draftText, setDraftText] = useState("");
  const [conversionError, setConversionError] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadedSource, setUploadedSource] = useState<string | null>(null);
  const [sourcePreview, setSourcePreview] = useState<Artifact | null>(null);
  const [playing, setPlaying] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<ConfirmState>(null);
  const [speechSetup, setSpeechSetup] = useState<boolean | null>(null);
  const lastSavedRef = useRef<Record<string, number>>({});
  const timeRef = useRef<Record<string, number>>({});
  const playerRef = useRef<HTMLAudioElement | null>(null);
  const pendingProgress = useRef<Record<string, Progress>>({});
  const urlsRef = useRef<Record<string, string>>({});
  const mountedRef = useRef(false);
  const playbackVersions = useRef<Record<string, number>>({});

  const invalidateAudio = useCallback((id: string) => {
    playbackVersions.current[id] = (playbackVersions.current[id] ?? 0) + 1;
    if (urlsRef.current[id]) URL.revokeObjectURL(urlsRef.current[id]);
    delete urlsRef.current[id];
    setAudioUrl((prev) => { const next = { ...prev }; delete next[id]; return next; });
    setPlaying((current) => current === id ? null : current);
    delete timeRef.current[id];
    delete lastSavedRef.current[id];
    delete pendingProgress.current[id];
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    const unsaved = pendingProgress.current;
    return () => {
      mountedRef.current = false;
      for (const [id, update] of Object.entries(unsaved)) {
        void api(`/api/v1/audio/${id}/progress`, {
          method: "PUT", body: JSON.stringify(update), keepalive: true,
        }).catch(() => {});
      }
      for (const url of Object.values(urlsRef.current)) URL.revokeObjectURL(url);
      urlsRef.current = {};
    };
  }, []);

  // Durable server-side listing (GET /api/v1/audio?context_id=…). No more
  // per-browser localStorage index: artifacts appear on every device and
  // rehydrate progress from the same response.
  const hydrate = useCallback(async (cid: string) => {
    const listed = await api<AudioListItem[]>(`/api/v1/audio?context_id=${cid}`);
    setArtifacts((prev) => {
      // Server status is authoritative; preserve only client detail fields.
      const byId = new Map(prev.map((a) => [a.id, a]));
      return listed.map((row) => ({ text: "", error_detail: null, ...byId.get(row.id), ...row } as Artifact));
    });    const pr: Record<string, Progress> = {};
    for (const row of listed) {
      pr[row.id] = { position_seconds: row.position_seconds, completed: row.completed };
    }
    setProgress(pr);
  }, []);

  const load = useCallback(
    async (cid: string) => {
      const [n, r, c, capabilities] = await Promise.all([
        api<Note[]>(`/api/v1/notes?context_id=${cid}`),
        api<Resource[]>(`/api/v1/resources?context_id=${cid}`),
        api<Chat[]>(`/api/v1/study/sessions?context_id=${cid}`).catch(() => []),
        api<{ cloud_speech_configured: boolean }>("/api/v1/settings/capabilities").catch(() => null),
      ]);
      setNotes(n);
      setResources(r);
      setChats(c.filter((chat) => (chat.message_count ?? 0) > 1));
      setSpeechSetup(typeof capabilities?.cloud_speech_configured === "boolean" ? capabilities.cloud_speech_configured : null);
      await hydrate(cid);
    },
    [hydrate],
  );

  useEffect(() => {
    if (!context) return;
    let cancelled = false;
    (async () => {
      try {
        await load(context.id);
      } catch {
        if (!cancelled) setFailed(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [context, load]);

  const hasPendingAudio = artifacts.some(a => a.status === "PENDING" || a.status === "PROCESSING");
  useEffect(() => {
    const id = window.location.hash.slice(1);
    if (id.startsWith("episode-")) document.getElementById(id)?.scrollIntoView({ block: "center" });
  }, [artifacts]);
  useEffect(() => {
    if (!context || !hasPendingAudio) return;
    const timer = setInterval(() => { void hydrate(context.id).catch(() => {}); }, 5000);
    return () => clearInterval(timer);
  }, [context, hasPendingAudio, hydrate]);

  const convert = async () => {
    if (!context || busy || (sourceMode === "chat" ? !chatId : sourceMode === "saved" ? !source : sourceMode === "file" ? !uploadFile : !draftText.trim())) {
      return;
    }
    setBusy(true);
    setConversionError("");
    try {
      let [kind, id] = source.split(":", 2);
      if (sourceMode === "file") {
        if (!uploadFile) return;
        const isPdfFile = uploadFile.type === "application/pdf" || uploadFile.name.toLowerCase().endsWith(".pdf");
        if (uploadFile.size > (isPdfFile ? 50 : 25) * 1024 * 1024) throw new Error(isPdfFile ? "Choose a PDF smaller than 50 MB." : "Choose a photo smaller than 25 MB.");
        kind = "resource";
        if (uploadedSource) id = uploadedSource;
        else {
          const isPdf = uploadFile.type === "application/pdf" || uploadFile.name.toLowerCase().endsWith(".pdf");
          const saved = await apiUpload<Resource>(`/api/v1/resources/${isPdf ? "pdf" : "image"}?context_id=${context.id}&title=${encodeURIComponent(uploadFile.name)}`, uploadFile, isPdf ? "application/pdf" : uploadFile.type);
          id = saved.id;
          if (mountedRef.current) setUploadedSource(id);
        }
      }
      const styleQuery = audioStyle === "conversation" ? "?style=conversation" : "";
      const artifact = await api<Artifact>(
        sourceMode === "chat" ? `/api/v1/audio/sessions/${chatId}/generate${styleQuery}` :
        sourceMode === "text" ? "/api/v1/audio/text/generate" : `/api/v1/audio/${kind === "note" ? "notes" : "resources"}/${id}/generate${styleQuery}`,
        { method: "POST", ...(sourceMode === "text" ? { body: JSON.stringify({context_id: context.id, title: draftTitle.trim() || "Audio from text", text: draftText.trim(), style: audioStyle}) } : {}) },
      );
      if (!mountedRef.current) return;
      invalidateAudio(artifact.id);
      artifact.title =
        sourceMode === "chat" ? artifact.title ?? chats.find((chat) => chat.id === chatId)?.title ?? "Chat" :
        sourceMode === "text" ? draftTitle.trim() || "Audio from text" : sourceMode === "file" ? uploadFile?.name : kind === "note"
          ? notes.find((n) => n.id === id)?.title ?? "Note"
          : resources.find((r) => r.id === id)?.title ?? "Resource";
      setArtifacts((prev) => [artifact, ...prev.filter((a) => a.id !== artifact.id)]);
      setProgress((prev) => ({ ...prev, [artifact.id]: { position_seconds: 0, completed: false } }));
      setOpen(false);
      setSource("");
      setChatId("");
      setDraftText("");
      setDraftTitle("");
      setUploadFile(null);
      setUploadedSource(null);
      await load(context.id);
      if (artifact.status === "READY") toast("Audio ready.", "success");
      else if (artifact.status === "FAILED") toast("Audio generation failed. Please retry or check audio setup.", "error");
      else toast("Creating your episode in the background. You can leave this page; it will appear here when ready.");
    } catch (e) {
      if (mountedRef.current) setConversionError(e instanceof Error ? e.message : "Could not generate audio. Your source is kept here so you can retry.");
    } finally {
      setBusy(false);
    }
  };

  const togglePlay = async (id: string) => {
    if (artifacts.find(artifact => artifact.id === id)?.status !== "READY") return;
    if (playing && playing !== id) {
      await saveProgress(playing, timeRef.current[playing] ?? progress[playing]?.position_seconds ?? 0,
        progress[playing]?.completed ?? false);
    }
    if (playing === id) {
      // Persist the exact current position before unmounting the element so
      // pause never loses up to the 5-second autosave delta.
      const current = timeRef.current[id] ?? progress[id]?.position_seconds ?? 0;
      await saveProgress(id, current, false);
      setPlaying(null);
      return;
    }
    if (!audioUrl[id]) {
      try {
        const version = playbackVersions.current[id] ?? 0;
        const blob = await apiBlob(`/api/v1/audio/${id}/play`);
        if (!mountedRef.current || version !== (playbackVersions.current[id] ?? 0)) return;
        const url = URL.createObjectURL(blob);
        if (urlsRef.current[id]) URL.revokeObjectURL(urlsRef.current[id]);
        urlsRef.current[id] = url;
        setAudioUrl((prev) => ({ ...prev, [id]: url }));
      } catch (e) {
        toast(e instanceof ApiError ? e.message : "Audio is not ready yet.", "error");
        return;
      }
    }
    setPlaying(id);
  };

  const saveProgress = async (id: string, position: number, completed: boolean) => {
    const update = { position_seconds: Math.round(position), completed };
    pendingProgress.current[id] = update;
    try {
      const saved = await api<Progress>(`/api/v1/audio/${id}/progress`, {
        method: "PUT",
        body: JSON.stringify(update),
      });
      if (pendingProgress.current[id] === update) {
        delete pendingProgress.current[id];
        if (mountedRef.current) setProgress((prev) => ({ ...prev, [id]: saved }));
      }
    } catch {
      // silent — progress is best-effort
    }
  };

  const remove = async (id: string) => {
    try {
      await api(`/api/v1/audio/${id}`, { method: "DELETE" });
      invalidateAudio(id);
      setArtifacts((prev) => prev.filter((a) => a.id !== id));
      if (playing === id) setPlaying(null);
      toast("Audio deleted.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not delete audio.", "error");
    }
  };

  const sources: { kind: "note" | "resource"; id: string; title: string }[] = [
    ...notes.map((n) => ({ kind: "note" as const, id: n.id, title: n.title })),
    ...resources.map((r) => ({ kind: "resource" as const, id: r.id, title: r.title })),
  ];

  if (loading) {
    return <Loading label="your audio studio" />;
  }
  if (failed) {
    return <ErrorState message="This screen could not be loaded." onRetry={() => window.location.reload()} />;
  }

  return (
    <div>
      <div className="section-head">
        <div>
          <h1 className="pg-title">Audio studio</h1>
          <p className="pg-sub">Turn your learning into beautiful audio.</p>
        </div>
        <button className="btn btn-primary" data-tour="convert-audio" onClick={() => setOpen(true)}>
          <Icon name="plus" /> Convert to audio
        </button>
      </div>
      <PageGuide page="audio" />

      <p className="banner" role="status" style={{ marginBottom: 16 }}>
        {speechSetup === true
          ? "Choose a source to create an audio episode. If a voice service is unavailable, we’ll help you try again."
          : speechSetup === false
            ? "Choose a source to create an audio episode with local speech, where available."
            : "Choose a source to create an audio episode. We’ll let you know if audio creation needs attention."}
      </p>

      {artifacts.length === 0 ? (
        <div className="empty-state">
          <Icon name="headphones" size={30} />
          <p style={{ margin: "10px 0 14px", fontSize: 14, color: "var(--text-1)" }}>
            No audio yet. Pick one of your chats, paste text, or upload a file to make your first episode.
          </p>
          <button className="btn btn-primary" onClick={() => setOpen(true)} style={{ justifyContent: "center" }}>
            <Icon name="plus" /> Convert to audio
          </button>
        </div>
      ) : (
        artifacts.map((a) => {
          const p = progress[a.id] ?? { position_seconds: 0, completed: false };
          const isPlaying = playing === a.id;
          return (
            <div className="audio-card" id={`episode-${a.id}`} key={a.id}>
              <div className="card-header">
                <button
                  className="play-btn"
                  disabled={a.status !== "READY"}
                  onClick={() => togglePlay(a.id)}
                  aria-label={isPlaying ? "Pause" : `Play ${a.source_type} audio`}
                >
                  {isPlaying ? <Icon name="pause" /> : <Icon name="play" />}
                </button>
                <div>
                  <b style={{ fontSize: 15 }}>
                    {a.title ??
                      (a.source_type === "NOTE"
                        ? notes.find((n) => n.id === a.source_id)?.title ?? "Note"
                        : resources.find((r) => r.id === a.source_id)?.title ?? "Resource")}
                  </b>
                  <div style={{ fontSize: 12, color: "var(--text-3)" }}>
                    {({ PENDING: "Creating…", PROCESSING: "Creating…", READY: "Ready", FAILED: "Failed" } as Record<string, string>)[a.status] ?? a.status} {a.duration_seconds ? ` · ${fmtDur(a.duration_seconds)}` : ""}{" "}
                    {p.completed ? " · Complete" : p.position_seconds > 0 ? ` · Resume ${fmtDur(p.position_seconds)}` : ""}
                  </div>
                </div>
              </div>
              <div className="card-header">
                <div className={`wave${isPlaying ? " playing" : ""}`} style={{ width: 120 }}>
                  {Array.from({ length: 12 }).map((_, i) => (
                    <b key={i} style={{ animationDuration: `${0.5 + ((i % 5) * 0.12)}s`, ["--wh" as string]: `${10 + ((i * 7) % 20)}px` }} />
                  ))}
                </div>
                {a.status === "PENDING" || a.status === "PROCESSING"
                  ? <button className="btn btn-ghost" onClick={() => setConfirm({ title: "Stop creating this episode?", body: "ARIA stops writing it and it is removed from your library.", confirmLabel: "Stop", onConfirm: () => void remove(a.id) })} aria-label={`Cancel ${a.source_type} audio`}>
                      Cancel
                    </button>
                  : <button className="btn btn-ghost" onClick={() => setConfirm({ title: "Delete audio", body: "Delete this audio artifact? Its saved progress goes with it.", confirmLabel: "Delete audio", onConfirm: () => void remove(a.id) })} aria-label={`Delete ${a.source_type} audio`}>
                      Delete
                    </button>}
              </div>
              {a.status === "FAILED" && (
                <div role="alert" className="ui-mt-16">
                  <p>Audio generation failed. Your source is saved so you can retry.</p>
                  <button className="btn btn-secondary" onClick={() => { setSourceMode("saved"); setSource(`${a.source_type === "NOTE" ? "note" : "resource"}:${a.source_id}`); setConversionError(""); setOpen(true); }}>Retry audio</button>
                </div>
              )}
              <button className="btn btn-ghost" onClick={async () => {
                try { const detail = await api<Artifact>(`/api/v1/audio/${a.id}`); if (mountedRef.current) setSourcePreview({ ...detail, title: a.title }); }
                catch { toast("Could not load the source. Please retry.", "error"); }
              }}>View saved source</button>
              {a.status === "READY" && (
                <Link className="btn btn-ghost" href={`/app/learn?${new URLSearchParams({ ask: `Explain the main ideas of "${a.title ?? "this episode"}" and answer my questions about it.` })}`}>
                  <Icon name="message" size={15} /> Ask about this
                </Link>
              )}
              {isPlaying && a.status === "READY" && (
                <audio
                  ref={playerRef}
                  autoPlay
                  controls
                  src={audioUrl[a.id]}
                  onLoadedMetadata={(e) => {
                    // Resume where the learner left off.
                    const saved = progress[a.id]?.position_seconds ?? 0;
                    if (saved > 0 && !progress[a.id]?.completed) {
                      e.currentTarget.currentTime = saved;
                      timeRef.current[a.id] = saved;
                    }
                  }}
                  onTimeUpdate={(e) => {
                    const t = e.currentTarget.currentTime;
                    timeRef.current[a.id] = t;
                    pendingProgress.current[a.id] = { position_seconds: Math.round(t), completed: false };
                    const last = lastSavedRef.current[a.id] ?? -Infinity;
                    if (t - last >= 5) {
                      lastSavedRef.current[a.id] = t;
                      void saveProgress(a.id, t, false);
                    }
                  }}
                  onEnded={() => {
                    lastSavedRef.current[a.id] = 0;
                    timeRef.current[a.id] = 0;
                    void saveProgress(a.id, 0, true);
                  }}
                  style={{ width: "100%", marginTop: 10 }}
                />
              )}
              {isPlaying && a.status === "READY" && (a.parts?.length ?? 0) > 1 && (
                <div className="audio-parts" role="group" aria-label="Jump to part">
                  {a.parts!.map((part) => (
                    <button key={part.part} type="button" className="btn btn-ghost" onClick={() => {
                      if (playerRef.current) { playerRef.current.currentTime = part.start_seconds; void playerRef.current.play(); }
                    }}>
                      Part {part.part} · {fmtDur(part.start_seconds) || "0:00"}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })
      )}

      <div style={{ margin: "26px 0 8px" }} className="nav-sec">Available sources</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))", gap: 16 }}>
        {sources.map((s) => (
          <div className="resource-card" key={`${s.kind}-${s.id}`}>
            <div className="ui-row ui-gap-12">
              <div className="fsq-ic" style={{ width: 46, height: 46 }}>
                <Icon name={s.kind === "note" ? "file" : "folder"} size={21} />
              </div>
              <div>
                <b style={{ fontSize: 14 }}>{s.title}</b>
                <div style={{ fontSize: 11, color: "var(--text-3)" }}>{s.kind === "note" ? "Note" : "Resource"}</div>
              </div>
            </div>
          </div>
        ))}
        {sources.length === 0 && (
          <div className="card card-pad" style={{ gridColumn: "1 / -1" }}>
            <p style={{ fontSize: 13, color: "var(--text-1)", margin: 0 }}>
              Choose Convert to audio to turn a chat, pasted text, or a file into an episode.{" "}
              <Link href="/app/materials" style={{ color: "var(--accent-strong)", fontWeight: 700 }}>
                Open materials library
              </Link>
            </p>
          </div>
        )}
      </div>

      {/* convert modal */}
      <Modal open={open} title="Convert to audio" onClose={() => { if (!busy) setOpen(false); }}>
        <div className="modal">
          <div className="m-head dialog-heading">
            <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}><Icon name="headphones" size={20} /> Convert to audio</h3>
            <button className="btn btn-ghost" style={{ padding: 6 }} disabled={busy} onClick={() => setOpen(false)} aria-label="Close"><Icon name="x" size={16} /></button>
          </div>
          <div className="form-group">
            <label className="field-label" htmlFor="audio-mode">Create from</label>
            <select id="audio-mode" className="input" value={sourceMode} disabled={busy} onChange={e => { setSourceMode(e.target.value); setConversionError(""); }}>
              <option value="chat">A chat with ARIA</option>
              <option value="text">Paste text</option>
              <option value="file">Upload PDF or image</option>
              <option value="saved">Saved material</option>
            </select>
          </div>
          <fieldset className="form-group audio-style">
            <legend className="field-label">How it sounds</legend>
            <label><input type="radio" name="audio-style" checked={audioStyle === "explainer"} disabled={busy} onChange={() => setAudioStyle("explainer")} />
              <span><b>A tutor explains</b><small>One voice teaches the key ideas with examples, then recaps.</small></span></label>
            <label><input type="radio" name="audio-style" checked={audioStyle === "conversation"} disabled={busy} onChange={() => setAudioStyle("conversation")} />
              <span><b>Tutor and learner</b><small>Two voices: a learner asks the questions you would, the tutor answers.</small></span></label>
          </fieldset>
          {sourceMode === "chat" ? <div className="form-group">
            <label className="field-label" htmlFor="audio-chat">Chat</label>
            <select id="audio-chat" className="input" value={chatId} disabled={busy} onChange={(e) => setChatId(e.target.value)}>
              <option value="">Choose a chat…</option>
              {chats.map((chat) => <option key={chat.id} value={chat.id}>{chat.title ?? "Untitled chat"}</option>)}
            </select>
            <p>{chats.length ? "ARIA turns the conversation into a short lesson you can listen to." : "No chats yet. Talk to ARIA in Learn first, then come back here."}</p>
          </div> : sourceMode === "text" ? <>
            <div className="form-group"><label className="field-label" htmlFor="audio-title">Episode title (optional)</label><input id="audio-title" className="input" maxLength={200} value={draftTitle} disabled={busy} onChange={e => setDraftTitle(e.target.value)} /></div>
            <div className="form-group"><label className="field-label" htmlFor="audio-text">Text to turn into a lesson</label><textarea id="audio-text" className="input" rows={7} maxLength={200000} value={draftText} disabled={busy} onChange={e => setDraftText(e.target.value)} /><p>{draftText.length.toLocaleString()} / 200,000 characters. A copy is saved to Materials automatically.</p></div>
          </> : sourceMode === "file" ? <div className="form-group">
            <label className="field-label" htmlFor="audio-file">PDF (up to 50 MB) or image (up to 25 MB)</label>
            <input id="audio-file" className="input" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" disabled={busy} onChange={e => { setUploadFile(e.target.files?.[0] ?? null); setUploadedSource(null); }} />
            <p>We’ll extract the text and save the source to Materials automatically.</p>
          </div> : <>
          <div className="form-group">
            <label className="field-label" htmlFor="audio-source">Source</label>
            <select id="audio-source" className="input" value={source} disabled={busy} onChange={(e) => setSource(e.target.value)}>
              <option value="">Choose a note or resource…</option>
              {notes.map((n) => (
                <option key={`note-${n.id}`} value={`note:${n.id}`}>Note · {n.title}</option>
              ))}
              {resources.map((r) => (
                <option key={`resource-${r.id}`} value={`resource:${r.id}`}>Resource · {r.title}</option>
              ))}
            </select>
          </div>
          {sources.length === 0 && (
            <p style={{ fontSize: 12, color: "var(--text-1)", margin: "0 0 8px" }}>
              No saved materials yet. Choose Paste text to create audio now.
            </p>
          )}
          </>}
          {conversionError && <p role="alert">{conversionError}</p>}
          {busy && <p role="status">Starting your episode…</p>}
          <div className="dialog-actions ui-mt-16">
            <button className="btn btn-ghost" disabled={busy} onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={convert} disabled={busy || (sourceMode === "chat" ? !chatId : sourceMode === "saved" ? !source : sourceMode === "file" ? !uploadFile : !draftText.trim())}>
              {busy ? "Creating audio…" : "Create audio"} <Icon name="arrow" />
            </button>
          </div>
        </div>
      </Modal>
      <Modal open={!!sourcePreview} title="Saved audio source" onClose={() => setSourcePreview(null)}>
        <div className="modal"><h3>{sourcePreview?.title ?? "Saved audio source"}</h3><div style={{ whiteSpace: "pre-wrap", maxHeight: "60vh", overflowY: "auto" }}>{sourcePreview?.text}</div><div className="dialog-actions"><Link href="/app/materials">Open Materials</Link><button className="btn btn-secondary" onClick={() => setSourcePreview(null)}>Close</button></div></div>
      </Modal>
      <ConfirmDialog state={confirm} onClose={() => setConfirm(null)} />
    </div>
  );
}
