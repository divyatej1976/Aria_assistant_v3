"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { api } from "../../../lib/api";
import { useActiveContext } from "../../../components/use-active-context";

type Question = { id: string; position: number; prompt: string; options: string[]; concept_id: string | null };
type AttemptStart = { attempt_id: string; assessment_id: string; questions: Question[] };
type QuestionEval = { question_id: string; selected_option: string | null; correct: boolean; correct_option: string };
type AttemptResult = { attempt_id: string; evaluation_id: string; score: number; total: number; status: string; details: QuestionEval[] };
type ConceptState = { concept_id: string; concept_name: string; state: string; confidence: number; reason: string };

type View = "setup" | "taking" | "result";

const LETTERS = ["A", "B", "C", "D"];

export default function AssessPage() {
  const { context, loading } = useActiveContext();
  const [view, setView] = useState<View>("setup");
  const [count, setCount] = useState(5);
  const [difficulty, setDifficulty] = useState("medium");
  const [topic, setTopic] = useState("__all__");
  const [topics, setTopics] = useState<ConceptState[]>([]);
  const [generating, setGenerating] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [attemptId, setAttemptId] = useState("");
  const [assessmentId, setAssessmentId] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [index, setIndex] = useState(0);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!context) return;
    api<{ states: ConceptState[] }>(`/api/v1/contexts/${context.id}/adaptation`)
      .then((summary) => setTopics(summary.states))
      .catch(() => setTopics([]));
  }, [context]);

  if (loading) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <p className="text-body-md text-on-surface-variant">Loading assessment workspace…</p>
      </div>
    );
  }

  if (!context) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <div className="bg-surface shadow-extruded rounded-3xl p-8 max-w-xl">
          <h2 className="text-headline-md text-on-surface mb-4">No learning context yet</h2>
          <p className="text-body-md text-on-surface-variant mb-6">Set up your context before generating assessments.</p>
          <Link href="/onboarding" className="inline-flex items-center gap-2 px-8 py-4 rounded-xl shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
            Initialize learning journey
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </Link>
        </div>
      </div>
    );
  }

  const activeContext = context;
  const weakIds = topics
    .filter((state) => state.state === "NEEDS_REVIEW" || state.state === "DEVELOPING")
    .map((state) => state.concept_id);

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGenerating(true);
    setError("");
    try {
      const isTargeted = topic !== "__all__";
      const conceptIds = topic === "__weak__" ? weakIds : isTargeted ? [topic] : [];
      const created = await api<{ id: string }>("/api/v1/assessments", {
        method: "POST",
        body: JSON.stringify({
          context_id: activeContext.id,
          format: "mcq",
          question_count: count,
          difficulty,
          mode: conceptIds.length > 0 ? "TARGETED" : "BASELINE",
          concept_ids: conceptIds,
        }),
      });
      const started = await api<AttemptStart>(`/api/v1/assessments/${created.id}/attempts`, {
        method: "POST",
      });
      setAssessmentId(started.assessment_id);
      setAttemptId(started.attempt_id);
      setQuestions(started.questions);
      setAnswers({});
      setIndex(0);
      setView("taking");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to generate assessment");
    } finally {
      setGenerating(false);
    }
  }

  function selectAnswer(questionId: string, option: string) {
    const next = { ...answers, [questionId]: option };
    setAnswers(next);
    void api(`/api/v1/assessments/${assessmentId}/attempts/${attemptId}/answers`, {
      method: "PUT",
      body: JSON.stringify({ answers: next }),
    }).catch(() => {
      // Best-effort autosave; the final set is submitted explicitly.
    });
  }

  async function submit() {
    setSubmitting(true);
    setError("");
    try {
      const submitted = await api<AttemptResult>(
        `/api/v1/assessments/${assessmentId}/attempts/${attemptId}/submit`,
        {
          method: "POST",
          body: JSON.stringify({ idempotency_key: crypto.randomUUID(), answers }),
        },
      );
      setResult(submitted);
      setConfirmOpen(false);
      setView("result");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to submit assessment");
    } finally {
      setSubmitting(false);
    }
  }

  const answeredCount = Object.keys(answers).length;
  const question = questions[index];

  return (
    <div className="p-container-padding md:p-section-margin w-full max-w-3xl mx-auto flex flex-col gap-8">
      <h2 className="text-headline-xl text-on-background">Assessment</h2>

      {view === "setup" && (
        <form onSubmit={generate} className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <label className="text-label-md text-on-surface-variant" htmlFor="topic">Topic</label>
            <select
              id="topic"
              className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface"
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
            >
              <option value="__all__">Entire context (Baseline)</option>
              {weakIds.length > 0 && <option value="__weak__">Weak concepts (Targeted retest)</option>}
              {topics.map((state) => (
                <option key={state.concept_id} value={state.concept_id}>{state.concept_name}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="flex flex-col gap-2">
              <label className="text-label-md text-on-surface-variant" htmlFor="count">Questions</label>
              <select id="count" className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface" value={count} onChange={(event) => setCount(Number(event.target.value))}>
                {[3, 5, 8, 10, 15, 20].map((value) => <option key={value} value={value}>{value}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-label-md text-on-surface-variant" htmlFor="difficulty">Difficulty</label>
              <select id="difficulty" className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface" value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>
          {error && <p className="text-label-md text-error" role="alert">{error}</p>}
          <button
            type="submit"
            disabled={generating}
            className="h-14 bg-surface rounded-2xl shadow-extruded btn-extruded flex items-center justify-center gap-2 text-label-md font-bold text-secondary disabled:opacity-60"
          >
            {generating ? "Generating…" : "Generate assessment"}
            {!generating && <span className="material-symbols-outlined">auto_awesome</span>}
          </button>
        </form>
      )}

      {view === "taking" && question && (
        <>
          <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <p className="text-label-md text-secondary tracking-widest uppercase">{topic === "__all__" ? "Baseline" : "Targeted check"}</p>
              <p className="text-label-md text-on-surface-variant">Question {index + 1} of {questions.length}</p>
            </div>
            <h3 className="text-headline-md text-on-surface">{question.prompt}</h3>
            <ul className="flex flex-col gap-3">
              {question.options.map((option, optionIndex) => {
                const letter = LETTERS[optionIndex];
                const selected = answers[question.id] === letter;
                return (
                  <li key={letter}>
                    <button
                      type="button"
                      onClick={() => selectAnswer(question.id, letter)}
                      className={`w-full text-left px-5 py-4 rounded-xl flex items-center gap-4 transition-all ${
                        selected ? "bg-surface-container shadow-injected text-secondary" : "bg-surface shadow-extruded btn-extruded text-on-surface"
                      }`}
                    >
                      <span className={`w-8 h-8 rounded-full flex items-center justify-center text-label-md ${selected ? "bg-secondary text-on-secondary" : "bg-surface shadow-extruded text-on-surface-variant"}`}>{letter}</span>
                      <span className="text-body-md">{option}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                disabled={index === 0}
                onClick={() => setIndex((value) => value - 1)}
                className="px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-on-surface-variant disabled:opacity-40"
              >
                Previous
              </button>
              {index < questions.length - 1 ? (
                <button
                  type="button"
                  onClick={() => setIndex((value) => value + 1)}
                  className="px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary"
                >
                  Next
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirmOpen(true)}
                  className="px-6 py-3 rounded-full bg-secondary text-on-secondary text-label-md font-bold shadow-extruded btn-extruded"
                >
                  Submit assessment
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-2 pt-2 border-t border-surface-dim">
              {questions.map((item, itemIndex) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setIndex(itemIndex)}
                  className={`w-9 h-9 rounded-full flex items-center justify-center text-label-sm ${
                    itemIndex === index
                      ? "bg-secondary text-on-secondary shadow-injected"
                      : answers[item.id]
                        ? "bg-tertiary-container text-on-tertiary-container shadow-extruded"
                        : "bg-surface shadow-extruded text-on-surface-variant"
                  }`}
                >
                  {answers[item.id] ? "✓" : itemIndex + 1}
                </button>
              ))}
            </div>
          </div>
          {error && <p className="text-label-md text-error" role="alert">{error}</p>}
        </>
      )}

      {view === "result" && result && (
        <>
          <div className="bg-surface shadow-extruded rounded-3xl p-8 text-center">
            <p className="text-label-md text-secondary uppercase tracking-widest">Assessment complete</p>
            <h3 className="text-headline-xl text-on-surface mt-2">{result.score} / {result.total} correct</h3>
            <p className="text-body-md text-on-surface-variant mt-3">
              Score is deterministic: the same answers always produce the same result.
            </p>
          </div>
          <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-6">
            {questions.map((item, itemIndex) => {
              const detail = result.details.find((d) => d.question_id === item.id);
              return (
                <div key={item.id} className={detail?.correct ? "border-l-4 border-tertiary pl-4" : "border-l-4 border-error pl-4"}>
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`material-symbols-outlined ${detail?.correct ? "text-tertiary" : "text-error"}`}>
                      {detail?.correct ? "check_circle" : "cancel"}
                    </span>
                    <p className="text-body-md text-on-surface">{item.prompt}</p>
                  </div>
                  <ul className="flex flex-col gap-2">
                    {item.options.map((option, optionIndex) => {
                      const letter = LETTERS[optionIndex];
                      const isCorrect = detail?.correct_option === letter;
                      const isSelected = detail?.selected_option === letter;
                      return (
                        <li key={letter} className={`px-4 py-2 rounded-xl text-body-md ${isCorrect ? "bg-tertiary-container/40 text-on-surface" : isSelected ? "bg-error-container/40 text-on-surface" : "text-on-surface-variant"}`}>
                          {letter}. {option}
                          {isCorrect && " · correct"}
                          {isSelected && !isCorrect && " · your answer"}
                        </li>
                      );
                    })}
                  </ul>
                  <p className="text-label-sm text-on-surface-variant mt-2">Question {itemIndex + 1}</p>
                </div>
              );
            })}
          </div>
          <div className="flex flex-wrap gap-3">
            <button onClick={() => setView("setup")} className="px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
              New assessment
            </button>
            <Link href="/app/learn" className="px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-on-surface-variant">
              Continue studying
            </Link>
            <Link href="/app/progress" className="px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-on-surface-variant">
              View progress
            </Link>
          </div>
          {error && <p className="text-label-md text-error" role="alert">{error}</p>}
        </>
      )}

      {confirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="bg-surface shadow-extruded rounded-3xl p-8 max-w-sm w-full flex flex-col gap-4">
            <h3 className="text-headline-md text-on-surface">Submit assessment?</h3>
            <p className="text-body-md text-on-surface-variant">Answered: {answeredCount} of {questions.length}</p>
            <p className="text-body-md text-on-surface-variant">Unanswered: {questions.length - answeredCount}</p>
            <p className="text-body-md text-on-surface">After submission, answers cannot be changed.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setConfirmOpen(false)} className="px-5 py-2 rounded-full text-label-md text-on-surface-variant">Continue assessment</button>
              <button onClick={() => void submit()} disabled={submitting} className="px-5 py-2 rounded-full bg-secondary text-on-secondary text-label-md font-bold shadow-extruded btn-extruded disabled:opacity-60">
                {submitting ? "Submitting…" : "Submit"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
