"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthShell } from "@/components/auth-shell";
import { Icon } from "@/components/icons";
import { toast } from "@/lib/toast";
import { api, ApiError } from "@/lib/api";
import { deviceName } from "@/lib/device-name";
import { emailOk, passwordOk, PasswordRules } from "@/lib/password-rules";
import { useAuth, type AuthUser } from "@/components/auth-provider";

export default function SignUpPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email) {
      setError("Please fill in your name and email.");
      return;
    }
    if (!emailOk(email)) {
      setError("Please enter a valid email, like name@example.com.");
      return;
    }
    if (!passwordOk(password)) {
      setError("Password needs 8+ characters with a letter, a number and a symbol.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api("/api/v1/auth/register?bearer=false", {
        method: "POST",
        body: JSON.stringify({ email, password, display_name: name, device_label: deviceName() }),
      });
      const me = await api<AuthUser & { display_name?: string | null }>("/api/v1/auth/me");
      setUser({ id: me.id, email: me.email, display_name: me.display_name ?? null, verified: me.verified ?? false });
      toast("Account created");
      router.push("/onboarding");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Unable to create account";
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Sign Up" subtitle="Create your account to begin your personalized learning journey.">
      <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div>
          <label className="field-label" htmlFor="su-name">Full Name</label>
          <input id="su-name" className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" autoComplete="name" />
        </div>
        <div>
          <label className="field-label" htmlFor="su-email">Email</label>
          <input id="su-email" className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" />
        </div>
        <div>
          <label className="field-label" htmlFor="su-pass">Password</label>
          <input id="su-pass" className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Create a password" autoComplete="new-password" />
          <PasswordRules value={password} />
        </div>
        {error && <p role="alert" style={{ color: "var(--danger)", fontSize: 13, fontWeight: 600 }}>{error}</p>}
        <button className="btn btn-primary btn-lg btn-block" disabled={busy} style={{ marginTop: 8 }}>
          <span className="shine" />
          {busy ? "Creating account…" : "Sign Up"} {!busy && <Icon name="arrow" />}
        </button>
      </form>
      <p style={{ textAlign: "center", fontSize: 13, color: "var(--text-2)", marginTop: 16 }}>
        Already have an account?{" "}
        <Link href="/signin" style={{ color: "var(--accent-strong, var(--accent))", fontWeight: 700, textDecoration: "none" }}>
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
