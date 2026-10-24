"use client";

import { AnswerRating } from "@/components/answer-rating";
import Link from "next/link";
import { Icon } from "@/components/icons";
import { TutorMarkdown } from "@/components/tutor-markdown";
import { StudyCards, splitSections } from "@/components/study-cards";

export type Depth = "quick" | "balanced" | "deep";
export type RequestedDepth = "auto" | Depth;
export type Source = { resource_id: string; chunk_id: string; title: string; score: number };

export const DEPTH_LABEL: Record<Depth, string> = { quick: "Quick", balanced: "Balanced", deep: "Deep" };
const DEPTH_LEVEL: Record<Depth, number> = { quick: 1, balanced: 2, deep: 3 };

// A block label is a line that is only bold text, e.g. "**Example**" or "**Watch out:**".
const LABEL_LINE = /^\s*\*\*([^*\n]{1,48}?):?\*\*:?\s*$/;

/** Split a reply into its lead answer and labelled blocks, so each idea reads
 * as its own small card instead of one long wall of text. Code fences are
 * respected: a bold line inside a fence never starts a block. */
export function splitBlocks(content: string): { lead: string; blocks: { label: string; body: string }[] } {
  const lines = content.split("\n");
  let lead: string[] = [];
  const blocks: { label: string; body: string[] }[] = [];
  let inFence = false;
  for (const line of lines) {
    if (/^\s*(```|~~~)/.test(line)) inFence = !inFence;
    const label = !inFence ? LABEL_LINE.exec(line) : null;
    if (label) {
      blocks.push({ label: label[1].trim(), body: [] });
    } else if (blocks.length) {
      blocks[blocks.length - 1].body.push(line);
    } else {
      lead.push(line);
    }
  }
  lead = trimBlank(lead);
  return {
    lead: lead.join("\n"),
    blocks: blocks.map((b) => ({ label: b.label, body: trimBlank(b.body).join("\n") })).filter((b) => b.body),
  };
}

function trimBlank(lines: string[]): string[] {
  let start = 0;
  let end = lines.length;
  while (start < end && !lines[start].trim()) start++;
  while (end > start && !lines[end - 1].trim()) end--;
  return lines.slice(start, end);
}

export function DepthBadge({ depth }: { depth: Depth }) {
  const level = DEPTH_LEVEL[depth];
  return (
    <span className="depth-badge" title={`${DEPTH_LABEL[depth]} answer`}>
      {DEPTH_LABEL[depth]}
      <span className="depth-bars" aria-hidden="true">
        {[1, 2, 3].map((n) => <i key={n} className={n <= level ? "on" : ""} />)}
      </span>
    </span>
  );
}

export function TutorReply({
  content, depth, sources, fallback, done = true, fresh, onDeeper, onShorter, quickCheckHref, answerId,
}: {
  content: string;
  depth?: Depth | null;
  sources?: Source[];
  fallback?: boolean;
  done?: boolean;
  fresh?: boolean;
  onDeeper?: () => void;
  onShorter?: () => void;
  quickCheckHref?: string;
  // The saved answer's id: shows the thumbs (unsaved or stopped replies have none).
  answerId?: string;
}) {
  const { lead, blocks } = splitBlocks(content);
  // A finished answer with several sections reads as a deck of study cards (never a Quick one).
  const deck = done && depth !== "quick" ? splitSections(content) : null;
  const asCards = deck !== null && deck.sections.length >= 3;
  const titles = [...new Set((sources ?? []).map((s) => s.title))];
  return (
    <article className={`msg msg-aria${fresh ? " message-arrival" : ""}`}>
      <header className="mh">
        <span className="mh-name"><Icon name="sparkles" size={13} /> ARIA</span>
        {depth && <DepthBadge depth={depth} />}
      </header>
      {/* Every reply says where it came from: the learner's material or ARIA's own knowledge. */}
      <p className="reply-sources">
        {titles.length > 0
          ? <><Icon name="file" size={12} /> From your material {titles.map((title) => <span key={title} className="source-chip">{title}</span>)}</>
          : <span className="reply-note"><Icon name="sparkles" size={12} /> From ARIA&apos;s general knowledge{fallback ? " · add files in Library for answers from your documents" : ""}</span>}
      </p>
      {asCards && <StudyCards lead={deck.lead} sections={deck.sections} />}
      {!asCards && lead && <div className="reply-lead"><TutorMarkdown content={lead} /></div>}
      {!asCards && blocks.map((block, index) => (
        <section className="reply-block" key={`${block.label}-${index}`}>
          <h4 className="reply-block-label">{block.label}</h4>
          <TutorMarkdown content={block.body} />
        </section>
      ))}
      {done && (onDeeper || onShorter || quickCheckHref) && (
        <div className="reply-actions">
          {onDeeper && depth !== "deep" && <button type="button" className="reply-action" onClick={onDeeper}><Icon name="chevron-down" size={13} /> Go deeper</button>}
          {onShorter && depth !== "quick" && <button type="button" className="reply-action" onClick={onShorter}><Icon name="chevron-up" size={13} /> Shorter</button>}
          {quickCheckHref && <Link className="reply-action" href={quickCheckHref}><Icon name="clipboard" size={13} /> Quick check</Link>}
        </div>
      )}
      {done && answerId && <AnswerRating answerId={answerId} />}
    </article>
  );
}
