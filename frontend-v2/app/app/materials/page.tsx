"use client";

import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { api, apiBlob, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { toast } from "@/lib/toast";
import { ConfirmDialog, type ConfirmState } from "@/components/confirm";
import { ErrorState, Loading } from "@/components/states";

type Note = {
  id: string;
  context_id: string;
  title: string;
  body: string;
  concept_id: string | null;
  study_session_id: string | null;
  created_at: string;
  state: string | null;
  interval_days: number | null;
  next_review_at: string | null;
  last_outcome: string | null;
};
type Resource = {
  id: string;
  context_id: string;
  title: string;
  resource_type: string;
  processing_status: string;
  error_detail: string | null;
  chunk_count: number;
};
type Session = {
  id: string;
  context_id: string;
  mode: string;
  status: string;
  created_at: string;
};

function fmtDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function MaterialsPage() {
  const { context } = useActiveContext();
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState<Note[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [genOpen, setGenOpen] = useState(false);
  const [resOpen, setResOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [resTitle, setResTitle] = useState("");
  const [resText, setResText] = useState("");
  const [confirm, setConfirm] = useState<ConfirmState>(null);

  const [failed, setFailed] = useState(false);

  const load = useCallback(async (cid: string) => {
    const [n, r, s] = await Promise.all([
      api<Note[]>(`/api/v1/notes?context_id=${cid}`),
      api<Resource[]>(`/api/v1/resources?context_id=${cid}`),
      api<Session[]>(`/api/v1/study/sessions?context_id=${cid}`),
    ]);
    setNotes(n);
    setResources(r);
    setSessions(s);
  }, []);

  useEffect(() => {
    if (!context) return;
    let cancelled = false;
    (async () => {
      try {
        await load(context.id);
        if (!cancelled) setFailed(false);
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

  const retry = () => {
    setLoading(true);
    load(context!.id)
      .then(() => setFailed(false))
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  };

  const download = async (note: Note) => {
    try {
      const blob = await apiBlob(`/api/v1/notes/${note.id}/download`);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${note.title.replace(/[^\w -]/g, "").trim() || "note"}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not download the note.");
    }
  };

  const review = async (note: Note, outcome: "again" | "good") => {
    try {
      const updated = await api<Note>(`/api/v1/notes/${note.id}/review`, {
        method: "POST",
        body: JSON.stringify({ outcome }),
      });
      setNotes((list) => list.map((n) => (n.id === updated.id ? updated : n)));
      toast(outcome === "good" ? "Marked as known — review scheduled." : "Noted — we will revisit this soon.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not save the review.");
    }
  };

  const generate = async () => {
    if (!context) return;
    setBusy(true);
    try {
      const created = await api<Note>("/api/v1/notes/generate", {
        method: "POST",
        body: JSON.stringify({
          context_id: context.id,
          ...(sessionId ? { study_session_id: sessionId } : {}),
        }),
      });
      setNotes((list) => [created, ...list]);
      setGenOpen(false);
      setSessionId("");
      toast("Material generated.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not generate material.");
    } finally {
      setBusy(false);
    }
  };

  const addResource = async () => {
    if (!context || !resTitle.trim() || !resText.trim()) {
      toast("Please enter a title and some text.");
      return;
    }
    setBusy(true);
    try {
      await api<Resource>("/api/v1/resources/text", {
        method: "POST",
        body: JSON.stringify({ context_id: context.id, title: resTitle.trim(), text: resText.trim() }),
      });
      setResOpen(false);
      setResTitle("");
      setResText("");
      await load(context.id);
      toast("Resource added.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not add the resource.");
    } finally {
      setBusy(false);
    }
  };

  const removeResource = async (id: string) => {
    if (!context) return;
    try {
      await api(`/api/v1/resources/${id}`, { method: "DELETE" });
      setResources((list) => list.filter((r) => r.id !== id));
      toast("Resource deleted.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not delete the resource.");
    }
  };

  if (loading) {
    return <Loading label="Loading your materials" />;
  }
  if (failed) {
    return <ErrorState message="Could not load your materials." onRetry={retry} />;
  }

  return (
    <div>
      <div className="section-head">
        <div>
          <h1 className="pg-title">Materials Library</h1>
          <p className="pg-sub">Download the material you learned — generated from your chat sessions.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setGenOpen(true)}>
          <Icon name="plus" /> Add Material
        </button>
      </div>

      <div style={{ marginBottom: 8 }} className="nav-sec">Generated from your learning</div>
      {notes.length === 0 ? (
        <div className="empty-state">
          <Icon name="file" size={30} />
          <p style={{ margin: "10px 0 14px", fontSize: 14, color: "var(--text-1)" }}>
            No materials yet. Generate your first note from a chat session or your study material.
          </p>
          <button className="btn btn-primary" onClick={() => setGenOpen(true)} style={{ justifyContent: "center" }}>
            <Icon name="plus" /> Generate Notes
          </button>
        </div>
      ) : (
        notes.map((n) => (
          <div className="audio-card" key={n.id}>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div className="fsq-ic" style={{ width: 46, height: 46 }}><Icon name="file" size={21} /></div>
              <div>
                <b style={{ fontSize: 15 }}>{n.title}</b>
                <div style={{ fontSize: 12, color: "var(--text-3)" }}>Generated {fmtDate(n.created_at)}</div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              {n.state && <span className="type-tag">{n.state}</span>}
              {n.next_review_at && (
                <span style={{ fontSize: 11, color: "var(--text-3)" }}>Due {fmtDate(n.next_review_at)}</span>
              )}
              <button className="btn btn-ghost" style={{ padding: "5px 10px", fontSize: 12 }} onClick={() => review(n, "again")} aria-label={`Review again ${n.title}`}>
                Again
              </button>
              <button className="btn btn-ghost" style={{ padding: "5px 10px", fontSize: 12 }} onClick={() => review(n, "good")} aria-label={`Review good ${n.title}`}>
                Good
              </button>
              <button className="btn btn-primary" onClick={() => download(n)} aria-label={`Download ${n.title}`}>
                <Icon name="download" /> Download
              </button>
            </div>
          </div>
        ))
      )}

      <div style={{ margin: "26px 0 8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="nav-sec" style={{ marginBottom: 0 }}>Resources</span>
        <button className="btn btn-secondary" onClick={() => setResOpen(true)}>
          <Icon name="plus" /> Add Resource
        </button>
      </div>
      {resources.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-1)", margin: "6px 0 0" }}>
          No resources yet — add study material so ARIA can learn from it.
        </p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))", gap: 16 }}>
          {resources.map((r) => (
            <div className="resource-card" key={r.id}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div className="fsq-ic" style={{ width: 46, height: 46 }}><Icon name={r.resource_type === "PDF" ? "book" : "file"} size={21} /></div>
                <div>
                  <b style={{ fontSize: 15 }}>{r.title}</b>
                  <div style={{ fontSize: 11, color: "var(--text-3)" }}>{r.resource_type} · {r.chunk_count} chunks</div>
                </div>
                <span className="type-tag" style={{ marginLeft: "auto" }}>{r.processing_status}</span>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => setConfirm({ title: "Delete resource", body: `Delete "${r.title}"? Chunks and generated audio go with it.`, confirmLabel: "Delete resource", onConfirm: () => void removeResource(r.id) })} aria-label={`Delete ${r.title}`}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* generate-material modal */}
      <div className="modal-bg show" style={{ display: genOpen ? "flex" : "none" }}>
        <div className="modal">
          <div className="m-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: 14, marginBottom: 18 }}>
            <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}><Icon name="file" size={20} /> Create Material</h3>
            <button className="btn btn-ghost" style={{ padding: 6 }} onClick={() => setGenOpen(false)} aria-label="Close"><Icon name="x" size={16} /></button>
          </div>
          <div className="form-group">
            <label className="field-label" htmlFor="note-source">Source</label>
            <select id="note-source" className="input" value={sessionId} onChange={(e) => setSessionId(e.target.value)}>
              <option value="">Context study material</option>
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>Chat · {fmtDate(s.created_at)} ({s.mode})</option>
              ))}
            </select>
          </div>
          <div style={{ fontSize: 12, color: "var(--text-3)", margin: "0 0 8px" }}>
            Generates downloadable study notes via ARIA.
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, borderTop: "1px solid var(--border)", paddingTop: 18, marginTop: 16 }}>
            <button className="btn btn-ghost" onClick={() => setGenOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={generate} disabled={busy}>
              Create Material <Icon name="arrow" />
            </button>
          </div>
        </div>
      </div>

      {/* add-resource modal */}
      <div className="modal-bg show" style={{ display: resOpen ? "flex" : "none" }}>
        <div className="modal">
          <div className="m-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: 14, marginBottom: 18 }}>
            <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}><Icon name="folder" size={20} /> Add Resource</h3>
            <button className="btn btn-ghost" style={{ padding: 6 }} onClick={() => setResOpen(false)} aria-label="Close"><Icon name="x" size={16} /></button>
          </div>
          <div className="form-group">
            <label className="field-label" htmlFor="resource-title">Title</label>
            <input id="resource-title" className="input" value={resTitle} onChange={(e) => setResTitle(e.target.value)} placeholder="Python basics article" />
          </div>
          <div className="form-group">
            <label className="field-label" htmlFor="resource-text">Text</label>
            <textarea id="resource-text" className="input" rows={7} value={resText} onChange={(e) => setResText(e.target.value)} placeholder="Paste or type the study text…" />
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, borderTop: "1px solid var(--border)", paddingTop: 18, marginTop: 16 }}>
            <button className="btn btn-ghost" onClick={() => setResOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={addResource} disabled={busy}>
              Add Resource <Icon name="arrow" />
            </button>
          </div>
        </div>
      </div>
      <ConfirmDialog state={confirm} onClose={() => setConfirm(null)} />
    </div>
  );
}