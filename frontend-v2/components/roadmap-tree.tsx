"use client";

import Link from "next/link";
import { Icon } from "./icons";
import type { RoadmapTier, RoadmapTopic } from "@/lib/roadmap";

/**
 * A roadmap.sh-style map: a vertical path of main topics, each with sub-topics
 * branching out to alternate sides that the learner ticks off one by one.
 */
export function RoadmapTree({ tiers, nextKey, contextId, roadmapId, onDetails, onTick }: {
  tiers: RoadmapTier[];
  nextKey?: string;
  contextId?: string;
  roadmapId?: string;
  onDetails: (topic: RoadmapTopic) => void;
  onTick: (topic: RoadmapTopic, skill: string, done: boolean) => void;
}) {
  const all = tiers.flatMap((tier) => tier.topics);
  const totalSubtopics = all.reduce((sum, topic) => sum + (topic.keySkills?.length ?? 0), 0);
  const doneSubtopics = all.reduce((sum, topic) => sum + (topic.doneSkills?.length ?? 0), 0);
  const studyHref = (title: string, topic: RoadmapTopic) =>
    `/app/learn?${new URLSearchParams({ topic: title, context: contextId ?? "", roadmap: roadmapId ?? "", milestone: topic.key })}`;
  let position = 0;

  return (
    <div className="rm-map">
      {totalSubtopics > 0 && (
        <div className="rm-progress" role="status">
          <b>{doneSubtopics} of {totalSubtopics}</b> sub-topics done
          <span className="rm-progress-bar" aria-hidden="true"><span style={{ width: `${Math.round((doneSubtopics / totalSubtopics) * 100)}%` }} /></span>
        </div>
      )}
      <ol className="rm-path">
        {tiers.map((tier, phaseIndex) => (
          <li key={tier.name} className="rm-phase">
            <div className="rm-phase-label"><span>{phaseIndex + 1}</span>{tier.name}</div>
            <ol className="rm-topics">
              {tier.topics.map((topic) => {
                const side = position++ % 2 === 0 ? "right" : "left";
                const skills = topic.keySkills ?? [];
                const done = new Set(topic.doneSkills ?? []);
                const allDone = skills.length > 0 && skills.every((skill) => done.has(skill));
                const review = topic.state === "NEEDS_REVIEW";
                const developing = !topic.ticked && topic.state === "DEVELOPING";
                const pending = topic.prereqNames.some((name) => !all.some((other) => other.ticked
                  && other.title.toLowerCase() === name.toLowerCase()));
                const label = topic.ticked ? "Completed" : review ? "Review needed" : developing ? "Developing"
                  : topic.key === nextKey ? "Up next" : allDone ? "All sub-topics done" : pending ? "Prerequisites first" : "Upcoming";
                const status = topic.ticked ? " completed" : review ? " needs-review" : developing ? " in-progress"
                  : topic.key === nextKey ? " up-next" : pending ? " prerequisite-pending" : "";
                return (
                  <li key={topic.key} className={`rm-row rm-${side}`}>
                    <article className={`roadmap-topic-card rm-node${status}`}>
                      <Link className="roadmap-topic-study rm-node-main" href={studyHref(topic.title, topic)} aria-label={`Study ${topic.title}`} title={topic.title}>
                        <span className="rm-node-icon"><Icon name={topic.ticked || allDone ? "check" : review ? "refresh" : tier.icon} size={16} /></span>
                        <span className="rm-node-text">
                          <b className="roadmap-topic-title">{topic.title}</b>
                          <small className="roadmap-topic-label">{label}{skills.length ? ` · ${done.size}/${skills.length}` : ""}</small>
                        </span>
                      </Link>
                      <button className="roadmap-topic-details" onClick={() => onDetails(topic)} aria-label={`View ${topic.title} details`} title="View milestone details"><Icon name="info" size={15} /></button>
                    </article>
                    {skills.length > 0 && (
                      <ul className="rm-subtopics" aria-label={`${topic.title} sub-topics`}>
                        {skills.map((skill) => (
                          <li key={skill} className={done.has(skill) ? "done" : ""}>
                            <input type="checkbox" id={`st-${topic.key}-${skill}`} checked={done.has(skill)}
                              onChange={(event) => onTick(topic, skill, event.target.checked)} aria-label={`Mark ${skill} done`} />
                            <Link href={studyHref(`${skill} (${topic.title})`, topic)} title={`Study ${skill}`}>{skill}</Link>
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                );
              })}
            </ol>
          </li>
        ))}
      </ol>
    </div>
  );
}
