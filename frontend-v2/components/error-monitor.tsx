"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/react";
import { useAuth } from "@/components/auth-provider";

const DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;
let started = false;

/** Sends browser errors to Sentry, tagged with the learner's id, when NEXT_PUBLIC_SENTRY_DSN is set. */
export function ErrorMonitor() {
  const { user } = useAuth();
  useEffect(() => {
    if (!DSN || started) return;
    started = true;
    Sentry.init({
      dsn: DSN,
      environment: process.env.NEXT_PUBLIC_VERCEL_ENV ?? "development",
      tracesSampleRate: 0.1,
    });
  }, []);
  useEffect(() => {
    if (DSN) Sentry.setUser(user ? { id: user.id } : null);
  }, [user]);
  return null;
}
