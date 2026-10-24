import Link from "next/link";
import { useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { api } from "@/lib/api";

/** A topic's mastery, as /contexts/{id}/adaptation returns it. */
export type TopicState = { concept_id: string; concept_name: string; state: string; confidence: number; reason: string };

// Weakest first: what to work on comes before what is already strong.
const GROUPS = [
  { state: "NEEDS_REVIEW", label: "Needs work", tone: "review" },
  { state: "DEVELOPING", label: "Getting there", tone: "developing" },
  { state: "SUPPORTED", label: "Strong", tone: "strong" },
] as const;

const askHref = (text: string) => `/app/learn?${new URLSearchParams({ ask: text })}`;

/** Topics grouped by strength, each with a way to study or practise it. `results` adds this quiz's score per topic. */
export function TopicList({ topics, results, empty }: {
  topics: TopicState[];
  results?: Record<string, { correct: number; total: number }>;
  empty?: string;
}) {
  const tested = topics.filter((t) => GROUPS.some((g) => g.state === t.state));
  if (!tested.length) return empty ? <p className="pg-hint">{empty}</p> : null;
  return (
    <div className="topic-groups">
      {GROUPS.map((group) => {
        const items = tested.filter((t) => t.state === group.state);
        if (!items.length) return null;
        return (
          <section key={group.state} className={`topic-group ${group.tone}`} aria-label={group.label}>
            <h4><i className={`pg-dot ${group.tone}`} /> {group.label} <span>{items.length}</span></h4>
            <ul>
              {items.map((topic) => {
                const result = results?.[topic.concept_id];
                return (
                  <li key={topic.concept_id}>
                    <div className="topic-main">
                      <b>{topic.concept_name}</b>
                      <small>{result ? `${result.correct} of ${result.total} right in this quiz · ` : ""}{topic.reason}</small>
                    </div>
                    <div className="topic-actions">
                      <Link className="btn btn-ghost" href={askHref(`Help me understand ${topic.concept_name}. Start with a clear explanation and an example.`)}>
                        <Icon name="message" size={14} /> Study
                      </Link>
                      {group.state !== "SUPPORTED" && (
                        <Link className="btn btn-secondary" href={askHref(`Quiz me with 3 questions on ${topic.concept_name}, one at a time.`)}>
                          <Icon name="target" size={14} /> Practise
                        </Link>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

/** Plan's "Focus next": the subject's topics that need work or are still developing, weakest first. */
export function FocusNext({ contextId }: { contextId: string }) {
  const [topics, setTopics] = useState<TopicState[]>([]);
  useEffect(() => {
    let cancelled = false;
    api<{ states: TopicState[] }>(`/api/v1/contexts/${contextId}/adaptation`)
      .then((data) => { if (!cancelled) setTopics(data.states.filter((t) => t.state === "NEEDS_REVIEW" || t.state === "DEVELOPING")); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [contextId]);
  if (!topics.length) return null;
  return (
    <section className="card card-pad focus-next" aria-labelledby="focus-next-title">
      <h2 id="focus-next-title" style={{ fontSize: 17, fontWeight: 800, margin: "0 0 4px" }}>Focus next</h2>
      <p className="field-help" style={{ margin: "0 0 12px" }}>From your quiz answers: work on these before moving on.</p>
      <TopicList topics={topics} />
    </section>
  );
}
