"use client";

import { Modal } from "@/components/modal";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/icons";
import { api, apiBlob, apiUpload, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { toast } from "@/lib/toast";
import { ConfirmDialog, type ConfirmState } from "@/components/confirm";
import { ErrorState, Loading } from "@/components/states";
import { ResourceProcessing } from "@/components/resource-processing";
import { RequestStatus } from "@/components/request-status";
import { noteReviewLabel } from "@/lib/note-review-label";

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
  if (!context) return <Loading label="Loading your materials" />;
  return <ContextMaterials key={context.id} />;
}

function ContextMaterials() {
  const { context } = useActiveContext();
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState<Note[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [genOpen, setGenOpen] = useState(false);
  const [resOpen, setResOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [generationError, setGenerationError] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [resTitle, setResTitle] = useState("");
  const [resText, setResText] = useState("");
  const [resMode, setResMode] = useState<"file" | "text">("file");
  const [resFile, setResFile] = useState<File | null>(null);
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
      toast(e instanceof ApiError ? e.message : "Could not download the note.", "error");
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
      toast(e instanceof ApiError ? e.message : "Could not save the review.", "error");
    }
  };

  const generate = async () => {
    if (!context || busy) return;
    setBusy(true);
    setGenerationError("");
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
      toast("Learning notes saved.", "success");
    } catch (e) {
      setGenerationError(e instanceof ApiError ? e.message : "Could not generate your notes. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const addResource = async () => {
    if (!context || busy) return;
    setUploadError("");
    if (resMode === "file") {
      if (!resFile) {
        setUploadError("Choose a PDF or image to upload.");
        return;
      }
      const title = resTitle.trim() || resFile.name.replace(/\.[^/.]+$/, "");
      setBusy(true);
      try {
        const isPdf = resFile.name.toLowerCase().endsWith(".pdf") || resFile.type === "application/pdf";
        const endpoint = isPdf
          ? `/api/v1/resources/pdf?context_id=${context.id}&title=${encodeURIComponent(title)}`
          : `/api/v1/resources/image?context_id=${context.id}&title=${encodeURIComponent(title)}`;
        const mime = isPdf ? "application/pdf" : (resFile.type || "image/png");
        await apiUpload<Resource>(endpoint, resFile, mime);
        setResOpen(false);
        setResTitle("");
        setResFile(null);
        await load(context.id);
        toast("Resource uploaded and processed.");
      } catch (e) {
        setUploadError(e instanceof ApiError ? e.message : "Could not upload your material. Please try again.");
      } finally {
        setBusy(false);
      }
      return;
    }

    if (!resTitle.trim() || !resText.trim()) {
      setUploadError("Enter a title and the text you want to study.");
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
      setUploadError(e instanceof ApiError ? e.message : "Could not save your material. Please try again.");
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
      toast(e instanceof ApiError ? e.message : "Could not delete the resource.", "error");
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
          <h1 className="pg-title">Materials library</h1>
          <p className="pg-sub">Keep your sources and saved learning notes together.</p>
        </div>
        <div className="page-actions">
          <button className="btn btn-secondary" onClick={() => { setGenerationError(""); setGenOpen(true); }} title="Save notes from a conversation or your study material"><Icon name="sparkles" /> Generate notes</button>
          <button className="btn btn-primary" onClick={() => { setUploadError(""); setResOpen(true); }} title="Upload a PDF or image, or paste text"><Icon name="plus" /> Add material</button>
        </div>
      </div>

      <div style={{ marginBottom: 8 }} className="nav-sec">Generated from your learning</div>
      {notes.length === 0 ? (
        <div className="empty-state">
          <Icon name="file" size={30} />
          <p style={{ margin: "10px 0 14px", fontSize: 14, color: "var(--text-1)" }}>
            No saved notes yet. Generate your first note from a chat session or your study material.
          </p>
            <button className="btn btn-primary" onClick={() => { setGenerationError(""); setGenOpen(true); }} style={{ justifyContent: "center" }}>
            <Icon name="plus" /> Generate notes
          </button>
        </div>
      ) : (
        notes.map((n) => (
          <div className="audio-card" key={n.id}>
            <div className="card-header">
              <div className="fsq-ic" style={{ width: 46, height: 46 }}><Icon name="file" size={21} /></div>
              <div>
                <b style={{ fontSize: 15 }}>{n.title}</b>
                <div style={{ fontSize: 12, color: "var(--text-3)" }}>Generated {fmtDate(n.created_at)}</div>
              </div>
            </div>
            <div className="ui-row ui-gap-10 ui-wrap">
              {n.state && <span className="type-tag">{noteReviewLabel(n.state)}</span>}
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
        <button className="btn btn-secondary" onClick={() => { setUploadError(""); setResOpen(true); }}>
          <Icon name="plus" /> Add resource
        </button>
      </div>
      {resources.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-1)", margin: "6px 0 0" }}>
          No resources yet — add study material so ARIA can learn from it.
        </p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))", gap: 16 }}>
          {resources.map((r) => (
            <div className="resource-card motion-reveal" key={r.id}>
              <div className="ui-row ui-gap-12">
                <div className="fsq-ic" style={{ width: 46, height: 46 }}><Icon name={r.resource_type === "PDF" ? "book" : r.resource_type === "IMAGE" ? "image" : "file"} size={21} /></div>
                <div>
                  <b style={{ fontSize: 15 }}>{r.title}</b>
                  <div style={{ fontSize: 11, color: "var(--text-3)" }}>{r.resource_type === "TEXT" ? "Text" : r.resource_type === "IMAGE" ? "Image" : r.resource_type}</div>
                </div>
                <span className="type-tag" style={{ marginLeft: "auto" }}>{r.processing_status === "READY" ? "Ready" : r.processing_status === "FAILED" ? "Needs attention" : "Processing"}</span>
              </div>
              {r.processing_status === "READY" && <Link href="/app/map" className="text-link">Explore connected concepts <Icon name="arrow" size={15} /></Link>}
              {r.error_detail && <p style={{ fontSize: 12, color: "var(--danger-strong)" }}>{r.error_detail}</p>}
              <div className="ui-flex ui-gap-8">
                <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => setConfirm({ title: "Delete resource", body: `Delete "${r.title}"? Chunks and generated audio go with it.`, confirmLabel: "Delete resource", onConfirm: () => void removeResource(r.id) })} aria-label={`Delete ${r.title}`}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* generate-material modal */}
      <Modal open={genOpen} title="Generate notes" onClose={() => { setGenerationError(""); setGenOpen(false); }}>
        <div className="modal">
          <div className="m-head dialog-heading">
            <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}><Icon name="file" size={20} /> Generate notes</h3>
            <button className="btn btn-ghost" style={{ padding: 6 }} onClick={() => setGenOpen(false)} aria-label="Close"><Icon name="x" size={16} /></button>
          </div>
          <div className="form-group">
            <label className="field-label" htmlFor="note-source">Source</label>
            <select id="note-source" className="input" value={sessionId} onChange={(e) => setSessionId(e.target.value)}>
              <option value="">Context study material</option>
              {sessions.map((s) => (
                  <option key={s.id} value={s.id}>Conversation · {fmtDate(s.created_at)}</option>
              ))}
            </select>
          </div>
          <div style={{ fontSize: 12, color: "var(--text-3)", margin: "0 0 8px" }}>
            Save a summary from your conversation or study material. Uploaded notes are optional when you choose a conversation.
          </div>
          {generationError && <div className="inline-error" role="alert"><b>Notes could not be saved</b><p>{generationError}</p></div>}
          {busy && <RequestStatus label="Preparing your learning notes…" />}
          <div className="dialog-actions ui-mt-16">
            <button className="btn btn-ghost" onClick={() => setGenOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={generate} disabled={busy}>
              {busy ? "Preparing…" : "Generate notes"} <Icon name="arrow" />
            </button>
          </div>
        </div>
      </Modal>

      {/* add-resource modal */}
      <Modal open={resOpen} title="Add resource" onClose={() => { setResOpen(false); setResFile(null); }}>
        <div className="modal">
          <div className="m-head dialog-heading">
            <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}><Icon name="folder" size={20} /> Add resource</h3>
            <button className="btn btn-ghost" style={{ padding: 6 }} onClick={() => setResOpen(false)} aria-label="Close"><Icon name="x" size={16} /></button>
          </div>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <button
              type="button"
              className={`btn ${resMode === "file" ? "btn-primary" : "btn-ghost"}`}
              style={{ flex: 1, justifyContent: "center", fontSize: 13, padding: "8px 12px" }}
              onClick={() => setResMode("file")}
            >
              <Icon name="image" size={15} /> Upload file (PDF / Image OCR)
            </button>
            <button
              type="button"
              className={`btn ${resMode === "text" ? "btn-primary" : "btn-ghost"}`}
              style={{ flex: 1, justifyContent: "center", fontSize: 13, padding: "8px 12px" }}
              onClick={() => setResMode("text")}
            >
              <Icon name="file" size={15} /> Paste text
            </button>
          </div>
          <div className="form-group">
            <label className="field-label" htmlFor="resource-title">Title</label>
            <input id="resource-title" className="input" value={resTitle} onChange={(e) => setResTitle(e.target.value)} placeholder="e.g. Lecture 4 Notes, Textbook scan, Architecture diagram" />
          </div>
          {resMode === "file" ? (
            <div className="form-group">
              <label className="field-label" htmlFor="resource-file">File (PDF, PNG, JPG, WEBP)</label>
              <input
                id="resource-file"
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp"
                className="input"
                style={{ padding: "8px" }}
                onChange={(e) => {
                  const f = e.target.files?.[0] ?? null;
                  setResFile(f);
                  if (f && !resTitle) {
                    setResTitle(f.name.replace(/\.[^/.]+$/, ""));
                  }
                }}
              />
              <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 6 }}>
                Scanned PDFs and photo/whiteboard images are transcribed automatically using OCR. Max 10 MB.
              </div>
            </div>
          ) : (
            <div className="form-group">
              <label className="field-label" htmlFor="resource-text">Text</label>
              <textarea id="resource-text" className="input" rows={7} value={resText} onChange={(e) => setResText(e.target.value)} placeholder="Paste or type the study text…" />
            </div>
          )}
          {resOpen && busy && <ResourceProcessing kind={resMode} />}
          {uploadError && <div className="inline-error" role="alert"><b>Material needs attention</b><p>{uploadError}</p></div>}
          <div className="dialog-actions ui-mt-16">
            <button className="btn btn-ghost" disabled={busy} onClick={() => { setResOpen(false); setResFile(null); }}>Cancel</button>
            <button className="btn btn-primary" onClick={addResource} disabled={busy}>
              {busy ? "Processing material…" : "Add resource"} <Icon name="arrow" />
            </button>
          </div>
        </div>
      </Modal>
      <ConfirmDialog state={confirm} onClose={() => setConfirm(null)} />
    </div>
  );
}
