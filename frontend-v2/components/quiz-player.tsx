"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icons";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";

export type QuizQuestion = {
  id: string;
  position: number;
  prompt: string;
  options: string[];
  concept_id: string | null;
  kind?: string;
};
export type QuizSettings = { timing: string; time_limit_seconds: number | null; reveal: string; source?: string };
type Feedback = { correct: boolean; correct_answer: string; explanation: string | null };

export const DONT_KNOW = "I don't know";

function clock(total: number): string {
  const safe = Math.max(0, total);
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, "0")}`;
}

/** One question at a time. Practice mode checks each answer straight away;
 * exam mode reveals everything at the end. Answers are reported upward on
 * every change so the page can keep a resumable draft. */
export function QuizPlayer({
  assessmentId, attemptId, questions, settings, answers, onAnswer, onFinish, onExit, busy,
}: {
  assessmentId: string;
  attemptId: string;
  questions: QuizQuestion[];
  settings: QuizSettings;
  answers: Record<string, string>;
  onAnswer: (questionId: string, value: string) => void;
  onFinish: (answers: Record<string, string>) => void;
  onExit: () => void;
  busy: boolean;
}) {
  const practice = settings.reveal === "practice";
  const firstOpen = Math.max(0, questions.findIndex((q) => !(q.id in answers)));
  const [index, setIndex] = useState(firstOpen);
  const [feedback, setFeedback] = useState<Record<string, Feedback>>({});
  const [checking, setChecking] = useState(false);
  const [flagged, setFlagged] = useState<Record<string, boolean>>({});
  // Exam mode ends on a review screen listing unanswered and flagged questions.
  const [reviewing, setReviewing] = useState(false);
  const limit = settings.time_limit_seconds ?? 0;
  const [remaining, setRemaining] = useState(limit);
  const [elapsed, setElapsed] = useState(0);
  const answersRef = useRef(answers);
  useEffect(() => { answersRef.current = answers; }, [answers]);

  const question = questions[index];
  const value = answers[question.id] ?? "";
  const shown = feedback[question.id];
  const isLast = index === questions.length - 1;
  const answeredCount = questions.filter((q) => q.id in answers).length;

  const finish = useCallback(() => {
    // Anything left unanswered counts as "I don't know" rather than blocking submission.
    const complete = { ...answersRef.current };
    for (const q of questions) if (!(q.id in complete)) complete[q.id] = DONT_KNOW;
    onFinish(complete);
  }, [onFinish, questions]);

  const check = useCallback(async (answer: string) => {
    if (checking) return;
    setChecking(true);
    try {
      const result = await api<Feedback>(`/api/v1/assessments/${assessmentId}/attempts/${attemptId}/check`, {
        method: "POST", body: JSON.stringify({ question_id: question.id, answer }),
      });
      setFeedback((all) => ({ ...all, [question.id]: result }));
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Could not check this answer. Try again.", "error");
    } finally {
      setChecking(false);
    }
  }, [assessmentId, attemptId, checking, question.id]);

  // Moving to another question restarts a per-question timer.
  const goTo = useCallback((target: number) => {
    setReviewing(false);
    setIndex(target);
    if (settings.timing === "per_question") setRemaining(limit);
  }, [limit, settings.timing]);

  const next = useCallback(() => {
    if (!isLast) goTo(index + 1);
    else if (practice) finish();
    else setReviewing(true);
  }, [finish, goTo, index, isLast, practice]);

  const answer = (text: string) => {
    if (practice && shown) return;
    onAnswer(question.id, text);
  };

  const primary = () => {
    if (practice && !shown) {
      if (!value.trim()) return;
      void check(value);
      return;
    }
    next();
  };

  // Timers: a countdown for the whole quiz or for each question, otherwise a quiet stopwatch.
  useEffect(() => {
    const timer = window.setInterval(() => {
      setElapsed((e) => e + 1);
      if (settings.timing !== "none") setRemaining((r) => r - 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [settings.timing]);

  useEffect(() => {
    if (settings.timing === "none" || remaining > 0) return;
    if (settings.timing === "total") {
      toast("Time is up. Your answers have been submitted.");
      finish();
      return;
    }
    // Per-question timer ran out: count it as "I don't know" and move on.
    if (!(question.id in answersRef.current)) onAnswer(question.id, DONT_KNOW);
    if (practice && !shown) void check(answersRef.current[question.id] ?? DONT_KNOW);
    else next();
  }, [remaining]); // eslint-disable-line react-hooks/exhaustive-deps -- react only to the clock reaching zero

  // Keyboard: 1-4 pick an option, Enter checks or moves on.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (reviewing) return;
      const target = event.target as HTMLElement | null;
      if (target?.tagName === "TEXTAREA" || (target?.tagName === "INPUT" && (target as HTMLInputElement).type === "text")) {
        if (event.key === "Enter") { event.preventDefault(); primary(); }
        return;
      }
      const n = Number(event.key);
      if (n >= 1 && n <= question.options.length) answer(question.options[n - 1]);
      if (event.key === "Enter") primary();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const timeLabel = settings.timing === "none" ? clock(elapsed) : `${clock(remaining)} left`;
  const lowTime = settings.timing !== "none" && remaining <= 10;

  return (
    <section className="quiz-player" aria-label="Quiz">
      <header className="quiz-player-head">
        <button type="button" className="btn btn-ghost" onClick={onExit} disabled={busy}><Icon name="back" size={15} /> Save and exit</button>
        <span className={`quiz-clock${lowTime ? " low" : ""}`} aria-live={lowTime ? "polite" : "off"}>
          <Icon name="clock" size={14} /> {timeLabel}
        </span>
      </header>
      <div className="quiz-meta">
        <span>Question {index + 1} of {questions.length}</span>
        <span>{practice ? "Practice · answers shown as you go" : "Exam · answers shown at the end"}</span>
      </div>
      <div className="quiz-progress" role="progressbar" aria-valuemin={0} aria-valuemax={questions.length} aria-valuenow={answeredCount} aria-label="Questions answered">
        <span style={{ width: `${(answeredCount / questions.length) * 100}%` }} />
      </div>
      <nav className="quiz-nav" aria-label="Questions">
        {questions.map((q, i) => (
          <button key={q.id} type="button" onClick={() => goTo(i)} aria-current={!reviewing && i === index ? "step" : undefined}
            aria-label={`Question ${i + 1}${q.id in answers ? ", answered" : ""}${flagged[q.id] ? ", flagged" : ""}`}
            className={`${q.id in answers ? "answered" : ""}${flagged[q.id] ? " flagged" : ""}${!reviewing && i === index ? " current" : ""}`}>
            {i + 1}
          </button>
        ))}
      </nav>

      {reviewing ? (() => {
        const unanswered = questions.map((q, i) => ({ q, i })).filter(({ q }) => !(q.id in answers));
        const marked = questions.map((q, i) => ({ q, i })).filter(({ q }) => flagged[q.id]);
        return (
          <article className="quiz-card quiz-review-screen" aria-labelledby="quiz-review-title">
            <h2 id="quiz-review-title">Ready to submit?</h2>
            <p>{answeredCount} of {questions.length} answered.{unanswered.length ? ` Unanswered questions count as "I don't know".` : ""}</p>
            {unanswered.length > 0 && <div className="quiz-review-group"><b>Unanswered</b>
              <span>{unanswered.map(({ q, i }) => <button key={q.id} type="button" className="tag-chip" onClick={() => goTo(i)}>Question {i + 1}</button>)}</span></div>}
            {marked.length > 0 && <div className="quiz-review-group"><b>Flagged to review</b>
              <span>{marked.map(({ q, i }) => <button key={q.id} type="button" className="tag-chip" onClick={() => goTo(i)}>Question {i + 1}</button>)}</span></div>}
            <div className="quiz-actions">
              <button type="button" className="btn btn-ghost" onClick={() => goTo(index)} disabled={busy}><Icon name="back" size={15} /> Back to questions</button>
              <button type="button" className="btn btn-primary" onClick={finish} disabled={busy}>Submit answers <Icon name="arrow" size={15} /></button>
            </div>
          </article>
        );
      })() : <>
      <article className="quiz-card">
        <div className="quiz-card-top">
          <span className="quiz-kind">{question.kind === "true_false" ? "True or false" : question.kind === "short_answer" ? "Type your answer" : "Choose one"}</span>
          {!practice && (
            <button type="button" className={`quiz-flag${flagged[question.id] ? " on" : ""}`} aria-pressed={!!flagged[question.id]}
              onClick={() => setFlagged((f) => ({ ...f, [question.id]: !f[question.id] }))}>
              <Icon name="pin" size={13} /> {flagged[question.id] ? "Flagged" : "Flag to review"}
            </button>
          )}
        </div>
        <p className="quiz-prompt">{question.prompt}</p>

        {question.kind === "short_answer" ? (
          <input className="input quiz-text" type="text" aria-label="Your answer" placeholder="Type your answer"
            value={value === DONT_KNOW ? "" : value} disabled={practice && !!shown}
            onChange={(e) => answer(e.target.value)} autoFocus />
        ) : (
          <div className="quiz-options" role="radiogroup" aria-label="Answer options">
            {question.options.map((option, i) => {
              const state = shown ? (option === shown.correct_answer ? " right" : option === value ? " wrong" : "") : "";
              return (
                <label key={option} className={`quiz-option${value === option ? " selected" : ""}${state}`}>
                  <input type="radio" name={`q-${question.id}`} checked={value === option}
                    disabled={practice && !!shown} onChange={() => answer(option)} />
                  <span className="quiz-key" aria-hidden="true">{i + 1}</span>
                  <span>{option}</span>
                </label>
              );
            })}
          </div>
        )}

        {shown && (
          <div className={`quiz-feedback${shown.correct ? " right" : " wrong"}`} role="status">
            <b><Icon name={shown.correct ? "check" : "x"} size={15} /> {shown.correct ? "Correct" : "Not quite"}</b>
            {!shown.correct && <p>Answer: <strong>{shown.correct_answer}</strong></p>}
            {shown.explanation && <p>{shown.explanation}</p>}
          </div>
        )}
      </article>

      <footer className="quiz-actions">
        <button type="button" className="btn btn-ghost" disabled={index === 0 || busy} onClick={() => goTo(index - 1)}>
          <Icon name="back" size={15} /> Back
        </button>
        {!(practice && shown) && (
          <button type="button" className="btn btn-ghost" disabled={busy || checking} onClick={() => {
            onAnswer(question.id, DONT_KNOW);
            if (practice) void check(DONT_KNOW); else next();
          }}>I don&apos;t know</button>
        )}
        <button type="button" className="btn btn-primary" onClick={primary}
          disabled={busy || checking || (practice && !shown && !value.trim())}>
          {practice && !shown ? (checking ? "Checking…" : "Check") : isLast ? (practice ? "Finish" : "Review answers") : "Next"} <Icon name="arrow" size={15} />
        </button>
      </footer>
      </>}
    </section>
  );
}
