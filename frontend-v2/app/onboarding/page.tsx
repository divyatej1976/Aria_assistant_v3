"use client";

import { useState } from "react";
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

  const submit = async () => {
    if (!vector.trim()) {
      setError("Please enter a topic to learn.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await createContext({ title: vector.trim(), description: goal.trim() || undefined, masteryLevel: level });
      toast("Learning vector set: " + vector.trim());
      router.push("/app");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Unable to start learning";
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Onboarding" subtitle="Tell us what you want to learn and we'll personalize ARIA for you.">
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div>
          <label className="field-label" htmlFor="ob-vec">Primary Learning Vector</label>
          <input id="ob-vec" className="input" value={vector} placeholder="e.g. Database Management Systems" onChange={(e) => setVector(e.target.value)} />
        </div>

        <div>
          <label className="field-label">Current Mastery Level</label>
          <div className="seg" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
            {LEVELS.map((l) => (
              <button
                key={l}
                type="button"
                aria-pressed={level === l}
                className={`seg-item${level === l ? " on" : ""}`}
                onClick={() => setLevel(l)}
                style={{ background: "none", border: "none", width: "100%" }}
              >
                {l}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="field-label" htmlFor="ob-goal">Goal Objective</label>
          <textarea id="ob-goal" className="textarea" rows={3} value={goal} placeholder="What do you want to achieve?" onChange={(e) => setGoal(e.target.value)} />
        </div>

        {error && <p role="alert" style={{ color: "var(--danger)", fontSize: 13, fontWeight: 600 }}>{error}</p>}

        <button className="btn btn-primary btn-lg btn-block" disabled={busy} onClick={submit} style={{ marginTop: 4 }}>
          <span className="shine" />
          {busy ? "Setting up…" : "Enter ARIA"} {!busy && <Icon name="arrow" />}
        </button>
      </div>
    </AuthShell>
  );
}
