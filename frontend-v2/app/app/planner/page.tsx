"use client";

import { Modal } from "@/components/modal";

import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { api, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { toast } from "@/lib/toast";
import { ErrorState, Loading } from "@/components/states";
import { ConfirmDialog, type ConfirmState } from "@/components/confirm";

type Deadline = {
  id: string;
  context_id: string;
  title: string;
  due_at: string;
  syllabus_resource_id: string | null;
  reminder_days_before: number;
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
type ConceptState = { state: string; concept_name?: string };

function daysUntil(dueAt: string): number {
  const due = new Date(dueAt);
  const now = new Date();
  return Math.round((due.getTime() - now.getTime()) / 86_400_000);
}
function dayLabel(dueAt: string): string {
  const d = daysUntil(dueAt);
  if (d < 0) return "Overdue";
  if (d === 0) return "Today";
  if (d === 1) return "Tomorrow";
  return new Date(dueAt).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
function bucket(dueAt: string | null): string {
  if (!dueAt) return "No date";
  const d = daysUntil(dueAt);
  if (d < 0) return "Missed";
  if (d === 0) return "Today";
  if (d === 1) return "Tomorrow";
  if (d <= 7) return "This week";
  return "Later";
}

let remindersCheckedThisSession = false;

const tomorrowIso = () => new Date(Date.now() + 86_400_000).toISOString();

export default function PlannerPage() {
  const { context } = useActiveContext();
  return <PlannerPageWorkspace key={context?.id ?? "no-subject"} />;
}

function PlannerPageWorkspace() {
  const { context, loading: ctxLoading } = useActiveContext();
  const [tab, setTab] = useState<"exams" | "tasks">("exams");
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [missed, setMissed] = useState<Task[]>([]);
  const [concepts, setConcepts] = useState<ConceptState[]>([]);
  const [selected, setSelected] = useState<Deadline | null>(null);
  const [open, setOpen] = useState<"deadline" | "task" | null>(null);
  // create form state
  const [title, setTitle] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [reminderDays, setReminderDays] = useState(5);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reminderResult, setReminderResult] = useState("");
  const [confirm, setConfirm] = useState<ConfirmState>(null);

  const load = useCallback(async (cid: string) => {
    const [d, t, m, a] = await Promise.all([
      api<Deadline[]>("/api/v1/planner/deadlines?context_id=" + cid),
      api<Task[]>("/api/v1/planner/tasks?context_id=" + cid),
      api<Task[]>(`/api/v1/planner/missed?context_id=${cid}`),
      api<{ states: ConceptState[] }>(`/api/v1/contexts/${cid}/adaptation`),
    ]);
    setDeadlines(d);
    setTasks(t);
    setMissed(m);
    setConcepts(a.states);
    setSelected((s) => (s && d.find((x) => x.id === s.id) ? d.find((x) => x.id === s.id)! : d[0] ?? null));
  }, []);

  useEffect(() => {
    if (!context) return;
    let cancelled = false;
    (async () => {
      try {
        await load(context.id);
        if (!remindersCheckedThisSession) {
          remindersCheckedThisSession = true;
          const result = await api<{ notifications_created: number }>("/api/v1/planner/reminders/check", { method: "POST" });
          if (!cancelled && result.notifications_created > 0) {
            toast(`${result.notifications_created} new reminder${result.notifications_created === 1 ? "" : "s"} — see the bell.`);
          }
        }
      } catch {
        if (!cancelled) setFailed(true);
      } finally {
        if (!cancelled) { setBusy(false); setLoading(false); }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [context, load]);

  const supported = concepts.filter((c) => c.state === "SUPPORTED").length;
  const progress = concepts.length ? Math.round((supported / concepts.length) * 100) : 0;

  // ---- R3 planner intelligence ----
  const weakConcepts = concepts
    .filter((c) => c.state !== "SUPPORTED" && c.concept_name)
    .sort((a, b) => (a.state === "NEEDS_REVIEW" ? -1 : b.state === "NEEDS_REVIEW" ? 1 : 0))
    .slice(0, 4);
  const [addedSuggestions, setAddedSuggestions] = useState<Record<string, boolean>>({});
  const suggestStudyTask = async (name: string) => {
    if (!context) return;
    try {
      const created = await api<Task>("/api/v1/planner/tasks", {
        method: "POST",
        body: JSON.stringify({ context_id: context.id, title: `Study ${name}`, due_at: tomorrowIso() }),
      });
      setTasks((p) => [...p, created]);
      setAddedSuggestions((s) => ({ ...s, [name]: true }));
      toast(`Study task added for ${name}.`);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not add the study task.", "error");
    }
  };
  const rescheduleMissed = async (t: Task) => {
    try {
      await api(`/api/v1/planner/tasks/${t.id}`, { method: "DELETE" });
      const moved = await api<Task>("/api/v1/planner/tasks", {
        method: "POST",
        body: JSON.stringify({ context_id: context!.id, title: t.title, due_at: tomorrowIso() }),
      });
      setMissed((p) => p.filter((x) => x.id !== t.id));
      setTasks((p) => [...p.filter((x) => x.id !== moved.id), moved]);
      toast("Rescheduled to tomorrow.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not reschedule.", "error");
    }
  };
  const tasksToday = tasks.filter(
    (t) => t.status === "PENDING" && bucket(t.due_at) === "Today",
  ).length;

  const createDeadline = async () => {
    if (ctxLoading || !context) {
      toast("Still loading your learning context — try again in a moment.");
      return;
    }
    if (!title.trim() || !dueAt) {
      toast("Please enter a name and date.");
      return;
    }
    setBusy(true);
    try {
      const created = await api<Deadline>("/api/v1/planner/deadlines", {
        method: "POST",
        body: JSON.stringify({ context_id: context.id, title: title.trim(), due_at: dueAt, reminder_days_before: reminderDays }),
      });
      setDeadlines((p) => [...p, created]);
      setSelected(created);
      setOpen(null);
      setTitle("");
      setDueAt("");
      setReminderDays(5);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not create exam.", "error");
    } finally {
      setBusy(false);
    }
  };

  const completeDeadline = async (id: string) => {
    try {
      const updated = await api<Deadline>(`/api/v1/planner/deadlines/${id}/complete`, { method: "POST" });
      setDeadlines((p) => p.map((d) => (d.id === id ? updated : d)));
      setSelected((s) => (s?.id === id ? updated : s));
      toast("Exam marked complete");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not complete the exam.", "error");
    }
  };

  const deleteDeadline = async (id: string) => {
    try {
      await api(`/api/v1/planner/deadlines/${id}`, { method: "DELETE" });
      setDeadlines((p) => p.filter((d) => d.id !== id));
      setSelected((s) => (s?.id === id ? null : s));
      toast("Exam deleted");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not delete the exam.", "error");
    }
  };

  const createTask = async () => {
    if (ctxLoading || !context) {
      toast("Still loading your learning context — try again in a moment.");
      return;
    }
    if (!title.trim()) {
      toast("Please enter a task name.");
      return;
    }
    setBusy(true);
    try {
      const created = await api<Task>("/api/v1/planner/tasks", {
        method: "POST",
        body: JSON.stringify({ context_id: context.id, title: title.trim(), due_at: dueAt || undefined }),
      });
      setTasks((p) => [...p, created]);
      setOpen(null);
      setTitle("");
      setDueAt("");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not create task.", "error");
    } finally {
      setBusy(false);
    }
  };

  const completeTask = async (id: string) => {
    try {
      const updated = await api<Task>(`/api/v1/planner/tasks/${id}/complete`, { method: "POST" });
      setTasks((p) => p.map((t) => (t.id === id ? updated : t)));
      toast("Task completed");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not complete the task.", "error");
    }
  };

  const deleteTask = async (id: string) => {
    try {
      await api(`/api/v1/planner/tasks/${id}`, { method: "DELETE" });
      setTasks((p) => p.filter((t) => t.id !== id));
      toast("Task deleted");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not delete the task.", "error");
    }
  };

  const runReminderCheck = async () => {
    try {
      const res = await api<{ notifications_created: number }>("/api/v1/planner/reminders/check", { method: "POST" });
      setReminderResult(`${res.notifications_created} reminder(s) created`);
      toast(res.notifications_created > 0 ? `${res.notifications_created} reminders created` : "No new reminders");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not run the reminder check.", "error");
    }
  };

  const groups = [
    { label: "Missed", items: missed.filter((t) => t.status !== "DONE") },
    { label: "Today", items: tasks.filter((t) => t.status === "PENDING" && bucket(t.due_at) === "Today") },
    { label: "Tomorrow", items: tasks.filter((t) => t.status === "PENDING" && bucket(t.due_at) === "Tomorrow") },
    { label: "This week", items: tasks.filter((t) => t.status === "PENDING" && bucket(t.due_at) === "This week") },
    { label: "Later", items: tasks.filter((t) => t.status === "PENDING" && bucket(t.due_at) === "Later") },
    { label: "No date", items: tasks.filter((t) => t.status === "PENDING" && bucket(t.due_at) === "No date") },
    { label: "Completed", items: tasks.filter((t) => t.status === "DONE") },
  ];

  if (failed) {
    return <ErrorState message="This screen could not be loaded." onRetry={() => window.location.reload()} />;
  }

  if (ctxLoading || (context && loading)) return <Loading label="your planner" />;

  return (
    <div>
      <div className="section-head">
        <div>
          <h1 className="pg-title">Planner</h1>
          <p className="pg-sub">Plan it. Learn it. Complete it. Reminders keep you on track day-to-day.</p>
        </div>
        <div className="ui-flex ui-gap-8">
          {process.env.NEXT_PUBLIC_ENABLE_DEV_TOOLS === "1" && (
            <button className="btn btn-ghost" onClick={runReminderCheck} title="Run reminder check (dev)">
              <Icon name="bell" /> Check reminders
            </button>
          )}
          <button className="btn btn-primary" disabled={ctxLoading || !context} onClick={() => { setOpen(tab === "exams" ? "deadline" : "task"); setTitle(""); setDueAt(""); }}>
            <Icon name="plus" /> {tab === "exams" ? "Create exam" : "Create task"}
          </button>
        </div>
      </div>


      <div className="card card-pad" style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 24, alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1.4, color: "var(--accent-strong)", textTransform: "uppercase" }}>What should I do today?</div>
            <div style={{ fontSize: 14, fontWeight: 700, marginTop: 2 }}>
              {missed.length} missed · {tasksToday} task{tasksToday === 1 ? "" : "s"} today · readiness {progress}%
            </div>
          </div>
          <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-3)" }}>
            Suggestions below are generated from your weakest concepts.
          </span>
        </div>
        {weakConcepts.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>
              Suggested by ARIA
            </div>
            {weakConcepts.map((c) => (
              <div key={c.concept_name} className="ws-row" style={{ cursor: "default", marginBottom: 6 }}>
                <span
                  style={{
                    width: 9,
                    height: 9,
                    borderRadius: "50%",
                    background: c.state === "NEEDS_REVIEW" ? "var(--danger)" : "var(--accent)",
                    marginRight: 8,
                    flexShrink: 0,
                  }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <b style={{ fontSize: 13 }}>{c.concept_name}</b>{" "}
                  <span style={{ fontSize: 11, color: "var(--text-3)" }}>{c.state.replace("_", " ")}</span>
                </div>
                <button
                  className="btn btn-secondary"
                  style={{ padding: "4px 10px", fontSize: 11.5 }}
                  disabled={!!addedSuggestions[c.concept_name!]}
                  onClick={() => suggestStudyTask(c.concept_name!)}
                >
                  {addedSuggestions[c.concept_name!] ? "Added" : "+ Add study task"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <button className={`btn ${tab === "exams" ? "btn-primary" : "btn-secondary"}`} onClick={() => setTab("exams")}>
          <Icon name="calendar" /> Exams &amp; deadlines
        </button>
        <button className={`btn ${tab === "tasks" ? "btn-primary" : "btn-secondary"}`} onClick={() => setTab("tasks")}>
          <Icon name="check" /> Task planning
        </button>
      </div>

      {reminderResult && (
        <div className="banner" style={{ marginTop: 0, marginBottom: 16 }}>
          <span style={{ color: "var(--accent)", display: "inline-flex" }}><Icon name="bell" size={20} /></span>
          <div><b>Reminder check</b><p>{reminderResult}</p></div>
        </div>
      )}

      {tab === "exams" ? (
        <div className="planner-split">
          <div className="card card-pad" style={{ padding: 12, position: "sticky", top: 84 }}>
            <div className="nav-sec">Deadlines</div>
            {deadlines.length === 0 && (
              <div style={{ fontSize: 13, color: "var(--text-3)", padding: "8px 12px" }}>No exams yet. Create one above.</div>
            )}
            {deadlines.map((d) => (
              <button
                key={d.id}
                type="button"
                aria-pressed={selected?.id === d.id}
                aria-label={`Select exam ${d.title}`}
                className={`ws-row${selected?.id === d.id ? " on" : ""}`}
                style={{ marginBottom: 8, width: "100%", textAlign: "left" }}
                onClick={() => setSelected(d)}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <b style={{ fontSize: 13.5 }}>{d.title}</b>
                  <span style={{ fontSize: 11, color: "var(--text-3)" }}>{dayLabel(d.due_at)} · remind {d.reminder_days_before}d</span>
                </div>
                {d.status === "DONE" && <Icon name="check" size={16} />}
              </button>
            ))}
          </div>

          {selected ? (
            <div className="card card-pad">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: 240 }}>
                  <h2 style={{ fontSize: 24, fontWeight: 800 }}>{selected.title}</h2>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "8px 0 4px" }}>
                    <span className="type-tag">{dayLabel(selected.due_at)}</span>
                    <span className="type-tag" style={{ borderColor: "var(--border-hi)", color: "var(--text-2)", background: "var(--chip-bg)" }}>Reminder: {selected.reminder_days_before} days before</span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-3)" }}>
                    {supported}/{concepts.length} concepts strong · {progress}% prepared
                    {selected.syllabus_resource_id ? " · linked material (Phase 7)" : ""}
                  </div>
                  <div className="bar" style={{ marginTop: 12 }}><i style={{ width: `${progress}%` }} /></div>
                </div>
                <div className="ring" style={{ "--p": String(progress), "--r": "46px" } as React.CSSProperties}>
                  <span className="r-n" style={{ color: "var(--accent)" }}>{progress}%</span>
                </div>
              </div>

              <div className="n-group-title" style={{ marginTop: 20 }}><Icon name="list" size={15} /> Concept mastery</div>
              {concepts.length === 0 ? (
                <div style={{ fontSize: 13, color: "var(--text-3)", padding: "8px 0" }}>
                  Add material and study so ARIA can track concepts here.
                </div>
              ) : (
                concepts.map((c, i) => (
                  <div key={i} className={`n-item${c.state === "SUPPORTED" ? " checked" : ""}`}>
                    <div className="n-check"><Icon name="check" size={13} /></div>
                    <span className="n-text">{c.state.replace("_", " ")}</span>
                  </div>
                ))
              )}

              <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
                {selected.status !== "DONE" && (
                  <button className="btn btn-primary" onClick={() => completeDeadline(selected.id)}><Icon name="check" /> Mark complete</button>
                )}
                <button className="btn btn-ghost" onClick={() => setConfirm({ title: "Delete exam", body: `Delete “${selected.title}”? This cannot be undone.`, confirmLabel: "Delete exam", onConfirm: () => void deleteDeadline(selected.id) })} style={{ color: "var(--danger)" }}>
                  <Icon name="x" /> Delete
                </button>
              </div>
            </div>
          ) : (
            <div className="card card-pad empty-state-card">
              Select an exam, or create one to begin.
            </div>
          )}
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(300px,1fr))", gap: 18 }}>
          {groups.map((g) => (
            <div className="card card-pad" key={g.label}>
              <div className="section-title" style={{ marginBottom: 10 }}><span className="tick" style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)" }} /> {g.label}</div>
              {g.items.length === 0 ? (
                <div style={{ fontSize: 13, color: "var(--text-3)", padding: "8px 0" }}>Nothing here.</div>
              ) : (
                g.items.map((t) => (
                  <div key={t.id} className="ws-row" style={{ cursor: "default", marginBottom: 8 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 700, fontSize: 13.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.title}</div>
                      {t.status === "DONE" ? (
                        <div style={{ fontSize: 11, color: "var(--success)" }}>Completed</div>
                      ) : (
                        <div style={{ fontSize: 11, color: "var(--text-3)" }}>{g.label === "No date" ? "No due date" : dayLabel(t.due_at!)}</div>
                      )}
                    </div>
                    {t.status !== "DONE" && (
                      <button className="btn btn-ghost" style={{ padding: "4px 8px", borderRadius: 99 }} aria-label={`Complete ${t.title}`} onClick={() => completeTask(t.id)}>
                        <Icon name="check" size={16} />
                      </button>
                    )}
                    {g.label === "Missed" && (
                      <button className="btn btn-ghost" style={{ padding: "4px 8px", borderRadius: 99 }} aria-label={`Reschedule ${t.title}`} onClick={() => void rescheduleMissed(t)}>
                        <Icon name="refresh" size={15} />
                      </button>
                    )}
                    <button className="btn btn-ghost" style={{ padding: "4px 8px", borderRadius: 99, color: "var(--danger)" }} aria-label={`Delete ${t.title}`} onClick={() => setConfirm({ title: "Delete task", body: `Delete “${t.title}”? This cannot be undone.`, confirmLabel: "Delete task", onConfirm: () => void deleteTask(t.id) })}>
                      <Icon name="x" size={15} />
                    </button>
                  </div>
                ))
              )}
            </div>
          ))}
        </div>
      )}

      {open && (
        <Modal open={Boolean(open)} title={open === "deadline" ? "Create exam" : "Create task"} onClose={() => setOpen(null)}>
          <div className="modal">
            <div className="m-head dialog-heading">
              <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}>
                <Icon name={open === "deadline" ? "calendar" : "check"} size={20} /> {open === "deadline" ? "Create exam" : "Create task"}
              </h3>
              <button className="btn btn-ghost" style={{ padding: 6 }} onClick={() => setOpen(null)} aria-label="Close"><Icon name="x" size={16} /></button>
            </div>
            <div className="form-group"><label className="field-label" htmlFor="pl-title">{open === "deadline" ? "Exam name" : "Task name"}</label><input id="pl-title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder={open === "deadline" ? "e.g. Data Structures" : "e.g. Solve LeetCode problems"} /></div>
            <div className="form-group"><label className="field-label" htmlFor="pl-due">Due date</label><input id="pl-due" type="datetime-local" className="input" value={dueAt} onChange={(e) => setDueAt(e.target.value)} /></div>
            {open === "deadline" && (
              <div className="form-group"><label className="field-label" htmlFor="pl-remind">Remind me (days before)</label><input id="pl-remind" type="number" min={1} max={60} className="input" value={reminderDays} onChange={(e) => setReminderDays(Number(e.target.value))} /></div>
            )}
            <div className="dialog-actions ui-mt-16">
              <button className="btn btn-ghost" onClick={() => setOpen(null)}>Cancel</button>
              <button className="btn btn-primary" disabled={busy || ctxLoading || !context} onClick={open === "deadline" ? createDeadline : createTask}>
                {busy ? "Saving…" : "Create"} <Icon name="arrow" />
              </button>
            </div>
          </div>
        </Modal>
      )}
      <ConfirmDialog state={confirm} onClose={() => setConfirm(null)} />
    </div>
  );
}
