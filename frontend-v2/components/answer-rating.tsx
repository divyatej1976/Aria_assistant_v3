"use client";

import { useState } from "react";
import { api } from "@/lib/api";

const REASONS: [string, string][] = [
  ["wrong", "Wrong"], ["too_long", "Too long"], ["too_short", "Too short"],
  ["outdated", "Outdated"], ["ignored_my_file", "Ignored my file"], ["other", "Other"],
];
const storageKey = (id: string) => `aria.rated:${id}`;

function readRated(id: string): string | null {
  try { return window.localStorage.getItem(storageKey(id)); } catch { return null; }
}

/** Thumbs on one tutor answer; a thumbs-down asks what was wrong. Ratings reach the team's feedback inbox. */
export function AnswerRating({ answerId }: { answerId: string }) {
  const [rated, setRated] = useState<string | null>(() => (typeof window === "undefined" ? null : readRated(answerId)));
  const [asking, setAsking] = useState(false);
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);

  const send = async (rating: "up" | "down") => {
    setSending(true);
    try {
      await api("/api/v1/feedback", {
        method: "POST",
        body: JSON.stringify({
          kind: "answer", rating, answer_id: answerId, reason: rating === "down" ? reason || "other" : undefined,
          message: note.trim() || undefined, page: window.location.pathname, user_agent: navigator.userAgent.slice(0, 300),
        }),
      });
      setRated(rating);
      setAsking(false);
      try { window.localStorage.setItem(storageKey(answerId), rating); } catch { /* remembered for this visit only */ }
    } catch {
      // Rating is optional; the buttons stay so the learner can try again.
    } finally {
      setSending(false);
    }
  };

  if (rated) return <p className="answer-rated" role="status">{rated === "up" ? "Thanks for the thumbs up." : "Thanks, we'll look into it."}</p>;
  return (
    <div className="answer-rating">
      <span className="answer-rating-label">Was this helpful?</span>
      <button type="button" className="rate-btn" aria-label="Helpful" disabled={sending} onClick={() => void send("up")}>
        <Thumb />
      </button>
      <button type="button" className={`rate-btn${asking ? " on" : ""}`} aria-label="Not helpful" aria-expanded={asking}
        disabled={sending} onClick={() => setAsking((open) => !open)}>
        <Thumb down />
      </button>
      {asking && (
        <div className="rate-why" role="group" aria-label="What was wrong?">
          <div className="rate-reasons">
            {REASONS.map(([value, label]) => (
              <button key={value} type="button" className={`tag-chip${reason === value ? " tag-chip-selected" : ""}`}
                aria-pressed={reason === value} onClick={() => setReason(value)}>{label}</button>
            ))}
          </div>
          <input className="input" value={note} maxLength={1000} onChange={(e) => setNote(e.target.value)}
            placeholder="Anything else? (optional)" aria-label="More detail (optional)" />
          <button type="button" className="btn btn-primary" disabled={sending} onClick={() => void send("down")}>
            {sending ? "Sending…" : "Send rating"}
          </button>
        </div>
      )}
    </div>
  );
}

function Thumb({ down = false }: { down?: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true" style={down ? { transform: "rotate(180deg)" } : undefined}>
      <path d="M7 10v12M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" />
    </svg>
  );
}
