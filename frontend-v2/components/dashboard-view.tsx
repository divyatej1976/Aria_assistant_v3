"use client";

import Link from "next/link";
import { Icon, type IconName } from "./icons";
import { ProgressRing, Reveal } from "./motion-system";
import type { NextAction } from "@/lib/next-action";

const TOOLS: { title: string; icon: IconName; description: string; href: string }[] = [
  { title: "Learn", icon: "message", description: "Follow your curiosity with ARIA.", href: "/app/learn" },
  { title: "Assess", icon: "clipboard", description: "Discover what needs another look.", href: "/app/assess" },
  { title: "Listen", icon: "headphones", description: "Take your learning wherever you go.", href: "/app/audio" },
  { title: "Roadmaps", icon: "route", description: "Turn your goal into a clear path.", href: "/app/roadmaps" },
];

type Props = {
  title: string;
  pct: number | null;
  nextAction: NextAction;
  streak: { current_streak: number; today_active: boolean } | null;
  upcoming: { id: string; title: string; due_at: string }[];
  dueNotes: { id: string; title: string }[];
  insight: string;
  progressError: boolean;
  onRetry: () => void;
  onReview: (id: string, outcome: "again" | "good") => Promise<void>;
  firstSteps?: { learned: boolean | null; reviewCreated: boolean | null; reviewTaken: boolean | null; noteSaved: boolean | null; materialAdded: boolean | null };
};

function dueLabel(dueAt: string) {
  const days = Math.ceil((new Date(dueAt).getTime() - Date.now()) / 86_400_000);
  return days < 0 ? "Overdue" : days === 0 ? "Today" : days === 1 ? "Tomorrow" : new Date(dueAt).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function DashboardView({ title, pct, nextAction, streak, upcoming, dueNotes, insight, onReview, progressError, onRetry, firstSteps }: Props) {
  const guide = pct === 0 && firstSteps && !(firstSteps.learned && firstSteps.reviewTaken);
  return (
    <div className="learning-dashboard">
      <Reveal>
        <div className="dashboard-heading">
          <div><p className="eyebrow">YOUR LEARNING UNIVERSE</p><h1>Make room for a little discovery.</h1><p className="dashboard-intro">One idea at a time. A clearer picture with every session.</p></div>
          {streak && <span className="learning-streak"><Icon name="flame" size={17} /> {streak.current_streak}-day streak{streak.today_active && <span className="today-dot" title="Active today" />}</span>}
        </div>
      </Reveal>

      <div className="dashboard-overview">
        <Reveal delay={45}>
          <section className="learning-hero" aria-labelledby="continue-heading">
            <div className="hero-content">
              <p className="eyebrow"><Icon name="sparkles" size={14} /> YOUR NEXT CHAPTER</p>
              <h2 id="continue-heading">Continue Learning</h2>
              <p className="hero-topic">{title}</p>
              <p className="hero-description">Pick up a thread, connect an idea, and take your understanding a little further.</p>
              <div className="hero-actions"><Link href="/app/learn" className="btn btn-primary">Continue learning <Icon name="arrow" /></Link><Link href="/app/map" className="btn btn-ghost">Explore your map <Icon name="target" size={16} /></Link></div>
            </div>
          </section>
        </Reveal>
        <Reveal delay={90}>
          <section className="learning-progress" aria-labelledby="progress-heading">
            <p className="eyebrow" id="progress-heading">{guide ? "YOUR FIRST CHAPTER" : "THE BIGGER PICTURE"}</p>
            {guide && !progressError ? <div className="first-chapter">
              <h3>A small start. A clear path.</h3><p>You can learn with ARIA right away. Your own notes are optional.</p>
              <ol>
                {[
                  { label: "Have a tutor conversation", done: firstSteps.learned, href: "/app/learn", hint: "Ask about something you want to understand." },
                  { label: "Take your first review", done: firstSteps.reviewTaken, href: firstSteps.reviewCreated ? "/app/assess" : "/app/learn", hint: firstSteps.reviewCreated ? "Your review is ready in Assessments." : "Choose Done for today after learning." },
                  { label: "Save learning notes", done: firstSteps.noteSaved, href: "/app/materials", hint: "Optional · save a conversation for later." },
                  { label: "Add your own material", done: firstSteps.materialAdded, href: "/app/materials", hint: "Optional · bring a PDF, image, or text." },
                ].map((step, index) => <li key={step.label} className={step.done ? "done" : ""}>
                  <span className="step-check" aria-label={step.done ? "Completed" : step.done === null ? "Status unavailable" : "Not completed"}>{step.done ? <Icon name="check" size={14} /> : index + 1}</span>
                  <Link href={step.href}><b>{step.label}</b><small>{step.hint}{step.done === null ? " · Status unavailable" : ""}</small></Link>
                </li>)}
              </ol>
            </div> : <>
            {progressError ? <div className="progress-unavailable"><p>Progress is unavailable.</p><button className="btn btn-ghost" onClick={onRetry}>Retry progress</button></div> : pct === null || (pct === 0 && !firstSteps) ? <div className="ring-placeholder skeleton" role="status"><span className="sr-only">Loading concept progress</span></div> : <ProgressRing value={pct} label="of concepts supported" />}
            <h3>Knowledge takes shape.</h3><p>Supported concepts in this learning context.</p>
            <Link href="/app/progress" className="text-link">See your progress <Icon name="arrow" size={15} /></Link>
            </>}
          </section>
        </Reveal>
      </div>

      <Reveal delay={135}>
        <section className="next-action-card" aria-labelledby="next-heading">
          <span className="tool-icon"><Icon name={nextAction.icon} size={23} /></span>
          <div><p className="eyebrow">Next best action</p><h2 id="next-heading">{nextAction.title}</h2><p>{nextAction.why}</p></div>
          <Link href={nextAction.href} className="btn btn-primary">{nextAction.cta} <Icon name="arrow" /></Link>
        </section>
      </Reveal>

      <div className="dashboard-section-title"><h2>A way into every idea.</h2><span>Your learning tools</span></div>
      <div className="learning-tools">
        {TOOLS.map((tool, index) => <Reveal key={tool.href} delay={150 + index * 30}><Link href={tool.href} className="learning-tool"><span className="tool-icon"><Icon name={tool.icon} size={22} /></span><h3>{tool.title}</h3><p>{tool.description}</p><span className="tool-open">Explore <Icon name="arrow" size={16} /></span></Link></Reveal>)}
      </div>

      <div className="dashboard-bottom">
        <Reveal delay={210}>
          <section className="studio-panel">
            <div className="section-head"><h2>On the horizon</h2><Icon name="calendar" size={19} /></div>
            {upcoming.length === 0 ? <p className="dashboard-empty">A little space to plan your next step. Add a reminder when you’re ready.</p> : <ul className="upcoming-list">{upcoming.map(item => <li key={item.id}><span>{item.title}</span><span className="due-label">{dueLabel(item.due_at)}</span></li>)}</ul>}
            <Link href="/app/planner" className="text-link">View Planner <Icon name="arrow" size={15} /></Link>
          </section>
        </Reveal>
        <Reveal delay={240}>
          <section className="studio-panel map-invitation">
            <p className="eyebrow">EVERY IDEA IS CONNECTED</p><h2>Watch your universe grow.</h2><p>Explore your concepts, their prerequisites, and the evidence behind your understanding.</p><Link href="/app/map" className="text-link">Open Knowledge Map <Icon name="arrow" size={15} /></Link>
          </section>
        </Reveal>
      </div>

      {dueNotes.length > 0 && <section className="studio-panel review-panel"><div className="section-head"><h2>Due for review ({dueNotes.length})</h2><Link href="/app/materials" className="text-link">Open materials</Link></div>{dueNotes.map(note => <div className="review-row" key={note.id}><span><Icon name="file" size={16} /> {note.title}</span><div><button className="btn btn-ghost" aria-label={`Review again ${note.title}`} onClick={() => void onReview(note.id, "again")}>Again</button><button className="btn btn-primary" aria-label={`Review good ${note.title}`} onClick={() => void onReview(note.id, "good")}>Good</button></div></div>)}</section>}
      {insight && <div className="banner"><Icon name="lightbulb" size={20} /><div><b>ARIA Recommendation</b><p>{insight}</p></div></div>}
    </div>
  );
}
