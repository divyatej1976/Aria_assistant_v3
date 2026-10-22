"use client";

import { useCallback, useEffect, useRef, useState, ViewTransition, type ReactNode, type CSSProperties, type MouseEventHandler } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Icon, type IconName } from "./icons";
import { PaletteSwitcher } from "./palette-switcher";
import { api } from "@/lib/api";
import { toast } from "@/lib/toast";
import { useActiveContext } from "./use-active-context";
import { useAuth } from "./auth-provider";
import { AnimatePresence, LayoutGroup, motion, useIsPresent } from "motion/react";
import { useMotionPreference } from "./motion-system";
import { useHydrated } from "@/lib/use-hydrated";
import { Modal } from "./modal";
import { useDismissed } from "@/lib/use-dismissed";

function ShellPopover({ children, style, onClick }: { children: ReactNode; style?: CSSProperties; onClick?: MouseEventHandler<HTMLDivElement> }) {
  const present = useIsPresent();
  const reduced = useMotionPreference();
  return <motion.div className="popover-card" style={style} onClick={onClick}
    inert={!present} aria-hidden={!present ? true : undefined}
    initial={{ opacity: 0, y: reduced ? 0 : -6 }} animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: reduced ? 0 : -4 }}
    transition={{ duration: reduced ? 0 : 0.18, ease: [0.22, 1, 0.36, 1] }}>
    {children}
  </motion.div>;
}

type NavItem = { href: string; label: string; icon: IconName; pages: { href: string; label: string }[] };

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

// Seven destinations. Where two pages serve one job they share a destination
// and switch with tabs, so the sidebar stays short.
// The bar shows only the everyday places; the rest sit under "More" so a new learner is not overwhelmed.
const MAIN_TABS = ["/app", "/app/learn", "/app/assess"];

const NAV: NavItem[] = [
  { href: "/app", label: "Home", icon: "home", pages: [{ href: "/app", label: "Home" }] },
  { href: "/app/learn", label: "Learn", icon: "message", pages: [{ href: "/app/learn", label: "Learn" }] },
  { href: "/app/materials", label: "Library", icon: "folder", pages: [{ href: "/app/materials", label: "Library" }] },
  { href: "/app/audio", label: "Audio", icon: "headphones", pages: [{ href: "/app/audio", label: "Audio" }] },
  { href: "/app/assess", label: "Practice", icon: "clipboard", pages: [{ href: "/app/assess", label: "Practice" }] },
  { href: "/app/roadmaps", label: "Plan", icon: "route", pages: [
    { href: "/app/roadmaps", label: "Roadmap" }, { href: "/app/planner", label: "Exams & deadlines" },
  ]},
  { href: "/app/progress", label: "Progress", icon: "trend", pages: [
    { href: "/app/progress", label: "Overview" }, { href: "/app/map", label: "Topic map" },
  ]},
];

function navItemFor(pathname: string): NavItem | undefined {
  return NAV.find((item) => item.pages.some((page) => page.href === "/app"
    ? pathname === "/app"
    : pathname === page.href || pathname.startsWith(page.href + "/")));
}

export function AppShell({ children }: { children: ReactNode }) {
  const hydrated = useHydrated();
  const pathname = usePathname();
  const router = useRouter();
  const { signout, user, loading: authLoading } = useAuth();
  const { context, contexts, selectContext, loading: contextLoading } = useActiveContext();
  const isChat = pathname === "/app/learn";
  const current = navItemFor(pathname);

  const [bellOpen, setBellOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const moreRef = useRef<HTMLDetailsElement>(null);
  // "More" closes when you click anywhere else.
  useEffect(() => {
    const close = (event: MouseEvent) => { if (!moreRef.current?.contains(event.target as Node)) moreRef.current?.removeAttribute("open"); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  const [notifs, setNotifs] = useState<AppNotification[]>([]);
  const [unread, setUnread] = useState(0);
  // Dismissal persists per browser so the verify banner doesn't reappear on
  // every navigation/reload; it clears automatically once the email verifies.
  const { dismissed: bannerDismissed, dismiss: dismissBanner } = useDismissed(`aria.verifyBannerDismissed:${user?.id ?? "anonymous"}`);
  // The reminder shows for a few seconds per visit; the avatar dot keeps reminding after that.
  const [bannerTimedOut, setBannerTimedOut] = useState(false);
  useEffect(() => {
    if (!user || user.verified) return;
    const timer = window.setTimeout(() => setBannerTimedOut(true), 8000);
    return () => window.clearTimeout(timer);
  }, [user]);
  const ref = useRef<HTMLDivElement>(null);
  const bellTrigger = useRef<HTMLButtonElement>(null);
  const profileTrigger = useRef<HTMLButtonElement>(null);

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

  // Streaks, "today" and dates are computed server-side in the learner's timezone; tell it ours once per session.
  useEffect(() => {
    if (!user) return;
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    try { if (!zone || window.sessionStorage.getItem("aria.tz") === zone) return; } catch {}
    api("/api/v1/me/preferences", { method: "PUT", body: JSON.stringify({ key: "timezone", value: zone }) })
      .then(() => { try { window.sessionStorage.setItem("aria.tz", zone); } catch {} })
      .catch(() => {});
  }, [user]);

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

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (bellOpen) bellTrigger.current?.focus();
        if (profileOpen) profileTrigger.current?.focus();
        setBellOpen(false);
        setProfileOpen(false);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [bellOpen, profileOpen]);

  useEffect(() => {
    if (!bellOpen && !profileOpen) return;
    const frame = requestAnimationFrame(() => ref.current?.querySelector<HTMLElement>(".popover-card:not([inert]) button, .popover-card:not([inert]) a")?.focus());
    return () => cancelAnimationFrame(frame);
  }, [bellOpen, profileOpen]);

  return (
    <div className={`shell${isChat ? " shell-chat" : ""}`}>
      <div className="shell-main">
        {/* One bar on every page: brand, the main sections and More, then alerts and profile. */}
        <header className="shell-top">
          <div className="top-left">
            <button className="btn btn-secondary mobile-menu-toggle" disabled={!hydrated || authLoading || contextLoading} aria-label="Open navigation" onClick={() => setMobileMenuOpen(true)}><Icon name="menu" size={20} /></button>
            <Link href="/app" className="shell-brand" aria-label="ARIA dashboard">
              <span className="brand-mark">A</span>
              <span className="brand-name">ARIA</span>
            </Link>
          </div>
          <LayoutGroup id="workspace-navigation">
          <nav className="top-nav" aria-label="Workspace">
            {NAV.filter((item) => MAIN_TABS.includes(item.href)).map((item) => {
              const active = current === item;
              return (
                <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined} className={`nav-link${active ? " active" : ""}`}>
                  {active && <motion.span layoutId="active-navigation" className="nav-active-surface" aria-hidden="true" transition={{ type: "spring", stiffness: 420, damping: 36 }} />}
                  <Icon name={item.icon} size={16} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
            <details ref={moreRef} className="nav-more">
              <summary className={`nav-link${current && !MAIN_TABS.includes(current.href) ? " active" : ""}`}>
                <Icon name="menu" size={16} />
                <span>{current && !MAIN_TABS.includes(current.href) ? current.label : "More"}</span>
              </summary>
              <div className="nav-more-menu">
                {NAV.filter((item) => !MAIN_TABS.includes(item.href)).map((item) => (
                  <Link key={item.href} href={item.href} aria-current={current === item ? "page" : undefined}
                    onClick={() => moreRef.current?.removeAttribute("open")}>
                    <Icon name={item.icon} size={16} /><span>{item.label}</span>
                  </Link>
                ))}
              </div>
            </details>
          </nav>
          </LayoutGroup>
          <div ref={ref} className="top-right">
            {contexts.length > 1 && (
              <select
                className="input top-context"
                aria-label="Active learning context"
                value={context?.id ?? ""}
                onChange={(e) => selectContext(e.target.value)}
              >
                {contexts.map((c) => (
                  <option key={c.id} value={c.id}>{c.title}</option>
                ))}
              </select>
            )}
            <button ref={bellTrigger} disabled={!hydrated || authLoading || contextLoading} type="button" className="bell-btn" onClick={(e) => { e.stopPropagation(); openBell(); }} aria-label="Notifications" aria-expanded={bellOpen}>
              <Icon name="bell" size={19} />
              {unread > 0 && <span className="badge">{unread}</span>}
            </button>
            <PaletteSwitcher />
            <button ref={profileTrigger} disabled={!hydrated || authLoading || contextLoading} type="button" className="avatar-btn" onClick={(e) => { e.stopPropagation(); setProfileOpen((o) => !o); setBellOpen(false); }} aria-label="Profile" aria-expanded={profileOpen}>
              {initials}
              {user && !user.verified && <span className="attention-dot" title="Email not verified" />}
            </button>

            <AnimatePresence>
            {bellOpen && (
              <ShellPopover key="notifications" style={{ width: 330, maxHeight: 420, overflowY: "auto" }}>
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
              </ShellPopover>
            )}

            {profileOpen && (
              <ShellPopover key="profile" onClick={(e) => { e.stopPropagation(); if ((e.target as HTMLElement).closest("a")) setProfileOpen(false); }}>
                <div className="pop-head">
                  <div style={{ width: 40, height: 40, borderRadius: 12, background: "var(--accent-grad)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800 }}>{initials}</div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 800, fontSize: 14 }}>{user?.display_name ?? "Learner"}</div>
                    <div style={{ fontSize: 11, color: "var(--text-3)", overflow: "hidden", textOverflow: "ellipsis" }}>{user?.email ?? ""}</div>
                    <span className={`pop-status${user?.verified ? " ok" : ""}`}>{user?.verified ? "Email verified" : "Email not verified"}</span>
                  </div>
                </div>
                <Link href="/app/account" className="pop-link"><Icon name="user" size={17} /> Account & settings</Link>
                <button type="button" className="pop-link signout" onClick={() => { signout().then(() => router.push("/")).catch(() => toast("Sign-out failed. Your session may still be active. Please retry.", "error")); }}><Icon name="logout" size={17} /> Sign Out</button>
              </ShellPopover>
            )}
            </AnimatePresence>
          </div>
        </header>
        {!isChat && user && !user.verified && !bannerDismissed && !bannerTimedOut && (
          <div className="banner shell-banner" role="status">
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
                  toast("Could not send the verification email.", "error");
                }
              }}
            >
              Resend link
            </button>
            <button className="btn btn-ghost" aria-label="Dismiss verification banner" onClick={dismissBanner}>
              <Icon name="x" size={16} />
            </button>
          </div>
        )}
        <main className={`shell-content${isChat ? " shell-content-flush" : ""}`}>
          {!isChat && (
            <LayoutGroup id="mobile-workspace-navigation">
            <nav className="mobile-nav" aria-label="Primary">
              {NAV.filter((item) => MAIN_TABS.includes(item.href)).map((item) => {
                const active = current === item;
                return (
                  <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined} className={active ? "active" : undefined}>
                    {active && <motion.span layoutId="mobile-active-navigation" className="mobile-active-surface" aria-hidden="true" />}
                    <Icon name={item.icon} size={20} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
              <button type="button" className={current && !MAIN_TABS.includes(current.href) ? "active" : undefined} onClick={() => setMobileMenuOpen(true)}>
                <Icon name="menu" size={20} />
                <span>{current && !MAIN_TABS.includes(current.href) ? current.label : "More"}</span>
              </button>
            </nav>
            </LayoutGroup>
          )}
          {current && current.pages.length > 1 && (
            <nav className="section-tabs" aria-label={`${current.label} sections`}>
              {current.pages.map((page) => (
                <Link key={page.href} href={page.href} aria-current={pathname === page.href ? "page" : undefined} className={pathname === page.href ? "active" : undefined}>
                  {page.label}
                </Link>
              ))}
            </nav>
          )}
                    {/* Route changes are transitions, so the browser cross-fades the
              outgoing page into the incoming one while the shell stays put. */}
          <ViewTransition key={pathname} enter="page-enter" exit="page-exit" default="none">
            <div className="route-view">{children}</div>
          </ViewTransition>
        </main>
      </div>
      <Modal open={mobileMenuOpen} title="Navigation" onClose={() => setMobileMenuOpen(false)}>
        <div className="modal mobile-workspace-drawer">
          <div className="section-head"><h2>Explore ARIA</h2><button className="btn btn-ghost" aria-label="Close navigation" onClick={() => setMobileMenuOpen(false)}><Icon name="x" /></button></div>
          <label className="field-label" htmlFor="mobile-subject">Learning subject</label>
          <select className="input" id="mobile-subject" value={context?.id ?? ""} onChange={event => selectContext(event.target.value)}>{contexts.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select>
          <nav aria-label="Mobile workspace">
            {[...NAV, { href: "/app/account", label: "Account", icon: "user" as IconName }].map(item => <Link key={item.href} href={item.href} aria-current={pathname === item.href ? "page" : undefined} onClick={() => setMobileMenuOpen(false)}><Icon name={item.icon} size={18} /><span>{item.label}</span></Link>)}
          </nav>
        </div>
      </Modal>
    </div>
  );
}
