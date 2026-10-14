"use client";

import { Modal } from "@/components/modal";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon, type IconName } from "@/components/icons";
import { api, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { tickExplanation, type Roadmap, type RoadmapSummary, type RoadmapTopic } from "@/lib/roadmap";
import { toast } from "@/lib/toast";
import { ErrorState, Loading } from "@/components/states";
import { MilestoneTrail } from "@/components/milestone-trail";
import { useDismissed } from "@/lib/use-dismissed";
import { RequestStatus } from "@/components/request-status";

const LEVELS = ["Beginner", "Intermediate", "Advanced"];

type ServerRoadmapResponse = {
  id: string;
  goal: string;
  level: string;
  target_date?: string;
  status: string;
  generation_mode?: "ai" | "starter" | null;
  fallback_reason?: string | null;
  tiers: {
    name: string;
    icon: string;
    topics: {
      id: string;
      phase_name: string;
      phase_order: number;
      title: string;
      description?: string;
      key_skills: string[];
      prerequisites: string[];
      state: string;
      confidence: number;
      reason?: string;
      ticked: boolean;
      order_index: number;
    }[];
  }[];
  total: number;
  done: number;
};

export default function RoadmapsPage() {
  const { context } = useActiveContext();
  return <RoadmapsPageWorkspace key={context?.id ?? "no-subject"} />;
}

function RoadmapsPageWorkspace() {
  const { context } = useActiveContext();
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [roadmapList, setRoadmapList] = useState<RoadmapSummary[]>([]);
  const [activeRoadmapId, setActiveRoadmapId] = useState<string | null>(null);
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [open, setOpen] = useState(false);
  const [goal, setGoal] = useState("");
  const [level, setLevel] = useState("Beginner");
  const [targetDate, setTargetDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [openTiers, setOpenTiers] = useState<Record<string, boolean>>({});
  const [selected, setSelected] = useState<RoadmapTopic | null>(null);
  const [createError, setCreateError] = useState("");
  const { dismissed: infoDismissed, dismiss: dismissInfo } = useDismissed(`aria.roadmap-info:${context?.id}:${roadmap?.id}:${roadmap?.generationMode ?? "legacy"}`);

  const detailsVersion = useRef(0);
  const activeIdRef = useRef<string | null>(null);

  useEffect(() => () => { detailsVersion.current += 1; }, []);

  const fetchRoadmapDetails = useCallback(async (roadmapId: string) => {
    const version = ++detailsVersion.current;
    setFailed(false);
    setRoadmap(null);
    try {
      const data = await api<ServerRoadmapResponse>(`/api/v1/roadmaps/${roadmapId}`);
      const mappedRoadmap: Roadmap = {
        id: data.id,
        goal: data.goal,
        level: data.level,
        targetDate: data.target_date,
        status: data.status,
        generationMode: data.generation_mode,
        fallbackReason: data.fallback_reason,
        tiers: data.tiers.map((t) => ({
          name: t.name,
          icon: (t.icon as IconName) || "book",
          topics: t.topics.map((tp) => ({
            key: tp.id,
            title: tp.title,
            description: tp.description,
            keySkills: tp.key_skills,
            ticked: tp.ticked,
            state: tp.state,
            confidence: tp.confidence,
            reason: tp.reason || "",
            prereqNames: tp.prerequisites,
          })),
        })),
        total: data.total,
        done: data.done,
      };
      if (version !== detailsVersion.current) return;
      setRoadmap(mappedRoadmap);
      if (mappedRoadmap.tiers.length > 0) {
        setOpenTiers((prev) => ({
          ...prev,
          [mappedRoadmap.tiers[0].name]: true,
        }));
      }
    } catch {
      if (version === detailsVersion.current) setFailed(true);
    }
  }, []);

  const load = useCallback(
    async (cid: string, preferredId?: string) => {
      try {
        setFailed(false);
        const summaries = await api<RoadmapSummary[]>(`/api/v1/roadmaps?context_id=${cid}`);
        setRoadmapList(summaries);

        if (summaries.length === 0) {
          // Check for legacy preference if no server roadmaps exist yet
          try {
            const prefs = await api<{ key: string; value: string }[]>("/api/v1/me/preferences");
            const legacyGoal = prefs.find((p) => p.key === "roadmap_goal")?.value;
            const legacyLevel = prefs.find((p) => p.key === "roadmap_level")?.value ?? "Beginner";
            const legacyTarget = prefs.find((p) => p.key === "roadmap_target")?.value;
            if (legacyGoal) {
              const created = await api<ServerRoadmapResponse>("/api/v1/roadmaps", {
                method: "POST",
                body: JSON.stringify({
                  goal: legacyGoal,
                  level: legacyLevel,
                  target_date: legacyTarget || undefined,
                  context_id: cid,
                }),
              });
              setRoadmapList([
                {
                  id: created.id,
                  goal: created.goal,
                  level: created.level,
                  target_date: created.target_date,
                  status: created.status,
                  created_at: new Date().toISOString(),
                  total: created.total,
                  done: created.done,
                },
              ]);
              setActiveRoadmapId(created.id);
              await fetchRoadmapDetails(created.id);
              return;
            }
          } catch {
            setFailed(true);
            return;
          }
          setRoadmap(null);
          setActiveRoadmapId(null);
          return;
        }

        const targetId = preferredId || (activeIdRef.current && summaries.some((s) => s.id === activeIdRef.current) ? activeIdRef.current : summaries[0].id);
        activeIdRef.current = targetId;
        setActiveRoadmapId(targetId);
        await fetchRoadmapDetails(targetId);
      } catch {
        setFailed(true);
      }
    },
    [fetchRoadmapDetails],
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

  const create = async () => {
    setCreateError("");
    if (!context) return;
    if (!goal.trim()) {
      setCreateError("Please enter a learning goal.");
      return;
    }
    setBusy(true);
    try {
      const created = await api<ServerRoadmapResponse>("/api/v1/roadmaps", {
        method: "POST",
        body: JSON.stringify({
          goal: goal.trim(),
          level,
          target_date: targetDate || undefined,
          context_id: context.id,
        }),
      });
      setOpen(false);
      setGoal("");
      toast("Goal-oriented roadmap created!");
      await load(context.id, created.id);
    } catch (e) {
      setCreateError(e instanceof ApiError ? e.message : "Could not create the roadmap. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const removeCurrentRoadmap = async () => {
    if (!activeRoadmapId || !context) return;
    if (!confirm("Are you sure you want to delete this roadmap?")) return;
    try {
      await api(`/api/v1/roadmaps/${activeRoadmapId}`, { method: "DELETE" });
      toast("Roadmap removed.");
      setSelected(null);
      await load(context.id);
    } catch {
      toast("Could not delete roadmap.", "error");
    }
  };

  const remainingPct = roadmap && roadmap.total ? Math.round((roadmap.done / roadmap.total) * 100) : 0;
  const topics = roadmap?.tiers.flatMap(tier => tier.topics) ?? [];
  const nextTopic = topics.find(topic => !topic.ticked && topic.prereqNames.every(name =>
    topics.some(candidate => candidate.title.toLowerCase() === name.toLowerCase() && candidate.ticked)));
  const generationLabel = roadmap?.generationMode === "ai" ? "AI-generated curriculum" : roadmap?.generationMode === "starter" ? "General starter plan" : "Generation source unknown";

  if (loading) {
    return <Loading label="your roadmap" />;
  }
  if (failed) {
    return <ErrorState message="This screen could not be loaded." onRetry={() => window.location.reload()} />;
  }

  return (
    <div>
      <div className="section-head">
        <div>
          <h1 className="pg-title">Roadmaps</h1>
          <p className="pg-sub">Choose a goal and follow milestones backed by your learning evidence.</p>
        </div>
        <button className="btn btn-primary" onClick={() => { setCreateError(""); setOpen(true); }}>
          <Icon name="route" /> Create roadmap
        </button>
      </div>

      {/* Multi-Roadmap Switcher */}
      {roadmapList.length > 1 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20, alignItems: "center" }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-3)", marginRight: 4 }}>Goals:</span>
          {roadmapList.map((r) => (
            <button
              key={r.id}
              type="button"
              className={`tag-chip${r.id === activeRoadmapId ? " tag-chip-selected" : ""}`}
              onClick={() => {
                activeIdRef.current = r.id;
                setActiveRoadmapId(r.id);
                fetchRoadmapDetails(r.id);
                setSelected(null);
              }}
              style={{ cursor: "pointer", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 6 }}
            >
              <span>{r.goal}</span>
              <span style={{ fontSize: 10, opacity: 0.8 }}>({r.done}/{r.total})</span>
            </button>
          ))}
        </div>
      )}

      {roadmap === null ? (
        <div className="empty-state">
          <Icon name="route" size={30} />
          <p style={{ margin: "10px 0 14px", fontSize: 14, color: "var(--text-1)" }}>
            No roadmap yet. Set a learning goal to see the skills and milestones to work through.
          </p>
          <button className="btn btn-primary" onClick={() => { setCreateError(""); setOpen(true); }} style={{ justifyContent: "center" }}>
            <Icon name="route" /> Create roadmap
          </button>
        </div>
      ) : selected ? (
        <div className="card card-pad" style={{ maxWidth: 720 }}>
          <button className="btn btn-ghost mb-2" onClick={() => setSelected(null)}>
            <Icon name="back" /> All topics
          </button>
          <h2 style={{ fontSize: 24, fontWeight: 800, marginBottom: 4 }}>{selected.title}</h2>
          <div style={{ fontSize: 13, color: "var(--text-3)", marginBottom: 12 }}>
            {roadmap.goal} · {roadmap.level}
          </div>

          {selected.description && (
            <p style={{ fontSize: 14, color: "var(--text-1)", marginBottom: 16, lineHeight: 1.5 }}>
              {selected.description}
            </p>
          )}

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <span className={`tag-chip${selected.ticked ? " tag-chip-selected" : ""}`}>
              {selected.ticked ? "Completed" : ({ NOT_STARTED: "Upcoming", DEVELOPING: "Developing", NEEDS_REVIEW: "Review needed", SUPPORTED: "Evidence supported" }[selected.state] ?? "Learning in progress")}
            </span>
            <span className="tag-chip">{selected.confidence}% confidence</span>
            {selected.prereqNames && selected.prereqNames.length > 0 && (
              <span className="tag-chip">Prerequisites: {selected.prereqNames.join(", ")}</span>
            )}
          </div>

          {selected.keySkills && selected.keySkills.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-3)", marginBottom: 6 }}>Key skills & concepts:</div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {selected.keySkills.map((skill, i) => (
                  <span key={i} className="tag-chip" style={{ fontSize: 11 }}>
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="banner" style={{ margin: "16px 0" }}>
            <span style={{ color: "var(--accent)", display: "inline-flex" }}><Icon name="sparkles" size={20} /></span>
            <div>
              <b>Why this tick state?</b>
              <p style={{ marginTop: 2 }}>{tickExplanation(selected)}</p>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 20 }}>
            <Link href={`/app/learn?${new URLSearchParams({ topic: selected.title, context: context?.id ?? "", roadmap: roadmap.id ?? "", milestone: selected.key })}`} className="btn btn-primary" style={{ justifyContent: "center" }}>
              <Icon name="message" /> Study this milestone
            </Link>
          </div>
        </div>
      ) : (
        <>
          <div className="roadmap-summary">
            <div className="ring" style={{ "--p": remainingPct, "--r": "42px" } as React.CSSProperties}>
              <span className="r-n" style={{ color: "var(--accent)" }}>{remainingPct}%</span>
            </div>
            <div style={{ fontSize: 14, color: "var(--text-1)", marginTop: 10, fontWeight: 700 }}>
              {roadmap.goal}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 4 }}>
              {roadmap.level} {roadmap.targetDate ? `· Target: ${roadmap.targetDate}` : ""} · {roadmap.done} / {roadmap.total} completed
            </div>
            <span className="tag-chip roadmap-source">{generationLabel}</span>
            <button
              onClick={removeCurrentRoadmap}
              className="btn btn-ghost"
              style={{ fontSize: 11, color: "var(--text-3)", marginTop: 6, padding: "4px 8px" }}
            >
              <Icon name="x" size={12} /> Delete this roadmap
            </button>
          </div>

          {!infoDismissed && <div className="banner roadmap-information" style={{ marginBottom: 16 }}>
            <div>
              <b>About this learning path</b>
              <p>{roadmap.generationMode === "starter"
                ? "AI generation was unavailable or could not produce a valid plan. This outline is a general learning structure; add subject-specific skills from your material."
                : roadmap.generationMode === "ai"
                  ? "Review the milestones against reliable subject material as you learn."
                  : "This saved plan predates generation tracking. Its source cannot be confirmed."}</p>
            </div>
            <button className="btn btn-ghost" aria-label="Dismiss roadmap information" onClick={dismissInfo}><Icon name="x" size={16} /></button>
          </div>}

          <MilestoneTrail key={roadmap.id} roadmapId={roadmap.id} milestones={roadmap.tiers.flatMap(tier => tier.topics)} onSelect={key => setSelected(roadmap.tiers.flatMap(tier => tier.topics).find(topic => topic.key === key) ?? null)} />
          <div className="roadmap-timeline">{roadmap.tiers.map((tier, phaseIndex) => {
            const tierDone = tier.topics.filter((t) => t.ticked).length;
            const tierPct = tier.topics.length ? Math.round((tierDone / tier.topics.length) * 100) : 0;
            return (
            <div key={tier.name} className={`roadmap-tier phase-${phaseIndex}${tierDone === tier.topics.length && tierDone > 0 ? " phase-complete" : ""}`}>
              <span className="phase-node" aria-hidden="true">{tierDone === tier.topics.length && tierDone > 0 ? <Icon name="check" size={15} /> : phaseIndex + 1}</span>
              <button
                type="button"
                className="roadmap-tier-head"
                onClick={() => setOpenTiers((o) => ({ ...o, [tier.name]: !o[tier.name] }))}
                aria-expanded={!!openTiers[tier.name]}
                aria-controls={`tier-${phaseIndex}`}
              >
                <div className="roadmap-tier-icon">
                  <Icon name={tier.icon} size={18} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <b style={{ fontSize: 14 }}>{tier.name}</b>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
                    <div className="roadmap-tier-bar">
                      <div style={{ width: `${tierPct}%` }} />
                    </div>
                    <span style={{ fontSize: 11, color: "var(--text-3)", whiteSpace: "nowrap" }}>
                      {tierDone}/{tier.topics.length}
                    </span>
                  </div>
                  {!openTiers[tier.name] && <p className="phase-preview">{tier.topics.slice(0, 3).map(topic => topic.title).join(" · ")}{tier.topics.length > 3 ? ` · +${tier.topics.length - 3} more` : ""}</p>}
                </div>
                <Icon name={openTiers[tier.name] ? "chevron-up" : "chevron-down"} size={16} />
              </button>
                <div className="roadmap-tile-grid route-arrival" id={`tier-${phaseIndex}`} hidden={!openTiers[tier.name]}>
                  {tier.topics.map((topic) => {
                    const requiresReview = topic.state === "NEEDS_REVIEW";
                    const developing = !topic.ticked && topic.state === "DEVELOPING";
                    const next = !topic.ticked && !requiresReview && !developing && topic.key === nextTopic?.key;
                    const label = topic.ticked ? "Completed" : requiresReview ? "Review needed" : developing ? "Developing" : next ? "Up next" : "Upcoming";
                    const prerequisitesPending = topic.prereqNames.some(name => !topics.some(candidate => candidate.title.toLowerCase() === name.toLowerCase() && candidate.ticked));
                    return (
                    <article
                      className={`roadmap-topic-card${topic.ticked ? " completed" : requiresReview ? " needs-review" : developing ? " in-progress" : next ? " up-next" : prerequisitesPending ? " prerequisite-pending" : " upcoming"}`}
                      key={topic.key}
                    >
                      <Link className="roadmap-topic-study" title={topic.title} href={`/app/learn?${new URLSearchParams({ topic: topic.title, context: context?.id ?? "", roadmap: roadmap.id ?? "", milestone: topic.key })}`} aria-label={`Study ${topic.title}`}>
                      <div className="roadmap-topic-status">
                        <Icon name={topic.ticked ? "check" : requiresReview ? "refresh" : developing ? "activity" : prerequisitesPending ? "lock" : tier.icon} size={18} />
                      </div>
                      <b className="roadmap-topic-title">{topic.title}</b>
                      <div className="roadmap-topic-label">
                        {label}
                      </div>
                      {prerequisitesPending && !topic.ticked && <span className="roadmap-prerequisite-hint">Prerequisites first</span>}
                      </Link>
                      <button className="roadmap-topic-details" onClick={() => setSelected(topic)} aria-label={`View ${topic.title} details`} title="View milestone details"><Icon name="info" size={15} /></button>
                    </article>
                  );})}
                </div>
            </div>
            );
          })}</div>

          <p style={{ fontSize: 12, color: "var(--text-3)", marginTop: 18 }}>
            <Icon name="sparkles" size={13} /> Only learning activities relevant to this goal tick milestones. Unrelated lessons or document uploads will never alter this curriculum.
          </p>
        </>
      )}

      {/* create modal */}
      <Modal open={open} title="Create roadmap" onClose={() => setOpen(false)}>
        <div className="modal">
          <div className="m-head dialog-heading">
            <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}><Icon name="route" size={20} /> Create roadmap</h3>
            <button className="btn btn-ghost" style={{ padding: 6 }} onClick={() => setOpen(false)} aria-label="Close"><Icon name="x" size={16} /></button>
          </div>
          <div className="form-group">
            <label className="field-label" htmlFor="roadmap-goal">Learning goal</label>
            <input
              id="roadmap-goal"
              className="input"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g. Master Go for Cloud Microservices"
              disabled={busy}
            />
          </div>
          <div className="form-group">
            <label className="field-label">Target level</label>
            <div className="ui-flex ui-gap-8 ui-wrap">
              {LEVELS.map((l) => (
                <button
                  type="button"
                  key={l}
                  className={`tag-chip${level === l ? " tag-chip-selected" : ""}`}
                  onClick={() => setLevel(l)}
                  disabled={busy}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
          <div className="form-group">
            <label className="field-label" htmlFor="roadmap-target">Target date (optional)</label>
            <input
              id="roadmap-target"
              type="date"
              className="input"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              disabled={busy}
            />
          </div>
          {createError && <div className="inline-error" role="alert"><b>Roadmap could not be created</b><p>{createError}</p></div>}
          {busy && <RequestStatus label="Building your learning path…" />}
          <div className="dialog-actions ui-mt-16">
            <button className="btn btn-ghost" onClick={() => setOpen(false)} disabled={busy}>Cancel</button>
            <button className="btn btn-primary" onClick={create} disabled={busy}>
              {busy ? (
                <>
                  <Icon name="sparkles" /> Building your roadmap…
                </>
              ) : (
                <>
                  Create roadmap <Icon name="arrow" />
                </>
              )}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
