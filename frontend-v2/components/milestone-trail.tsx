"use client";

import { useEffect, useRef } from "react";
import { animate, createScope } from "animejs";
import { Icon } from "./icons";
import { useMotionPreference } from "./motion-system";

type Milestone = { key: string; title: string; ticked: boolean };

export function MilestoneTrail({ milestones, onSelect, roadmapId }: { milestones: Milestone[]; onSelect: (key: string) => void; roadmapId?: string }) {
  const root = useRef<HTMLDivElement>(null);
  const status = useRef<HTMLParagraphElement>(null);
  const previous = useRef<Set<string> | null>(null);
  const celebration = useRef<{ snapshot: string; keys: string[]; expires: number } | null>(null);
  const reduced = useMotionPreference();
  const completedKey = milestones.filter(item => item.ticked).map(item => item.key).join("|");
  const firstUpcoming = milestones.find(item => !item.ticked)?.key;
  const lastCompleted = milestones.filter(item => item.ticked).at(-1)?.key;

  useEffect(() => {
    const done = new Set(completedKey.split("|").filter(Boolean));
    const storageKey = roadmapId ? `aria.milestones.${roadmapId}` : null;
    let baseline = previous.current;
    try {
      if (!baseline && storageKey) {
        const saved: unknown = JSON.parse(sessionStorage.getItem(storageKey) ?? "null");
        if (Array.isArray(saved) && saved.every(key => typeof key === "string")) baseline = new Set(saved);
      }
      if (storageKey) sessionStorage.setItem(storageKey, JSON.stringify([...done]));
    } catch { /* Optional celebration memory must never block the roadmap. */ }
    const additions = baseline ? [...done].filter(key => !baseline.has(key)) : [];
    if (additions.length) celebration.current = { snapshot: completedKey, keys: additions, expires: Date.now() + 3000 };
    const pending = celebration.current;
    const newlyDone = pending?.snapshot === completedKey && pending.expires > Date.now() ? pending.keys : [];
    previous.current = done;
    if (!root.current || newlyDone.length === 0) return;
    const elements = Array.from(root.current.querySelectorAll<HTMLElement>("[data-milestone]"))
      .filter(element => newlyDone.includes(element.dataset.milestone!));
    if (status.current) status.current.textContent = `${newlyDone.length} new milestone${newlyDone.length === 1 ? "" : "s"} completed.`;
    const scope = createScope({ root }).add(() => {
      if (!reduced) animate(elements, { scale: [1, 1.08, 1], duration: 850, ease: "inOutSine" });
    });
    const timer = window.setTimeout(() => { if (status.current) status.current.textContent = ""; }, Math.max(0, (pending?.expires ?? Date.now()) - Date.now()));
    const announcement = status.current;
    return () => {
      scope.revert();
      window.clearTimeout(timer);
      if (announcement) announcement.textContent = "";
    };
  }, [completedKey, reduced, roadmapId]);

  return <div className="milestone-trail" ref={root}>
    <div className="section-head"><div><p className="eyebrow">YOUR PATH TO UNDERSTANDING</p><h2>{firstUpcoming ? "Your next step." : "Your path is complete."}</h2></div><span className="milestone-count">{milestones.filter(item => item.ticked).length} / {milestones.length} complete</span></div>
    <ol className="milestone-track milestone-next">{milestones.filter(item => item.key === firstUpcoming || item.key === lastCompleted).map(item => <li key={item.key} className={item.ticked ? "done" : "current"}><button data-milestone={item.key} onClick={() => onSelect(item.key)} aria-label={`${item.title}, ${item.ticked ? "completed" : "next milestone"}`}><span className="milestone-disc"><Icon name={item.ticked ? "check" : "arrow"} size={18} /></span><span>{item.title}</span><small>{item.ticked ? "Completed" : "Next milestone"}</small></button></li>)}</ol>
    <p ref={status} className="milestone-status" role="status" />
  </div>;
}
