"use client";

import { useEffect, useState } from "react";

import { api } from "../../lib/api";

export default function VerifyEmailPage() {
  const [state, setState] = useState<"working" | "done" | "error">("working");
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const email = params.get("email");
    if (!token || !email) {
      setState("error");
      setError("Missing verification link. Request a new link from Settings.");
      return;
    }
    api("/api/v1/auth/verify-email/confirm", {
      method: "POST",
      body: JSON.stringify({ email, token }),
    })
      .then(() => setState("done"))
      .catch((requestError: unknown) => {
        setState("error");
        setError(
          requestError instanceof Error ? requestError.message : "Unable to verify email",
        );
      });
  }, []);

  return (
    <main className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-[480px] bg-surface shadow-extruded rounded-3xl p-8 sm:p-10 flex flex-col items-center gap-6 text-center">
        <div className="w-14 h-14 rounded-2xl bg-surface shadow-extruded flex items-center justify-center text-secondary">
          <span className="material-symbols-outlined text-3xl ms-fill">
            {state === "done" ? "verified" : "mark_email_read"}
          </span>
        </div>
        <h1 className="text-headline-lg text-on-surface">
          {state === "done" ? "Email verified" : "Verifying your email…"}
        </h1>
        {state === "done" && (
          <p className="text-body-md text-on-surface-variant">
            Your email is verified. You can continue using ARIA.
          </p>
        )}
        {state === "error" && (
          <p className="text-label-md text-error" role="alert">
            {error}
          </p>
        )}
        <a
          href="/app"
          className="px-8 py-4 rounded-xl shadow-extruded btn-extruded bg-surface text-label-md text-secondary"
        >
          Go to my dashboard
        </a>
      </div>
    </main>
  );
}
