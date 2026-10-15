"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Icon, type IconName } from "./icons";
import { ProgressRing, Reveal } from "./motion-system";
import type { NextAction } from "@/lib/next-action";

const TOOLS: { title: string; icon: IconName; description: string; href: string }[] = [
  { title: "Learn", icon: "message", description: "Chat with ARIA about anything you want to understand.", href: "/app/learn" },
  { title: "Practice", icon: "clipboard", description: "Quiz yourself your way, one question at a time.", href: "/app/assess" },
  { title: "Plan", icon: "route", description: "Turn your goal into a roadmap and a plan for this week.", href: "/app/roadmaps" },
  { title: "Library", icon: "folder", description: "Keep files and notes every chat can use.", href: "/app/materials" },
  { title: "Audio", icon: "headphones", description: "Turn chats and notes into episodes to listen on the go.", href: "/app/audio" },
  { title: "Progress", icon: "trend", description: "See what you know well and what needs review.", href: "/app/progress" },
];

export type WeekItem = { key: string; title: string; kind: "milestone" | "deadline"; due?: string };

type Props = {
  title: string;
  pct: number | null;
  nextAction: NextAction;
  streak: { current_streak: number; today_active: boolean } | null;
  dueNotes: { id: string; title: string }[];
  progressError: boolean;
  onRetry: () => void;
  onReview: (id: string, outcome: "again" | "good") => Promise<void>;
  firstSteps?: { learned: boolean | null; reviewCreated: boolean | null; reviewTaken: boolean | null; noteSaved: boolean | null; materialAdded: boolean | null };
  lastChat: { id: string; title: string } | null;
  week: WeekItem[];
};

function dueLabel(dueAt: string) {
  const days = Math.ceil((new Date(dueAt).getTime() - Date.now()) / 86_400_000);
  return days < 0 ? "Overdue" : days === 0 ? "Today" : days === 1 ? "Tomorrow" : new Date(dueAt).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function askHref(question: string): string {
  return `/app/learn?${new URLSearchParams({ ask: question, autosend: "1" })}`;
}

/** Home has two shapes: a first visit asks one question and shows three small
 * steps; a returning learner gets their last chat, one suggestion, and this
 * week. No streak, ring or locked badges before there is anything to show. */
export function DashboardView({ title, pct, nextAction, streak, dueNotes, onReview, progressError, onRetry, firstSteps, lastChat, week }: Props) {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const firstVisit = !firstSteps || !(firstSteps.learned && firstSteps.reviewTaken);
  const starters = [
    `Explain the basics of ${title}`,
    `Give me a real-world example from ${title}`,
    `What should I learn first in ${title}?`,
  ];

  return (
    <div className="learning-dashboard home" data-home-ready={firstSteps ? "true" : undefined}>
      {firstVisit && !lastChat ? (
        <Reveal>
          <section className="learning-hero home-ask" aria-labelledby="home-ask-title">
            <p className="hero-topic">{title}</p>
            <h1 id="home-ask-title">What do you want to learn?</h1>
            <form className="home-ask-box" onSubmit={(event) => {
              event.preventDefault();
              if (question.trim()) router.push(askHref(question.trim()));
            }}>
              <input className="input" aria-label="Your question" placeholder="Ask ARIA anything…" value={question}
                onChange={(event) => setQuestion(event.target.value)} maxLength={2000} />
              <button className="btn btn-primary" type="submit" disabled={!question.trim()}>Ask <Icon name="arrow" size={16} /></button>
            </form>
            <div className="home-starters">
              {starters.map((starter) => <Link key={starter} className="tag-chip" href={askHref(starter)}>{starter}</Link>)}
            </div>
          </section>
        </Reveal>
      ) : (
        <Reveal>
          <div className="home-welcome">
            <h1>{firstVisit ? "Keep going" : "Welcome back"}</h1>
            {streak && streak.current_streak > 0 && (
              <span className="learning-streak"><Icon name="flame" size={16} /> {streak.current_streak}-day streak{streak.today_active && <span className="today-dot" title="Active today" />}</span>
            )}
          </div>
        </Reveal>
      )}

      <div className="home-grid">
        {lastChat && (
          <Reveal delay={45}>
            <section className="learning-hero home-continue" aria-labelledby="continue-heading">
              <p className="hero-topic">{title}</p>
              <h2 id="continue-heading">Continue learning</h2>
              <p className="home-last-chat">{lastChat.title}</p>
              <Link href={`/app/learn?session=${lastChat.id}`} className="btn btn-primary">Open this chat <Icon name="arrow" /></Link>
              <Link href="/app/learn" className="text-link">Start a new chat</Link>
            </section>
          </Reveal>
        )}

        {firstVisit ? (
          <Reveal delay={90}>
            <section className="studio-panel first-chapter" aria-labelledby="first-steps-title">
              <h2 id="first-steps-title">Three small steps</h2>
              <p>You can learn with ARIA right away. Your own notes are optional.</p>
              <ol>
                {[
                  { label: "Have a tutor conversation", done: firstSteps?.learned ?? null, href: "/app/learn", hint: "Ask about something you want to understand." },
                  { label: "Take your first quiz", done: firstSteps?.reviewTaken ?? null, href: "/app/assess", hint: firstSteps?.reviewCreated ? "Your quiz is ready in Practice." : "After a chat, create a short quiz in Practice." },
                  { label: "Add your own material", done: firstSteps ? Boolean(firstSteps.materialAdded || firstSteps.noteSaved) : null, href: "/app/materials", hint: "Optional · a PDF, image, text or saved notes." },
                ].map((step, index) => <li key={step.label} className={step.done ? "done" : ""}>
                  <span className="step-check" aria-label={step.done ? "Completed" : step.done === null ? "Status unavailable" : "Not completed"}>{step.done ? <Icon name="check" size={14} /> : index + 1}</span>
                  <Link href={step.href}><b>{step.label}</b><small>{step.hint}</small></Link>
                </li>)}
              </ol>
            </section>
          </Reveal>
        ) : (
          <>
            <Reveal delay={90}>
              <section className="next-action-card" aria-labelledby="next-heading">
                <span className="tool-icon"><Icon name={nextAction.icon} size={23} /></span>
                <div><p className="eyebrow">Suggested next</p><h2 id="next-heading">{nextAction.title}</h2><p>{nextAction.why}</p></div>
                <Link href={nextAction.href} className="btn btn-primary">{nextAction.cta} <Icon name="arrow" /></Link>
              </section>
            </Reveal>
            <Reveal delay={120}>
              <section className="studio-panel home-progress" aria-labelledby="progress-heading">
                <h2 id="progress-heading">Your progress</h2>
                {progressError
                  ? <div className="progress-unavailable"><p>Progress is unavailable.</p><button className="btn btn-ghost" onClick={onRetry}>Retry progress</button></div>
                  : pct === null ? <div className="ring-placeholder skeleton" role="status"><span className="sr-only">Loading concept progress</span></div>
                  : <ProgressRing value={pct} label="of concepts supported" size={110} />}
                <Link href="/app/progress" className="text-link">See your progress <Icon name="arrow" size={15} /></Link>
              </section>
            </Reveal>
          </>
        )}
      </div>

      <section aria-labelledby="home-tools-title">
        <div className="dashboard-section-title"><h2 id="home-tools-title">Everything in ARIA</h2></div>
        <div className="learning-tools">
          {TOOLS.map((tool, index) => <Reveal key={tool.href} delay={150 + index * 30}><Link href={tool.href} className="learning-tool"><span className="tool-icon"><Icon name={tool.icon} size={22} /></span><h3>{tool.title}</h3><p>{tool.description}</p><span className="tool-open">Explore <Icon name="arrow" size={16} /></span></Link></Reveal>)}
        </div>
      </section>

      {week.length > 0 && (
        <section className="studio-panel home-week" aria-labelledby="home-week-title">
          <div className="section-head"><h2 id="home-week-title">This week</h2><Link href="/app/roadmaps" className="text-link">Open plan</Link></div>
          <ul>
            {week.map((item) => (
              <li key={item.key}>
                <Icon name={item.kind === "deadline" ? "calendar" : "route"} size={16} />
                <span>{item.title}</span>
                {item.kind === "deadline" && item.due
                  ? <span className="due-label">{dueLabel(item.due)}</span>
                  : <Link className="text-link" href={askHref(`Help me learn ${item.title}. Start with a clear explanation and an example.`)}>Study</Link>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {dueNotes.length > 0 && <section className="studio-panel review-panel"><div className="section-head"><h2>Due for review ({dueNotes.length})</h2><Link href="/app/materials" className="text-link">Open library</Link></div>{dueNotes.map(note => <div className="review-row" key={note.id}><span><Icon name="file" size={16} /> {note.title}</span><div><button className="btn btn-ghost" aria-label={`Review again ${note.title}`} onClick={() => void onReview(note.id, "again")}>Again</button><button className="btn btn-primary" aria-label={`Review good ${note.title}`} onClick={() => void onReview(note.id, "good")}>Good</button></div></div>)}</section>}
    </div>
  );
}
