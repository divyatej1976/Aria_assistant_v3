"use client";

import { useState } from "react";
import { Icon } from "@/components/icons";
import { Modal } from "@/components/modal";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";

/** "Send feedback": a problem report with the page and browser attached, for the team to fix. */
export function FeedbackDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const send = async () => {
    if (!message.trim()) { setError("Tell us what happened."); return; }
    setSending(true);
    setError("");
    try {
      await api("/api/v1/feedback", {
        method: "POST",
        body: JSON.stringify({
          kind: "report", message: message.trim(), page: window.location.pathname,
          user_agent: navigator.userAgent.slice(0, 300),
        }),
      });
      setMessage("");
      onClose();
      toast("Thanks! Your feedback reached the team.", "success");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send it. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal open={open} title="Send feedback" onClose={onClose}>
      <div className="modal">
        <div className="m-head dialog-heading">
          <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}><Icon name="message" size={20} /> Send feedback</h3>
          <button className="btn btn-ghost" style={{ padding: 6 }} onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>
        <label className="field-label" htmlFor="feedback-text">What went wrong, or what would make ARIA better?</label>
        <textarea id="feedback-text" className="input" rows={5} maxLength={4000} value={message}
          onChange={(e) => setMessage(e.target.value)} placeholder="e.g. The audio stopped at 40% on the Data structures notes" />
        <p className="field-help">We also attach the page you are on and your browser, so we can reproduce it.</p>
        {error && <p role="alert" style={{ color: "var(--danger)", fontSize: 13, fontWeight: 600 }}>{error}</p>}
        <div className="dialog-actions ui-mt-16">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => void send()} disabled={sending}>{sending ? "Sending…" : "Send feedback"}</button>
        </div>
      </div>
    </Modal>
  );
}
