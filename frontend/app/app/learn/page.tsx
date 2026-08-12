"use client";

import { useState } from "react";
import Link from "next/link";

import { MapView } from "../../../components/map-view";
import { StudyView } from "../../../components/study-view";
import { useActiveContext } from "../../../components/use-active-context";

export default function LearnPage() {
  const { context, loading } = useActiveContext();
  const [mode, setMode] = useState<"study" | "map">("study");

  if (loading) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <p className="text-body-md text-on-surface-variant">Loading your learning workspace…</p>
      </div>
    );
  }

  if (!context) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <div className="bg-surface shadow-extruded rounded-3xl p-8 max-w-xl">
          <h2 className="text-headline-md text-on-surface mb-4">No learning context yet</h2>
          <p className="text-body-md text-on-surface-variant mb-6">
            Set up your learning context and add material to start studying.
          </p>
          <Link href="/onboarding" className="inline-flex items-center gap-2 px-8 py-4 rounded-xl shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
            Initialize learning journey
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-2">
          <button
            onClick={() => setMode("study")}
            className={`px-5 py-2 rounded-full text-label-md transition-all ${mode === "study" ? "bg-secondary text-on-secondary shadow-injected" : "bg-surface text-secondary shadow-extruded btn-extruded"}`}
          >
            Study
          </button>
          <button
            onClick={() => setMode("map")}
            className={`px-5 py-2 rounded-full text-label-md transition-all ${mode === "map" ? "bg-secondary text-on-secondary shadow-injected" : "bg-surface text-secondary shadow-extruded btn-extruded"}`}
          >
            Topology Map
          </button>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/app/notes" className="text-label-md text-secondary hover:underline">Notes</Link>
          <Link href="/app/resources" className="text-label-md text-secondary hover:underline">Manage resources</Link>
        </div>
      </div>
      {mode === "study" ? (
        <StudyView contextId={context.id} contextTitle={context.title} />
      ) : (
        <MapView contextId={context.id} contextTitle={context.title} />
      )}
    </div>
  );
}
