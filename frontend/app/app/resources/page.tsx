"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { api, apiBinary } from "../../../lib/api";
import { AudioPlayer } from "../../../components/audio-player";
import { useActiveContext } from "../../../components/use-active-context";

type AudioMeta = { id: string; status: string; error_detail: string | null };

type Resource = {
  id: string;
  context_id: string;
  title: string;
  resource_type: string;
  processing_status: string;
  error_detail: string | null;
  chunk_count: number;
  created_at: string;
};

function statusChip(status: string): { label: string; cls: string; pulse?: boolean } {
  switch (status) {
    case "READY":
      return { label: "Ready", cls: "bg-tertiary-container text-on-tertiary-container" };
    case "PROCESSING":
      return { label: "Processing", cls: "bg-surface-variant text-on-surface-variant", pulse: true };
    case "FAILED":
    case "UNSUPPORTED":
      return { label: status === "FAILED" ? "Failed" : "Unsupported", cls: "bg-error-container text-on-error-container" };
    default:
      return { label: status, cls: "bg-surface-variant text-on-surface-variant" };
  }
}

export default function ResourcesPage() {
  const { context, loading } = useActiveContext();
  const [resources, setResources] = useState<Resource[]>([]);
  const [loadingResources, setLoadingResources] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [replaceId, setReplaceId] = useState<string | null>(null);
  const [replaceTitle, setReplaceTitle] = useState("");
  const [replaceText, setReplaceText] = useState("");
  const [studyResourceId, setStudyResourceId] = useState<string | null>(null);
  const [audio, setAudio] = useState<Record<string, AudioMeta>>({});
  const [error, setError] = useState("");

  useEffect(() => {
    if (!context) return;
    setStudyResourceId(localStorage.getItem(`aria_study_resource_${context.id}`));
    api<Resource[]>(`/api/v1/resources?context_id=${context.id}`)
      .then(setResources)
      .catch((requestError: unknown) =>
        setError(requestError instanceof Error ? requestError.message : "Unable to load resources")
      )
      .finally(() => setLoadingResources(false));
  }, [context]);

  if (loading || loadingResources) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <p className="text-body-md text-on-surface-variant">Loading resources…</p>
      </div>
    );
  }

  if (!context) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <div className="bg-surface shadow-extruded rounded-3xl p-8 max-w-xl">
          <h2 className="text-headline-md text-on-surface mb-4">No learning context yet</h2>
          <p className="text-body-md text-on-surface-variant mb-6">
            Set up your learning context first, then add study material.
          </p>
          <Link href="/onboarding" className="inline-flex items-center gap-2 px-8 py-4 rounded-xl shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
            Initialize learning journey
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </Link>
        </div>
      </div>
    );
  }

  const activeContext = context;

  async function addText(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/v1/resources/text", {
        method: "POST",
        body: JSON.stringify({ context_id: activeContext.id, title, text }),
      });
      setTitle("");
      setText("");
      setShowAdd(false);
      const list = await api<Resource[]>(`/api/v1/resources?context_id=${activeContext.id}`);
      setResources(list);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to add resource");
    }
  }

  async function uploadPdf(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !context) return;
    setError("");
    try {
      await apiBinary(
        `/api/v1/resources/pdf?context_id=${activeContext.id}&title=${encodeURIComponent(file.name || "Uploaded PDF")}`,
        "POST",
        file,
        file.type || "application/pdf",
      );
      event.target.value = "";
      setShowAdd(false);
      const list = await api<Resource[]>(`/api/v1/resources?context_id=${activeContext.id}`);
      setResources(list);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to upload PDF");
    }
  }

  async function generateAudio(id: string) {
    setError("");
    try {
      const artifact = await api<AudioMeta>(`/api/v1/audio/resources/${id}/generate`, {
        method: "POST",
      });
      setAudio((items) => ({ ...items, [id]: artifact }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to generate audio");
    }
  }

  async function retry(id: string) {
    setError("");
    try {
      await api(`/api/v1/resources/${id}/process`, { method: "POST" });
      const list = await api<Resource[]>(`/api/v1/resources?context_id=${activeContext.id}`);
      setResources(list);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to retry");
    }
  }

  async function remove(id: string) {
    setError("");
    try {
      await api(`/api/v1/resources/${id}`, { method: "DELETE" });
      if (studyResourceId === id) setStudyResourceId(null);
      const list = await api<Resource[]>(`/api/v1/resources?context_id=${activeContext.id}`);
      setResources(list);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to delete resource");
    }
  }

  function selectForStudy(id: string) {
    const next = studyResourceId === id ? null : id;
    setStudyResourceId(next);
    localStorage.setItem(`aria_study_resource_${activeContext.id}`, next ?? "");
  }

  async function submitReplace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!replaceId) return;
    setError("");
    try {
      await api(`/api/v1/resources/${replaceId}/text`, {
        method: "PUT",
        body: JSON.stringify({ title: replaceTitle, text: replaceText }),
      });
      setReplaceId(null);
      const list = await api<Resource[]>(`/api/v1/resources?context_id=${activeContext.id}`);
      setResources(list);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to replace resource");
    }
  }

  async function replacePdf(id: string, event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    try {
      await apiBinary(
        `/api/v1/resources/${id}/pdf?title=${encodeURIComponent(replaceTitle || "Uploaded PDF")}`,
        "PUT",
        file,
        file.type || "application/pdf",
      );
      event.target.value = "";
      setReplaceId(null);
      const list = await api<Resource[]>(`/api/v1/resources?context_id=${activeContext.id}`);
      setResources(list);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to replace PDF");
    }
  }

  return (
    <div className="p-container-padding md:p-section-margin w-full max-w-5xl mx-auto flex flex-col gap-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-headline-xl text-on-background">Resources</h2>
          <p className="text-body-lg text-on-surface-variant mt-2">
            {context.title} · {resources.filter((r) => r.processing_status === "READY").length} ready
          </p>
        </div>
        <button
          onClick={() => setShowAdd((value) => !value)}
          className="px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary flex items-center gap-2"
        >
          <span className="material-symbols-outlined">add</span>
          {showAdd ? "Close" : "Add material"}
        </button>
      </div>

      {showAdd && (
        <div className="bg-surface shadow-extruded rounded-3xl p-8 grid grid-cols-1 md:grid-cols-2 gap-8">
          <form onSubmit={addText} className="flex flex-col gap-4">
            <h3 className="text-headline-md text-on-surface">Paste text</h3>
            <label className="flex flex-col gap-2">
              <span className="text-label-md text-on-surface-variant">Title</span>
              <input
                required
                className="h-12 bg-surface-container rounded-xl input-injected px-4 text-on-surface placeholder:text-outline-variant"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="e.g. Lecture 3 — Two-phase locking"
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="text-label-md text-on-surface-variant">Study text</span>
              <textarea
                required
                rows={6}
                className="bg-surface-container rounded-xl input-injected p-4 text-on-surface placeholder:text-outline-variant resize-none"
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="Paste the material you want ARIA to study from."
              />
            </label>
            <button className="self-start px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
              Add material
            </button>
          </form>
          <div className="flex flex-col gap-4">
            <h3 className="text-headline-md text-on-surface">Upload PDF</h3>
            <label className="flex-1 bg-surface-container-low rounded-2xl shadow-injected p-6 flex flex-col items-center justify-center gap-3 text-center cursor-pointer">
              <span className="material-symbols-outlined text-4xl text-secondary">upload_file</span>
              <span className="text-body-md text-on-surface-variant">Drop PDF here or choose a file</span>
              <span className="px-5 py-2 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
                Choose PDF
              </span>
              <input className="hidden" type="file" accept="application/pdf" onChange={(event) => void uploadPdf(event)} />
            </label>
            <p className="text-label-sm text-on-surface-variant">Supported type: PDF</p>
          </div>
        </div>
      )}

      {resources.length === 0 ? (
        <div className="bg-surface shadow-extruded rounded-3xl p-8 text-center">
          <p className="text-headline-md text-on-surface mb-2">No resources yet</p>
          <p className="text-body-md text-on-surface-variant">Add study material so ARIA can ground Study responses.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {resources.map((resource) => {
            const chip = statusChip(resource.processing_status);
            const selected = studyResourceId === resource.id;
            return (
              <div key={resource.id} className="bg-surface shadow-extruded rounded-3xl p-8">
                <div className="flex flex-col md:flex-row md:items-center gap-4 justify-between">
                  <div>
                    <div className="flex items-center gap-3 flex-wrap">
                      <h3 className="text-headline-md text-on-surface">{resource.title}</h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold shadow-extruded flex items-center gap-1 ${chip.cls}`}>
                        {chip.pulse && <span className="w-2 h-2 rounded-full bg-secondary shadow-extruded animate-pulse"></span>}
                        {chip.label}
                      </span>
                    </div>
                    <p className="text-label-md text-on-surface-variant mt-1">
                      {resource.resource_type === "PDF" ? "PDF" : "Pasted text"} · {resource.chunk_count} chunk{resource.chunk_count === 1 ? "" : "s"} · added {new Date(resource.created_at).toLocaleDateString()}
                    </p>
                    {resource.error_detail && (
                      <p className="text-label-md text-error mt-1">{resource.error_detail}</p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-3">
                    {resource.processing_status === "READY" && (
                      <button
                        onClick={() => selectForStudy(resource.id)}
                        className={`px-5 py-2 rounded-full text-label-md transition-all ${selected ? "bg-secondary text-on-secondary shadow-injected" : "bg-surface text-secondary shadow-extruded btn-extruded"}`}
                      >
                        {selected ? "Selected for Study" : "Use in Study"}
                      </button>
                    )}
                    {resource.processing_status === "READY" && (
                      <button
                        onClick={() => void generateAudio(resource.id)}
                        disabled={audio[resource.id]?.status === "READY"}
                        className="px-5 py-2 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary flex items-center gap-2 disabled:opacity-60"
                      >
                        <span className="material-symbols-outlined text-[16px]">graphic_eq</span>
                        {audio[resource.id]?.status === "READY" ? "Audio ready" : "Convert to audio"}
                      </button>
                    )}
                    {resource.processing_status === "FAILED" && (
                      <button onClick={() => void retry(resource.id)} className="px-5 py-2 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
                        Try processing again
                      </button>
                    )}
                    {resource.processing_status === "READY" && (
                      <button onClick={() => setReplaceId(replaceId === resource.id ? null : resource.id)} className="px-5 py-2 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-on-surface-variant">
                        Replace
                      </button>
                    )}
                    <button onClick={() => void remove(resource.id)} className="px-5 py-2 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-error">
                      Remove
                    </button>
                  </div>
                </div>
                {audio[resource.id]?.status === "READY" && (
                  <div className="mt-5">
                    <AudioPlayer artifactId={audio[resource.id].id} />
                  </div>
                )}
                {audio[resource.id]?.status === "FAILED" && (
                  <p className="text-label-md text-error mt-3" role="alert">
                    {audio[resource.id].error_detail ?? "Audio generation failed."}{" "}
                    <button onClick={() => void generateAudio(resource.id)} className="underline">Retry</button>
                  </p>
                )}
                {replaceId === resource.id && resource.resource_type === "TEXT" && (
                  <form onSubmit={submitReplace} className="mt-6 bg-surface-container-low rounded-2xl shadow-injected p-6 flex flex-col gap-4">
                    <label className="flex flex-col gap-2">
                      <span className="text-label-md text-on-surface-variant">Title</span>
                      <input className="h-12 bg-surface rounded-xl input-injected px-4 text-on-surface" value={replaceTitle} onChange={(event) => setReplaceTitle(event.target.value)} />
                    </label>
                    <label className="flex flex-col gap-2">
                      <span className="text-label-md text-on-surface-variant">New text</span>
                      <textarea rows={4} className="bg-surface rounded-xl input-injected p-4 text-on-surface resize-none" value={replaceText} onChange={(event) => setReplaceText(event.target.value)} />
                    </label>
                    <div className="flex gap-3">
                      <button type="submit" className="px-5 py-2 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary">Save replacement</button>
                      <button type="button" onClick={() => setReplaceId(null)} className="px-5 py-2 rounded-full text-label-md text-on-surface-variant">Cancel</button>
                    </div>
                  </form>
                )}
                {replaceId === resource.id && resource.resource_type === "PDF" && (
                  <div className="mt-6 bg-surface-container-low rounded-2xl shadow-injected p-6 flex flex-col gap-3">
                    <label className="text-label-md text-on-surface-variant">Replace with PDF</label>
                    <input className="text-label-md text-on-surface" type="file" accept="application/pdf" onChange={(event) => void replacePdf(resource.id, event)} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {error && <p className="text-label-md text-error" role="alert">{error}</p>}
    </div>
  );
}
