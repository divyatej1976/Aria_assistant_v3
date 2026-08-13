"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api, clearToken } from "../../../lib/api";
import { useAuth } from "../../../components/auth-provider";

type SessionRecord = { id: string; device_label: string | null; is_current: boolean; created_at: string };

export default function AccountPage() {
  const router = useRouter();
  const { learner, signOut } = useAuth();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [emailReminders, setEmailReminders] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [confirmingReset, setConfirmingReset] = useState(false);

  useEffect(() => {
    api<{ key: string; value: string }[]>("/api/v1/me/preferences")
      .then((preferences) => {
        const pref = preferences.find((item) => item.key === "email_reminders");
        setEmailReminders(pref ? pref.value !== "off" : true);
      })
      .catch(() => {
        // Preferences are optional for rendering.
      });
  }, []);

  async function loadSessions() {
    try {
      const list = await api<SessionRecord[]>("/api/v1/auth/sessions");
      setSessions(list);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load sessions");
    }
  }

  useEffect(() => {
    if (learner) {
      setDisplayName(learner.display_name ?? "");
      setEmail(learner.email);
    }
    void loadSessions();
  }, [learner]);

  async function updateProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      await api("/api/v1/auth/profile", {
        method: "PATCH",
        body: JSON.stringify({ email, display_name: displayName }),
      });
      setNotice("Profile updated.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update profile");
    }
  }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      await api("/api/v1/auth/password", {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      setCurrentPassword("");
      setNewPassword("");
      setNotice("Password changed. Other devices were signed out.");
      await loadSessions();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to change password");
    }
  }

  async function revokeSession(sessionId: string) {
    setError("");
    setNotice("");
    try {
      await api(`/api/v1/auth/sessions/${sessionId}/revoke`, { method: "POST" });
      await loadSessions();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to sign out that device");
    }
  }

  async function toggleEmailReminders() {
    const next = !emailReminders;
    setEmailReminders(next);
    setError("");
    setNotice("");
    try {
      await api("/api/v1/me/preferences", {
        method: "PUT",
        body: JSON.stringify({ key: "email_reminders", value: next ? "on" : "off" }),
      });
      setNotice(next ? "Email reminders enabled." : "Email reminders disabled.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update preference");
    }
  }

  async function resetData() {
    setError("");
    setNotice("");
    try {
      await api("/api/v1/account/data", { method: "DELETE" });
      clearToken();
      router.replace("/signin");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to reset data");
    }
  }

  return (
    <div className="p-container-padding md:p-section-margin w-full max-w-5xl mx-auto flex flex-col gap-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-headline-xl text-on-background">Settings</h2>
          <p className="text-body-lg text-on-surface-variant mt-2">
            {learner?.display_name || learner?.email || "Account"}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <a
            href="/app/memory"
            className="px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary"
          >
            Memory
          </a>
          <a
            href="/app/orchestration"
            className="px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary"
          >
            Orchestration
          </a>
          <button
            onClick={() => void signOut()}
            className="px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-error"
          >
            Sign out this device
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-6">
          <h3 className="text-headline-md text-on-surface">Profile</h3>
          <form onSubmit={updateProfile} className="flex flex-col gap-4">
            <label className="flex flex-col gap-2">
              <span className="text-label-md text-on-surface-variant">Display name</span>
              <input className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface" value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
            </label>
            <label className="flex flex-col gap-2">
              <span className="text-label-md text-on-surface-variant">Email</span>
              <input type="email" required className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface" value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
            <button type="submit" className="self-start px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
              Save profile
            </button>
          </form>
        </div>

        <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-6">
          <h3 className="text-headline-md text-on-surface">Change password</h3>
          <form onSubmit={changePassword} className="flex flex-col gap-4">
            <label className="flex flex-col gap-2">
              <span className="text-label-md text-on-surface-variant">Current password</span>
              <input type="password" required className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
            </label>
            <label className="flex flex-col gap-2">
              <span className="text-label-md text-on-surface-variant">New password</span>
              <input type="password" required minLength={8} className="h-14 bg-surface-container rounded-xl input-injected px-6 text-on-surface" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
            </label>
            <button type="submit" className="self-start px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
              Change password
            </button>
          </form>
        </div>

        <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-4">
          <h3 className="text-headline-md text-on-surface">Active devices</h3>
          {sessions.length === 0 ? (
            <p className="text-body-md text-on-surface-variant">No active sessions.</p>
          ) : (
            <ul className="flex flex-col gap-4">
              {sessions.map((session) => (
                <li key={session.id} className="bg-surface shadow-injected p-4 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <p className="text-body-md text-on-background">
                      {session.device_label ?? "Unknown device"}
                      {session.is_current && <span className="text-secondary"> · this device</span>}
                    </p>
                    <p className="text-label-sm text-on-surface-variant mt-1">Signed in {new Date(session.created_at).toLocaleString()}</p>
                  </div>
                  {!session.is_current && (
                    <button onClick={() => void revokeSession(session.id)} className="self-start px-5 py-2 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-error">
                      Sign out
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-4">
          <h3 className="text-headline-md text-on-surface">Notifications</h3>
          <p className="text-body-md text-on-surface-variant">
            Receive exam reminders and the daily digest by email when SMTP is configured.
          </p>
          <button
            onClick={() => void toggleEmailReminders()}
            className={`self-start px-6 py-3 rounded-full text-label-md font-bold shadow-extruded btn-extruded ${
              emailReminders ? "bg-secondary text-on-secondary" : "bg-surface text-on-surface-variant"
            }`}
          >
            {emailReminders ? "Email reminders: ON" : "Email reminders: OFF"}
          </button>
        </div>

        <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-4">
          <h3 className="text-headline-md text-on-surface">Reset learning data</h3>
          <p className="text-body-md text-on-surface-variant">
            Deletes every context, resource, study session, assessment, and piece of evidence you own, and signs out every device. Your account remains.
          </p>
          {confirmingReset ? (
            <div className="flex flex-wrap gap-3">
              <button onClick={() => void resetData()} className="px-6 py-3 rounded-full bg-error-container text-on-error-container text-label-md font-bold shadow-extruded btn-extruded">
                Yes, delete everything
              </button>
              <button onClick={() => setConfirmingReset(false)} className="px-6 py-3 rounded-full text-label-md text-on-surface-variant">
                Cancel
              </button>
            </div>
          ) : (
            <button onClick={() => setConfirmingReset(true)} className="self-start px-6 py-3 rounded-full text-label-md text-error">
              Reset my data
            </button>
          )}
        </div>
      </div>

      {notice && <p className="text-label-md text-tertiary" role="status">{notice}</p>}
      {error && <p className="text-label-md text-error" role="alert">{error}</p>}
    </div>
  );
}
