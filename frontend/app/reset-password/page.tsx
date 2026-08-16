"use client";

import { FormEvent, useEffect, useState } from "react";

import { api } from "../../lib/api";

export default function ResetPasswordPage() {
  const [email, setEmail] = useState("");
  const [requested, setRequested] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [tokenParam, setTokenParam] = useState<string | null>(null);
  const [emailParam, setEmailParam] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setTokenParam(params.get("token"));
    setEmailParam(params.get("email") ?? "");
  }, []);

  const hasToken = Boolean(tokenParam);

  async function requestReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/v1/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setRequested(true);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to send reset link");
    } finally {
      setBusy(false);
    }
  }

  async function confirmReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/v1/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({
          email: emailParam,
          token: tokenParam,
          new_password: newPassword,
        }),
      });
      setNotice("Password updated. You can now sign in with your new password.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to reset password");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-[480px] bg-surface shadow-extruded rounded-3xl p-8 sm:p-10 flex flex-col gap-6">
        <div className="text-center flex flex-col items-center gap-3">
          <div className="w-14 h-14 rounded-2xl bg-surface shadow-extruded flex items-center justify-center text-secondary">
            <span className="material-symbols-outlined text-3xl ms-fill">lock_reset</span>
          </div>
          <h1 className="text-headline-lg text-on-surface">
            {hasToken ? "Set a new password" : "Reset your password"}
          </h1>
          <p className="text-body-md text-on-surface-variant">
            {hasToken
              ? "Enter a new password for your ARIA account."
              : "Enter your account email and we will send you a reset link."}
          </p>
        </div>

        {notice && (
          <p className="text-label-md text-tertiary bg-tertiary-container/30 rounded-xl p-3" role="status">
            {notice}
          </p>
        )}
        {error && <p className="text-label-md text-error" role="alert">{error}</p>}

        {!hasToken ? (
          requested ? (
            <p className="text-label-md text-on-surface-variant" role="status">
              If that email is registered, a reset link has been sent. It expires in 1 hour.
            </p>
          ) : (
            <form onSubmit={requestReset} className="flex flex-col gap-5">
              <label className="flex flex-col gap-2">
                <span className="text-label-md text-on-surface-variant">Email</span>
                <input
                  type="email"
                  required
                  className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
              <button
                disabled={busy}
                type="submit"
                className="h-14 bg-surface rounded-2xl shadow-extruded btn-extruded text-label-md font-bold text-secondary disabled:opacity-60"
              >
                {busy ? "Sending…" : "Send reset link"}
              </button>
            </form>
          )
        ) : (
          <form onSubmit={confirmReset} className="flex flex-col gap-5">
            <label className="flex flex-col gap-2">
              <span className="text-label-md text-on-surface-variant">New password</span>
              <input
                type="password"
                required
                minLength={8}
                className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
              />
            </label>
            <button
              disabled={busy}
              type="submit"
              className="h-14 bg-surface rounded-2xl shadow-extruded btn-extruded text-label-md font-bold text-secondary disabled:opacity-60"
            >
              {busy ? "Updating…" : "Update password"}
            </button>
          </form>
        )}

        <a href="/signin" className="text-center text-label-md text-secondary hover:underline">
          Back to sign in
        </a>
      </div>
    </main>
  );
}
