"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { api, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { toast } from "@/lib/toast";
import { ErrorState, Loading } from "@/components/states";

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

const STATE_COLOR: Record<string, string> = {
  SUPPORTED: "var(--success)",
  DEVELOPING: "var(--accent)",
  NEEDS_REVIEW: "var(--danger)",
  UNTESTED: "var(--text-3)",
};

const STATE_TEXT: Record<string, string> = {
  SUPPORTED: "var(--success-strong)",
  DEVELOPING: "var(--accent-strong)",
  NEEDS_REVIEW: "var(--danger-strong)",
  UNTESTED: "var(--text-2)",
};

const STATE_LABEL: Record<string, string> = {
  SUPPORTED: "Supported",
  DEVELOPING: "Developing",
  NEEDS_REVIEW: "Needs review",
  UNTESTED: "Untested",
};

const RX = 33;
const RY = 37;

const FILTERS: { key: "ALL" | "SUPPORTED" | "DEVELOPING" | "NEEDS_REVIEW" | "UNTESTED"; label: string }[] = [
  { key: "ALL", label: "All" },
  { key: "SUPPORTED", label: "Supported" },
  { key: "DEVELOPING", label: "Developing" },
  { key: "NEEDS_REVIEW", label: "Needs review" },
  { key: "UNTESTED", label: "Untested" },
];

export default function MapPage() {
  const { context } = useActiveContext();
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [states, setStates] = useState<ConceptState[]>([]);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState<"ALL" | "SUPPORTED" | "DEVELOPING" | "NEEDS_REVIEW" | "UNTESTED">("ALL");
  const [prereqs, setPrereqs] = useState<Record<string, string[]>>({});

  const load = useCallback(async (cid: string) => {
    const [adaptation, ev, concepts] = await Promise.all([
      api<{ states: ConceptState[] }>(`/api/v1/contexts/${cid}/adaptation`),
      api<EvidenceItem[]>(`/api/v1/contexts/${cid}/evidence`),
      api<{ id: string; name: string }[]>(`/api/v1/contexts/${cid}/concepts`),
    ]);
    setStates(adaptation.states);
    setEvidence(ev);
    // prerequisite edges for badges (best-effort; missing = no badge)
    const map: Record<string, string[]> = {};
    await Promise.all(
      concepts.map(async (c) => {
        try {
          const pr = await api<{ prerequisite_concept_id: string }[]>(
            `/api/v1/contexts/${cid}/concepts/${c.id}/prerequisites`,
          );
          map[c.id] = pr.map((p) => p.prerequisite_concept_id);
        } catch {
          map[c.id] = [];
        }
      }),
    );
    setPrereqs(map);
  }, []);

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

  const invalidate = async (id: string) => {
    if (!context) return;
    try {
      await api(`/api/v1/contexts/${context.id}/evidence/${id}/invalidate`, { method: "POST" });
      toast("Evidence invalidated — learner state recalculated.");
      await load(context.id);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not invalidate evidence.");
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
  const n = visible.length;

  return (
    <div>
      <div className="section-head">
        <div>
          <h1 className="pg-title">Knowledge Map</h1>
          <p className="pg-sub">Neural Topology Map — see how well you master each concept in this context.</p>
        </div>
      </div>

      {states.length === 0 ? (
        <div className="empty-state">
          <Icon name="target" size={30} />
          <p style={{ margin: "10px 0 14px", fontSize: 14, color: "var(--text-1)" }}>
            No concepts tracked yet. Start a study session to build your map.
          </p>
          <Link href="/app/learn" className="btn btn-primary" style={{ justifyContent: "center" }}>
            Start Learning <Icon name="arrow" />
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
          <div
            style={{
              position: "relative",
              height: 520,
              borderRadius: 28,
              overflow: "hidden",
              background: "var(--bg-1)",
              boxShadow: "var(--shadow-2)",
            }}
          >
            {/* connector lines */}
            <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
              {visible.map((c, i) => {
                const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
                const x2 = 50 + RX * Math.cos(angle);
                const y2 = 50 + RY * Math.sin(angle);
                return <line key={c.concept_id} x1="50%" y1="50%" x2={`${x2}%`} y2={`${y2}%`} stroke="var(--border-hi)" strokeWidth="1.5" />;
              })}
            </svg>
            {/* center hub */}
            <div
              style={{
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%,-50%)",
                width: 136,
                height: 136,
                borderRadius: "50%",
                background: "var(--bg-2)",
                boxShadow: "var(--shadow-2)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 4,
              }}
            >
              <Icon name="target" size={26} />
              <b style={{ fontSize: 13, textAlign: "center", padding: "0 8px" }}>{context?.title ?? "Knowledge Map"}</b>
            </div>
            {visible.map((c, i) => {
              const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
              const x = 50 + RX * Math.cos(angle);
              const y = 50 + RY * Math.sin(angle);
              const color = STATE_COLOR[c.state] ?? "var(--text-3)";
              const textColor = STATE_TEXT[c.state] ?? "var(--text-2)";
              return (
                <div
                  key={c.concept_id}
                  style={{
                    position: "absolute",
                    left: `${x}%`,
                    top: `${y}%`,
                    transform: "translate(-50%,-50%)",
                    width: 136,
                    padding: "12px 10px",
                    borderRadius: 14,
                    background: "var(--bg-1)",
                    boxShadow: "var(--shadow-2)",
                    border: `2px solid ${color}`,
                    textAlign: "center",
                  }}
                >
                  <b style={{ fontSize: 13, display: "block" }}>{c.concept_name}</b>
                  <div style={{ fontSize: 10, color: "var(--text-3)", marginTop: 2 }}>{STATE_LABEL[c.state] ?? c.state.replace("_", " ")}</div>
                  <div style={{ fontSize: 11, fontWeight: 800, color: textColor, marginTop: 2 }}>{c.confidence}%</div>
                </div>
              );
            })}
          </div>
          )}

          <div className="grid-2" style={{ gap: 14, marginTop: 22 }}>
            {visible.map((c) => (
              <div className="card card-pad" key={c.concept_id} style={{ padding: 16, display: "flex", gap: 12, alignItems: "flex-start" }}>
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: STATE_COLOR[c.state] ?? "var(--text-3)", marginTop: 4, flexShrink: 0 }} />
                <div>
                  <b style={{ fontSize: 14 }}>{c.concept_name}</b>{" "}
                  <span style={{ fontSize: 11, color: "var(--text-3)" }}>· {STATE_LABEL[c.state] ?? c.state.replace("_", " ")}</span>{(prereqs[c.concept_id]?.length ?? 0) > 0 && (<span className="tag-chip" style={{ marginLeft: 6 }}>↑ {(prereqs[c.concept_id] ?? []).length} prereq</span>) }
                  <p style={{ fontSize: 12, color: "var(--text-2)", marginTop: 3 }}>{c.reason}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="card card-pad" style={{ marginTop: 22 }}>
            <h2 style={{ fontSize: 17, fontWeight: 800, marginBottom: 6 }}>Evidence</h2>
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