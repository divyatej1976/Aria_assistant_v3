"use client";

import { useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { AuthShell } from "@/components/auth-shell";
import { Icon } from "@/components/icons";
import { api, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { useAuth } from "@/components/auth-provider";

const SUBJECTS = ["Python", "Data structures", "Databases", "Calculus", "Physics", "English grammar"];
// Used when the learner skips: a subject they can rename or replace later.
const DEFAULT_SUBJECT = "My studies";

/** Two optional questions: what to call you and what you are studying. */
export default function OnboardingPage() {
  const router = useRouter();
  const { createContext } = useActiveContext();
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user?.display_name ?? "");
  const [subject, setSubject] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);

  const finish = async (title: string) => {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      const preferred = name.trim();
      if (preferred && preferred !== (user?.display_name ?? "")) {
        const updated = await api<{ id: string; email: string; display_name: string | null; verified: boolean; email_delivery?: boolean }>(
          "/api/v1/auth/profile", { method: "PATCH", body: JSON.stringify({ display_name: preferred }) },
        );
        setUser({ id: updated.id, email: updated.email, display_name: updated.display_name, verified: updated.verified, email_delivery: updated.email_delivery });
      }
      await createContext({ title, masteryLevel: "Beginner" });
      router.push("/app");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not finish setting up. Please try again.");
    } finally {
      pending.current = false;
      setBusy(false);
    }
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void finish(subject.trim() || DEFAULT_SUBJECT);
  };

  return (
    <AuthShell title="Welcome to ARIA" subtitle="Two quick questions. You can skip both and change them later.">
      <form onSubmit={submit} aria-busy={busy} noValidate style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div>
          <label className="field-label" htmlFor="ob-name">What should we call you?</label>
          <input id="ob-name" className="input" value={name} disabled={busy} maxLength={120} autoComplete="nickname"
            placeholder="Your name" onChange={(e) => setName(e.target.value)} />
        </div>

        <div>
          <label className="field-label" htmlFor="ob-vec">What are you studying?</label>
          <input id="ob-vec" className="input" value={subject} disabled={busy} maxLength={255}
            placeholder="e.g. Python or databases" onChange={(e) => { setSubject(e.target.value); setError(""); }} />
          <p className="field-help">A course, exam or skill. Each subject keeps its own chats, quizzes and plan.</p>
          <div className="quiz-choice-row">
            {SUBJECTS.map((s) => (
              <button key={s} type="button" className={`tag-chip${subject === s ? " tag-chip-selected" : ""}`} disabled={busy} onClick={() => setSubject(s)}>{s}</button>
            ))}
          </div>
        </div>

        {error && <p id="ob-error" role="alert" style={{ color: "var(--danger)", fontSize: 13, fontWeight: 600 }}>{error}</p>}

        <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={busy} style={{ marginTop: 4 }}>
          <span className="shine" />
          {busy ? "Setting up…" : "Start learning"} {!busy && <Icon name="arrow" />}
        </button>
        <button type="button" className="btn btn-ghost btn-block" disabled={busy} onClick={() => void finish(DEFAULT_SUBJECT)}>
          Skip for now
        </button>
      </form>
    </AuthShell>
  );
}
