"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icons";
import { Modal } from "@/components/modal";
import { api } from "@/lib/api";
import { toast } from "@/lib/toast";

const LAST_ASKED = "aria.experience.lastAsked";
const ASK_EVERY_MS = 14 * 24 * 3600 * 1000; // at most once every two weeks
const REPLIES = "aria.experience.replies";

const read = (key: string) => { try { return window.localStorage.getItem(key); } catch { return null; } };
const write = (key: string, value: string) => { try { window.localStorage.setItem(key, value); } catch { /* this visit only */ } };

/** Ask now? Only when the learner has not been asked in the last two weeks. */
function dueForAsking(): boolean {
  return Date.now() - Number(read(LAST_ASKED) || 0) > ASK_EVERY_MS;
}

/** Report a natural pause: a finished quiz, a tutor reply (the 5th one counts), or signing out. */
export function noteMilestone(kind: "quiz" | "reply" | "signout") {
  if (kind === "reply") {
    const replies = Number(read(REPLIES) || 0) + 1;
    write(REPLIES, String(replies));
    if (replies !== 5) return;
  }
  window.dispatchEvent(new CustomEvent("aria:milestone", { detail: kind }));
}

/**
 * "How's ARIA so far?" with 1-5 stars and an optional comment, shown at natural pauses at most once
 * every two weeks. For sign-out, `beforeSignOut` resolves once the learner answers or skips.
 */
export function ExperiencePrompt() {
  const [open, setOpen] = useState<null | "quiz" | "reply" | "signout">(null);
  const [stars, setStars] = useState(0);
  const [comment, setComment] = useState("");
  const [sending, setSending] = useState(false);
  const afterClose = useRef<(() => void) | null>(null);

  useEffect(() => {
    const onMilestone = (event: Event) => {
      const kind = (event as CustomEvent).detail as "quiz" | "reply" | "signout";
      const proceed = (event as CustomEvent & { proceed?: () => void }).proceed;
      if (!dueForAsking()) { proceed?.(); return; }
      write(LAST_ASKED, String(Date.now()));
      afterClose.current = proceed ?? null;
      setStars(0);
      setComment("");
      setOpen(kind);
    };
    window.addEventListener("aria:milestone", onMilestone);
    return () => window.removeEventListener("aria:milestone", onMilestone);
  }, []);

  const close = useCallback(() => {
    setOpen(null);
    const next = afterClose.current;
    afterClose.current = null;
    next?.();
  }, []);

  const send = async () => {
    if (!stars) return;
    setSending(true);
    try {
      await api("/api/v1/feedback", {
        method: "POST",
        body: JSON.stringify({ kind: "experience", rating: String(stars), message: comment.trim() || undefined,
          page: window.location.pathname, user_agent: navigator.userAgent.slice(0, 300) }),
      });
      toast("Thank you! This helps us improve ARIA.", "success");
    } catch {
      // A rating is optional; never block the learner on it.
    } finally {
      setSending(false);
      close();
    }
  };

  const title = open === "signout" ? "Before you go…" : open === "quiz" ? "Quiz done! Quick question" : "How's ARIA so far?";
  return (
    <Modal open={open !== null} title={title} onClose={close}>
      <div className="modal experience-prompt">
        <div className="m-head dialog-heading">
          <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}>{title}</h3>
          <button className="btn btn-ghost" style={{ padding: 6 }} onClick={close} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>
        <p className="field-help" style={{ marginTop: 0 }}>How would you rate your experience with ARIA?</p>
        <div className="star-row" role="radiogroup" aria-label="Rating">
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} type="button" role="radio" aria-checked={stars === n} aria-label={`${n} star${n > 1 ? "s" : ""}`}
              className={`star${n <= stars ? " on" : ""}`} onClick={() => setStars(n)}>★</button>
          ))}
        </div>
        {stars > 0 && (
          <textarea className="input" rows={3} maxLength={2000} value={comment} onChange={(e) => setComment(e.target.value)}
            placeholder={stars <= 3 ? "What should we fix first? (optional)" : "What do you like most? (optional)"}
            aria-label="Comment (optional)" />
        )}
        <div className="dialog-actions ui-mt-16">
          <button className="btn btn-ghost" onClick={close}>{open === "signout" ? "Skip and sign out" : "Not now"}</button>
          <button className="btn btn-primary" disabled={!stars || sending} onClick={() => void send()}>
            {sending ? "Sending…" : "Send"}
          </button>
        </div>
      </div>
    </Modal>
  );
}

/** Sign-out goes through the prompt (when it is due), then continues. */
export function askBeforeSignOut(proceed: () => void) {
  const event = new CustomEvent("aria:milestone", { detail: "signout" }) as CustomEvent & { proceed?: () => void };
  event.proceed = proceed;
  window.dispatchEvent(event);
}
