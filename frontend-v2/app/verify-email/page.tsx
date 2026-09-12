"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AuthShell } from "@/components/auth-shell";
import { Icon } from "@/components/icons";
import { toast } from "@/lib/toast";
import { api, ApiError } from "@/lib/api";

function VerifyEmailForm() {
  const params = useSearchParams();
  const urlEmail = params.get("email") ?? "";
  const urlToken = params.get("token") ?? "";
  const confirming = urlEmail !== "" && urlToken !== "";

  const [state, setState] = useState<"idle" | "verifying" | "verified" | "failed">(
    confirming ? "verifying" : "idle",
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const firedRef = useRef(false);

  const resend = async () => {
    setBusy(true);
    try {
      await api("/api/v1/auth/verify-email/request", { method: "POST" });
      toast("Verification email re-sent");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast("Sign in first, then resend the verification email.");
      } else {
        toast(err instanceof ApiError ? err.message : "Unable to re-send");
      }
    } finally {
      setBusy(false);
    }
  };

  // Consume the emailed token exactly once per mount.
  useEffect(() => {
    if (!confirming || firedRef.current) return;
    firedRef.current = true;
    api<{ detail: string }>("/api/v1/auth/verify-email/confirm", {
      method: "POST",
      body: JSON.stringify({ email: urlEmail, token: urlToken }),
    })
      .then(() => setState("verified"))
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "This verification link is invalid or has expired.");
        setState("failed");
      });
  }, [confirming, urlEmail, urlToken]);

  if (confirming) {
    return (
      <AuthShell
        title="Verify your email"
        subtitle={state === "verified" ? "Your email address is confirmed." : state === "failed" ? "We couldn't verify that link." : "Confirming your email…"}
      >
        <div style={{ textAlign: "center", padding: "10px 0" }}>
          <div
            style={{
              width: 64,
              height: 64,
              margin: "0 auto 16px",
              borderRadius: 20,
              background:
                state === "verified" ? "var(--accent-grad-soft)" : "rgba(239,68,68,.12)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: state === "verified" ? "var(--accent)" : "var(--danger)",
              boxShadow: "var(--shadow-2)",
            }}
          >
            <Icon name={state === "verified" ? "check" : "alert"} size={28} />
          </div>

          {state === "verifying" && (
            <p style={{ fontSize: 14, color: "var(--text-2)" }} role="status">
              Verifying…
            </p>
          )}

          {state === "verified" && (
            <>
              <p style={{ fontSize: 14, color: "var(--text-2)", margin: "0 0 8px" }}>
                Everything is set. Continue to sign in and keep learning.
              </p>
              <Link href="/signin" className="btn btn-primary btn-block">
                Continue to Sign In
              </Link>
            </>
          )}

          {state === "failed" && (
            <>
              {error && (
                <p role="alert" style={{ color: "var(--danger)", fontSize: 13, fontWeight: 600 }}>
                  {error}
                </p>
              )}
              {!urlEmail && (
                <p style={{ fontSize: 13, color: "var(--text-2)" }}>
                  The link didn&apos;t include your email — request a fresh verification email instead.
                </p>
              )}
              <button className="btn btn-secondary btn-block" style={{ marginTop: 18 }} disabled={busy} onClick={resend}>
                {busy ? "Sending…" : "Re-send verification email"}
              </button>
              <Link href="/signin" className="btn btn-ghost btn-block" style={{ marginTop: 8 }}>
                Back to Sign In
              </Link>
            </>
          )}
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Verify your email" subtitle="We sent a verification link to your inbox.">
      <div style={{ textAlign: "center", padding: "10px 0" }}>
        <div
          style={{
            width: 64,
            height: 64,
            margin: "0 auto 16px",
            borderRadius: 20,
            background: "var(--accent-grad-soft)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--accent)",
            boxShadow: "var(--shadow-2)",
          }}
        >
          <Icon name="sparkles" size={28} />
        </div>
        <p style={{ fontSize: 14, color: "var(--text-2)" }}>
          Check your inbox and click the link to activate your account.
        </p>
        <button className="btn btn-secondary btn-block" style={{ marginTop: 18 }} disabled={busy} onClick={resend}>
          {busy ? "Sending…" : "Re-send email"}
        </button>
        <Link href="/signin" className="btn btn-ghost btn-block" style={{ marginTop: 8 }}>
          Back to Sign In
        </Link>
      </div>
    </AuthShell>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <AuthShell title="Verify your email" subtitle="Loading…">
        <div style={{ minHeight: 8 }} />
      </AuthShell>
    }>
      <VerifyEmailForm />
    </Suspense>
  );
}