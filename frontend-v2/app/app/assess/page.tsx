"use client";

import { Modal } from "@/components/modal";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { api, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { useAuth } from "@/components/auth-provider";
import { interactiveProps } from "@/components/interactive";
import { ErrorState, Loading } from "@/components/states";
import { ConfirmDialog, type ConfirmState } from "@/components/confirm";
import { ProgressRing } from "@/components/motion-system";
import { toast } from "@/lib/toast";
import { assessmentTypeClass, assessmentTypeLabel } from "@/lib/assessment-label";
import { RequestStatus } from "@/components/request-status";
import { AssessmentScoreTrend, type AssessmentScore } from "@/components/assessment-score-trend";

type Summary = {
  id: string;
  context_id: string;
  format: string;
  mode: string;
  status: string;
  question_count: number;
  created_at: string;
  completed_scores?: AssessmentScore[];
};
type Question = { id: string; position: number; prompt: string; options: string[]; concept_id: string | null };
type ReviewDetail = { question_id: string; selected_option: string | null; correct: boolean; correct_option: string };

type Draft = {
  assessmentId: string;
  attemptId: string;
  answers: Record<string, string>;
  marked: Record<string, boolean>;
};

const FORMAT_LABEL: Record<string, string> = { mcq: "Multiple Choice" };
const DIFFICULTIES = ["easy", "medium", "hard"];
const DRAFT_KEY = "aria_assess_draft";

function fmtDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
function formatLabel(f: string): string {
  return FORMAT_LABEL[f] ?? f;
}
function fmtClock(total: number): string {
  const m = Math.floor(total / 60);
  const s = String(total % 60).padStart(2, "0");
  return `${m}:${s}`;
}

export default function AssessPage() {
  const { context } = useActiveContext();
  const { user } = useAuth();
  return <AssessPageWorkspace key={`${user?.id ?? "anonymous"}:${context?.id ?? "no-subject"}`} />;
}

function AssessPageWorkspace() {
  const { context } = useActiveContext();
  const { user } = useAuth();
  const draftKey = `${DRAFT_KEY}:${user?.id ?? "anonymous"}:${context?.id ?? "no-subject"}`;
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [list, setList] = useState<Summary[]>([]);
  const [formats, setFormats] = useState<{ name: string; label: string }[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [createError, setCreateError] = useState("");
  const [materialReady, setMaterialReady] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [difficulty, setDifficulty] = useState("medium");
  const [questionCount, setQuestionCount] = useState(5);

  const [taking, setTaking] = useState<{ assessmentId: string; attemptId: string; questions: Question[] } | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [marked, setMarked] = useState<Record<string, boolean>>({});
  const [resumed, setResumed] = useState(false);
  const [draftWarning, setDraftWarning] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const [review, setReview] = useState<{ score: number; total: number; details: ReviewDetail[]; focus: string; wrongConcepts: string[] } | null>(null);
  const [confirmState, setConfirmState] = useState<ConfirmState>(null);

  const readDraft = (): Draft | null => {
    try {
      const draft = JSON.parse(window.localStorage.getItem(draftKey) ?? "null") as Draft | null;
      if (!draft || typeof draft.assessmentId !== "string" || typeof draft.attemptId !== "string"
        || !draft.answers || typeof draft.answers !== "object" || Array.isArray(draft.answers)
        || !Object.values(draft.answers).every(value => typeof value === "string")
        || !draft.marked || typeof draft.marked !== "object" || Array.isArray(draft.marked)
        || !Object.values(draft.marked).every(value => typeof value === "boolean")) return null;
      return draft;
    } catch {
      return null;
    }
  };
  const writeDraft = useCallback((d: Draft | null) => {
    try {
      if (d) window.localStorage.setItem(draftKey, JSON.stringify(d));
      else window.localStorage.removeItem(draftKey);
      setDraftWarning(null);
    } catch {
      setDraftWarning(d
        ? "Your draft could not be saved on this device. Keep this tab open; refreshing or leaving may lose your answers."
        : "The saved draft could not be cleared on this device. It may still appear when you reopen this assessment.");
    }
  }, [draftKey]);

  const load = useCallback(async (cid: string) => {
    const [summaries, fmtList] = await Promise.all([
      api<Summary[]>(`/api/v1/assessments?context_id=${cid}`),
      api<{ name: string; label: string }[]>("/api/v1/assessments/formats").catch(() => []),
    ]);
    setList(summaries);
    setFormats(fmtList);
    setFailed(false);
  }, []);

  useEffect(() => {
    if (!createOpen || !context) return;
    let cancelled = false;
    api<{ processing_status: string }[]>(`/api/v1/resources?context_id=${context.id}`)
      .then(items => { if (!cancelled) setMaterialReady(items.some(item => item.processing_status === "READY")); })
      .catch(() => { if (!cancelled) setMaterialReady(null); });
    return () => { cancelled = true; };
  }, [createOpen, context]);

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

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("review");
    if (!requested || !list.some(item => item.id === requested)) return;
    const card = document.getElementById(`review-${requested}`);
    card?.scrollIntoView({ block: "nearest" });
    card?.focus({ preventScroll: true });
  }, [list]);

  // timer while an attempt is open
  useEffect(() => {
    if (!taking) return;
    const t = window.setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => window.clearInterval(t);
  }, [taking]);

  // persist draft whenever answers/marks change mid-attempt
  useEffect(() => {
    if (!taking || !resumed) return;
    if (Object.keys(answers).length === 0 && Object.keys(marked).length === 0) return;
    const persistence = window.setTimeout(() => {
      writeDraft({ assessmentId: taking.assessmentId, attemptId: taking.attemptId, answers, marked });
    }, 0);
    return () => window.clearTimeout(persistence);
  }, [answers, marked, taking, resumed, writeDraft]);

  const beginAttempt = async (assessmentId: string, opts?: { resume?: boolean }) => {
    setBusy(true);
    try {
      const draft = readDraft();
      if (opts?.resume && draft && draft.assessmentId === assessmentId) {
        // resume: reuse saved attempt id, refetch stable question list
        const detail = await api<{ questions: Question[] }>(`/api/v1/assessments/${assessmentId}`);
        setAnswers(draft.answers);
        setMarked(draft.marked ?? {});
        setElapsed(0);
        setReview(null);
        setResumed(true);
        setTaking({ assessmentId, attemptId: draft.attemptId, questions: detail.questions });
        return;
      }
      const attempt = await api<{ attempt_id: string; questions: Question[] }>(
        `/api/v1/assessments/${assessmentId}/attempts`,
        { method: "POST" },
      );
      setAnswers({});
      setMarked({});
      setElapsed(0);
      setReview(null);
      setResumed(true);
      setTaking({ assessmentId, attemptId: attempt.attempt_id, questions: attempt.questions });
      writeDraft({ assessmentId, attemptId: attempt.attempt_id, answers: {}, marked: {} });
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not start the assessment.", "error");
    } finally {
      setBusy(false);
    }
  };

  const create = async () => {
    if (!context || busy || materialReady === false) return;
    setBusy(true);
    setCreateError("");
    try {
      const created = await api<{ id: string }>("/api/v1/assessments", {
        method: "POST",
        body: JSON.stringify({ context_id: context.id, format: "mcq", question_count: questionCount, difficulty }),
      });
      setCreateOpen(false);
      setDifficulty("medium");
      setQuestionCount(5);
      toast("Assessment created.");
      void load(context.id);
      await beginAttempt(created.id);
    } catch (e) {
      setCreateError(e instanceof ApiError ? e.message : "Could not create the assessment. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!taking || !context) return;
    if (Object.keys(answers).length < taking.questions.length) {
      toast("Answer every question before submitting.");
      return;
    }
    setBusy(true);
    try {
      const result = await api<{ score: number; total: number; details: ReviewDetail[] }>(
        `/api/v1/assessments/${taking.assessmentId}/attempts/${taking.attemptId}/submit`,
        {
          method: "POST",
          body: JSON.stringify({
            idempotency_key: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `aria-${Date.now()}`,
            answers,
          }),
        },
      );
      let focus = "";
      try {
        const adaptation = await api<{ decisions: { decision_type: string; reason: string }[] }>(
          `/api/v1/contexts/${context.id}/adaptation`,
        );
        focus = adaptation.decisions.find((d) => d.decision_type === "FOCUS_STUDY")?.reason ?? "";
      } catch {
        focus = "";
      }
      // concepts behind missed questions -> one-tap targeted retest
      const wrongQ = new Set(result.details.filter((d) => !d.correct).map((d) => d.question_id));
      const wrongConcepts = Array.from(
        new Set(taking.questions.filter((q) => wrongQ.has(q.id) && q.concept_id).map((q) => q.concept_id as string)),
      );
      setTaking(null);
      writeDraft(null);
      setResumed(false);
      setReview({ score: result.score, total: result.total, details: result.details, focus, wrongConcepts });
      void load(context.id);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not submit the assessment.", "error");
    } finally {
      setBusy(false);
    }
  };

  const retryMissed = async () => {
    if (!review || review.wrongConcepts.length === 0 || !context) return;
    setBusy(true);
    try {
      const created = await api<{ id: string }>("/api/v1/assessments", {
        method: "POST",
        body: JSON.stringify({
          context_id: context.id,
          format: "mcq",
          question_count: Math.max(3, Math.min(10, review.wrongConcepts.length * 2)),
          difficulty: "medium",
          concept_ids: review.wrongConcepts,
        }),
      });
      await beginAttempt(created.id);
      toast("Targeted retest ready — focused on your missed concepts.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not build the retest.", "error");
    } finally {
      setBusy(false);
    }
  };

  const reviewing = review;

  return (
    <div>
      <div className="section-head">
        <div>
          <h1 className="pg-title">Assessments</h1>
          <p className="pg-sub">Test what you know. Find what you don&apos;t. Improve where it matters.</p>
        </div>
        {!taking && !reviewing && (
          <button className="btn btn-primary" onClick={() => { setCreateError(""); setMaterialReady(null); setCreateOpen(true); }} disabled={busy}>
            <Icon name="plus" /> Create Assessment
          </button>
        )}
      </div>

      {draftWarning && <div className="banner" role="alert" style={{ marginBottom: 16 }}>{draftWarning}</div>}

      {!taking && !reviewing && (
        <>
          {!loading && !failed && <AssessmentScoreTrend scores={list.flatMap(item => item.completed_scores ?? [])} />}
          {loading ? (
            <Loading label="Loading assessments" />
          ) : failed ? (
            <ErrorState message="Could not load your assessments." onRetry={() => context && void load(context.id).catch(() => setFailed(true))} />
          ) : list.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-illustration" aria-hidden="true"><Icon name="clipboard" size={30} /></div>
              <p style={{ margin: "10px 0 0", fontSize: 14, color: "var(--text-1)" }}>
                Create your first assessment to test what you&apos;ve learned.
              </p>
              <div className="page-actions" style={{ justifyContent: "center", marginTop: 16 }}>
                <button className="btn btn-primary" onClick={() => { setCreateError(""); setMaterialReady(null); setCreateOpen(true); }}>Create your first assessment</button>
                <Link className="btn btn-ghost" href="/app/learn">Study with ARIA</Link>
              </div>
            </div>
          ) : (
            <div className="grid-2" style={{ gap: 18 }}>
              {list.map((a) => {
                const draft = typeof window !== "undefined" ? readDraft() : null;
                const hasDraft = draft?.assessmentId === a.id;
                return (
                  <div
                    className="card card-pad card-hover"
                    key={a.id}
                    id={`review-${a.id}`}
                    style={{ cursor: "pointer" }}
                    onClick={() => void beginAttempt(a.id, { resume: true })}
                    {...interactiveProps(() => void beginAttempt(a.id, { resume: true }))}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                      <div className="fsq-ic"><Icon name="clipboard" size={26} /></div>
                      <div>
                        <b style={{ fontSize: 17 }}>{a.mode === "DAILY_REVIEW" ? "Daily learning review" : formatLabel(a.format)}</b>
                        <div style={{ fontSize: 12, color: "var(--text-3)" }}>{a.question_count} questions · {fmtDate(a.created_at)}</div>
                        {a.mode === "DAILY_REVIEW" && <div style={{ fontSize: 12, color: "var(--text-2)" }}>Reviews today&apos;s tutoring conversation.</div>}
                      </div>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16 }}>
                      <span className={`tag-chip assessment-kind ${assessmentTypeClass(a.mode)}`}>{assessmentTypeLabel(a.mode)}</span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: "var(--accent-strong)", display: "inline-flex", alignItems: "center", gap: 4 }}>
                        {hasDraft ? "Resume test" : "Take test"} <Icon name="arrow" size={14} />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {taking && (
        <div className="card card-pad" style={{ maxWidth: 760 }}>
          {resumed && (
            <div className="banner" style={{ marginBottom: 16 }}>
              <span style={{ display: "inline-flex" }}><Icon name="refresh" size={18} /></span>
              <div style={{ flex: 1 }}>Saved progress restored — finish and submit when ready.</div>
              <button
                className="btn btn-ghost"
                onClick={() =>
                  setConfirmState({
                    title: "Discard saved progress",
                    body: "Discard your saved answers for this test? This cannot be undone.",
                    confirmLabel: "Discard",
                    onConfirm: () => {
                      writeDraft(null);
                      setResumed(false);
                      toast("Saved progress discarded.");
                    },
                  })
                }
              >
                Discard
              </button>
            </div>
          )}
          <div className="section-head" style={{ marginBottom: 16 }}>
            <h2 style={{ fontSize: 22, fontWeight: 800 }}>Assessment</h2>
            <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-2)", display: "inline-flex", alignItems: "center", gap: 12 }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <Icon name="clock" size={14} /> {fmtClock(elapsed)}
              </span>
              {Object.keys(marked).filter(Boolean).length > 0 && (
                <span className="tag-chip">{Object.values(marked).filter(Boolean).length} marked</span>
              )}
              <span>{Object.keys(answers).length}/{taking.questions.length} answered</span>
            </span>
          </div>
          <div className="quiz-progress" role="progressbar" aria-valuemin={0} aria-valuemax={taking.questions.length} aria-valuenow={Object.keys(answers).length} aria-label="Questions answered">
            <span style={{ width: `${(Object.keys(answers).length / taking.questions.length) * 100}%` }} />
          </div>
          {taking.questions.map((q) => (
            <div key={q.id} style={{ marginBottom: 22 }}>
              <p style={{ fontSize: 15, fontWeight: 700, margin: "0 0 10px", display: "flex", justifyContent: "space-between", gap: 10 }}>
                <span>{q.position}. {q.prompt}</span>
                <button
                  type="button"
                  className="btn btn-ghost"
                  aria-label={`Mark for review`}
                  aria-pressed={!!marked[q.id]}
                  title="Mark for review"
                  style={{ padding: "2px 6px", color: marked[q.id] ? "var(--streak)" : "var(--text-3)", flexShrink: 0 }}
                  onClick={() => setMarked((m) => ({ ...m, [q.id]: !m[q.id] }))}
                >
                  <Icon name="pin" size={15} />
                </button>
              </p>
              <div className="quiz-options">
                {q.options.map((opt) => (
                  <label key={opt} className={`quiz-option${answers[q.id] === opt ? " selected" : ""}`}>
                    <input
                      type="radio"
                      name={`q-${q.id}`}
                      checked={answers[q.id] === opt}
                      onChange={() => setAnswers((a) => ({ ...a, [q.id]: opt }))}
                    />
                    <span>{opt}</span>
                  </label>
                ))}
              </div>
            </div>
          ))}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, borderTop: "1px solid var(--border)", paddingTop: 18 }}>
            <button className="btn btn-ghost" onClick={() => setTaking(null)} disabled={busy}>Cancel</button>
            <button className="btn btn-primary" onClick={submit} disabled={busy}>
              Submit Answers <Icon name="arrow" />
            </button>
          </div>
        </div>
      )}

      {reviewing && (
        <div className="card card-pad" style={{ maxWidth: 720 }}>
          <button className="btn btn-ghost mb-2" onClick={() => setReview(null)}><Icon name="back" /> All assessments</button>
          {(() => {
            const scorePct = reviewing.total ? Math.round((reviewing.score / reviewing.total) * 100) : 0;
            const tone = scorePct >= 80 ? "success" : scorePct >= 50 ? "warning" : "danger";
            const headline = scorePct >= 80 ? "Great work!" : scorePct >= 50 ? "Good progress." : "Keep going.";
            return (
              <div className="score-hero">
                <ProgressRing value={scorePct} label="score" caption="score" size={150} tone={tone} />
                <div className="score-hero-text">
                  <h2>{headline}</h2>
                  <p>You answered <b>{reviewing.score}</b> of <b>{reviewing.total}</b> questions correctly.</p>
                  <div className="score-hero-stats">
                    <span className="score-stat ok"><Icon name="check" size={15} /> {reviewing.score} correct</span>
                    <span className="score-stat bad"><Icon name="x" size={15} /> {reviewing.total - reviewing.score} incorrect</span>
                  </div>
                </div>
              </div>
            );
          })()}
          {reviewing.focus && (
            <div className="banner" style={{ margin: "0 0 20px" }}>
              <span style={{ color: "var(--accent)", display: "inline-flex" }}><Icon name="lightbulb" size={20} /></span>
              <div>
                <b>ARIA Feedback</b>
                <p style={{ marginTop: 2 }}>{reviewing.focus}</p>
              </div>
            </div>
          )}
          <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 10 }}>Answer Review</h3>
          {reviewing.details.map((d) => (
            <div className="kv" key={d.question_id}>
              <span className="k" style={{ color: d.correct ? "var(--success-strong)" : "var(--danger-strong)" }}>
                <Icon name={d.correct ? "check" : "x"} size={16} /> {d.selected_option ?? "No answer"}
              </span>
              <span className="v">{d.correct ? "Correct" : <>Correct: {d.correct_option}</>}</span>
            </div>
          ))}
          <div style={{ display: "flex", gap: 10, marginTop: 18, flexWrap: "wrap" }}>
            {reviewing.wrongConcepts.length > 0 && (
              <button className="btn btn-secondary" onClick={() => void retryMissed()} disabled={busy}>
                <Icon name="target" /> Retry missed ({reviewing.wrongConcepts.length} concept{reviewing.wrongConcepts.length === 1 ? "" : "s"})
              </button>
            )}
            <Link href="/app/learn" className="btn btn-primary">
              <Icon name="message" /> Keep Learning
            </Link>
          </div>
        </div>
      )}

      {/* create modal */}
      <Modal open={createOpen} title="Create Assessment" onClose={() => setCreateOpen(false)}>
        <div className="modal">
          <div className="m-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: 14, marginBottom: 18 }}>
            <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}><Icon name="clipboard" size={20} /> Create Assessment</h3>
            <button className="btn btn-ghost" style={{ padding: 6 }} onClick={() => setCreateOpen(false)} aria-label="Close"><Icon name="x" size={16} /></button>
          </div>
          <div className="form-group">
            <label className="field-label">Format</label>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {(formats.length ? formats : [{ name: "mcq", label: "Multiple Choice" }]).map((f) => (
                <span className="tag-chip tag-chip-selected" key={f.name}>{f.label}</span>
              ))}
            </div>
          </div>
          {materialReady === false && <div className="inline-guidance" role="status">
            <b>Choose how you want to review</b>
            <p>For a material-based assessment, add ready study material. You can also study with ARIA without notes and choose Done for today to create a daily review.</p>
            <div className="action-links"><Link href="/app/materials">Add material</Link><Link href="/app/learn">Study with ARIA</Link></div>
          </div>}
          {materialReady !== false && <p className="field-help">Questions use your ready material. Very short material may need more detail to make a useful assessment.</p>}
          {createError && <div className="inline-error" role="alert"><b>Assessment could not be created</b><p>{createError}</p></div>}
          {busy && <RequestStatus label="Preparing your assessment…" />}
          <div className="form-group">
            <label className="field-label">Difficulty</label>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {DIFFICULTIES.map((d) => (
                <button
                  type="button"
                  key={d}
                  className={`tag-chip${difficulty === d ? " tag-chip-selected" : ""}`}
                  onClick={() => setDifficulty(d)}
                >
                  {d[0].toUpperCase() + d.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <div className="form-group">
            <label className="field-label" htmlFor="question-count">Number of Questions</label>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <button className="btn btn-ghost" style={{ padding: "6px 12px" }} onClick={() => setQuestionCount((q) => Math.max(1, q - 1))} aria-label="Fewer questions">−</button>
              <span id="question-count" style={{ minWidth: 40, textAlign: "center", fontWeight: 800 }}>{questionCount}</span>
              <button className="btn btn-ghost" style={{ padding: "6px 12px" }} onClick={() => setQuestionCount((q) => Math.min(20, q + 1))} aria-label="More questions">+</button>
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, borderTop: "1px solid var(--border)", paddingTop: 18, marginTop: 16 }}>
            <button className="btn btn-ghost" onClick={() => setCreateOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={create} disabled={busy || materialReady === false} title={materialReady === false ? "Add ready material, or create a daily review from Learn" : undefined}>
              {busy ? "Preparing…" : "Create Assessment"} <Icon name="arrow" />
            </button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog state={confirmState} onClose={() => setConfirmState(null)} />
    </div>
  );
}
