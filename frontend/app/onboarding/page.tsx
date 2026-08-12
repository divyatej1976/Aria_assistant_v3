"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "../../lib/api";

type Context = { id: string; title: string };

const MASTERY_LEVELS = ["Beginner", "Intermediate", "Advanced"];

export default function OnboardingPage() {
  const router = useRouter();
  const [learningVector, setLearningVector] = useState("");
  const [mastery, setMastery] = useState("Beginner");
  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Context[]>("/api/v1/contexts")
      .then((contexts) => {
        if (contexts.length > 0) router.replace("/app");
      })
      .catch(() => {
        // Ignore; the form submit will surface real errors.
      });
  }, [router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/v1/contexts", {
        method: "POST",
        body: JSON.stringify({
          title: learningVector,
          description: goal || undefined,
          configuration: { mastery_level: mastery.toLowerCase() },
        }),
      });
      router.push("/app");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to start learning");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-background flex items-center justify-center p-4 sm:p-container-padding">
      <div className="w-full max-w-2xl flex flex-col gap-8">
        <header className="text-center flex flex-col items-center gap-4 mb-2">
          <div className="w-16 h-16 rounded-2xl bg-surface shadow-extruded flex items-center justify-center text-secondary">
            <span className="material-symbols-outlined text-4xl ms-fill">all_inclusive</span>
          </div>
          <h1 className="text-headline-lg text-on-surface">Neural Initialization</h1>
          <p className="text-body-md text-on-surface-variant max-w-md">
            Configure your learning parameters to begin the calibration sequence.
          </p>
        </header>

        <form className="bg-surface rounded-3xl p-6 sm:p-10 shadow-extruded flex flex-col gap-8" onSubmit={submit}>
          <div className="flex flex-col gap-2">
            <label className="text-label-md text-on-surface-variant flex items-center gap-2" htmlFor="learning_vector">
              <span className="material-symbols-outlined text-outline">explore</span>
              Primary Learning Vector
            </label>
            <input
              id="learning_vector"
              required
              className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface placeholder:text-outline-variant"
              placeholder="e.g. Database Management Systems"
              value={learningVector}
              onChange={(event) => setLearningVector(event.target.value)}
            />
          </div>

          <fieldset className="flex flex-col gap-2">
            <legend className="text-label-md text-on-surface-variant flex items-center gap-2 mb-1">
              <span className="material-symbols-outlined text-outline">signal_cellular_alt</span>
              Current Mastery Level
            </legend>
            <div className="grid grid-cols-3 gap-4">
              {MASTERY_LEVELS.map((level) => {
                const selected = mastery === level;
                return (
                  <button
                    key={level}
                    type="button"
                    onClick={() => setMastery(level)}
                    className={`h-12 rounded-xl text-label-md transition-all duration-200 ${
                      selected
                        ? "bg-surface-container shadow-injected text-secondary font-bold"
                        : "bg-surface-container shadow-extruded text-on-surface-variant hover:opacity-80"
                    }`}
                  >
                    {level}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <div className="flex flex-col gap-2">
            <label className="text-label-md text-on-surface-variant flex items-center gap-2" htmlFor="goal_objective">
              <span className="material-symbols-outlined text-outline">flag</span>
              Goal Objective
            </label>
            <textarea
              id="goal_objective"
              className="bg-surface-container rounded-2xl input-injected p-6 text-on-surface placeholder:text-outline-variant resize-none"
              placeholder="What do you want to achieve?"
              rows={4}
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
            />
          </div>

          {error && <p className="text-label-md text-error" role="alert">{error}</p>}

          <div className="pt-2">
            <button
              type="submit"
              disabled={busy}
              className="w-full h-16 bg-surface rounded-2xl shadow-extruded btn-extruded flex items-center justify-center gap-3 disabled:opacity-60"
            >
              <span className="text-label-md text-secondary font-bold">{busy ? "Initializing…" : "Start Journey"}</span>
              {!busy && <span className="material-symbols-outlined text-secondary">arrow_forward</span>}
            </button>
          </div>
        </form>

        <p className="text-center text-label-sm text-outline flex items-center justify-center gap-1">
          <span className="material-symbols-outlined text-[14px]">lock</span>
          Secure Environment
        </p>
      </div>
    </main>
  );
}
