"use client";

import { useRef, useState } from "react";
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

/** A Deep answer as a deck of study cards, one idea per card; quiz cards flip to reveal the answer. */
export function StudyCards({ lead, sections }: { lead: string; sections: CardSection[] }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [asText, setAsText] = useState(false);
  const swipeFrom = useRef<number | null>(null);
  const go = (next: number) => { setIndex(Math.max(0, Math.min(sections.length - 1, next))); setFlipped(false); };
  const card = sections[index];
  const kind = cardKind(card.title);
  const quiz = kind.key === "quiz" ? splitAnswer(card.body) : null;

  return (
    <div className="study-deck">
      <div className="study-deck-bar">
        <span className="study-deck-count">{asText ? `${sections.length} sections` : `Card ${index + 1} of ${sections.length}`}</span>
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
      )) : <>
        <section className={`study-card kind-${kind.key}${flipped ? " flipped" : ""}`} aria-roledescription="card"
          aria-label={`Card ${index + 1} of ${sections.length}: ${card.title}`}
          onKeyDown={(event) => {
            if (event.key === "ArrowRight") go(index + 1);
            if (event.key === "ArrowLeft") go(index - 1);
          }} tabIndex={0}
          // A sideways swipe on a phone moves between cards.
          onPointerDown={(event) => { if (event.pointerType !== "mouse") swipeFrom.current = event.clientX; }}
          onPointerUp={(event) => {
            const from = swipeFrom.current;
            swipeFrom.current = null;
            if (from !== null && Math.abs(event.clientX - from) > 50) go(index + (event.clientX < from ? 1 : -1));
          }}>
          <span className="study-card-kind"><Icon name={kind.icon} size={14} /> {kind.label}</span>
          {card.title.toLowerCase() !== kind.label.toLowerCase() && <h3>{card.title}</h3>}
          {quiz ? (
            <div className="study-flip">
              <div className="study-flip-face front" aria-hidden={flipped}><TutorMarkdown content={quiz.question} /></div>
              <div className="study-flip-face back" aria-hidden={!flipped}><TutorMarkdown content={quiz.answer} /></div>
              <button type="button" className="btn btn-secondary study-flip-btn" aria-pressed={flipped} onClick={() => setFlipped((value) => !value)}>
                <Icon name="refresh" size={14} /> {flipped ? "Show the question" : "Flip to see the answer"}
              </button>
            </div>
          ) : <div className="study-card-body"><TutorMarkdown content={card.body} /></div>}
        </section>
        <nav className="study-deck-nav" aria-label="Cards">
          <button type="button" className="btn btn-ghost" onClick={() => go(index - 1)} disabled={index === 0} aria-label="Previous card"><Icon name="back" size={15} /></button>
          <span className="study-dots">
            {sections.map((section, i) => (
              <button key={i} type="button" className={`study-dot kind-${cardKind(section.title).key}${i === index ? " on" : ""}`}
                aria-label={`Card ${i + 1}: ${section.title}`} aria-current={i === index ? "step" : undefined} onClick={() => go(i)} />
            ))}
          </span>
          <button type="button" className="btn btn-primary" onClick={() => go(index + 1)} disabled={index === sections.length - 1} aria-label="Next card"><Icon name="arrow" size={15} /></button>
        </nav>
      </>}
    </div>
  );
}
