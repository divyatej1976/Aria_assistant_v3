"use client";

import { useState } from "react";
import { Icon, type IconName } from "@/components/icons";
import { TutorMarkdown } from "@/components/tutor-markdown";

export type CardSection = { title: string; body: string };

/** Split a reply at its '### ' headings (never inside code fences): the lead, then one section per heading. */
export function splitSections(content: string): { lead: string; sections: CardSection[] } {
  const lead: string[] = [];
  const sections: { title: string; body: string[] }[] = [];
  let inFence = false;
  for (const line of content.split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) inFence = !inFence;
    const heading = !inFence ? /^#{1,3}\s+(.+?)\s*#*\s*$/.exec(line) : null;
    if (heading) sections.push({ title: heading[1].replace(/\*\*/g, ""), body: [] });
    else if (sections.length) sections[sections.length - 1].body.push(line);
    else lead.push(line);
  }
  return {
    lead: lead.join("\n").trim(),
    sections: sections.map((s) => ({ title: s.title, body: s.body.join("\n").trim() })).filter((s) => s.body),
  };
}

type Kind = { key: string; label: string; icon: IconName };
const KINDS: [RegExp, Kind][] = [
  [/check yourself|quiz|test yourself|try it|question/i, { key: "quiz", label: "Check yourself", icon: "clipboard" }],
  [/takeaway|summary|recap|key points|in short|remember/i, { key: "summary", label: "Summary", icon: "check" }],
  [/mistake|pitfall|watch out|gotcha|careful|misconception/i, { key: "warn", label: "Watch out", icon: "alert" }],
  [/example|walkthrough|in practice|case|demo|let'?s see/i, { key: "example", label: "Example", icon: "code" }],
  [/defin|what is|what are|meaning|terms|vocabulary/i, { key: "define", label: "Definition", icon: "book" }],
  [/how|step|why|work|process|intuition|idea behind/i, { key: "how", label: "How it works", icon: "lightbulb" }],
];
const CONCEPT: Kind = { key: "concept", label: "Core idea", icon: "sparkles" };

export function cardKind(title: string): Kind {
  return KINDS.find(([pattern]) => pattern.test(title))?.[1] ?? CONCEPT;
}

/** A quiz card's question and answer: the body splits at a line that starts with "Answer". */
export function splitAnswer(body: string): { question: string; answer: string } | null {
  const match = /^\s*(?:\*\*)?answer(?:\*\*)?\s*[:：-]?(?:\*\*)?\s*/im.exec(body);
  if (!match || match.index === 0) return null;
  return { question: body.slice(0, match.index).trim(), answer: body.slice(match.index + match[0].length).trim() };
}

/** A Deep answer as flip cards, all visible at once: the front names the idea (or asks the
 * quiz question), a tap turns the card over to the explanation (or the answer). */
export function StudyCards({ lead, sections }: { lead: string; sections: CardSection[] }) {
  const [flipped, setFlipped] = useState<Set<number>>(new Set());
  const [asText, setAsText] = useState(false);
  const flip = (i: number) => setFlipped((prev) => {
    const next = new Set(prev);
    if (!next.delete(i)) next.add(i);
    return next;
  });

  return (
    <div className="study-deck">
      <div className="study-deck-bar">
        <span className="study-deck-count">{asText ? `${sections.length} sections` : `${sections.length} cards · tap a card to flip it`}</span>
        <div className="study-deck-toggle" role="group" aria-label="Show answer as">
          <button type="button" aria-pressed={!asText} onClick={() => setAsText(false)}>Cards</button>
          <button type="button" aria-pressed={asText} onClick={() => setAsText(true)}>Full text</button>
        </div>
      </div>
      {lead && <div className="reply-lead"><TutorMarkdown content={lead} /></div>}
      {asText ? sections.map((section, i) => (
        <section key={i} className="reply-block">
          <h4 className="reply-block-label">{section.title}</h4>
          <TutorMarkdown content={section.body} />
        </section>
      )) : (
        <div className="flip-grid">
          {sections.map((card, i) => {
            const kind = cardKind(card.title);
            const quiz = kind.key === "quiz" ? splitAnswer(card.body) : null;
            const on = flipped.has(i);
            const named = card.title.toLowerCase() !== kind.label.toLowerCase();
            return (
              <div key={i} role="button" tabIndex={0} aria-pressed={on}
                aria-label={`${kind.label}: ${card.title}. ${on ? "Showing the back" : "Tap to flip"}`}
                className={`flip-card kind-${kind.key}${on ? " flipped" : ""}`}
                // Links and copy buttons inside the back work without turning the card over.
                onClick={(event) => { if (!(event.target as HTMLElement).closest("a, button")) flip(i); }}
                onKeyDown={(event) => {
                  if ((event.key === "Enter" || event.key === " ") && event.target === event.currentTarget) { event.preventDefault(); flip(i); }
                }}>
                <div className="flip-face front" aria-hidden={on}>
                  <span className="study-card-kind"><Icon name={kind.icon} size={14} /> {kind.label}</span>
                  {named && <h3>{card.title}</h3>}
                  {quiz && <div className="flip-question"><TutorMarkdown content={quiz.question} /></div>}
                  <span className="flip-hint"><Icon name="refresh" size={13} /> {quiz ? "Tap to see the answer" : "Tap to read"}</span>
                </div>
                <div className="flip-face back" aria-hidden={!on}>
                  <span className="study-card-kind"><Icon name={kind.icon} size={14} /> {quiz ? "Answer" : kind.label}</span>
                  {named && !quiz && <h3>{card.title}</h3>}
                  <div className="flip-body"><TutorMarkdown content={quiz ? quiz.answer : card.body} /></div>
                  <span className="flip-hint"><Icon name="refresh" size={13} /> Tap to turn back</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
