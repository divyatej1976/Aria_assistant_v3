"use client";

import { useEffect, useRef, useState } from "react";
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
/** The first words of a card's body as plain text, for its front. */
function preview(body: string) {
  const text = body.replace(/```[\s\S]*?```/g, " ").replace(/\$\$[\s\S]*?\$\$/g, " ").replace(/[#*_`>|$]|\[([^\]]*)\]\([^)]*\)/g, "$1").replace(/\s+/g, " ").trim();
  return text.length > 150 ? `${text.slice(0, 150).replace(/\s\S*$/, "")}…` : text;
}

// Sections in learning order: what it is first, the recap last.
const SECTION_ORDER = ["define", "concept", "how", "example", "warn", "quiz", "summary"];

/** Center `child` inside the horizontally scrolling `box`. */
function centerIn(box: HTMLElement | null, child: HTMLElement | null | undefined) {
  if (!box || !child) return;
  box.scrollTo({ left: child.offsetLeft - (box.clientWidth - child.offsetWidth) / 2, behavior: "smooth" });
}

/** A Deep answer as a swipeable row of flip cards (like a photo carousel), in learning order,
 * with section tabs that keep the current section centered. */
export function StudyCards({ lead, sections }: { lead: string; sections: CardSection[] }) {
  const [flipped, setFlipped] = useState<Set<number>>(new Set());
  const [asText, setAsText] = useState(false);
  const [index, setIndex] = useState(0);
  // Cards in view at once: one on phones, three side by side on wider screens.
  const [perView, setPerView] = useState(1);
  const trackRef = useRef<HTMLDivElement | null>(null);
  const tabsRef = useRef<HTMLElement | null>(null);
  const springBack = useRef<number | undefined>(undefined);
  const flip = (i: number) => setFlipped((prev) => {
    const next = new Set(prev);
    if (!next.delete(i)) next.add(i);
    return next;
  });
  const ordered = SECTION_ORDER.flatMap((key) =>
    sections.map((card, i) => ({ card, i, kind: cardKind(card.title) })).filter((c) => c.kind.key === key));
  const groups = SECTION_ORDER.map((key) => ({ key, cards: ordered.filter((c) => c.kind.key === key) })).filter((g) => g.cards.length);
  const currentKey = ordered[index]?.kind.key;

  const centerTab = () => centerIn(tabsRef.current, tabsRef.current?.querySelector<HTMLElement>(".deck-tab.active"));
  // The current section's tab glides to the center as the cards move into it.
  useEffect(() => { centerTab(); }, [currentKey, asText]);
  useEffect(() => () => window.clearTimeout(springBack.current), []);

  const lastStart = Math.max(0, ordered.length - perView);
  const goTo = (n: number) => {
    const track = trackRef.current;
    const card = track?.children[Math.max(0, Math.min(lastStart, n))] as HTMLElement | undefined;
    if (track && card) track.scrollTo({ left: card.offsetLeft, behavior: "smooth" });
  };
  // The leftmost card in view is the current one.
  const onTrackScroll = () => {
    const track = trackRef.current;
    const first = track?.children[0] as HTMLElement | undefined;
    if (!track || !first) return;
    const cards = Array.from(track.children) as HTMLElement[];
    const distance = (card: HTMLElement) => Math.abs(card.offsetLeft - track.scrollLeft);
    setIndex(cards.reduce((best, card, n) => (distance(card) < distance(cards[best]) ? n : best), 0));
    setPerView(Math.max(1, Math.round((track.clientWidth + 12) / (first.offsetWidth + 12))));
  };
  // Count the cards in view on load and whenever the window is resized.
  useEffect(() => {
    onTrackScroll();
    window.addEventListener("resize", onTrackScroll);
    return () => window.removeEventListener("resize", onTrackScroll);
  });
  // Tabs pushed aside by hand spring back to the current section after a moment, like a rubber band.
  const onTabsScroll = () => {
    window.clearTimeout(springBack.current);
    springBack.current = window.setTimeout(centerTab, 1200);
  };

  const renderCard = ({ card, i, kind }: { card: CardSection; i: number; kind: Kind }) => {
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
          {!quiz && <p className="flip-preview">{preview(card.body)}</p>}
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
  };

  return (
    <div className="study-deck">
      <div className="study-deck-bar">
        <span className="study-deck-count">{asText ? `${sections.length} sections` : `${ordered.length} cards · swipe or use the arrows, tap a card to open it`}</span>
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
        {groups.length > 1 && (
          <nav ref={tabsRef} className="deck-tabs" aria-label="Card sections" onScroll={onTabsScroll}>
            {groups.map(({ key, cards }) => (
              <button key={key} type="button" className={`deck-tab kind-${key}${currentKey === key ? " active" : ""}`}
                aria-current={currentKey === key ? "true" : undefined} onClick={() => goTo(ordered.indexOf(cards[0]))}>
                <Icon name={cards[0].kind.icon} size={14} /> {cards[0].kind.label} <small>{cards.length}</small>
              </button>
            ))}
          </nav>
        )}
        <div className="deck-carousel">
          <div ref={trackRef} className="deck-track" onScroll={onTrackScroll} role="group" aria-label="Study cards" tabIndex={-1}
            onKeyDown={(event) => {
              if (event.key === "ArrowRight") { event.preventDefault(); goTo(index + 1); }
              if (event.key === "ArrowLeft") { event.preventDefault(); goTo(index - 1); }
            }}>
            {ordered.map(renderCard)}
          </div>
        </div>
        <div className="deck-pager">
          <button type="button" className="deck-arrow" aria-label="Previous card" disabled={index === 0} onClick={() => goTo(index - 1)}><Icon name="back" size={16} /></button>
          <span className="deck-position" aria-live="polite">
            {perView > 1 ? `${index + 1}–${Math.min(ordered.length, index + perView)}` : index + 1} / {ordered.length}
          </span>
          <button type="button" className="deck-arrow" aria-label="Next card" disabled={index >= lastStart} onClick={() => goTo(index + 1)}><Icon name="arrow" size={16} /></button>
        </div>
      </>}
    </div>
  );
}
