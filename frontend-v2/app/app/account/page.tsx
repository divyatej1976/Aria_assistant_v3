"use client";

import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { api, apiBlob, ApiError, clearToken } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { useActiveContext } from "@/components/use-active-context";
import { disablePush, enablePush, pushSupported } from "@/lib/push";
import { useRouter } from "next/navigation";
import { ConfirmDialog, type ConfirmState } from "@/components/confirm";
import { toast } from "@/lib/toast";
import { passwordOk, PasswordRules } from "@/lib/password-rules";
import { ErrorState, Loading } from "@/components/states";

type Me = { id: string; email: string; display_name: string | null; verified: boolean };
type Preference = { key: string; value: string };
type SessionRecord = { id: string; device_label: string | null; is_current: boolean; created_at: string };
type LlmKeyStatus = { configured: boolean; usable?: boolean; issue?: string | null; provider: string | null; model: string | null; hint: string | null };

type Capabilities = { allowed_models: string[]; model: string; personal_keys_enabled: boolean; personal_key: LlmKeyStatus };

const PREF_REMINDERS = "notify_reminders";
const PREF_PUSH = "notify_push";

function fmtDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function ToggleRow({
  icon,
  label,
  on,
  onToggle,
  disabled,
}: {
  icon: Parameters<typeof Icon>[0]["name"];
  label: string;
  on: boolean;
  onToggle: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      className="kv"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={onToggle}
      disabled={disabled}
      style={{
        width: "100%",
        background: "none",
        border: "none",
        cursor: disabled ? "default" : "pointer",
        textAlign: "left",
        color: "inherit",
        padding: 0,
        font: "inherit",
        opacity: disabled ? 0.7 : 1,
      }}
    >
      <span className="k"><Icon name={icon} size={16} /> {label}</span>
      <span className="v" style={{ color: on ? "var(--success-strong)" : "var(--text-2)", fontWeight: 800 }}>
        {on ? "On" : "Off"}
      </span>
    </button>
  );
}

export default function AccountPage() {
  const router = useRouter();
  const { context, contexts, removeContext } = useActiveContext();
  const { setUser } = useAuth();
  const [me, setMe] = useState<Me | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  const [remindersOn, setRemindersOn] = useState(false);
  const [pushOn, setPushOn] = useState(false);
  const [prefsLoaded, setPrefsLoaded] = useState(false);
  const [pushBusy, setPushBusy] = useState(false);

  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [revokingId, setRevokingId] = useState<string | null>(null);
  const [confirmState, setConfirmState] = useState<ConfirmState>(null);

  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwBusy, setPwBusy] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);

  const [llmStatus, setLlmStatus] = useState<LlmKeyStatus | null>(null);
  const [llmUnavailable, setLlmUnavailable] = useState(false);
  const [llmKey, setLlmKey] = useState("");
  const [llmModel, setLlmModel] = useState("");
  const [llmModels, setLlmModels] = useState<string[]>([]);
  const [personalKeysEnabled, setPersonalKeysEnabled] = useState(false);
  const [llmBusy, setLlmBusy] = useState(false);

  const load = useCallback(async () => {
    const profile = await api<Me>("/api/v1/auth/me");
    setMe(profile);
    setName(profile.display_name ?? "");
    setEmail(profile.email);
    const prefs = await api<Preference[]>("/api/v1/me/preferences");
    setRemindersOn(prefs.find((p) => p.key === PREF_REMINDERS)?.value === "true");
    setPushOn(prefs.find((p) => p.key === PREF_PUSH)?.value === "true");
    const active = await api<SessionRecord[]>("/api/v1/auth/sessions");
    setSessions(active);
    try {
      const capabilities = await api<Capabilities>("/api/v1/settings/capabilities");
      const status = capabilities.personal_key;
      setLlmStatus(status);
      setLlmModels(capabilities.allowed_models);
      setPersonalKeysEnabled(capabilities.personal_keys_enabled);
      setLlmUnavailable(false);
      const preferred = status.model ?? capabilities.model;
      setLlmModel(capabilities.allowed_models.includes(preferred) ? preferred : capabilities.allowed_models[0] ?? "");
    } catch {
      // A failed request is an unknown capability, not a disabled feature.
      setLlmStatus(null);
      setLlmUnavailable(true);
    }
    setPrefsLoaded(true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await load();
      } catch {
        if (!cancelled) setLoadFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  const saveProfile = async () => {
    if (!name.trim()) {
      toast("Please enter a name.");
      return;
    }
    setSavingProfile(true);
    try {
      const updated = await api<Me>("/api/v1/auth/profile", {
        method: "PATCH",
        body: JSON.stringify({ display_name: name.trim(), email: email.trim() }),
      });
      setMe(updated);
      setName(updated.display_name ?? "");
      setEmail(updated.email);
      setUser({ id: updated.id, email: updated.email, display_name: updated.display_name, verified: updated.verified });
      toast("Profile updated.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not update your profile.", "error");
    } finally {
      setSavingProfile(false);
    }
  };

  const changePassword = async () => {
    if (!currentPw || !newPw) {
      toast("Enter your current and new password.");
      return;
    }
    if (!passwordOk(newPw)) {
      toast("Password needs 8+ characters with a letter, a number and a symbol.");
      return;
    }
    if (newPw !== confirmPw) {
      toast("Passwords do not match.");
      return;
    }
    setPwBusy(true);
    try {
      await api("/api/v1/auth/password", {
        method: "POST",
        body: JSON.stringify({ current_password: currentPw, new_password: newPw }),
      });
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
      toast("Password changed — other devices were signed out.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not change the password.", "error");
    } finally {
      setPwBusy(false);
    }
  };

  const revokeSession = async (id: string) => {
    setRevokingId(id);
    try {
      await api(`/api/v1/auth/sessions/${id}/revoke`, { method: "POST" });
      setSessions((prev) => prev.filter((s) => s.id !== id));
      toast("Session signed out.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not revoke the session.", "error");
    } finally {
      setRevokingId(null);
    }
  };

  const savePref = async (key: string, value: boolean) => {
    try {
      await api<Preference>("/api/v1/me/preferences", {
        method: "PUT",
        body: JSON.stringify({ key, value: String(value) }),
      });
      return true;
    } catch {
      toast("Could not save the preference.");
      return false;
    }
  };

  const toggleReminders = async () => {
    const next = !remindersOn;
    setRemindersOn(next);
    const saved = await savePref(PREF_REMINDERS, next);
    if (saved) toast(`Learning reminders ${next ? "enabled" : "disabled"}.`);
    else setRemindersOn(!next);
  };

  const togglePush = async () => {
    if (pushBusy || !prefsLoaded) return;
    if (!pushOn && !pushSupported()) {
      toast("Web push is not available in this browser.");
      return;
    }
    setPushBusy(true);
    try {
      if (!pushOn) {
        const result = await enablePush((payload) =>
          api("/api/v1/push/subscribe", { method: "POST", body: JSON.stringify(payload) }),
        );
        if (result.status === "subscribed") {
          setPushOn(true);
          const saved = await savePref(PREF_PUSH, true);
          if (saved) toast("Push notifications enabled.");
          else {
            setPushOn(false);
            await disablePush((endpoint) =>
              api("/api/v1/push/unsubscribe", { method: "POST", body: JSON.stringify({ endpoint }) }),
            ).catch(() => {});
          }
        } else if (result.status === "permission-denied") {
          toast("Notification permission was denied.");
        } else if (result.status === "error") {
          toast(result.message);
        }
      } else {
        await disablePush((endpoint) =>
          api("/api/v1/push/unsubscribe", { method: "POST", body: JSON.stringify({ endpoint }) }),
        );
        setPushOn(false);
        const saved = await savePref(PREF_PUSH, false);
        if (saved) toast("Push notifications disabled.");
        else setPushOn(true);
      }
    } finally {
      setPushBusy(false);
    }
  };

  const saveLlmKey = async () => {
    if (llmKey.trim().length < 20) {
      toast("Paste a complete Groq API key (starts with gsk_).");
      return;
    }
    setLlmBusy(true);
    try {
      const status = await api<LlmKeyStatus>("/api/v1/settings/llm-key", {
        method: "POST",
        body: JSON.stringify({ key: llmKey.trim(), model: llmModel }),
      });
      setLlmStatus(status);
      setLlmKey("");
      toast("Your AI key was saved — only you use it.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not save the AI key.", "error");
    } finally {
      setLlmBusy(false);
    }
  };

  const removeLlmKey = async () => {
    setLlmBusy(true);
    try {
      await api("/api/v1/settings/llm-key", { method: "DELETE" });
      setLlmStatus({ configured: false, provider: null, model: null, hint: null });
      toast("Your AI key was removed.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not remove the AI key.", "error");
    } finally {
      setLlmBusy(false);
    }
  };

  const exportData = async () => {    try {
      const blob = await apiBlob("/api/v1/account/export");
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "aria-data-export.json";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not export your data.", "error");
    }
  };

  const deleteActiveContext = async () => {
    if (!context) return;
    const deletedId = context.id;
    const remaining = contexts.filter((c) => c.id !== deletedId);
    try {
      await api(`/api/v1/contexts/${deletedId}`, { method: "DELETE" });
      removeContext(deletedId);
      window.localStorage.removeItem(`aria_audio_${deletedId}`);
      toast("Learning context deleted.");
      if (remaining.length > 0) {
        router.push("/app");
      } else {
        router.push("/onboarding");
      }
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not delete the context.", "error");
    }
  };


  if (loadFailed) {
    return <ErrorState message="This screen could not be loaded." onRetry={() => window.location.reload()} />;
  }

  if (!me || !prefsLoaded) return <Loading label="your account" />;

  return (
    <div>
      <h1 className="pg-title" style={{ marginBottom: 24 }}>Account &amp; settings</h1>

      <div className="grid-2">
        <div className="ui-stack ui-gap-18">
          <div className="card card-pad">
            <h2 style={{ fontSize: 17, fontWeight: 800, marginBottom: 10 }}>Notifications</h2>
            <ToggleRow
              icon="bell"
              label="Learning reminders"
              on={remindersOn}
              onToggle={() => void toggleReminders()}
              disabled={!prefsLoaded}
            />
            <ToggleRow
              icon="zap"
              label="Push notifications"
              on={pushOn}
              onToggle={() => void togglePush()}
              disabled={!prefsLoaded || pushBusy}
            />
          </div>

          <div className="card card-pad">
            <h2 style={{ fontSize: 17, fontWeight: 800, marginBottom: 4 }}>AI model</h2>
            <p style={{ fontSize: 12.5, color: "var(--text-2)", margin: "0 0 12px" }}>
              ARIA works out of the box — you don&apos;t need to set anything up here.
            </p>
            {llmStatus === null ? (
              llmUnavailable ? (
                <p style={{ fontSize: 13, color: "var(--text-2)", margin: 0 }}>
                  AI key status could not be loaded. Retry this page to check your configuration.
                </p>
              ) : (
                <p style={{ fontSize: 13, color: "var(--text-1)", margin: 0 }}>Loading AI key status…</p>
              )
            ) : llmStatus.configured ? (
              <div>
                <p role={llmStatus.usable === false ? "alert" : undefined} style={{ fontSize: 13, marginBottom: 12 }}>
                  {llmStatus.usable === false
                    ? "Your saved key cannot currently be used. Remove it and save it again, or ask the administrator to restore its configuration. ARIA will use a shared key when available, otherwise its offline fallback."
                    : llmStatus.usable === true
                      ? "Your key can be loaded. Provider availability is checked when you send a request."
                      : "Your key is saved; usability has not been checked."}
                </p>
                <div className="kv">
                  <span className="k"><Icon name="lock" size={16} /> Saved key</span>
                  <span className="v" style={{ fontWeight: 800 }}>{llmStatus.hint ?? "configured"}</span>
                </div>
                <div className="kv">
                  <span className="k"><Icon name="zap" size={16} /> Model</span>
                  <span className="v">{llmStatus.model ?? "default"}</span>
                </div>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12 }}>
                  <button
                    className="btn btn-ghost"
                    onClick={() =>
                      setConfirmState({
                        title: "Remove AI key",
                        body: "Remove your saved Groq key? ARIA will fall back to the shared model or offline excerpts.",
                        confirmLabel: "Remove key",
                        onConfirm: () => void removeLlmKey(),
                      })
                    }
                    disabled={llmBusy}
                  >
                    <Icon name="alert" /> Remove my key
                  </button>
                </div>
              </div>
            ) : !personalKeysEnabled ? (
              <p>Personal AI keys are disabled on this deployment. Contact the administrator to enable secure key storage.</p>
            ) : (
              <details className="quiz-customize">
                <summary>Advanced: use your own Groq key</summary>
                <p style={{ fontSize: 12.5, color: "var(--text-2)", margin: "8px 0 12px" }}>
                  Your key is stored encrypted, only used for your requests, and never shown again.
                  Get one free at{" "}
                  <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer">console.groq.com/keys</a>.
                </p>
                <div className="form-group">
                  <label className="field-label" htmlFor="llm-key">Groq API Key</label>
                  <input
                    id="llm-key"
                    type="password"
                    className="input"
                    autoComplete="off"
                    placeholder="gsk_…"
                    value={llmKey}
                    onChange={(e) => setLlmKey(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="field-label" htmlFor="llm-model">Model</label>
                  <select id="llm-model" className="input" value={llmModel} onChange={(e) => setLlmModel(e.target.value)}>
                    {llmModels.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
                <button className="btn btn-primary" onClick={() => void saveLlmKey()} disabled={llmBusy || !llmModel}>
                  <Icon name="lock" /> Save my key
                </button>
              </details>
            )}
          </div>

          <div className="card card-pad">
            <h2 style={{ fontSize: 17, fontWeight: 800, marginBottom: 4 }}>Change password</h2>
            <p style={{ fontSize: 12, color: "var(--text-3)", margin: "0 0 12px" }}>Changing your password signs out every other device.</p>
            <div className="form-group"><label className="field-label" htmlFor="pw-current">Current password</label><input id="pw-current" type="password" className="input" autoComplete="current-password" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} /></div>
            <div className="form-group"><label className="field-label" htmlFor="pw-new">New password</label><input id="pw-new" type="password" className="input" autoComplete="new-password" value={newPw} onChange={(e) => setNewPw(e.target.value)} /><PasswordRules value={newPw} /></div>
            <div className="form-group"><label className="field-label" htmlFor="pw-confirm">Confirm new password</label><input id="pw-confirm" type="password" className="input" autoComplete="new-password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} /></div>
            <button className="btn btn-primary" onClick={() => void changePassword()} disabled={pwBusy}>
              <Icon name="lock" /> Change password
            </button>
          </div>
        </div>

        <div className="ui-stack ui-gap-18">
          <div className="card card-pad">
            <h2 style={{ fontSize: 17, fontWeight: 800, marginBottom: 18 }}>Personal details {me?.verified && <span className="tag-chip" style={{ marginLeft: 8 }}>Verified</span>}</h2>
            <div className="form-group"><label className="field-label" htmlFor="acct-name">Name</label><input id="acct-name" className="input" value={name} onChange={(e) => setName(e.target.value)} /></div>
            <div className="form-group"><label className="field-label" htmlFor="acct-email">Email</label><input id="acct-email" type="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
            <div className="ui-flex ui-gap-10 ui-wrap">
              <button className="btn btn-primary" onClick={() => void saveProfile()} disabled={savingProfile}>
                <Icon name="edit" /> Save changes
              </button>
            </div>
          </div>

          <div className="card card-pad" style={{ borderColor: "var(--danger)" }}>
            <h2 style={{ fontSize: 17, fontWeight: 800, marginBottom: 4, color: "var(--danger-strong)" }}>Data & privacy</h2>
            <p style={{ fontSize: 12.5, color: "var(--text-2)", margin: "0 0 12px" }}>
              Export everything ARIA stores about this account, or permanently delete the current learning context and all of its materials, sessions, assessments, and evidence.
            </p>
            <div className="ui-flex ui-gap-10 ui-wrap">
              <button className="btn btn-secondary" onClick={() => void exportData()}>
                <Icon name="download" /> Export my data
              </button>
              {context && (
                <button
                  className="btn btn-primary"
                  style={{ background: "var(--danger-strong)", borderColor: "var(--danger-strong)" }}
                  onClick={() =>
                    setConfirmState({
                      title: "Delete learning context",
                      body: `Permanently delete “${context.title}” with every material, session, assessment, and piece of evidence in it? This cannot be undone.`,
                      confirmLabel: "Delete context",
                      onConfirm: () => void deleteActiveContext(),
                    })
                  }
                >
                  <Icon name="alert" /> Delete this context
                </button>
              )}
              <button
                className="btn btn-ghost"
                style={{ color: "var(--danger-strong)" }}
                onClick={() =>
                  setConfirmState({
                    title: "Delete all my data",
                    body: "Permanently delete every subject, chat, file, quiz and roadmap, and sign out on all devices? Security audit records are kept per the retention policy. This cannot be undone.",
                    confirmLabel: "Delete everything",
                    onConfirm: async () => {
                      try {
                        await api("/api/v1/account/data", { method: "DELETE" });
                        clearToken();
                        // Full reload is intentional: it clears all client state after the data is gone.
                        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
                        window.location.assign("/");
                      } catch (e) {
                        toast(e instanceof ApiError ? e.message : "Could not delete your data. Please try again.", "error");
                      }
                    },
                  })
                }
              >
                <Icon name="x" /> Delete all my data
              </button>
            </div>
          </div>

          <div className="card card-pad">
            <h2 style={{ fontSize: 17, fontWeight: 800, marginBottom: 10 }}>Active sessions</h2>
            {sessions.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--text-1)", margin: 0 }}>{me ? "No other active sessions." : "Loading sessions…"}</p>
            ) : (
              sessions.map((s) => (
                <div className="kv" key={s.id}>
                  <span className="k">
                    <Icon name="terminal" size={16} /> {s.device_label || "Unknown device"}
                    {s.is_current && <span className="tag-chip" style={{ marginLeft: 8 }}>This device</span>}
                  </span>
                  <span className="v" style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span>{fmtDate(s.created_at)}</span>
                    {!s.is_current && (
                      <button
                        className="btn btn-ghost"
                        style={{ padding: "3px 8px", fontSize: 11 }}
                        onClick={() => void revokeSession(s.id)}
                        disabled={revokingId === s.id}
                        aria-label={`Revoke ${s.device_label || "session"}`}
                      >
                        Revoke
                      </button>
                    )}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
      <ConfirmDialog state={confirmState} onClose={() => setConfirmState(null)} />
    </div>
  );
}
