"use client";

import { ReactNode, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { api } from "../lib/api";
import { useAuth } from "./auth-provider";
import { ThemeToggle } from "./theme-toggle";
import { registerServiceWorker } from "../lib/push";

type AppNotification = {
  id: string;
  ntype: string;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
};

function NotificationBell() {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [open, setOpen] = useState(false);
  const popupRef = useRef<HTMLDivElement>(null);

  async function refresh() {
    try {
      const items = await api<AppNotification[]>("/api/v1/notifications");
      setNotifications(items);
    } catch {
      setNotifications([]);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
        return;
      }
      if (event.key !== "Tab" || !popupRef.current) return;
      const focusable = popupRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    popupRef.current?.focus();
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  const triggerRef = useRef<HTMLButtonElement>(null);

  const unread = notifications.filter((item) => item.read_at === null).length;

  async function markRead(id: string) {
    try {
      await api(`/api/v1/notifications/${id}/read`, { method: "POST" });
      await refresh();
    } catch {
      // Best effort; ignore transient failures.
    }
  }

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        aria-label={`Notifications (${unread} unread)`}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls="notifications-popup"
        onClick={() => {
          setOpen((value) => !value);
          if (!open) void refresh();
        }}
        className="w-10 h-10 rounded-full shadow-extruded flex items-center justify-center text-on-surface-variant bg-surface relative"
      >
        <span className="material-symbols-outlined">notifications</span>
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] rounded-full bg-secondary text-on-secondary text-[10px] font-bold flex items-center justify-center px-1">
            {unread}
          </span>
        )}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" aria-hidden="true" onClick={() => setOpen(false)} />
          <div
            ref={popupRef}
            id="notifications-popup"
            role="dialog"
            aria-label="Notifications"
            tabIndex={-1}
            className="absolute right-0 top-12 z-50 w-80 bg-surface shadow-extruded rounded-3xl p-4 flex flex-col gap-3 outline-none"
          >
            <p className="text-label-md text-secondary font-bold">Notifications</p>
            {notifications.length === 0 ? (
              <p className="text-body-md text-on-surface-variant" role="status">
                No notifications yet.
              </p>
            ) : (
              notifications.slice(0, 10).map((item) => (
                <button
                  key={item.id}
                  onClick={() => void markRead(item.id)}
                  className={`text-left rounded-xl p-3 ${item.read_at === null ? "bg-surface-container-low" : "opacity-60"}`}
                >
                  <p className="text-label-md text-on-surface font-semibold">{item.title}</p>
                  <p className="text-label-sm text-on-surface-variant mt-1">{item.body}</p>
                </button>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

type NavItem = {
  href: string;
  label: string;
  icon: string;
  active: (pathname: string) => boolean;
  coming?: boolean;
  more?: boolean;
};

const NAV: NavItem[] = [
  { href: "/app", label: "Dashboard", icon: "dashboard", active: (p) => p === "/app" },
  { href: "/app/learn", label: "Learn", icon: "school", active: (p) => p.startsWith("/app/learn") },
  { href: "/app/assess", label: "Assess", icon: "fact_check", active: (p) => p.startsWith("/app/assess") },
  { href: "/app/resources", label: "Resources", icon: "library_books", active: (p) => p.startsWith("/app/resources") },
  { href: "/app/notes", label: "Notes", icon: "sticky_note_2", active: (p) => p.startsWith("/app/notes") },
  { href: "/app/progress", label: "Progress", icon: "trending_up", active: (p) => p.startsWith("/app/progress") },
  { href: "/app/planner", label: "Planner", icon: "calendar_month", active: (p) => p.startsWith("/app/planner") },
  { href: "/app/account", label: "Settings", icon: "settings", active: (p) => p.startsWith("/app/account") },
];

const BOTTOM_NAV: NavItem[] = [
  { href: "/app", label: "Dashboard", icon: "dashboard", active: (p) => p === "/app" },
  { href: "/app/learn", label: "Learn", icon: "school", active: (p) => p.startsWith("/app/learn") },
  { href: "/app/assess", label: "Assess", icon: "fact_check", active: (p) => p.startsWith("/app/assess") },
  { href: "/app/notes", label: "Notes", icon: "sticky_note_2", active: (p) => p.startsWith("/app/notes") },
  { href: "/app/progress", label: "Progress", icon: "trending_up", active: (p) => p.startsWith("/app/progress") },
  { href: "/app/account", label: "Settings", icon: "settings", active: (p) => p.startsWith("/app/account") },
  { href: "/app/more", label: "More", icon: "more_horiz", active: (p) => p.startsWith("/app/resources") || p.startsWith("/app/planner"), more: true },
];

const MORE_NAV: NavItem[] = [
  { href: "/app/resources", label: "Resources", icon: "library_books", active: (p) => p.startsWith("/app/resources") },
  { href: "/app/planner", label: "Planner", icon: "calendar_month", active: (p) => p.startsWith("/app/planner") },
];

function NavList({ pathname }: { pathname: string }) {
  return (
    <ul className="flex flex-col gap-2 px-container-padding">
      {NAV.map((item) => {
        const active = item.active(pathname);
        return (
          <li key={item.label}>
            {item.coming ? (
              <span
                aria-disabled="true"
                title="Coming in a later step"
                className="flex items-center gap-3 py-3 px-4 rounded-lg text-on-surface-variant/50 select-none"
              >
                <span className="material-symbols-outlined">{item.icon}</span>
                <span className="text-label-md">{item.label}</span>
              </span>
            ) : (
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-3 py-3 px-4 rounded-lg transition-all duration-200 ease-out font-label-md ${
                  active
                    ? "bg-surface text-secondary font-bold border-r-4 border-secondary shadow-injected"
                    : "text-on-surface-variant hover:bg-surface-container-low"
                }`}
              >
                <span className={`material-symbols-outlined ${active ? "ms-fill" : ""}`}>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { learner } = useAuth();
  const [moreOpen, setMoreOpen] = useState(false);
  const moreButtonRef = useRef<HTMLButtonElement>(null);
  const moreSheetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void registerServiceWorker();
  }, []);

  useEffect(() => {
    if (!moreOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMoreOpen(false);
        moreButtonRef.current?.focus();
        return;
      }
      if (event.key !== "Tab" || !moreSheetRef.current) return;
      const focusable = moreSheetRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    moreSheetRef.current?.focus();
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [moreOpen]);

  function closeMore() {
    setMoreOpen(false);
    moreButtonRef.current?.focus();
  }

  return (
    <div className="min-h-screen bg-background text-on-background font-sans">
      {/* Desktop sidebar */}
      <nav
        aria-label="Sidebar Navigation"
        className="hidden md:flex bg-surface h-screen w-64 rounded-r-xl fixed left-0 top-0 flex-col py-container-padding z-40 shadow-extruded"
      >
        <div className="px-container-padding mb-8">
          <h1 className="text-headline-md text-secondary font-extrabold tracking-tight">ARIA</h1>
          <p className="text-label-sm text-on-surface-variant mt-1">AI Learning Operating System</p>
        </div>
        <div className="flex flex-col gap-2 flex-grow">
          <NavList pathname={pathname} />
        </div>
        <div className="px-container-padding mt-auto">
          <Link
            href="/app/assess"
            className="w-full py-3 rounded-lg shadow-extruded btn-extruded bg-surface text-secondary text-label-md font-bold flex items-center justify-center gap-2"
          >
            <span className="material-symbols-outlined">add</span>
            Start assessment
          </Link>
          <div className="mt-6 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full shadow-extruded bg-surface-variant flex items-center justify-center text-secondary">
              <span className="material-symbols-outlined">person</span>
            </div>
            <div className="min-w-0">
              <p className="text-label-md text-on-surface truncate">{learner?.display_name || learner?.email || "Learner"}</p>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <NotificationBell />
              <ThemeToggle />
            </div>
          </div>
        </div>
      </nav>

      {/* Mobile top header */}
      <header className="md:hidden flex justify-between items-center px-container-padding h-16 sticky top-0 z-50 bg-surface border-b border-outline-variant">
        <div className="text-headline-md font-extrabold text-secondary">ARIA</div>
        <div className="flex items-center gap-4">
          <NotificationBell />
          <ThemeToggle />
          <Link href="/app/account" aria-label="Account" className="text-on-surface-variant hover:opacity-80 transition-opacity">
            <span className="material-symbols-outlined">account_circle</span>
          </Link>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-grow md:ml-64 min-h-screen pb-24 md:pb-0">{children}</main>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 w-full bg-surface z-50 flex justify-around py-2 border-t border-outline-variant pb-[env(safe-area-inset-bottom)]">
        {BOTTOM_NAV.map((item) => {
          const active = item.active(pathname);
          if (item.more) {
            return (
              <button
                key={item.label}
                ref={moreButtonRef}
                type="button"
                aria-expanded={moreOpen}
                aria-controls="more-nav-sheet"
                aria-haspopup="dialog"
                aria-label={active ? "More (currently active)" : "More navigation"}
                onClick={() => setMoreOpen((value) => !value)}
                className={`flex flex-col items-center py-1 ${active || moreOpen ? "text-secondary font-bold" : "text-on-surface-variant"}`}
              >
                <span className="material-symbols-outlined">{item.icon}</span>
                <span className="text-[10px] mt-0.5">{item.label}</span>
              </button>
            );
          }
          return (
            <span key={item.label}>
              {item.coming ? (
                <span aria-disabled="true" className="flex flex-col items-center text-on-surface-variant/50 py-1">
                  <span className="material-symbols-outlined">{item.icon}</span>
                  <span className="text-[10px] mt-0.5">{item.label}</span>
                </span>
              ) : (
                <Link
                  href={item.href}
                  onClick={() => setMoreOpen(false)}
                  className={`flex flex-col items-center py-1 ${active ? "text-secondary font-bold" : "text-on-surface-variant"}`}
                >
                  <span className={`material-symbols-outlined ${active ? "ms-fill" : ""}`}>{item.icon}</span>
                  <span className="text-[10px] mt-0.5">{item.label}</span>
                </Link>
              )}
            </span>
          );
        })}
      </nav>

      {/* Mobile "More" sheet: Resources + Planner */}
      {moreOpen && (
        <div
          ref={moreSheetRef}
          id="more-nav-sheet"
          role="dialog"
          aria-modal="true"
          aria-label="More navigation"
          tabIndex={-1}
          className="md:hidden fixed inset-0 z-50 flex items-end outline-none"
        >
          <div className="absolute inset-0 bg-black/30" aria-hidden="true" onClick={closeMore} />
          <div className="relative w-full bg-surface rounded-t-3xl shadow-extruded p-6 pb-[calc(env(safe-area-inset-bottom)+24px)]">
            <div className="flex justify-between items-center mb-4">
              <p className="text-label-md text-secondary font-bold">More</p>
              <button
                type="button"
                aria-label="Close more navigation"
                onClick={closeMore}
                className="w-10 h-10 rounded-full shadow-extruded flex items-center justify-center text-on-surface-variant bg-surface"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <ul className="flex flex-col gap-2">
              {MORE_NAV.map((item) => {
                const active = item.active(pathname);
                return (
                  <li key={item.label}>
                    <Link
                      href={item.href}
                      onClick={() => setMoreOpen(false)}
                      aria-current={active ? "page" : undefined}
                      className={`flex items-center gap-3 py-3 px-4 rounded-lg text-label-md ${
                        active ? "bg-surface text-secondary font-bold shadow-injected" : "text-on-surface-variant hover:bg-surface-container-low"
                      }`}
                    >
                      <span className="material-symbols-outlined">{item.icon}</span>
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
