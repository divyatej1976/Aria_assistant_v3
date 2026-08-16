"use client";

import { FormEvent, useEffect, useState } from "react";

import { api } from "../../../lib/api";
import { useActiveContext } from "../../../components/use-active-context";
import { formatDateTime } from "../../../lib/format";

type Preference = { key: string; value: string };
type MemorySummary = {
  preferences: Preference[];
  concepts: number;
  weak_concepts: number;
  supported_concepts: number;
  evidence_count: number;
  message_count: number;
};
type ConceptState = {
  concept_id: string;
  concept_name: string;
  state: string;
  confidence: number;
  reason: string;
};
type EvidenceRecord = {
  id: string;
  concept_id: string;
  concept_name: string;
  signal: string;
  valid: boolean;
  created_at: string;
};
type SessionRecord = { id: string; context_id: string; mode: string; status: string; created_at: string };
type Source = { resource_id: string; chunk_id: string; title: string; score: number };
type Message = { id: string; role: string; content: string; sources: Source[] };

const SUGGESTED_KEYS = [
  { key: "difficulty", placeholder: "easy / medium / hard" },
  { key: "study_length", placeholder: "e.g. 25m" },
  { key: "review_interval", placeholder: "days, e.g. 3" },
  { key: "focus_goal", placeholder: "e.g. exams" },
  { key: "notification", placeholder: "on / off" },
];

function stateChip(state: string): { label: string; cls: string } {
  switch (state) {
    case "SUPPORTED":
      return { label: "Strong", cls: "bg-tertiary-container text-on-tertiary-container" };
    case "NEEDS_REVIEW":
      return { label: "Needs review", cls: "bg-error-container text-on-error-container" };
    case "DEVELOPING":
      return { label: "Learning", cls: "bg-surface-variant text-on-surface-variant" };
    default:
      return { label: "Not enough evidence", cls: "bg-surface-variant text-on-surface-variant/70" };
  }
}

export default function MemoryPage() {
  const { context, loading } = useActiveContext();
  const [summary, setSummary] = useState<MemorySummary | null>(null);
  const [states, setStates] = useState<ConceptState[]>([]);
  const [evidence, setEvidence] = useState<EvidenceRecord[]>([]);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [messagesBySession, setMessagesBySession] = useState<Record<string, Message[]>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [error, setError] = useState("");

  async function loadSummary() {
    const [memory, preferences] = await Promise.all([
      api<MemorySummary>("/api/v1/memory"),
      api<Preference[]>("/api/v1/me/preferences"),
    ]);
    setSummary({ ...memory, preferences });
  }

  async function loadContext(contextId: string) {
    const [adaptation, evidenceList, sessionList] = await Promise.all([
      api<{ states: ConceptState[] }>(`/api/v1/contexts/${contextId}/adaptation`),
      api<EvidenceRecord[]>(`/api/v1/contexts/${contextId}/evidence`),
      api<SessionRecord[]>(`/api/v1/study/sessions?context_id=${contextId}`),
    ]);
    setStates(adaptation.states);
    setEvidence(evidenceList);
    setSessions(sessionList);
    setMessagesBySession({});
    setExpanded({});
  }

  useEffect(() => {
    loadSummary().catch((requestError: unknown) =>
      setError(requestError instanceof Error ? requestError.message : "Unable to load memory")
    );
  }, []);

  useEffect(() => {
    if (!context) return;
    loadContext(context.id).catch((requestError: unknown) =>
      setError(requestError instanceof Error ? requestError.message : "Unable to load context memory")
    );
  }, [context]);

  async function addPreference(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/v1/me/preferences", {
        method: "PUT",
        body: JSON.stringify({ key: newKey, value: newValue }),
      });
      setNewKey("");
      setNewValue("");
      await loadSummary();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save preference");
    }
  }

  async function removePreference(key: string) {
    setError("");
    try {
      await api(`/api/v1/me/preferences/${encodeURIComponent(key)}`, { method: "DELETE" });
      await loadSummary();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to remove preference");
    }
  }

  async function toggleSession(sessionId: string) {
    const isOpen = expanded[sessionId];
    const next = { ...expanded, [sessionId]: !isOpen };
    setExpanded(next);
    if (!isOpen && !messagesBySession[sessionId]) {
      try {
        const list = await api<Message[]>(`/api/v1/study/sessions/${sessionId}/messages`);
        setMessagesBySession((items) => ({ ...items, [sessionId]: list }));
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Unable to load messages");
      }
    }
  }

  async function deleteMessage(sessionId: string, messageId: string) {
    setError("");
    try {
      await api(`/api/v1/study/sessions/${sessionId}/messages/${messageId}`, { method: "DELETE" });
      const list = await api<Message[]>(`/api/v1/study/sessions/${sessionId}/messages`);
      setMessagesBySession((items) => ({ ...items, [sessionId]: list }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to delete message");
    }
  }

  async function invalidateEvidence(evidenceId: string) {
    if (!context) return;
    setError("");
    try {
      await api(`/api/v1/contexts/${context.id}/evidence/${evidenceId}/invalidate`, {
        method: "POST",
      });
      const [adaptation, evidenceList] = await Promise.all([
        api<{ states: ConceptState[] }>(`/api/v1/contexts/${context.id}/adaptation`),
        api<EvidenceRecord[]>(`/api/v1/contexts/${context.id}/evidence`),
      ]);
      setStates(adaptation.states);
      setEvidence(evidenceList);
      await loadSummary();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update evidence");
    }
  }

  if (loading) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <p className="text-body-md text-on-surface-variant">Loading memory…</p>
      </div>
    );
  }

  return (
    <div className="p-container-padding md:p-section-margin w-full max-w-6xl mx-auto flex flex-col gap-8">
      <div>
        <h2 className="text-headline-xl text-on-background">Memory</h2>
        <p className="text-body-lg text-on-surface-variant mt-2">
          What ARIA remembers about you. Memory is separate from evidence and learner state, and you
          control it here.
        </p>
      </div>

      {/* Preferences */}
      <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-6">
        <h3 className="text-headline-md text-on-surface">Preferences</h3>
        <form onSubmit={addPreference} className="grid grid-cols-1 sm:grid-cols-[1fr_2fr_auto] gap-4">
          <input
            list="preference-keys"
            required
            className="h-12 bg-surface-container rounded-xl input-injected px-4 text-on-surface placeholder:text-outline-variant"
            placeholder="key (e.g. difficulty)"
            value={newKey}
            onChange={(event) => setNewKey(event.target.value)}
          />
          <datalist id="preference-keys">
            {SUGGESTED_KEYS.map((item) => <option key={item.key} value={item.key}>{item.placeholder}</option>)}
          </datalist>
          <input
            required
            className="h-12 bg-surface-container rounded-xl input-injected px-4 text-on-surface placeholder:text-outline-variant"
            placeholder="value"
            value={newValue}
            onChange={(event) => setNewValue(event.target.value)}
          />
          <button className="h-12 px-6 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
            Save
          </button>
        </form>
        {summary && summary.preferences.length > 0 ? (
          <ul className="flex flex-col gap-3">
            {summary.preferences.map((preference) => (
              <li key={preference.key} className="bg-surface shadow-injected rounded-xl p-4 flex items-center justify-between gap-4">
                <div>
                  <p className="text-body-md text-on-background font-semibold">{preference.key}</p>
                  <p className="text-label-md text-on-surface-variant mt-1">{preference.value}</p>
                </div>
                <button
                  onClick={() => void removePreference(preference.key)}
                  className="px-4 py-2 rounded-full text-label-md text-error hover:underline"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-body-md text-on-surface-variant">No preferences yet. Add one above.</p>
        )}
        <div className="flex flex-wrap gap-2">
          {SUGGESTED_KEYS.map((item) => (
            <button
              key={item.key}
              onClick={() => {
                setNewKey(item.key);
                setNewValue(item.placeholder.includes("e.g.") ? "" : item.placeholder);
              }}
              className="px-3 py-1 rounded-full bg-surface-container-low shadow-injected text-label-sm text-on-surface-variant"
            >
              {item.key}
            </button>
          ))}
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { label: "Concepts", value: summary.concepts },
            { label: "Weak", value: summary.weak_concepts },
            { label: "Supported", value: summary.supported_concepts },
            { label: "Evidence", value: summary.evidence_count },
            { label: "Messages", value: summary.message_count },
          ].map((stat) => (
            <div key={stat.label} className="bg-surface shadow-extruded rounded-3xl p-6 text-center">
              <p className="text-headline-lg text-secondary">{stat.value}</p>
              <p className="text-label-md text-on-surface-variant mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Concepts */}
      {context && (
        <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-4">
          <h3 className="text-headline-md text-on-surface">Concepts · {context.title}</h3>
          {states.length === 0 ? (
            <p className="text-body-md text-on-surface-variant">No concepts tracked yet.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {states.map((state) => {
                const chip = stateChip(state.state);
                return (
                  <li key={state.concept_id} className="bg-surface shadow-injected rounded-xl p-4 flex items-center justify-between gap-4">
                    <span className="text-body-md text-on-background">{state.concept_name}</span>
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${chip.cls}`}>{chip.label}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      {/* Evidence */}
      {context && evidence.length > 0 && (
        <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-4">
          <h3 className="text-headline-md text-on-surface">Evidence</h3>
          <ul className="flex flex-col gap-3">
            {evidence.map((item) => (
              <li key={item.id} className="bg-surface shadow-injected rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-body-md text-on-background">
                    {item.concept_name} — {item.signal === "CORRECT" && item.valid ? "correct" : item.valid ? "incorrect" : "challenged"}
                  </p>
                  <p className="text-label-sm text-on-surface-variant mt-1">{formatDateTime(item.created_at)}</p>
                </div>
                {item.valid && (
                  <button onClick={() => void invalidateEvidence(item.id)} className="px-4 py-2 rounded-full text-label-md text-error hover:underline">
                    This result looks wrong
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Conversations */}
      {context && (
        <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-4">
          <h3 className="text-headline-md text-on-surface">Conversations · {context.title}</h3>
          {sessions.length === 0 ? (
            <p className="text-body-md text-on-surface-variant">No conversations yet.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {sessions.map((session) => (
                <li key={session.id} className="bg-surface shadow-injected rounded-xl">
                  <button
                    onClick={() => void toggleSession(session.id)}
                    className="w-full flex items-center justify-between p-4 text-left"
                  >
                    <span className="text-body-md text-on-background">
                      Session · {formatDateTime(session.created_at)}
                    </span>
                    <span className="material-symbols-outlined text-on-surface-variant">
                      {expanded[session.id] ? "expand_less" : "expand_more"}
                    </span>
                  </button>
                  {expanded[session.id] && (
                    <ul className="flex flex-col gap-2 px-4 pb-4">
                      {(messagesBySession[session.id] ?? []).map((message) => (
                        <li key={message.id} className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <p className="text-label-sm text-secondary">{message.role === "user" ? "You" : "ARIA"}</p>
                            <p className="text-body-md text-on-surface whitespace-pre-wrap break-words">{message.content}</p>
                          </div>
                          <button
                            onClick={() => void deleteMessage(session.id, message.id)}
                            className="shrink-0 px-3 py-1 rounded-full text-label-sm text-error hover:underline"
                          >
                            Delete
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {error && <p className="text-label-md text-error" role="alert">{error}</p>}
    </div>
  );
}
