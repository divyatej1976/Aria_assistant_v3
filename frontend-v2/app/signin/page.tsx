"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthShell } from "@/components/auth-shell";
import { Icon } from "@/components/icons";
import { toast } from "@/lib/toast";
import { api, ApiError } from "@/lib/api";
import { deviceName } from "@/lib/device-name";
import { useAuth, type AuthUser } from "@/components/auth-provider";
import { useHydrated } from "@/lib/use-hydrated";
type SessionResponse = { learner_id: string; access_token?: string | null };

export default function SignInPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [error, setError] = useState("");
  const hydrated = useHydrated();
  const notice = hydrated && new URLSearchParams(window.location.search).get("reason") === "expired"
    ? "Your session expired. Sign in again to continue."
    : "";
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const fields = new FormData(e.currentTarget as HTMLFormElement);
    const email = String(fields.get("email") ?? "").trim();
    const password = String(fields.get("password") ?? "");
    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      // Cookie-only session: the bearer copy is for API clients, and must
      // never enter browser JS memory where XSS could steal it.
      await api<SessionResponse>("/api/v1/auth/login?bearer=false", {
        method: "POST",
        body: JSON.stringify({ email, password, device_label: deviceName() }),
      });
      // cookies are set by the backend; fetch current learner
      const me = await api<AuthUser & { display_name?: string | null }>("/api/v1/auth/me");
      setUser({ id: me.id, email: me.email, display_name: me.display_name ?? null, verified: me.verified ?? false });
      toast("Welcome back, " + (me.display_name ?? me.email));
      // route by whether the learner has a context yet
      const contexts = await api<{ id: string }[]>("/api/v1/contexts");
      const next = new URLSearchParams(window.location.search).get("next");
      const destination = next && /^\/app(?:\/|$)/.test(next) ? next : "/app";
      router.push(contexts.length > 0 ? destination : "/onboarding");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Unable to sign in";
      setError(msg === "Invalid credentials" ? "Invalid credentials." : msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Sign In" subtitle="Welcome back. Continue your learning journey.">
      <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <label className="field-label" htmlFor="si-email">Email</label>
          <input id="si-email" className="input" type="email" name="email" autoComplete="username" placeholder="you@example.com" />
        </div>
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <label className="field-label" htmlFor="si-pass" style={{ marginBottom: 8 }}>Password</label>
            <Link href="/reset-password" style={{ fontSize: 12, fontWeight: 600, color: "var(--accent-strong, var(--accent))", textDecoration: "none" }}>
              Forgot password?
            </Link>
          </div>
          <input id="si-pass" className="input" type="password" name="password" autoComplete="current-password" placeholder="Your password" />
        </div>
        {notice && !error && (
          <p style={{ color: "var(--warning, var(--accent-strong))", fontSize: 13, fontWeight: 600 }}>{notice}</p>
        )}
        {error && (
          <p role="alert" style={{ color: "var(--danger)", fontSize: 13, fontWeight: 600 }}>{error}</p>
        )}
        <button className="btn btn-primary btn-lg btn-block" disabled={busy} style={{ marginTop: 6 }}>
          <span className="shine" />
          {busy ? "Signing in…" : "Sign In"} {!busy && <Icon name="arrow" />}
        </button>
      </form>
      <p style={{ textAlign: "center", fontSize: 13, color: "var(--text-2)", marginTop: 18 }}>
        New to ARIA?{" "}
        <Link href="/signup" style={{ color: "var(--accent-strong, var(--accent))", fontWeight: 700, textDecoration: "none" }}>
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}
