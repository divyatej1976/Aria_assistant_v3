"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api, deviceLabel } from "../lib/api";

type SessionResponse = { access_token: string; learner_id: string };

export function AuthForm({ mode }: { mode: "signin" | "signup" }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [expired, setExpired] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setExpired(window.location.search.includes("reason=expired"));
    }
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const path = mode === "signup" ? "/api/v1/auth/register" : "/api/v1/auth/login";
      const body =
        mode === "signup"
          ? { email, password, display_name: displayName, device_label: deviceLabel() }
          : { email, password, device_label: deviceLabel() };
      await api<SessionResponse>(path, {
        method: "POST",
        body: JSON.stringify(body),
      });
      router.push(mode === "signup" ? "/onboarding" : "/app");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to authenticate");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="w-full max-w-[480px] bg-surface shadow-extruded rounded-3xl p-8 sm:p-10 flex flex-col gap-6" onSubmit={submit}>
      <div className="text-center flex flex-col items-center gap-3">
        <div className="w-14 h-14 rounded-2xl bg-surface shadow-extruded flex items-center justify-center text-secondary">
          <span className="material-symbols-outlined text-3xl ms-fill">all_inclusive</span>
        </div>
        <p className="text-label-md text-secondary uppercase tracking-widest">ARIA</p>
        <h1 className="text-headline-lg text-on-surface">
          {mode === "signup" ? "Create your learner account" : "Welcome back"}
        </h1>
        <p className="text-body-md text-on-surface-variant">
          Your learning context and evidence stay connected to your account.
        </p>
      </div>

      {expired && (
        <p className="text-label-md text-secondary bg-secondary-fixed/30 border border-secondary/20 rounded-xl p-3" role="status">
          Your session expired. Please sign in again.
        </p>
      )}

      <div className="flex flex-col gap-5">
        {mode === "signup" && (
          <label className="flex flex-col gap-2">
            <span className="text-label-md text-on-surface-variant">Display name</span>
            <input
              className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface placeholder:text-outline-variant"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="How should ARIA call you?"
            />
          </label>
        )}
        <label className="flex flex-col gap-2">
          <span className="text-label-md text-on-surface-variant">Email</span>
          <input
            type="email"
            required
            className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface placeholder:text-outline-variant"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />
        </label>
        <label className="flex flex-col gap-2">
          <span className="text-label-md text-on-surface-variant">Password</span>
          <input
            type="password"
            required
            minLength={8}
            className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface placeholder:text-outline-variant"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="At least 8 characters"
          />
        </label>
      </div>

      {error && <p className="text-label-md text-error" role="alert">{error}</p>}

      <button
        className="h-14 bg-surface rounded-2xl shadow-extruded btn-extruded flex items-center justify-center gap-3 text-label-md font-bold text-secondary disabled:opacity-60"
        disabled={busy}
        type="submit"
      >
        {busy ? "Working…" : mode === "signup" ? "Create account" : "Sign in"}
        {!busy && <span className="material-symbols-outlined">arrow_forward</span>}
      </button>

      <a
        href={mode === "signup" ? "/signin" : "/signup"}
        className="text-center text-label-md text-secondary hover:underline"
      >
        {mode === "signup" ? "Already have an account? Sign in" : "Don't have an account? Sign up"}
      </a>
    </form>
  );
}
