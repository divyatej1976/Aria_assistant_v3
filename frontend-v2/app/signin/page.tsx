"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthShell } from "@/components/auth-shell";
import { Icon } from "@/components/icons";
import { toast } from "@/lib/toast";
import { api, ApiError } from "@/lib/api";
import { useAuth, type AuthUser } from "@/components/auth-provider";
type SessionResponse = { learner_id: string; access_token: string };

export default function SignInPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  // Read the redirect reason once at first render (no effect setState cascade).
  // SSR-safe: window is unavailable during prerender.
  const [notice] = useState(() => {
    if (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("reason") === "expired") {
      return "Your session expired. Sign in again to continue.";
    }
    return "";
  });
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api<SessionResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      // cookies are set by the backend; fetch current learner
      const me = await api<AuthUser & { display_name?: string | null }>("/api/v1/auth/me");
      setUser({ id: me.id, email: me.email, display_name: me.display_name ?? null, verified: me.verified ?? false });
      toast("Welcome back, " + (me.display_name ?? me.email));
      // route by whether the learner has a context yet
      const contexts = await api<{ id: string }[]>("/api/v1/contexts").catch(() => []);
      router.push(contexts.length > 0 ? "/app" : "/onboarding");
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
          <input id="si-email" className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
        </div>
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <label className="field-label" htmlFor="si-pass" style={{ marginBottom: 8 }}>Password</label>
            <Link href="/reset-password" style={{ fontSize: 12, fontWeight: 600, color: "var(--accent)", textDecoration: "none" }}>
              Forgot password?
            </Link>
          </div>
          <input id="si-pass" className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Your password" />
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
        <Link href="/signup" style={{ color: "var(--accent)", fontWeight: 700, textDecoration: "none" }}>
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}
