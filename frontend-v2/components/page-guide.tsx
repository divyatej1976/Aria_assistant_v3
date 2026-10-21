"use client";

import { useEffect, useState } from "react";
import { Icon } from "./icons";
import { useDismissed } from "@/lib/use-dismissed";

/** One stop on a screen's tour: what to point at and what to say about it. */
type Step = { target: string; title: string; body: string };

/** First-visit tour for each screen: one control at a time, "Got it" at the end. */
const GUIDES = {
  home: [
    { target: ".top-nav", title: "Everything is up here", body: "Learn to chat with your tutor, Library for files and notes, Audio to listen, Practice for quizzes, Plan for roadmaps, Progress to see how you're doing." },
    { target: ".home-ask-box", title: "Ask from anywhere", body: "Type a question here and ARIA opens a new chat with it." },
    { target: ".home-stats", title: "Your progress at a glance", body: "Your streak, how many topics are strong, your chats and the quizzes you've taken." },
  ],
  learn: [
    { target: ".learn-side .btn", title: "New chat", body: "Start a fresh chat any time. Every chat is saved under Recents with a short topic name." },
    { target: ".chat-input-row .bar", title: "Ask anything", body: "Type a question and press Enter. While ARIA replies, Send turns into Stop so you can cut it short." },
    { target: ".attach-wrap > button", title: "Add files with +", body: "Add PDFs or photos, or take a picture. They wait in the bar until you press Send, then ARIA reads them in this chat." },
    { target: 'button[aria-label="Speak question"]', title: "Talk instead of typing", body: "Tap the mic, speak, tap again. ARIA turns your voice into text." },
    { target: ".depth-meter", title: "Depth", body: "Quick gives a line or two, Balanced a clear explanation, Deep a full lesson with examples. Auto picks for you." },
    { target: ".focus-toggle", title: "Focus mode", body: "Hide everything except the conversation. Tap again to bring it all back." },
  ],
  practice: [
    { target: '[data-tour="create-quiz"]', title: "Create a quiz", body: "Choose what to be quizzed on: a chat, your library files, a topic, or your weak spots." },
    { target: ".assessment-list", title: "Your quizzes", body: "Open one to take it full screen. Afterwards you see your score and what to review." },
    { target: '.top-nav a[href="/app/progress"]', title: "It counts", body: "Every answer updates Progress, so topics turn Strong only when you've shown it." },
  ],
  plan: [
    { target: '[data-tour="create-roadmap"]', title: "Create a roadmap", body: "Turn a goal into milestones, each with sub-topics you tick off as you learn them." },
    { target: ".roadmap-list", title: "Your learning goals", body: "Each goal has its own roadmap. Open one to see its milestones and study them with ARIA." },
    { target: '.section-tabs a[href="/app/planner"]', title: "Exams & deadlines", body: "Keep exam dates and reminders here; Home shows what's due this week." },
  ],
  library: [
    { target: '[data-tour="add-material"]', title: "Add material", body: "Upload a PDF, photo or text here and every chat in this subject can use it." },
    { target: '[data-tour="generate-notes"]', title: "Generate notes", body: "Turn a chat into clean study notes you can read here or download as a PDF." },
  ],
  audio: [
    { target: '[data-tour="convert-audio"]', title: "Convert to audio", body: "Turn a chat, a file or pasted text into a spoken lesson: one tutor, or a tutor and a learner talking." },
    { target: ".audio-card", title: "Your episodes", body: "Episodes are made in the background, so you can leave the page. Cancel stops one; long ones come in parts you can jump between." },
  ],
  progress: [
    { target: ".pg-overview", title: "How you're doing", body: "Topics turn Strong only when your quiz answers show it, not just because you chatted." },
    { target: ".pg-week", title: "This week", body: "Each day you study lights up. Keep the streak going." },
    { target: '.section-tabs a[href="/app/map"]', title: "Topic map", body: "See how your topics connect and which ones need review." },
  ],
} satisfies Record<string, Step[]>;

type Box = { top: number; left: number; width: number; height: number };

function boxOf(selector: string): Box | null {
  const element = document.querySelector(selector);
  if (!element) return null;
  const rect = element.getBoundingClientRect();
  if (!rect.width && !rect.height) return null;
  return { top: rect.top, left: rect.left, width: rect.width, height: rect.height };
}

export function PageGuide({ page, hidden = false }: { page: keyof typeof GUIDES; hidden?: boolean }) {
  // A new key: "Got it" on the old one-box guides must not hide these step-by-step tours.
  const { dismissed, dismiss } = useDismissed(`aria.tour:${page}`);
  const [index, setIndex] = useState(0);
  const [box, setBox] = useState<Box | null>(null);
  // Automated browsers (tests, screenshots) are not first-time learners.
  const [automated] = useState(() => typeof navigator !== "undefined" && navigator.webdriver);
  const steps: Step[] = GUIDES[page];
  const open = !dismissed && !hidden && !automated;
  const step = steps[index];

  // Follow the target while it moves (layout, scrolling, resizing).
  useEffect(() => {
    if (!open || !step) return;
    let frame = 0;
    let last = "";
    const track = () => {
      const next = boxOf(step.target);
      const key = JSON.stringify(next);
      if (key !== last) { last = key; setBox(next); }
      frame = requestAnimationFrame(track);
    };
    document.querySelector(step.target)?.scrollIntoView({ block: "nearest" });
    track();
    return () => cancelAnimationFrame(frame);
  }, [open, step]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") dismiss(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, dismiss]);

  if (!open || !step) return null;
  const last = index === steps.length - 1;
  const pad = 8;
  // The card sits below the target, or above it when there is no room, kept on screen.
  const cardWidth = Math.min(340, window.innerWidth - 32);
  const below = !box || box.top + box.height + 200 < window.innerHeight;
  const cardStyle = box
    ? {
        left: Math.max(16, Math.min(box.left, window.innerWidth - cardWidth - 16)),
        ...(below ? { top: box.top + box.height + pad + 10 } : { bottom: window.innerHeight - box.top + pad + 10 }),
        width: cardWidth,
      }
    : { left: "50%", top: "50%", transform: "translate(-50%, -50%)", width: cardWidth };

  return (
    <div className="tour" aria-live="polite">
      {box
        ? <div className="tour-spot" style={{ top: box.top - pad, left: box.left - pad, width: box.width + pad * 2, height: box.height + pad * 2 }} />
        : <div className="tour-dim" />}
      <section className="tour-card" role="dialog" aria-modal="false" aria-label={`${step.title}, step ${index + 1} of ${steps.length}`} style={cardStyle}>
        <p className="tour-count">{index + 1} of {steps.length}</p>
        <h2>{step.title}</h2>
        <p>{step.body}</p>
        <div className="tour-actions">
          <button type="button" className="btn btn-ghost" onClick={dismiss}>Skip</button>
          <span>
            {index > 0 && <button type="button" className="btn btn-secondary" onClick={() => setIndex(index - 1)}><Icon name="back" size={14} /> Back</button>}
            <button type="button" className="btn btn-primary" onClick={() => (last ? dismiss() : setIndex(index + 1))}>
              {last ? "Got it" : <>Next <Icon name="arrow" size={14} /></>}
            </button>
          </span>
        </div>
      </section>
    </div>
  );
}
