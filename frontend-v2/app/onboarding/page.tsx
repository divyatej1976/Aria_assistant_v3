"use client";

import { useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { AuthShell } from "@/components/auth-shell";
import { Icon } from "@/components/icons";
import { toast } from "@/lib/toast";
import { ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";

const LEVELS = ["Beginner", "Intermediate", "Advanced"];

export default function OnboardingPage() {
  const router = useRouter();
  const { createContext } = useActiveContext();
  const [vector, setVector] = useState("");
  const [level, setLevel] = useState("Beginner");
  const [goal, setGoal] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const topicInput = useRef<HTMLInputElement>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending.current) return;
    if (!vector.trim()) {
      setError("Please enter a topic to learn.");
      topicInput.current?.focus();
      return;
    }
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      await createContext({ title: vector.trim(), description: goal.trim() || undefined, masteryLevel: level });
      toast("Ready to explore " + vector.trim());
      router.push("/app");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Unable to start learning";
      setError(msg);
    } finally {
      pending.current = false;
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Start your learning journey" subtitle="Choose a topic and a starting point. You can explore more subjects later.">
      <form onSubmit={submit} aria-busy={busy} noValidate style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div>
          <label className="field-label" htmlFor="ob-vec">What would you like to learn?</label>
          <input ref={topicInput} id="ob-vec" className="input" value={vector} required disabled={busy} aria-invalid={!!error && !vector.trim()} aria-describedby={error ? "ob-error" : undefined} placeholder="e.g. Python, databases, or linear algebra" onChange={(e) => { setVector(e.target.value); setError(""); }} />
        </div>

        <div>
          <p id="ob-level" className="field-label">How familiar are you?</p>
          <div className="seg" role="group" aria-labelledby="ob-level" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
            {LEVELS.map((l) => (
              <button
                key={l}
                type="button"
                disabled={busy}
                aria-pressed={level === l}
                className={`seg-item${level === l ? " on" : ""}`}
                onClick={() => setLevel(l)}
                style={{ width: "100%" }}
              >
                {l}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="field-label" htmlFor="ob-goal">What’s your goal? <span style={{ color: "var(--text-2)", fontWeight: 400 }}>(optional)</span></label>
          <textarea id="ob-goal" className="textarea" rows={3} value={goal} disabled={busy} placeholder="e.g. Prepare for an exam or build my first project" onChange={(e) => setGoal(e.target.value)} />
        </div>

        {error && <p id="ob-error" role="alert" style={{ color: "var(--danger)", fontSize: 13, fontWeight: 600 }}>{error}</p>}

        <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={busy} style={{ marginTop: 4 }}>
          <span className="shine" />
          {busy ? "Setting up…" : "Start learning"} {!busy && <Icon name="arrow" />}
        </button>
      </form>
    </AuthShell>
  );
}
