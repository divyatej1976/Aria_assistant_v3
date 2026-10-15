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
import { QuizPlayer, DONT_KNOW, type QuizQuestion, type QuizSettings } from "@/components/quiz-player";
import { QuizSetup, rememberSetup, savedSetup, setupProblem, setupRequest, DEFAULT_SETUP, type QuizSetupValues } from "@/components/quiz-setup";

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
type Question = QuizQuestion;
type ReviewDetail = {
  question_id: string; selected_option: string | null; correct: boolean; correct_option: string;
  correct_answer?: string | null; explanation?: string | null;
};
const NO_SETTINGS: QuizSettings = { timing: "none", time_limit_seconds: null, reveal: "exam" };

type Draft = {
  assessmentId: string;
  attemptId: string;
  answers: Record<string, string>;
  marked: Record<string, boolean>;
};

const FORMAT_LABEL: Record<string, string> = {
  mcq: "Multiple choice", true_false: "True or false", short_answer: "Short answer", mixed: "Mixed questions",
};
const DRAFT_KEY = "aria_assess_draft";

function fmtDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
function formatLabel(f: string): string {
  return FORMAT_LABEL[f] ?? f;
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
  const [createOpen, setCreateOpen] = useState(false);
  const [createError, setCreateError] = useState("");
  const [materialReady, setMaterialReady] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [setup, setSetup] = useState<QuizSetupValues>(DEFAULT_SETUP);

  const [taking, setTaking] = useState<{ assessmentId: string; attemptId: string; questions: Question[]; settings: QuizSettings } | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [marked, setMarked] = useState<Record<string, boolean>>({});
  const [resumed, setResumed] = useState(false);
  const [draftWarning, setDraftWarning] = useState<string | null>(null);

  const [review, setReview] = useState<{ score: number; total: number; details: ReviewDetail[]; focus: string; wrongConcepts: string[]; questions: Question[] } | null>(null);
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
    const summaries = await api<Summary[]>(`/api/v1/assessments?context_id=${cid}`);
    setList(summaries);
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

  // "Quiz me" from a roadmap milestone opens the setup on that topic.
  useEffect(() => {
    const topic = new URLSearchParams(window.location.search).get("quiz_topic")?.trim().slice(0, 300);
    if (!topic) return;
    // The URL is only readable after hydration, so this one-time read happens in an effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSetup({ ...savedSetup(), source: "topic", topic });
    setCreateError("");
    setCreateOpen(true);
  }, []);

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("review");
    if (!requested || !list.some(item => item.id === requested)) return;
    const card = document.getElementById(`review-${requested}`);
    card?.scrollIntoView({ block: "nearest" });
    card?.focus({ preventScroll: true });
  }, [list]);

  // persist draft whenever answers/marks change mid-attempt
  useEffect(() => {
    if (!taking) return;
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
        const detail = await api<{ questions: Question[]; settings?: QuizSettings }>(`/api/v1/assessments/${assessmentId}`);
        setAnswers(draft.answers);
        setMarked(draft.marked ?? {});
        setReview(null);
        setResumed(true);
        setTaking({ assessmentId, attemptId: draft.attemptId, questions: detail.questions, settings: detail.settings ?? NO_SETTINGS });
        return;
      }
      const attempt = await api<{ attempt_id: string; questions: Question[]; settings?: QuizSettings }>(
        `/api/v1/assessments/${assessmentId}/attempts`,
        { method: "POST" },
      );
      setAnswers({});
      setMarked({});
      setReview(null);
      setResumed(false);
      setTaking({ assessmentId, attemptId: attempt.attempt_id, questions: attempt.questions, settings: attempt.settings ?? NO_SETTINGS });
      writeDraft({ assessmentId, attemptId: attempt.attempt_id, answers: {}, marked: {} });
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not start the assessment.", "error");
    } finally {
      setBusy(false);
    }
  };

  const create = async () => {
    if (!context || busy || setupProblem(setup, materialReady)) return;
    setBusy(true);
    setCreateError("");
    try {
      const created = await api<{ id: string }>("/api/v1/assessments", {
        method: "POST",
        body: JSON.stringify(setupRequest(context.id, setup)),
      });
      rememberSetup(setup);
      setCreateOpen(false);
      void load(context.id);
      await beginAttempt(created.id);
    } catch (e) {
      setCreateError(e instanceof ApiError ? e.message : "Could not create the assessment. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const submit = async (finalAnswers: Record<string, string> = answers) => {
    if (!taking || !context) return;
    if (Object.keys(finalAnswers).length < taking.questions.length) {
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
            answers: finalAnswers,
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
      setReview({ score: result.score, total: result.total, details: result.details, focus, wrongConcepts, questions: taking.questions });
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
          ...setupRequest(context.id, { ...savedSetup(), source: "library" }),
          question_count: Math.max(3, Math.min(10, review.wrongConcepts.length * 2)),
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
      <div className="section-head" hidden={!!taking}>
        <div>
          <h1 className="pg-title">Practice</h1>
          <p className="pg-sub">Test what you know. Find what you don&apos;t. Improve where it matters.</p>
        </div>
        {!taking && !reviewing && (
          <button className="btn btn-primary" onClick={() => { setCreateError(""); setMaterialReady(null); setSetup(savedSetup()); setCreateOpen(true); }} disabled={busy}>
            <Icon name="plus" /> Create assessment
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
                <button className="btn btn-primary" onClick={() => { setCreateError(""); setMaterialReady(null); setSetup(savedSetup()); setCreateOpen(true); }}>Create your first assessment</button>
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
                    <div className="card-header">
                      <div className="fsq-ic"><Icon name="clipboard" size={26} /></div>
                      <div>
                        <b style={{ fontSize: 17 }}>{a.mode === "DAILY_REVIEW" ? "Daily learning review" : formatLabel(a.format)}</b>
                        <div style={{ fontSize: 12, color: "var(--text-3)" }}>{a.question_count} questions · {fmtDate(a.created_at)}</div>
                        {a.mode === "DAILY_REVIEW" && <div style={{ fontSize: 12, color: "var(--text-2)" }}>Reviews today&apos;s tutoring conversation.</div>}
                      </div>
                    </div>
                    <div className="ui-row-between ui-mt-16">
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
        <>
          {resumed && (
            <div className="banner" style={{ marginBottom: 16, maxWidth: 760 }}>
              <span style={{ display: "inline-flex" }}><Icon name="refresh" size={18} /></span>
              <div style={{ flex: 1 }}>Saved progress restored. Pick up where you left off.</div>
              <button
                className="btn btn-ghost"
                onClick={() =>
                  setConfirmState({
                    title: "Discard saved progress",
                    body: "Discard your saved answers for this quiz? This cannot be undone.",
                    confirmLabel: "Discard",
                    onConfirm: () => {
                      writeDraft(null);
                      setResumed(false);
                      setAnswers({});
                      toast("Saved progress discarded.");
                    },
                  })
                }
              >
                Discard
              </button>
            </div>
          )}
          <QuizPlayer key={taking.attemptId} assessmentId={taking.assessmentId} attemptId={taking.attemptId}
            questions={taking.questions} settings={taking.settings} answers={answers} busy={busy}
            onAnswer={(id, value) => setAnswers((a) => ({ ...a, [id]: value }))}
            onFinish={(complete) => { setAnswers(complete); void submit(complete); }}
            onExit={() => { setTaking(null); toast("Progress saved. Open the quiz again to continue."); }} />
        </>
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
          <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 10 }}>Answer review</h3>
          <ol className="quiz-review">
            {reviewing.details.map((d) => {
              const question = reviewing.questions.find((q) => q.id === d.question_id);
              const answer = d.correct_answer ?? d.correct_option;
              const ask = `I got this quiz question wrong. Help me understand it.\n\nQuestion: ${question?.prompt ?? ""}\nMy answer: ${d.selected_option ?? DONT_KNOW}\nCorrect answer: ${answer}`;
              return (
                <li key={d.question_id} className={d.correct ? "right" : "wrong"}>
                  <p className="quiz-review-q">{question?.prompt}</p>
                  <p><Icon name={d.correct ? "check" : "x"} size={14} /> Your answer: <b>{d.selected_option || DONT_KNOW}</b></p>
                  {!d.correct && <p>Correct answer: <b>{answer}</b></p>}
                  {d.explanation && <p className="quiz-review-why">{d.explanation}</p>}
                  {!d.correct && <Link className="quiz-review-ask" href={`/app/learn?ask=${encodeURIComponent(ask.slice(0, 1500))}`}><Icon name="message" size={13} /> Explain this in chat</Link>}
                </li>
              );
            })}
          </ol>
          <div style={{ display: "flex", gap: 10, marginTop: 18, flexWrap: "wrap" }}>
            {reviewing.wrongConcepts.length > 0 && (
              <button className="btn btn-secondary" onClick={() => void retryMissed()} disabled={busy}>
                <Icon name="target" /> Retry missed ({reviewing.wrongConcepts.length} concept{reviewing.wrongConcepts.length === 1 ? "" : "s"})
              </button>
            )}
            <Link href="/app/learn" className="btn btn-primary">
              <Icon name="message" /> Keep learning
            </Link>
          </div>
        </div>
      )}

      {/* create modal */}
      <Modal open={createOpen} title="Create assessment" onClose={() => setCreateOpen(false)}>
        <div className="modal">
          <div className="m-head dialog-heading">
            <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}><Icon name="clipboard" size={20} /> Create assessment</h3>
            <button className="btn btn-ghost" style={{ padding: 6 }} onClick={() => setCreateOpen(false)} aria-label="Close"><Icon name="x" size={16} /></button>
          </div>
          {context && <QuizSetup contextId={context.id} values={setup} onChange={setSetup} />}
          {setupProblem(setup, materialReady) && <p className="field-help" role="status">{setupProblem(setup, materialReady)}</p>}
          {createError && <div className="inline-error" role="alert"><b>Assessment could not be created</b><p>{createError}</p></div>}
          {busy && <RequestStatus label="Preparing your assessment…" />}
          <div className="dialog-actions ui-mt-16">
            <button className="btn btn-ghost" onClick={() => setCreateOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={create} disabled={busy || !!setupProblem(setup, materialReady)}>
              {busy ? "Preparing…" : "Start quiz"} <Icon name="arrow" />
            </button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog state={confirmState} onClose={() => setConfirmState(null)} />
    </div>
  );
}
