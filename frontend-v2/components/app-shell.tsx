"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Icon, type IconName } from "./icons";
import { PaletteSwitcher } from "./palette-switcher";
import { api } from "@/lib/api";
import { toast } from "@/lib/toast";
import { useActiveContext } from "./use-active-context";
import { useAuth } from "./auth-provider";

type NavGroup = { sec: string; items: { href: string; label: string; icon: IconName }[] };

type AppNotification = {
  id: string;
  ntype: string;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
};

const NOTIF_ICON: Record<string, IconName> = {
  deadline: "calendar",
  digest: "list",
  assessment_result: "clipboard",
  reminder: "clock",
};

function notifIcon(ntype: string): IconName {
  return NOTIF_ICON[ntype] ?? "bell";
}

function relTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diff = Date.now() - then;
  const mins = Math.round(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const NAV: NavGroup[] = [
  { sec: "Learn", items: [
    { href: "/app", label: "Dashboard", icon: "home" },
    { href: "/app/learn", label: "Learn", icon: "message" },
    { href: "/app/map", label: "Knowledge Map", icon: "target" },
    { href: "/app/roadmaps", label: "Roadmaps", icon: "route" },
  ]},
  { sec: "Organize", items: [
    { href: "/app/planner", label: "Planner", icon: "calendar" },
    { href: "/app/assess", label: "Assessments", icon: "clipboard" },
    { href: "/app/materials", label: "Materials", icon: "file" },
    { href: "/app/audio", label: "Audio", icon: "headphones" },
  ]},
  { sec: "Grow", items: [
    { href: "/app/progress", label: "Progress", icon: "trend" },
    { href: "/app/account", label: "Account", icon: "user" },
  ]},
];

const FLAT: NavGroup["items"] = NAV.flatMap((g) => g.items);

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { signout, user } = useAuth();
  const { context, contexts, selectContext } = useActiveContext();
  const isChat = pathname === "/app/learn";
  const isHome = pathname === "/app";

  const [bellOpen, setBellOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notifs, setNotifs] = useState<AppNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const refreshCount = useCallback(() => {
    api<{ unread: number }>("/api/v1/notifications/unread-count")
      .then((c) => setUnread(c.unread))
      .catch(() => {});
  }, []);

  const refreshList = useCallback(() => {
    api<AppNotification[]>("/api/v1/notifications")
      .then((list) => {
        setNotifs(list);
        setUnread(list.filter((n) => n.read_at === null).length);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshCount();
  }, [refreshCount]);

  const initials = (user?.display_name || user?.email || "AR")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("") || "AR";

  const openBell = () => {
    const next = !bellOpen;
    setBellOpen(next);
    setProfileOpen(false);
    if (next) refreshList();
  };

  const markRead = async (id: string) => {
    setNotifs((prev) => prev.map((n) => (n.id === id && n.read_at === null ? { ...n, read_at: new Date().toISOString() } : n)));
    setUnread((u) => Math.max(0, u - 1));
    try {
      await api(`/api/v1/notifications/${id}/read`, { method: "POST" });
    } catch {
      refreshList();
    }
  };

  const markAllRead = async () => {
    setNotifs((prev) => prev.map((n) => ({ ...n, read_at: n.read_at ?? new Date().toISOString() })));
    setUnread(0);
    try {
      await api("/api/v1/notifications/read-all", { method: "POST" });
      toast("All marked as read");
    } catch {
      refreshList();
    }
  };

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setBellOpen(false);
        setProfileOpen(false);
      }
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  if (isChat) {
    return (
      <div style={{ position: "relative", zIndex: 1 }}>
        <button
          className="btn btn-secondary"
          style={{ position: "fixed", top: 16, left: 16, zIndex: 90, width: 42, height: 42, padding: 0, borderRadius: 9999 }}
          onClick={() => router.push("/app")}
          aria-label="Back to dashboard"
        >
          <Icon name="back" size={18} />
        </button>
        {children}
      </div>
    );
  }

  return (
    <div className="shell">
      {!isHome && (
      <aside className="shell-side">
        <Link href="/app" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 10, padding: "6px 12px 16px" }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 11,
              background: "var(--accent-grad)",
              color: "#fff",
              fontWeight: 800,
              fontSize: 16,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "var(--shadow-2)",
            }}
          >
            A
          </div>
          <div>
            <div style={{ fontSize: 19, fontWeight: 800, letterSpacing: "-.5px", lineHeight: 1 }}>ARIA</div>
            <div style={{ fontSize: 8.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1.4, color: "var(--text-3)" }}>AI Learning System</div>
          </div>
        </Link>

        {NAV.map((group) => (
          <div key={group.sec}>
            <div className="nav-sec">{group.sec}</div>
            {group.items.map((item) => {
              const active = pathname === item.href || (item.href !== "/app" && pathname.startsWith(item.href));
              return (
                <Link key={item.href} href={item.href} className={`nav-link${active ? " active" : ""}`}>
                  <Icon name={item.icon} size={17} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}

        <div style={{ marginTop: "auto", fontSize: 11, color: "var(--text-3)", padding: "14px 12px 0", fontWeight: 700 }}>
          <span style={{ display: "inline-flex", verticalAlign: "-2px", color: "var(--accent)" }}>
            <Icon name="flame" size={13} />
          </span>{" "}
          Tutor Mode: <span style={{ color: "var(--accent-strong)" }}>Adaptive</span>
        </div>
      </aside>
      )}

      <div className="shell-main" ref={ref}>
        <header className="shell-top">
          <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
            <div style={{ fontWeight: 700, color: "var(--text-2)", fontSize: 13, whiteSpace: "nowrap" }}>
              {pathname === "/app" ? "Dashboard" : FLAT.find((i) => i.href === pathname)?.label ?? "ARIA"}
            </div>
            {!isChat && contexts.length > 1 && (
              <select
                className="input"
                aria-label="Active learning context"
                value={context?.id ?? ""}
                onChange={(e) => selectContext(e.target.value)}
                style={{ maxWidth: 220, height: 34, fontSize: 12.5, padding: "4px 10px" }}
              >
                {contexts.map((c) => (
                  <option key={c.id} value={c.id}>{c.title}</option>
                ))}
              </select>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button type="button" className="bell-btn" onClick={(e) => { e.stopPropagation(); openBell(); }} aria-label="Notifications" aria-expanded={bellOpen}>
              <Icon name="bell" size={19} />
              {unread > 0 && <span className="badge">{unread}</span>}
            </button>
            <PaletteSwitcher />
            <button type="button" className="avatar-btn" onClick={(e) => { e.stopPropagation(); setProfileOpen((o) => !o); setBellOpen(false); }} aria-label="Profile" aria-expanded={profileOpen}>
              {initials}
              <span className="online" />
            </button>

            {bellOpen && (
              <div className="popover-card" style={{ width: 330, maxHeight: 420, overflowY: "auto" }}>
                <div className="pop-head" style={{ justifyContent: "space-between" }}>
                  <b style={{ fontSize: 14 }}>Notifications</b>
                  <button
                    className="btn btn-ghost"
                    style={{ padding: "4px 10px", fontSize: 11, borderRadius: 99 }}
                    onClick={(e) => { e.stopPropagation(); void markAllRead(); }}
                  >
                    Mark all read
                  </button>
                </div>
                {notifs.length === 0 ? (
                  <div style={{ textAlign: "center", padding: 26, color: "var(--text-3)", fontSize: 13 }}>No notifications yet.</div>
                ) : (
                  notifs.map((n) => (
                    <button
                      type="button"
                      key={n.id}
                      className={`notif-item${n.read_at === null ? " unread" : ""}`}
                      onClick={(e) => { e.stopPropagation(); if (n.read_at === null) void markRead(n.id); }}
                      disabled={n.read_at !== null}
                      aria-label={n.read_at === null ? `Mark ${n.title} as read` : n.title}
                      style={{ width: "100%", textAlign: "left", background: "none", border: "none", cursor: n.read_at === null ? "pointer" : "default", padding: 12 }}
                    >
                      <span style={{ color: "var(--accent)", display: "inline-flex", marginTop: 1 }}>
                        <Icon name={notifIcon(n.ntype)} size={16} />
                      </span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, fontSize: 13 }}>{n.title}</div>
                        <div style={{ fontSize: 12, color: "var(--text-2)" }}>{n.body}</div>
                        <div style={{ fontSize: 10, color: "var(--text-3)", marginTop: 3 }}>{relTime(n.created_at)}</div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            )}

            {profileOpen && (
              <div className="popover-card" onClick={(e) => e.stopPropagation()}>
                <div className="pop-head">
                  <div style={{ width: 40, height: 40, borderRadius: 12, background: "var(--accent-grad)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800 }}>{initials}</div>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: 14 }}>{user?.display_name ?? "Learner"}</div>
                    <div style={{ fontSize: 11, color: "var(--text-3)" }}>{user?.email ?? ""}</div>
                  </div>
                </div>
                <Link href="/app" className="pop-link"><Icon name="home" size={17} /> Home Dashboard</Link>
                <Link href="/app/materials" className="pop-link"><Icon name="file" size={17} /> Materials</Link>
                <Link href="/app/planner" className="pop-link"><Icon name="calendar" size={17} /> Planner</Link>
                <Link href="/app/progress" className="pop-link"><Icon name="trend" size={17} /> Progress</Link>
                <Link href="/app/account" className="pop-link"><Icon name="user" size={17} /> Account & Settings</Link>
                <button type="button" className="pop-link signout" style={{ width: "100%", textAlign: "left", background: "none", border: "none", cursor: "pointer" }} onClick={() => { signout().then(() => router.push("/")); }}><Icon name="logout" size={17} /> Sign Out</button>
              </div>
            )}
          </div>
        </header>
        {user && !user.verified && !bannerDismissed && (
          <div className="banner" role="status" style={{ margin: "14px 18px 0" }}>
            <span style={{ color: "var(--accent)", display: "inline-flex" }}><Icon name="alert" size={18} /></span>
            <div style={{ flex: 1 }}>
              <b>Please verify your email</b>
              <p style={{ margin: 0 }}>Check your inbox for the verification link ({user.email}).</p>
            </div>
            <button
              className="btn btn-secondary"
              onClick={async () => {
                try {
                  await api("/api/v1/auth/verify-email/request", { method: "POST" });
                  toast("If your email is unverified, a new link is on its way.");
                } catch {
                  toast("Could not send the verification email.");
                }
              }}
            >
              Resend link
            </button>
            <button className="btn btn-ghost" aria-label="Dismiss verification banner" onClick={() => setBannerDismissed(true)}>
              <Icon name="x" size={16} />
            </button>
          </div>
        )}
        <main className="shell-content">
          {!isChat && (
            <nav className="mobile-nav" aria-label="Primary">
              {FLAT.map((item) => {
                const active = pathname === item.href || (item.href !== "/app" && pathname.startsWith(item.href));
                return (
                  <Link key={item.href} href={item.href} className={active ? "active" : undefined}>
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}
