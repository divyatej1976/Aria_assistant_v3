"use client";

import { Modal } from "@/components/modal";
import { PageGuide } from "@/components/page-guide";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon, type IconName } from "@/components/icons";
import { api, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { milestonesPerWeek, tickExplanation, type Roadmap, type RoadmapSummary, type RoadmapTopic } from "@/lib/roadmap";
import { toast } from "@/lib/toast";
import { ErrorState, Loading } from "@/components/states";
import { MilestoneTrail } from "@/components/milestone-trail";
import { RoadmapTree } from "@/components/roadmap-tree";
import { useDismissed } from "@/lib/use-dismissed";
import { RequestStatus } from "@/components/request-status";

const LEVELS = [
  { value: "Beginner", hint: "New to this. Start from the basics." },
  { value: "Intermediate", hint: "Know the basics. Ready to build on them." },
  { value: "Advanced", hint: "Comfortable already. Go deep and fill gaps." },
];
const WEEKLY = [
  { hours: 2, label: "1–2 hours" },
  { hours: 4, label: "3–5 hours" },
  { hours: 8, label: "6–10 hours" },
  { hours: 12, label: "10+ hours" },
];
const GOAL_IDEAS = ["Pass my exam next month", "Build a small project", "Prepare for job interviews"];
const FOCUS = [
  { value: "concepts", label: "Understanding concepts" },
  { value: "projects", label: "Building projects" },
  { value: "exams", label: "Passing an exam" },
  { value: "interviews", label: "Job interviews" },
  { value: "mixed", label: "A mix" },
];
const SETUP_STEPS = 5;


type ServerRoadmapResponse = {
  id: string;
  goal: string;
  level: string;
  target_date?: string;
  hours_per_week?: number | null;
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
      done_skills?: string[];
      prerequisites: string[];
      state: string;
      confidence: number;
      reason?: string;
      ticked: boolean;
      order_index: number;
      outcome?: string | null;
      effort_hours?: number | null;
      activity?: string | null;
      check?: string | null;
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
  const [hoursPerWeek, setHoursPerWeek] = useState<number | null>(null);
  const [step, setStep] = useState(0);
  const [focus, setFocus] = useState("mixed");
  const [refineOpen, setRefineOpen] = useState(false);
  const [refineText, setRefineText] = useState("");
  const [refining, setRefining] = useState(false);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<RoadmapTopic | null>(null);
  const [createError, setCreateError] = useState("");
  const { dismissed: infoDismissed, dismiss: dismissInfo } = useDismissed(`aria.roadmap-info:${context?.id}:${roadmap?.id}:${roadmap?.generationMode ?? "legacy"}`);

  const detailsVersion = useRef(0);
  const activeIdRef = useRef<string | null>(null);

  useEffect(() => () => { detailsVersion.current += 1; }, []);

  // Tick a sub-topic straight away; put it back if the save fails.
  const tickSkill = async (topic: RoadmapTopic, skill: string, done: boolean) => {
    const roadmapId = roadmap?.id;
    if (!roadmapId) return;
    const apply = (isDone: boolean) => setRoadmap((current) => current && {
      ...current,
      tiers: current.tiers.map((tier) => ({ ...tier, topics: tier.topics.map((item) => item.key !== topic.key ? item : {
        ...item, doneSkills: isDone ? [...new Set([...(item.doneSkills ?? []), skill])] : (item.doneSkills ?? []).filter((s) => s !== skill),
      }) })),
    });
    apply(done);
    try {
      await api(`/api/v1/roadmaps/${roadmapId}/milestones/${topic.key}/skills`, { method: "PUT", body: JSON.stringify({ skill, done }) });
    } catch {
      apply(!done);
      toast("Could not save that tick. Please try again.", "error");
    }
  };

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
        hoursPerWeek: data.hours_per_week,
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
            doneSkills: tp.done_skills ?? [],
            ticked: tp.ticked,
            state: tp.state,
            confidence: tp.confidence,
            reason: tp.reason || "",
            prereqNames: tp.prerequisites,
            outcome: tp.outcome,
            effortHours: tp.effort_hours,
            activity: tp.activity,
            check: tp.check,
          })),
        })),
        total: data.total,
        done: data.done,
      };
      if (version !== detailsVersion.current) return;
      setRoadmap(mappedRoadmap);
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

        // The page opens on the list of roadmaps; a roadmap opens when picked (or right after it is made).
        const targetId = preferredId || (activeIdRef.current && summaries.some((s) => s.id === activeIdRef.current) ? activeIdRef.current : null);
        activeIdRef.current = targetId;
        setActiveRoadmapId(targetId);
        if (targetId) await fetchRoadmapDetails(targetId);
        else setRoadmap(null);
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
          hours_per_week: hoursPerWeek ?? undefined,
          focus,
          context_id: context.id,
        }),
      });
      setOpen(false);
      setGoal("");
      setStep(0);
      toast("Your roadmap is ready.");
      await load(context.id, created.id);
    } catch (e) {
      setCreateError(e instanceof ApiError ? e.message : "Could not create the roadmap. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const refine = async () => {
    if (!roadmap?.id || !context || !refineText.trim()) return;
    setRefining(true);
    try {
      await api(`/api/v1/roadmaps/${roadmap.id}/refine`, { method: "POST", body: JSON.stringify({ instruction: refineText.trim() }) });
      setRefineOpen(false);
      toast("Your plan was updated. Progress from your quizzes is kept.", "success");
      await load(context.id, roadmap.id);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not update the plan. Please try again.", "error");
    } finally {
      setRefining(false);
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
        <button className="btn btn-primary" data-tour="create-roadmap" onClick={() => { setCreateError(""); setStep(0); setGoal((g) => g || context?.title || ""); setOpen(true); }}>
          <Icon name="route" /> Create roadmap
        </button>
      </div>
      <PageGuide page="plan" />

      {activeRoadmapId === null && roadmapList.length > 0 ? (
        <section aria-labelledby="roadmap-list-title">
          <h2 id="roadmap-list-title" className="roadmap-list-title">Your learning goals</h2>
          <div className="roadmap-list">
            {roadmapList.map((r) => {
              const pct = r.total ? Math.round((r.done / r.total) * 100) : 0;
              return (
                <button key={r.id} type="button" className="roadmap-card" onClick={() => {
                  activeIdRef.current = r.id;
                  setActiveRoadmapId(r.id);
                  setSelected(null);
                  void fetchRoadmapDetails(r.id);
                }}>
                  <span className="tool-icon"><Icon name="route" size={20} /></span>
                  <b>{r.goal}</b>
                  <small>{r.level}{r.target_date ? ` · by ${new Date(r.target_date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}` : ""}</small>
                  <span className="roadmap-card-bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label={`${r.goal} progress`}><span style={{ width: `${pct}%` }} /></span>
                  <small>{r.done} of {r.total} milestones · {pct}%</small>
                </button>
              );
            })}
            <button type="button" className="roadmap-card roadmap-card-new" onClick={() => { setCreateError(""); setStep(0); setGoal(""); setOpen(true); }}>
              <span className="tool-icon"><Icon name="plus" size={20} /></span>
              <b>New roadmap</b>
              <small>Another goal, its own milestones</small>
            </button>
          </div>
        </section>
      ) : activeRoadmapId !== null && roadmap === null ? (
        <Loading label="Loading roadmap" />
      ) : roadmap === null ? (
        <div className="empty-state">
          <Icon name="route" size={30} />
          <p style={{ margin: "10px 0 14px", fontSize: 14, color: "var(--text-1)" }}>
            No roadmap yet. Set a learning goal to see the skills and milestones to work through.
          </p>
          <button className="btn btn-primary" onClick={() => { setCreateError(""); setStep(0); setGoal((g) => g || context?.title || ""); setOpen(true); }} style={{ justifyContent: "center" }}>
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
              {selected.ticked ? "Completed" : ({ NOT_STARTED: "Upcoming", DEVELOPING: "Developing", NEEDS_REVIEW: "Review needed", SUPPORTED: "Strong" }[selected.state] ?? "Learning in progress")}
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

          {(selected.outcome || selected.activity || selected.check || selected.effortHours) && (
            <dl className="milestone-facts">
              {selected.outcome && <><dt>You&apos;ll be able to</dt><dd>{selected.outcome.replace(/^You can /, "")}</dd></>}
              {selected.effortHours && <><dt>Effort</dt><dd>About {selected.effortHours} hour{selected.effortHours === 1 ? "" : "s"}</dd></>}
              {selected.activity && <><dt>How to learn it</dt><dd>{selected.activity}</dd></>}
              {selected.check && <><dt>How it&apos;s checked</dt><dd>{selected.check}</dd></>}
            </dl>
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
            <Link href={`/app/assess?${new URLSearchParams({ quiz_topic: selected.title })}`} className="btn btn-secondary">
              <Icon name="clipboard" /> Quiz me on this
            </Link>
          </div>
        </div>
      ) : (
        <>
          <div className="roadmap-open-head">
            <button className="btn btn-ghost" onClick={() => { activeIdRef.current = null; setActiveRoadmapId(null); setRoadmap(null); }}>
              <Icon name="back" /> All roadmaps
            </button>
            <h2>{roadmap.goal}</h2>
          </div>
          {(() => {
            const week = topics.filter((topic) => !topic.ticked).slice(0, milestonesPerWeek(roadmap.hoursPerWeek));
            if (week.length === 0) return null;
            return (
              <section className="plan-week" aria-labelledby="plan-week-title">
                <div className="plan-week-head">
                  <h2 id="plan-week-title">This week</h2>
                  <span>{roadmap.hoursPerWeek ? `About ${roadmap.hoursPerWeek} hours` : "Set your weekly time when you make your next roadmap"}</span>
                </div>
                <ol>
                  {week.map((topic) => (
                    <li key={topic.key}>
                      <span className="plan-week-title">{topic.title}</span>
                      <span className="plan-week-actions">
                        <Link className="btn btn-secondary" href={`/app/learn?${new URLSearchParams({ topic: topic.title, context: context?.id ?? "", roadmap: roadmap.id ?? "", milestone: topic.key })}`}>
                          <Icon name="message" size={14} /> Study
                        </Link>
                        <Link className="btn btn-ghost" href={`/app/assess?${new URLSearchParams({ quiz_topic: topic.title })}`}>
                          <Icon name="clipboard" size={14} /> Quiz me
                        </Link>
                      </span>
                    </li>
                  ))}
                </ol>
              </section>
            );
          })()}

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
            <button className="btn btn-secondary" style={{ marginTop: 8 }} onClick={() => { setRefineText(""); setRefineOpen(true); }}>
              <Icon name="edit" size={14} /> Refine this plan
            </button>
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
          <RoadmapTree tiers={roadmap.tiers} nextKey={nextTopic?.key} contextId={context?.id} roadmapId={roadmap.id}
            onDetails={setSelected} onTick={(topic, skill, done) => void tickSkill(topic, skill, done)} />

          <p style={{ fontSize: 12, color: "var(--text-3)", marginTop: 18 }}>
            <Icon name="sparkles" size={13} /> Only learning activities relevant to this goal tick milestones. Unrelated lessons or document uploads will never alter this curriculum.
          </p>
        </>
      )}

      <Modal open={refineOpen} title="Refine this plan" onClose={() => setRefineOpen(false)}>
        <div className="modal">
          <div className="m-head dialog-heading">
            <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}><Icon name="edit" size={20} /> Refine this plan</h3>
            <button className="btn btn-ghost" style={{ padding: 6 }} onClick={() => setRefineOpen(false)} aria-label="Close"><Icon name="x" size={16} /></button>
          </div>
          <label className="plan-q" htmlFor="refine-text">What should change?</label>
          <input id="refine-text" className="input" maxLength={300} value={refineText} disabled={refining}
            placeholder="e.g. less theory, more practice" onChange={(e) => setRefineText(e.target.value)} />
          <div className="quiz-choice-row">
            {["Less theory", "Add projects", "More practice", "Give me more time", "Make it faster"].map((idea) => (
              <button key={idea} type="button" className="tag-chip" disabled={refining} onClick={() => setRefineText(idea)}>{idea}</button>
            ))}
          </div>
          <p className="field-help">Your milestones are rebuilt with the same goal, level and weekly time. Progress from your quizzes is kept.</p>
          {refining && <RequestStatus label="Updating your plan…" />}
          <div className="dialog-actions ui-mt-16">
            <button className="btn btn-ghost" onClick={() => setRefineOpen(false)} disabled={refining}>Cancel</button>
            <button className="btn btn-primary" onClick={refine} disabled={refining || !refineText.trim()}>Update plan <Icon name="arrow" /></button>
          </div>
        </div>
      </Modal>

      {/* create modal */}
      <Modal open={open} title="Create roadmap" onClose={() => setOpen(false)}>
        <div className="modal">
          <div className="m-head dialog-heading">
            <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}><Icon name="route" size={20} /> Create roadmap</h3>
            <button className="btn btn-ghost" style={{ padding: 6 }} onClick={() => setOpen(false)} aria-label="Close"><Icon name="x" size={16} /></button>
          </div>
          <div className="plan-steps" aria-hidden="true">
            {Array.from({ length: SETUP_STEPS + 1 }, (_, i) => <span key={i} className={i <= step ? "on" : ""} />)}
          </div>
          {step === 0 && (
            <div className="plan-question">
              <label className="plan-q" htmlFor="roadmap-goal">What do you want to be able to do?</label>
              <input id="roadmap-goal" className="input" value={goal} disabled={busy}
                onChange={(e) => setGoal(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && goal.trim()) setStep(1); }}
                placeholder={`e.g. Build a REST API with ${context?.title ?? "Python"}`} />
              <div className="quiz-choice-row">
                {GOAL_IDEAS.map((idea) => <button key={idea} type="button" className="tag-chip" onClick={() => setGoal(idea)}>{idea}</button>)}
              </div>
            </div>
          )}
          {step === 1 && (
            <div className="plan-question" role="radiogroup" aria-label="Where are you starting from?">
              <p className="plan-q">Where are you starting from?</p>
              {LEVELS.map((option) => (
                <button key={option.value} type="button" role="radio" aria-checked={level === option.value}
                  className={`plan-option${level === option.value ? " selected" : ""}`} onClick={() => setLevel(option.value)}>
                  <b>{option.value}</b><span>{option.hint}</span>
                </button>
              ))}
            </div>
          )}
          {step === 2 && (
            <div className="plan-question" role="radiogroup" aria-label="How much time can you give it each week?">
              <p className="plan-q">How much time can you give it each week?</p>
              <div className="quiz-choice-row">
                {WEEKLY.map((option) => (
                  <button key={option.hours} type="button" role="radio" aria-checked={hoursPerWeek === option.hours}
                    className={`tag-chip${hoursPerWeek === option.hours ? " tag-chip-selected" : ""}`} onClick={() => setHoursPerWeek(option.hours)}>
                    {option.label}
                  </button>
                ))}
                <button type="button" role="radio" aria-checked={hoursPerWeek === null}
                  className={`tag-chip${hoursPerWeek === null ? " tag-chip-selected" : ""}`} onClick={() => setHoursPerWeek(null)}>Not sure yet</button>
              </div>
            </div>
          )}
          {step === 3 && (
            <div className="plan-question" role="radiogroup" aria-label="What should the plan focus on?">
              <p className="plan-q">What should the plan focus on?</p>
              <div className="quiz-choice-row">
                {FOCUS.map((option) => (
                  <button key={option.value} type="button" role="radio" aria-checked={focus === option.value}
                    className={`tag-chip${focus === option.value ? " tag-chip-selected" : ""}`} onClick={() => setFocus(option.value)}>
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          )}
          {step === 4 && (
            <div className="plan-question">
              <p className="plan-q">Is there a deadline?</p>
              <div className="quiz-choice-row">
                <button type="button" className={`tag-chip${!targetDate ? " tag-chip-selected" : ""}`} onClick={() => setTargetDate("")}>No deadline</button>
              </div>
              <label className="field-label" htmlFor="roadmap-target">Or pick a date</label>
              <input id="roadmap-target" type="date" className="input" value={targetDate} disabled={busy}
                min={new Date().toISOString().slice(0, 10)} onChange={(e) => setTargetDate(e.target.value)} />
            </div>
          )}
          {step === SETUP_STEPS && (
            <div className="plan-question">
              <p className="plan-q">Ready to build your roadmap?</p>
              <dl className="plan-summary">
                <dt>Goal</dt><dd>{goal}</dd>
                <dt>Starting level</dt><dd>{level}</dd>
                <dt>Each week</dt><dd>{WEEKLY.find((w) => w.hours === hoursPerWeek)?.label ?? "Not sure yet"}</dd>
                <dt>Focus</dt><dd>{FOCUS.find((f) => f.value === focus)?.label}</dd>
                <dt>Deadline</dt><dd>{targetDate || "None"}</dd>
              </dl>
            </div>
          )}
          {createError && <div className="inline-error" role="alert"><b>Roadmap could not be created</b><p>{createError}</p></div>}
          {busy && <RequestStatus label="Building your learning path…" />}
          <div className="dialog-actions ui-mt-16">
            {step > 0
              ? <button className="btn btn-ghost" onClick={() => setStep((s) => s - 1)} disabled={busy}><Icon name="back" /> Back</button>
              : <button className="btn btn-ghost" onClick={() => setOpen(false)} disabled={busy}>Cancel</button>}
            {step < SETUP_STEPS && (
              <button className="btn btn-primary" onClick={() => setStep((s) => s + 1)} disabled={step === 0 && !goal.trim()}>
                Next <Icon name="arrow" />
              </button>
            )}
            {step === SETUP_STEPS && <button className="btn btn-primary" onClick={create} disabled={busy}>
              {busy ? (
                <>
                  <Icon name="sparkles" /> Building your roadmap…
                </>
              ) : (
                <>
                  Create roadmap <Icon name="arrow" />
                </>
              )}
            </button>}
          </div>
        </div>
      </Modal>
    </div>
  );
}
