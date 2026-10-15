"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { api, ApiError } from "@/lib/api";
import { useActiveContext, type ActiveContext } from "@/components/use-active-context";
import { toast } from "@/lib/toast";
import { ErrorState, Loading } from "@/components/states";
import { KnowledgeConstellation } from "@/components/knowledge-constellation";

type ConceptState = {
  concept_id: string;
  concept_name: string;
  state: string;
  confidence: number;
  reason: string;
};
type EvidenceItem = {
  id: string;
  concept_id: string;
  concept_name: string;
  signal: string;
  valid: boolean;
  created_at: string;
};


const FILTERS: { key: "ALL" | "SUPPORTED" | "DEVELOPING" | "NEEDS_REVIEW" | "UNTESTED"; label: string }[] = [
  { key: "ALL", label: "All" },
  { key: "SUPPORTED", label: "Supported" },
  { key: "DEVELOPING", label: "Developing" },
  { key: "NEEDS_REVIEW", label: "Needs review" },
  { key: "UNTESTED", label: "Untested" },
];

export default function MapPage() {
  const { context } = useActiveContext();
  return <ContextMap key={context?.id ?? "empty"} context={context} />;
}

function ContextMap({ context }: { context: ActiveContext | null }) {
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [states, setStates] = useState<ConceptState[]>([]);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState<"ALL" | "SUPPORTED" | "DEVELOPING" | "NEEDS_REVIEW" | "UNTESTED">("ALL");
  const [prereqs, setPrereqs] = useState<Record<string, string[]>>({});
  const [prereqUnavailable, setPrereqUnavailable] = useState(0);
  const [prereqsLoading, setPrereqsLoading] = useState(false);

  const load = useCallback(async (cid: string, signal?: AbortSignal) => {
    const [adaptation, ev, concepts] = await Promise.all([
      api<{ states: ConceptState[] }>(`/api/v1/contexts/${cid}/adaptation`, { signal }),
      api<EvidenceItem[]>(`/api/v1/contexts/${cid}/evidence`, { signal }),
      api<{ id: string; name: string }[]>(`/api/v1/contexts/${cid}/concepts`, { signal }),
    ]);
    if (signal?.aborted) return;
    setStates(adaptation.states);
    setEvidence(ev);
    setPrereqs({});
    setPrereqUnavailable(0);
    setPrereqsLoading(concepts.length > 0);
    setLoading(false);
    // Missing edge data stays unknown; it never becomes a fabricated connection.
    const map: Record<string, string[]> = {};
    let unavailable = 0;
    let next = 0;
    // Bound request concurrency until the API provides a batch edge endpoint.
    await Promise.all(
      Array.from({ length: Math.min(6, concepts.length) }, async () => {
        while (next < concepts.length && !signal?.aborted) {
          const c = concepts[next++];
          try {
            const pr = await api<{ prerequisite_concept_id: string }[]>(
              `/api/v1/contexts/${cid}/concepts/${c.id}/prerequisites`,
              { signal },
            );
            map[c.id] = pr.map((p) => p.prerequisite_concept_id);
          } catch {
            unavailable++;
          }
        }
      }),
    );
    if (signal?.aborted) return;
    setPrereqs(map);
    setPrereqUnavailable(unavailable);
    setPrereqsLoading(false);
  }, []);

  useEffect(() => {
    if (!context) return;
    let cancelled = false;
    const controller = new AbortController();
    (async () => {
      try {
        await load(context.id, controller.signal);
      } catch {
        if (!cancelled) setFailed(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [context, load]);

  const invalidate = async (id: string) => {
    if (!context) return;
    try {
      await api(`/api/v1/contexts/${context.id}/evidence/${id}/invalidate`, { method: "POST" });
      toast("Evidence invalidated — learner state recalculated.");
      await load(context.id);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not invalidate evidence.", "error");
    }
  };

  const retry = () => {
    if (!context) return;
    setFailed(false);
    setLoading(true);
    load(context.id)
      .then(() => setFailed(false))
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  };

  if (failed) {
    return <ErrorState message="This screen could not be loaded." onRetry={retry} />;
  }
  if (loading && states.length === 0) {
    return <Loading label="your knowledge map" />;
  }

  const searchLc = search.trim().toLowerCase();
  const visible = states.filter(
    (s) =>
      (stateFilter === "ALL" || s.state === stateFilter) &&
      (searchLc === "" || s.concept_name.toLowerCase().includes(searchLc)),
  );

  return (
    <div>
      <div className="section-head">
        <div>
          <h1 className="pg-title">Topic map</h1>
          <p className="eyebrow">{context?.title}</p>
          <p className="pg-sub">Your learning universe — explore concepts, prerequisites, and the evidence behind your understanding.</p>
        </div>
      </div>

      {states.length === 0 ? (
        <div className="empty-state">
          <Icon name="target" size={30} />
          <p style={{ margin: "10px 0 14px", fontSize: 14, color: "var(--text-1)" }}>
            No concepts tracked yet. Start a study session to build your map.
          </p>
          <Link href="/app/learn" className="btn btn-primary" style={{ justifyContent: "center" }}>
            Start learning <Icon name="arrow" />
          </Link>
        </div>
      ) : (
        <>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 18 }}>
            <input
              className="input"
              aria-label="Search concepts"
              placeholder="Search concepts"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ maxWidth: 300, flex: 1, minWidth: 180 }}
            />
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }} role="group" aria-label="Filter concepts">
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  className={`tag-chip${stateFilter === f.key ? " tag-chip-selected" : ""}`}
                  aria-pressed={stateFilter === f.key}
                  onClick={() => setStateFilter(f.key)}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {visible.length === 0 ? (
            <div className="empty-state">
              <Icon name="target" size={30} />
              <p style={{ margin: "10px 0 14px", fontSize: 14, color: "var(--text-1)" }}>
                No concepts match this search or filter.
              </p>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setSearch("");
                  setStateFilter("ALL");
                }}
              >
                Clear filters
              </button>
            </div>
          ) : (
          <>
          {prereqsLoading && <p role="status" className="pg-sub">Loading confirmed connections… You can explore your concepts now.</p>}
          <KnowledgeConstellation concepts={states} visible={visible} prerequisites={prereqs} evidence={evidence} unavailable={prereqUnavailable} />
          </>
          )}

          <div className="card card-pad" style={{ marginTop: 22 }}>
            <h2 className="card-heading">Evidence</h2>
            {evidence.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--text-1)", margin: 0 }}>No evidence recorded yet — interactions with your study sessions appear here.</p>
            ) : (
              evidence.map((e) => (
                <div className="kv" key={e.id}>
                  <span className="k">
                    <Icon name="file" size={16} /> {e.concept_name} · {e.signal}
                  </span>
                  <span className="v" style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ color: e.valid ? "var(--success-strong)" : "var(--text-2)" }}>{e.valid ? "Valid" : "Invalid"}</span>
                    {e.valid && (
                      <button
                        className="btn btn-ghost"
                        style={{ padding: "3px 8px", fontSize: 11 }}
                        onClick={() => invalidate(e.id)}
                      >
                        Invalidate
                      </button>
                    )}
                  </span>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
