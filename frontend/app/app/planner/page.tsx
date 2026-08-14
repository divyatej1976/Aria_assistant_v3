"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { api } from "../../../lib/api";
import { useActiveContext } from "../../../components/use-active-context";

type Deadline = {
  id: string;
  context_id: string;
  title: string;
  due_at: string;
  syllabus_resource_id: string | null;
  reminder_days_before: number;
  reminder_sent_days_before: number | null;
  status: string;
};

type Task = {
  id: string;
  context_id: string;
  deadline_id: string | null;
  title: string;
  due_at: string | null;
  status: string;
  completed_at: string | null;
};

type Resource = { id: string; title: string; processing_status: string };

function daysUntil(dueAt: string): number {
  const due = new Date(dueAt);
  const now = new Date();
  return Math.max(0, Math.ceil((due.getTime() - now.getTime()) / 86_400_000));
}

export default function PlannerPage() {
  const { context, loading } = useActiveContext();
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [missed, setMissed] = useState<Task[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [deadlineTitle, setDeadlineTitle] = useState("");
  const [deadlineDate, setDeadlineDate] = useState("");
  const [reminderDays, setReminderDays] = useState(5);
  const [syllabusId, setSyllabusId] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDate, setTaskDate] = useState("");
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!context) return;
    const [deadlineList, taskList, missedList, resourceList] = await Promise.all([
      api<Deadline[]>(`/api/v1/planner/deadlines?context_id=${context.id}`),
      api<Task[]>(`/api/v1/planner/tasks?context_id=${context.id}`),
      api<Task[]>("/api/v1/planner/missed"),
      api<Resource[]>(`/api/v1/resources?context_id=${context.id}`),
    ]);
    setDeadlines(deadlineList);
    setTasks(taskList);
    setMissed(missedList);
    setResources(resourceList);
  }, [context]);

  useEffect(() => {
    load().catch((requestError: unknown) =>
      setError(requestError instanceof Error ? requestError.message : "Unable to load planner")
    );
  }, [load]);

  if (loading) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <p className="text-body-md text-on-surface-variant">Loading planner…</p>
      </div>
    );
  }

  if (!context) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <div className="bg-surface shadow-extruded rounded-3xl p-8 max-w-xl">
          <h2 className="text-headline-md text-on-surface mb-4">No learning context yet</h2>
          <p className="text-body-md text-on-surface-variant mb-6">Set up your context to plan around exams.</p>
          <Link href="/onboarding" className="inline-flex items-center gap-2 px-8 py-4 rounded-xl shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
            Initialize learning journey
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </Link>
        </div>
      </div>
    );
  }

  const activeContext = context;

  async function addDeadline(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/v1/planner/deadlines", {
        method: "POST",
        body: JSON.stringify({
          context_id: activeContext.id,
          title: deadlineTitle,
          due_at: new Date(deadlineDate).toISOString(),
          reminder_days_before: reminderDays,
          syllabus_resource_id: syllabusId || null,
        }),
      });
      setDeadlineTitle("");
      setDeadlineDate("");
      setSyllabusId("");
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to add deadline");
    }
  }

  async function addTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/v1/planner/tasks", {
        method: "POST",
        body: JSON.stringify({
          context_id: activeContext.id,
          title: taskTitle,
          due_at: taskDate ? new Date(taskDate).toISOString() : null,
        }),
      });
      setTaskTitle("");
      setTaskDate("");
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to add task");
    }
  }

  async function completeDeadline(id: string) {
    setError("");
    try {
      await api(`/api/v1/planner/deadlines/${id}/complete`, { method: "POST" });
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update deadline");
    }
  }

  async function removeDeadline(id: string) {
    setError("");
    try {
      await api(`/api/v1/planner/deadlines/${id}`, { method: "DELETE" });
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to remove deadline");
    }
  }

  async function completeTask(id: string) {
    setError("");
    try {
      await api(`/api/v1/planner/tasks/${id}/complete`, { method: "POST" });
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to complete task");
    }
  }

  async function removeTask(id: string) {
    setError("");
    try {
      await api(`/api/v1/planner/tasks/${id}`, { method: "DELETE" });
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to remove task");
    }
  }

  async function checkReminders() {
    setChecking(true);
    setError("");
    setCheckResult("");
    try {
      const result = await api<{
        notifications_created: number;
        emails_delivered: number;
        emails_logged: number;
        emails_failed: number;
      }>("/api/v1/planner/reminders/check", { method: "POST" });
      const parts = [`${result.notifications_created} notification(s) created`];
      if (result.emails_delivered > 0) parts.push(`${result.emails_delivered} email(s) delivered`);
      if (result.emails_logged > 0) parts.push(`${result.emails_logged} logged (no SMTP configured)`);
      if (result.emails_failed > 0) parts.push(`${result.emails_failed} failed`);
      setCheckResult(parts.length > 1 ? parts.join(", ") + "." : `${parts[0]}.`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Reminder check failed");
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="p-container-padding md:p-section-margin w-full max-w-5xl mx-auto flex flex-col gap-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-headline-xl text-on-background">Planner</h2>
          <p className="text-body-lg text-on-surface-variant mt-2">{activeContext.title}</p>
        </div>
        <button
          onClick={() => void checkReminders()}
          disabled={checking}
          className="self-start px-6 py-3 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary disabled:opacity-60"
        >
          {checking ? "Checking…" : "Run reminder check"}
        </button>
      </div>
      {checkResult && <p className="text-label-md text-tertiary" role="status">{checkResult}</p>}

      {/* Missed work */}
      {missed.length > 0 && (
        <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-4">
          <h3 className="text-headline-md text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-error">schedule</span>
            Missed work
          </h3>
          <ul className="flex flex-col gap-3">
            {missed.map((task) => (
              <li key={task.id} className="bg-surface shadow-injected rounded-xl p-4 flex items-center justify-between gap-4">
                <span className="text-body-md text-on-background">{task.title}</span>
                <button onClick={() => void completeTask(task.id)} className="px-5 py-2 rounded-full bg-secondary text-on-secondary text-label-md font-bold shadow-extruded btn-extruded">
                  Recover
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Exams */}
      <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-6">
        <h3 className="text-headline-md text-on-surface">Exams &amp; deadlines</h3>
        <form onSubmit={addDeadline} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr_auto] gap-4">
          <input required className="h-12 bg-surface-container rounded-xl input-injected px-4 text-on-surface placeholder:text-outline-variant" placeholder="Exam title (e.g. DBMS End Sem)" value={deadlineTitle} onChange={(event) => setDeadlineTitle(event.target.value)} />
          <input required type="date" className="h-12 bg-surface-container rounded-xl input-injected px-4 text-on-surface" value={deadlineDate} onChange={(event) => setDeadlineDate(event.target.value)} />
          <input type="number" min={1} max={60} className="h-12 bg-surface-container rounded-xl input-injected px-4 text-on-surface" placeholder="Remind (days)" value={reminderDays} onChange={(event) => setReminderDays(Number(event.target.value))} />
          <select className="h-12 bg-surface-container rounded-xl input-injected px-4 text-on-surface" value={syllabusId} onChange={(event) => setSyllabusId(event.target.value)}>
            <option value="">No syllabus</option>
            {resources.filter((r) => r.processing_status === "READY").map((resource) => (
              <option key={resource.id} value={resource.id}>{resource.title}</option>
            ))}
          </select>
          <button className="h-12 px-6 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary">Add</button>
        </form>
        {deadlines.length === 0 ? (
          <p className="text-body-md text-on-surface-variant">No exams yet. Add one to get reminders before it arrives.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {deadlines.map((deadline) => {
              const days = daysUntil(deadline.due_at);
              return (
                <li key={deadline.id} className="bg-surface shadow-injected rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <p className="text-body-md text-on-background font-semibold">{deadline.title}</p>
                    <p className="text-label-md text-on-surface-variant mt-1">
                      {new Date(deadline.due_at).toLocaleDateString()} · in {days} day{days === 1 ? "" : "s"} · remind {deadline.reminder_days_before} days before
                      {deadline.reminder_sent_days_before !== null && " · reminder sent"}
                    </p>
                  </div>
                  <div className="flex gap-3">
                    {deadline.status === "ACTIVE" && (
                      <button onClick={() => void completeDeadline(deadline.id)} className="px-4 py-2 rounded-full bg-tertiary-container text-on-tertiary-container text-label-md font-bold shadow-extruded btn-extruded">
                        Done
                      </button>
                    )}
                    <button onClick={() => void removeDeadline(deadline.id)} className="px-4 py-2 rounded-full text-label-md text-error">
                      Delete
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Planned tasks */}
      <div className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-6">
        <h3 className="text-headline-md text-on-surface">Planned tasks</h3>
        <form onSubmit={addTask} className="grid grid-cols-1 sm:grid-cols-[2fr_1fr_auto] gap-4">
          <input required className="h-12 bg-surface-container rounded-xl input-injected px-4 text-on-surface placeholder:text-outline-variant" placeholder="e.g. Revise serializability" value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} />
          <input type="date" className="h-12 bg-surface-container rounded-xl input-injected px-4 text-on-surface" value={taskDate} onChange={(event) => setTaskDate(event.target.value)} />
          <button className="h-12 px-6 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-secondary">Add</button>
        </form>
        {tasks.length === 0 ? (
          <p className="text-body-md text-on-surface-variant">No planned tasks. Completing one counts toward your learning streak.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {tasks.map((task) => (
              <li key={task.id} className={`bg-surface shadow-injected rounded-xl p-4 flex items-center justify-between gap-4 ${task.status === "DONE" ? "opacity-60" : ""}`}>
                <span className="text-body-md text-on-background">{task.title}</span>
                <div className="flex gap-3">
                  {task.status === "PENDING" && (
                    <button onClick={() => void completeTask(task.id)} className="px-4 py-2 rounded-full bg-secondary text-on-secondary text-label-md font-bold shadow-extruded btn-extruded">
                      Complete
                    </button>
                  )}
                  <button onClick={() => void removeTask(task.id)} className="px-4 py-2 rounded-full text-label-md text-error">
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {error && <p className="text-label-md text-error" role="alert">{error}</p>}
    </div>
  );
}
