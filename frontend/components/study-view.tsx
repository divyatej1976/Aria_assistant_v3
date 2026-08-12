"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";

import { api } from "../lib/api";

type SessionRecord = { id: string; context_id: string; mode: string; status: string; created_at: string };
type Source = { resource_id: string; chunk_id: string; title: string; score: number };
type Message = { role: "user" | "assistant"; content: string; sources: Source[] };
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
type Chunk = { chunk_index: number; content: string };
type Decision = { concept_id: string | null; decision_type: string; reason: string };
type ConceptState = { concept_id: string; concept_name: string; state: string; confidence: number; reason: string };

export function StudyView({ contextId, contextTitle }: { contextId: string; contextTitle: string }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [resources, setResources] = useState<Resource[]>([]);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [states, setStates] = useState<ConceptState[]>([]);
  const [error, setError] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [resourceList, adaptation] = await Promise.all([
          api<Resource[]>(`/api/v1/resources?context_id=${contextId}`),
          api<{ states: ConceptState[]; decisions: Decision[] }>(`/api/v1/contexts/${contextId}/adaptation`),
        ]);
        if (!active) return;
        setResources(resourceList);
        setDecisions(adaptation.decisions);
        setStates(adaptation.states);
        const selectedId = localStorage.getItem(`aria_study_resource_${contextId}`);
        const selected =
          resourceList.find((resource) => resource.id === selectedId && resource.processing_status === "READY") ||
          resourceList.find((resource) => resource.processing_status === "READY") ||
          null;
        setSelectedResource(selected);
        if (selected) {
          const chunkList = await api<Chunk[]>(`/api/v1/resources/${selected.id}/chunks`);
          if (active) setChunks(chunkList);
        }
        const sessions = await api<SessionRecord[]>(`/api/v1/study/sessions?context_id=${contextId}`);
        let session = sessions[sessions.length - 1];
        if (!session) {
          session = await api<SessionRecord>("/api/v1/study/sessions", {
            method: "POST",
            body: JSON.stringify({ context_id: contextId }),
          });
        }
        if (!active) return;
        setSessionId(session.id);
        const history = await api<Message[]>(`/api/v1/study/sessions/${session.id}/messages`);
        if (active) setMessages(history);
      } catch (requestError) {
        if (active) setError(requestError instanceof Error ? requestError.message : "Unable to start Study");
      }
    })();
    return () => {
      active = false;
    };
  }, [contextId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sessionId || !input.trim()) return;
    setSending(true);
    setError("");
    try {
      setMessages((items) => [...items, { role: "user", content: input, sources: [] }]);
      setInput("");
      await api(`/api/v1/study/sessions/${sessionId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content: input }),
      });
      const history = await api<Message[]>(`/api/v1/study/sessions/${sessionId}/messages`);
      setMessages(history);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to send message");
    } finally {
      setSending(false);
    }
  }

  const weakConcept = states.find((state) => state.state === "NEEDS_REVIEW" || state.state === "DEVELOPING");
  const focus = decisions.filter((d) => d.decision_type === "FOCUS_STUDY");
  const currentConcept = weakConcept?.concept_name ?? contextTitle;

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:gap-0 lg:h-[calc(100vh-7rem)] lg:overflow-hidden">
      {/* Left pane: source material + analysis */}
      <div className="flex-1 flex flex-col overflow-y-auto p-container-padding gap-6">
        <header className="bg-surface p-container-padding rounded-3xl shadow-extruded flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <p className="text-label-md text-secondary tracking-widest uppercase mb-1">Current Concept</p>
            <h2 className="text-headline-lg text-on-surface">{currentConcept}</h2>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-label-sm text-on-surface-variant">{contextTitle}</span>
          </div>
        </header>

        <section className="bg-surface rounded-3xl p-container-padding shadow-extruded flex flex-col gap-4">
          <div className="flex items-center gap-3 border-b border-surface-dim pb-4">
            <span className="material-symbols-outlined text-tertiary p-2 rounded-lg shadow-injected">menu_book</span>
            <h3 className="text-headline-md text-on-surface">Source Material</h3>
            {selectedResource && (
              <span className="ml-auto text-label-sm text-on-surface-variant bg-surface-container-highest px-3 py-1 rounded-full shadow-injected">
                {selectedResource.title}
              </span>
            )}
          </div>
          {selectedResource && chunks.length > 0 ? (
            <div className="relative bg-surface-container-low rounded-xl p-6 shadow-injected text-body-lg text-on-surface-variant leading-relaxed">
              <p>{chunks[0].content}</p>
              <div className="mt-4 flex gap-2">
                <span className="text-label-sm text-secondary bg-surface px-3 py-1 rounded-full shadow-extruded">Excerpt</span>
                <span className="text-label-sm text-secondary bg-surface px-3 py-1 rounded-full shadow-extruded">{chunks.length} chunk{chunks.length === 1 ? "" : "s"} loaded</span>
              </div>
            </div>
          ) : (
            <p className="text-body-md text-on-surface-variant">
              {selectedResource
                ? "Material is ready but no readable text was found."
                : "No material selected. Pick a Ready resource in Resources to ground Study."}
              {!selectedResource && (
                <Link href="/app/resources" className="block mt-3 text-label-md text-secondary underline">Open Resources</Link>
              )}
            </p>
          )}
        </section>

        <section className="bg-surface rounded-3xl p-container-padding shadow-extruded flex flex-col gap-4 flex-grow">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-secondary">edit_note</span>
            <h3 className="text-headline-md text-on-surface">Your Analysis</h3>
          </div>
          <p className="text-body-md text-on-surface-variant">
            Ask ARIA anything about {selectedResource ? `"${selectedResource.title}"` : "your material"}.
          </p>
        </section>
      </div>

      {/* Right pane: ARIA Guide chat */}
      <aside className="w-full max-h-[70vh] lg:max-h-none lg:h-auto lg:w-[450px] bg-surface flex flex-col border-t lg:border-l lg:border-t-0 border-surface-dim/30 shadow-[-12px_0_24px_rgba(209,217,230,0.5)]">
        <div className="p-container-padding flex items-center gap-4 border-b border-surface-dim/50 bg-surface">
          <div className="w-14 h-14 rounded-full shadow-extruded flex items-center justify-center bg-surface relative">
            <div className="absolute inset-0 rounded-full bg-secondary opacity-20 blur-md"></div>
            <span className="material-symbols-outlined text-secondary text-3xl relative z-10 ms-fill">smart_toy</span>
          </div>
          <div>
            <h2 className="text-headline-md text-on-surface">ARIA Guide</h2>
            <p className="text-label-sm text-tertiary flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span> Active Session
            </p>
          </div>
        </div>

        <div className="flex-grow overflow-y-auto p-container-padding flex flex-col gap-6" ref={scrollRef}>
          {focus.length > 0 && (
            <div className="p-5 rounded-2xl bg-secondary/5 border border-secondary/20 shadow-extruded flex flex-col gap-3">
              <div className="flex items-start gap-3">
                <span className="material-symbols-outlined text-secondary bg-surface p-2 rounded-full shadow-extruded">lightbulb</span>
                <p className="text-body-md text-on-surface">{focus[0].reason}</p>
              </div>
            </div>
          )}
          {messages.length === 0 ? (
            <p className="text-body-md text-on-surface-variant text-center mt-8">
              What would you like to understand?
            </p>
          ) : (
            messages.map((message, index) =>
              message.role === "assistant" ? (
                <div key={index} className="flex flex-col gap-2">
                  <div className="flex items-end gap-2 mb-1">
                    <span className="text-label-sm text-secondary">ARIA</span>
                  </div>
                  <div className="bg-surface rounded-2xl rounded-tl-sm p-4 shadow-extruded">
                    <p className="text-body-md text-on-surface whitespace-pre-wrap">{message.content}</p>
                  </div>
                  {message.sources.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {message.sources.map((source, sourceIndex) => (
                        <span key={sourceIndex} className="text-label-sm text-on-surface-variant bg-surface-container-low px-3 py-1 rounded-full shadow-injected">
                          {source.title} · {(source.score * 100).toFixed(0)}%
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div key={index} className="flex flex-col gap-2 items-end">
                  <div className="bg-surface-variant rounded-2xl rounded-tr-sm p-4 shadow-injected max-w-[85%]">
                    <p className="text-body-md text-on-surface whitespace-pre-wrap">{message.content}</p>
                  </div>
                </div>
              ),
            )
          )}
          {error && <p className="text-label-md text-error" role="alert">{error}</p>}
        </div>

        <div className="p-container-padding bg-surface border-t border-surface-dim/50 shadow-[0_-8px_16px_rgba(209,217,230,0.3)]">
          <form onSubmit={send} className="relative flex items-center">
            <input
              className="w-full py-4 pl-5 pr-14 rounded-full input-injected text-body-md text-on-surface placeholder:text-on-surface-variant"
              placeholder="Ask a question..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              aria-label="Send"
              className="absolute right-2 w-10 h-10 rounded-full flex items-center justify-center text-secondary btn-extruded bg-surface disabled:opacity-50"
            >
              <span className="material-symbols-outlined ms-fill">arrow_upward</span>
            </button>
          </form>
        </div>
      </aside>
    </div>
  );
}
