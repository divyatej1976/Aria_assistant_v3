"use client";

import { ReactNode, useEffect, useState } from "react";

import { api } from "../../../lib/api";

type Approval = {
  id: string;
  workflow_id: string;
  action: string;
  detail: string;
  status: string;
};

type Workflow = {
  id: string;
  name: string;
  status: string;
  current_step: number;
  error_detail: string | null;
  created_at: string;
};

type AgentTask = {
  id: string;
  workflow_id: string;
  agent: string;
  status: string;
  attempt: number;
  error_detail: string | null;
  created_at: string;
};

type AuditEntry = {
  id: string;
  agent: string;
  action: string;
  detail: Record<string, unknown>;
  request_id: string | null;
  created_at: string;
};

function Card({ children }: { children: ReactNode }) {
  return (
    <section className="bg-surface shadow-extruded rounded-3xl p-8 flex flex-col gap-5">
      {children}
    </section>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "COMPLETED" || status === "SUCCEEDED" || status === "APPROVED"
      ? "bg-tertiary-container text-on-tertiary-container"
      : status === "PENDING" || status === "RUNNING" || status === "WAITING_APPROVAL"
        ? "bg-secondary-container text-on-secondary-container"
        : status === "REJECTED" || status === "FAILED"
          ? "bg-error-container text-on-error-container"
          : "bg-surface-container-low text-on-surface-variant";
  return (
    <span className={`px-3 py-1 rounded-full text-label-sm font-bold ${tone}`}>{status}</span>
  );
}

function ApprovalsSection({ onChanged }: { onChanged: () => void }) {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const items = await api<Approval[]>("/api/v1/orchestration/approvals");
      setApprovals(items);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load approvals");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function decide(id: string, approved: boolean) {
    setError("");
    try {
      await api(`/api/v1/orchestration/approvals/${id}/${approved ? "approve" : "reject"}`, {
        method: "POST",
      });
      await refresh();
      onChanged();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to decide approval");
    }
  }

  return (
    <Card>
      <div className="flex items-center justify-between">
        <h3 className="text-headline-md text-on-surface">Approvals</h3>
        <span className="text-label-sm text-on-surface-variant">
          {loading ? "Loading…" : `${approvals.length} pending`}
        </span>
      </div>
      {approvals.length === 0 ? (
        <p className="text-body-md text-on-surface-variant">
          No actions need your approval right now.
        </p>
      ) : (
        <ul className="flex flex-col gap-4">
          {approvals.map((approval) => (
            <li
              key={approval.id}
              className="bg-surface shadow-injected p-4 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-label-md text-on-background font-semibold">
                    {approval.action.replaceAll("_", " ")}
                  </p>
                  <StatusBadge status={approval.status} />
                </div>
                <p className="text-body-md text-on-surface-variant mt-1">{approval.detail}</p>
                <p className="text-label-sm text-on-surface-variant mt-1">
                  Workflow {approval.workflow_id}
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => void decide(approval.id, true)}
                  className="px-5 py-2 rounded-full shadow-extruded btn-extruded bg-secondary text-on-secondary text-label-md font-bold"
                >
                  Approve
                </button>
                <button
                  onClick={() => void decide(approval.id, false)}
                  className="px-5 py-2 rounded-full shadow-extruded btn-extruded bg-surface text-label-md text-error"
                >
                  Reject
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {error && (
        <p className="text-label-md text-error" role="alert">
          {error}
        </p>
      )}
    </Card>
  );
}

function WorkflowRow({ workflow }: { workflow: Workflow }) {
  const [tasks, setTasks] = useState<AgentTask[] | null>(null);
  const [open, setOpen] = useState(false);

  async function loadTasks() {
    if (tasks !== null) return;
    try {
      const items = await api<AgentTask[]>(
        `/api/v1/orchestration/workflows/${workflow.id}/tasks`,
      );
      setTasks(items);
    } catch {
      setTasks([]);
    }
  }

  return (
    <li className="bg-surface shadow-injected rounded-xl">
      <button
        onClick={() => {
          setOpen((value) => !value);
          void loadTasks();
        }}
        aria-expanded={open}
        className="w-full flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-4 text-left"
      >
        <div className="min-w-0">
          <p className="text-label-md text-on-background font-semibold">{workflow.name}</p>
          <p className="text-label-sm text-on-surface-variant mt-0.5">
            {new Date(workflow.created_at).toLocaleString()}
            {workflow.error_detail ? ` · ${workflow.error_detail}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={workflow.status} />
          <span className={`material-symbols-outlined text-on-surface-variant ${open ? "rotate-180" : ""}`}>
            expand_more
          </span>
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 flex flex-col gap-2">
          {tasks === null ? (
            <p className="text-label-sm text-on-surface-variant">Loading tasks…</p>
          ) : tasks.length === 0 ? (
            <p className="text-label-sm text-on-surface-variant">No agent tasks recorded.</p>
          ) : (
            tasks.map((task) => (
              <div
                key={task.id}
                className="bg-surface-container-low rounded-lg p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div>
                  <p className="text-label-md text-on-surface">{task.agent}</p>
                  <p className="text-label-sm text-on-surface-variant">
                    Attempt {task.attempt}
                    {task.error_detail ? ` · ${task.error_detail}` : ""}
                  </p>
                </div>
                <StatusBadge status={task.status} />
              </div>
            ))
          )}
        </div>
      )}
    </li>
  );
}

function WorkflowsSection({ refreshKey }: { refreshKey: number }) {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    api<Workflow[]>("/api/v1/orchestration/workflows")
      .then(setWorkflows)
      .catch((requestError) =>
        setError(requestError instanceof Error ? requestError.message : "Unable to load workflows"),
      )
      .finally(() => setLoading(false));
  }, [refreshKey]);

  return (
    <Card>
      <div className="flex items-center justify-between">
        <h3 className="text-headline-md text-on-surface">Workflow history</h3>
        <span className="text-label-sm text-on-surface-variant">
          {loading ? "Loading…" : `${workflows.length} total`}
        </span>
      </div>
      {workflows.length === 0 ? (
        <p className="text-body-md text-on-surface-variant">No workflows have run yet.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {workflows.map((workflow) => (
            <WorkflowRow key={workflow.id} workflow={workflow} />
          ))}
        </ul>
      )}
      {error && (
        <p className="text-label-md text-error" role="alert">
          {error}
        </p>
      )}
    </Card>
  );
}

function AuditSection() {
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api<AuditEntry[]>("/api/v1/orchestration/audit")
      .then(setAudit)
      .catch((requestError) =>
        setError(requestError instanceof Error ? requestError.message : "Unable to load audit log"),
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <Card>
      <div className="flex items-center justify-between">
        <h3 className="text-headline-md text-on-surface">Audit trail</h3>
        <span className="text-label-sm text-on-surface-variant">
          {loading ? "Loading…" : `${audit.length} entries`}
        </span>
      </div>
      {audit.length === 0 ? (
        <p className="text-body-md text-on-surface-variant">No audit events recorded yet.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {audit.map((entry) => (
            <li
              key={entry.id}
              className="bg-surface shadow-injected rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
            >
              <div className="min-w-0">
                <p className="text-label-md text-on-background font-semibold">
                  <span className="text-secondary">{entry.agent}</span> · {entry.action}
                </p>
                <p className="text-label-sm text-on-surface-variant mt-0.5">
                  {new Date(entry.created_at).toLocaleString()}
                  {entry.request_id ? ` · request ${entry.request_id}` : ""}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
      {error && (
        <p className="text-label-md text-error" role="alert">
          {error}
        </p>
      )}
    </Card>
  );
}

export default function OrchestrationPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="p-container-padding md:p-section-margin w-full max-w-5xl mx-auto flex flex-col gap-8">
      <div>
        <h2 className="text-headline-xl text-on-background">Agent Orchestration</h2>
        <p className="text-body-lg text-on-surface-variant mt-2">
          Review what ARIA has done, decide what it may destroy, and inspect how each step ran.
        </p>
      </div>
      <ApprovalsSection onChanged={() => setRefreshKey((key) => key + 1)} />
      <WorkflowsSection refreshKey={refreshKey} />
      <AuditSection />
    </div>
  );
}
