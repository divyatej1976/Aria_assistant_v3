"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AuthShell } from "@/components/auth-shell";
import { toast } from "@/lib/toast";
import { api, ApiError } from "@/lib/api";
import { emailOk, passwordOk, PasswordRules } from "@/lib/password-rules";

function ResetPasswordForm() {
  const params = useSearchParams();
  const urlEmail = params.get("email") ?? "";
  const urlToken = params.get("token") ?? "";
  const confirming = urlEmail !== "" && urlToken !== "";

  const [sent, setSent] = useState(false);
  const [email, setEmail] = useState(urlEmail);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const request = async () => {
    if (!emailOk(email)) {
      setError("Please enter a valid email, like name@example.com.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api("/api/v1/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setSent(true);
      toast("Reset link sent");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to send reset link");
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    if (!passwordOk(newPassword)) {
      setError("Password needs 8+ characters with a letter, a number and a symbol.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api("/api/v1/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ email: urlEmail, token: urlToken, new_password: newPassword }),
      });
      setDone(true);
      toast("Password updated — please sign in.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reset the password. The link may have expired.");
    } finally {
      setBusy(false);
    }
  };

  if (confirming) {
    return (
      <AuthShell title="Set a new password" subtitle={`Resetting the password for ${urlEmail}.`}>
        {done ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <p style={{ fontSize: 14, color: "var(--text-2)", margin: 0 }}>
              Password updated. All other devices were signed out.
            </p>
            <Link href="/signin" className="btn btn-primary btn-lg btn-block">
              Continue to Sign In
            </Link>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label className="field-label" htmlFor="rp-new">New password</label>
              <input id="rp-new" className="input" type="password" autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
              <PasswordRules value={newPassword} />
            </div>
            <div>
              <label className="field-label" htmlFor="rp-confirm">Confirm new password</label>
              <input id="rp-confirm" className="input" type="password" autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
            </div>
            {error && <p role="alert" style={{ color: "var(--danger)", fontSize: 13, fontWeight: 600 }}>{error}</p>}
            <button className="btn btn-primary btn-lg btn-block" disabled={busy} onClick={confirm}>
              <span className="shine" />
              {busy ? "Updating…" : "Update password"}
            </button>
          </div>
        )}
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Reset password" subtitle={sent ? "Check your inbox for a reset link." : "Enter your email and we'll send a reset link."}>
      {!sent ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label className="field-label" htmlFor="rp-email">Email</label>
            <input id="rp-email" className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          </div>
          {error && <p role="alert" style={{ color: "var(--danger)", fontSize: 13, fontWeight: 600 }}>{error}</p>}
          <button className="btn btn-primary btn-lg btn-block" disabled={busy} onClick={request}>
            <span className="shine" />
            {busy ? "Sending…" : "Send reset link"}
          </button>
          <Link href="/signin" className="btn btn-ghost btn-block">
            Back to Sign In
          </Link>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <button className="btn btn-primary btn-lg btn-block" disabled={busy} onClick={request}>
            Re-send link
          </button>
          <Link href="/signin" className="btn btn-ghost btn-block">
            Back to Sign In
          </Link>
        </div>
      )}
    </AuthShell>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <AuthShell title="Reset password" subtitle="Loading…">
          <div style={{ minHeight: 8 }} />
        </AuthShell>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}