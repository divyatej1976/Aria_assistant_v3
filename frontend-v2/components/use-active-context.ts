"use client";

// Shared active-context store lives in active-context-store.tsx and is mounted
// once in app/layout.tsx; this file keeps the original import path stable.
export {
  ActiveContextProvider,
  useActiveContext,
  type ActiveContext,
} from "./active-context-store";