"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { api, apiBlob } from "../../../lib/api";
import { useActiveContext } from "../../../components/use-active-context";

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

export default function NotesPage() {
  const { context, loading } = useActiveContext();
  const [notes, setNotes] = useState<Note[]>([]);
  const [due, setDue] = useState<Note[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [newBody, setNewBody] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editBody, setEditBody] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    if (!context) return;
    const [noteList, dueList] = await Promise.all([
      api<Note[]>(`/api/v1/notes?context_id=${context.id}`),
      api<Note[]>(`/api/v1/notes/due?context_id=${context.id}`),
    ]);
    setNotes(noteList);
    setDue(dueList);
  }

  useEffect(() => {
    if (!context) return;
    load().catch((requestError: unknown) =>
      setError(requestError instanceof Error ? requestError.message : "Unable to load notes")
    );
  }, [context]);

  if (loading) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <p className="text-body-md text-on-surface-variant">Loading notes…</p>
      </div>
    );
  }

  if (!context) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <div className="bg-surface shadow-extruded rounded-3xl p-8 max-w-xl">
          <h2 className="text-headline-md text-on-surface mb-4">No learning context yet</h2>
          <p className="text-body-md text-on-surface-variant mb-6">Set up your context before taking notes.</p>
          <Link href="/onboarding" className="inline-flex items-center gap-2 px-8 py-4 rounded-xl shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
            Initialize learning journey
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </Link>
        </div>
      </div>
    );
  }

  const activeContext = context;

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/v1/notes", {
        method: "POST",
        body: JSON.stringify({ context_id: activeContext.id, title: newTitle, body: newBody }),
      });
      setNewTitle("");
      setNewBody("");
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to create note");
    }
  }

  async function generate() {
    setGenerating(true);
    setError("");
    try {
      await api("/api/v1/notes/generate", {
        method: "POST",
        body: JSON.stringify({ context_id: activeContext.id }),
      });
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to generate note");
    } finally {
      setGenerating(false);
    }
  }

  async function saveEdit(noteId: string) {
    setError("");
    try {
      await api(`/api/v1/notes/${noteId}`, {
        method: "PUT",
        body: JSON.stringify({ title: editTitle, body: editBody }),
      });
      setEditingId(null);
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save note");
    }
  }

  async function remove(noteId: string) {
    setError("");
    try {
      await api(`/api/v1/notes/${noteId}`, { method: "DELETE" });
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to delete note");
    }
  }

  async function review(noteId: string, outcome: "again" | "good") {
    setError("");
    try {
      await api(`/api/v1/notes/${noteId}/review`, {
        method: "POST",
        body: JSON.stringify({ outcome }),
      });
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to record review");
    }
  }

  async function download(noteId: string, title: string) {
    setError("");
    try {
      const blob = await apiBlob(`/api/v1/notes/${noteId}/download`);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${title}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to download note");
    }
  }

  function startEdit(note: Note) {
    setEditingId(note.id);
    setEditTitle(note.title);
    setEditBody(note.body);
  }

  return (
    <div className="p-container-padding md:p-section-margin w-full max-w-5xl mx-auto flex flex-col gap-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-headline-xl text-on-background">Notes</h2>
          <p className="text-body-lg text-on-surface-variant mt-2">{activeContext.title}</p>
        </div>
        <button
          onClick={() => void generate()}
          disabled={generating}
          className="self-start px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary disabled:opacity-60"
        >
          {generating ? "Generating…" : "Generate from study material"}
        </button>
      </div>

      {/* Revision queue */}
      {due.length > 0 && (
        <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-4">
          <h3 className="text-headline-md text-on-surface">Due for review</h3>
          <ul className="flex flex-col gap-3">
            {due.map((note) => (
              <li key={note.id} className="bg-surface shadow-injected rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-body-md text-on-background font-semibold">{note.title}</p>
                  <p className="text-label-md text-on-surface-variant mt-1">
                    {note.interval_days} day interval · last: {note.last_outcome ?? "new"}
                  </p>
                </div>
                <div className="flex gap-3">
                  <button onClick={() => void review(note.id, "again")} className="px-5 py-2 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-error">
                    Again
                  </button>
                  <button onClick={() => void review(note.id, "good")} className="px-5 py-2 rounded-full bg-secondary text-on-secondary text-label-md font-bold shadow-extruded btn-extruded">
                    Good
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Create */}
      <form onSubmit={create} className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-4">
        <h3 className="text-headline-md text-on-surface">New note</h3>
        <input
          required
          className="h-12 bg-surface-container rounded-xl input-injected px-4 text-on-surface placeholder:text-outline-variant"
          placeholder="Title"
          value={newTitle}
          onChange={(event) => setNewTitle(event.target.value)}
        />
        <textarea
          required
          rows={5}
          className="bg-surface-container rounded-xl input-injected p-4 text-on-surface placeholder:text-outline-variant resize-none"
          placeholder="Write your note…"
          value={newBody}
          onChange={(event) => setNewBody(event.target.value)}
        />
        <button className="self-start px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
          Save note
        </button>
      </form>

      {/* Notes list */}
      {notes.length === 0 ? (
        <div className="bg-surface shadow-extruded rounded-3xl p-8 text-center">
          <p className="text-body-md text-on-surface-variant">
            No notes yet. Write one or generate notes from your study material.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {notes.map((note) => (
            <div key={note.id} className="bg-surface shadow-extruded rounded-3xl p-8">
              {editingId === note.id ? (
                <div className="flex flex-col gap-4">
                  <input
                    className="h-12 bg-surface-container rounded-xl input-injected px-4 text-on-surface"
                    value={editTitle}
                    onChange={(event) => setEditTitle(event.target.value)}
                  />
                  <textarea
                    rows={6}
                    className="bg-surface-container rounded-xl input-injected p-4 text-on-surface resize-none"
                    value={editBody}
                    onChange={(event) => setEditBody(event.target.value)}
                  />
                  <div className="flex gap-3">
                    <button onClick={() => void saveEdit(note.id)} className="px-5 py-2 rounded-full bg-secondary text-on-secondary text-label-md font-bold shadow-extruded btn-extruded">
                      Save
                    </button>
                    <button onClick={() => setEditingId(null)} className="px-5 py-2 rounded-full text-label-md text-on-surface-variant">
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <h3 className="text-headline-md text-on-surface">{note.title}</h3>
                    <span className="text-label-sm text-on-surface-variant">
                      {note.state ?? "NEW"} · every {note.interval_days ?? 1}d
                    </span>
                  </div>
                  <p className="text-body-md text-on-surface-variant whitespace-pre-wrap mt-3">{note.body}</p>
                  <div className="flex flex-wrap gap-3 mt-5">
                    <button onClick={() => void download(note.id, note.title)} className="px-5 py-2 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary flex items-center gap-2">
                      <span className="material-symbols-outlined text-[16px]">download</span>
                      Download PDF
                    </button>
                    <button onClick={() => startEdit(note)} className="px-5 py-2 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-on-surface-variant">
                      Edit
                    </button>
                    <button onClick={() => void remove(note.id)} className="px-5 py-2 rounded-full text-label-md text-error">
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {error && <p className="text-label-md text-error" role="alert">{error}</p>}
    </div>
  );
}
