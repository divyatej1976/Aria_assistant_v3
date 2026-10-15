import type { IconName } from "@/components/icons";

export type ConceptStateLite = {
  concept_id: string;
  concept_name: string;
  state: string;
  confidence: number;
  reason: string;
};

export type RoadmapInput = {
  goal: string;
  level: string;
  targetDate?: string;
  states: ConceptStateLite[];
  prerequisites: Record<string, string[]>;
};

export type RoadmapTopic = {
  key: string;
  title: string;
  description?: string;
  keySkills?: string[];
  ticked: boolean;
  state: string;
  confidence: number;
  reason: string;
  prereqNames: string[];
  outcome?: string | null;
  effortHours?: number | null;
  activity?: string | null;
  check?: string | null;
};

export type RoadmapTier = {
  name: string;
  icon: IconName;
  topics: RoadmapTopic[];
};

export type Roadmap = {
  id?: string;
  goal: string;
  level: string;
  targetDate?: string;
  hoursPerWeek?: number | null;
  status?: string;
  generationMode?: "ai" | "starter" | null;
  fallbackReason?: string | null;
  tiers: RoadmapTier[];
  total: number;
  done: number;
};

export type RoadmapSummary = {
  id: string;
  goal: string;
  level: string;
  target_date?: string;
  status: string;
  generation_mode?: "ai" | "starter" | null;
  fallback_reason?: string | null;
  created_at: string;
  total: number;
  done: number;
};

const TIER_NAMES = ["Foundations", "Core Concepts", "Advanced Topics", "Mastery Track"];
const TIER_ICONS: IconName[] = ["book", "target", "zap", "trophy"];

/**
 * Layer each concept by its prerequisite depth (fallback safe crawl).
 */
function computeLayers(
  ids: string[],
  prereqs: Record<string, string[]>,
): Record<string, number> {
  const inSet = new Set(ids);
  const memo: Record<string, number> = {};
  const visiting = new Set<string>();

  const layerOf = (id: string): number => {
    if (memo[id] !== undefined) return memo[id];
    if (visiting.has(id)) return 0;
    visiting.add(id);
    let depth = 0;
    for (const p of prereqs[id] ?? []) {
      if (inSet.has(p)) {
        depth = Math.max(depth, 1 + layerOf(p));
      }
    }
    visiting.delete(id);
    memo[id] = depth;
    return depth;
  };

  for (const id of ids) layerOf(id);
  return memo;
}

export function buildRoadmap(input: RoadmapInput): Roadmap | null {
  if (input.states.length === 0) return null;

  const byId = new Map(input.states.map((s) => [s.concept_id, s]));
  const layers = computeLayers(input.states.map((s) => s.concept_id), input.prerequisites);

  const tiers: RoadmapTier[] = TIER_NAMES.map((name, i) => ({ name, icon: TIER_ICONS[i], topics: [] }));

  let done = 0;
  for (const state of input.states) {
    const layer = Math.min(layers[state.concept_id] ?? 0, TIER_NAMES.length - 1);
    const prereqNames = (input.prerequisites[state.concept_id] ?? [])
      .map((pid) => byId.get(pid)?.concept_name)
      .filter((name): name is string => Boolean(name));
    const ticked = state.state === "SUPPORTED";
    if (ticked) done += 1;
    tiers[layer].topics.push({
      key: state.concept_id,
      title: state.concept_name,
      ticked,
      state: state.state,
      confidence: state.confidence,
      reason: state.reason,
      prereqNames,
    });
  }
  for (const tier of tiers) {
    tier.topics.sort((a, b) => a.title.localeCompare(b.title));
  }

  return {
    goal: input.goal,
    level: input.level,
    ...(input.targetDate ? { targetDate: input.targetDate } : {}),
    tiers: tiers.filter((t) => t.topics.length > 0),
    total: input.states.length,
    done,
  };
}

/** Human-readable explanation for a topic's tick state. */
export function tickExplanation(topic: RoadmapTopic): string {
  if (topic.ticked) {
    return topic.reason || `Auto-ticked — "${topic.title}" has reached Supported in your Knowledge map (${topic.confidence}% confidence).`;
  }
  if (topic.state === "NEEDS_REVIEW") {
    return topic.reason || `Not ticked yet — recent evidence suggests "${topic.title}" needs review. Study the concept, then retake a focused assessment.`;
  }
  if (topic.state === "DEVELOPING") {
    return topic.reason || `Not ticked yet — "${topic.title}" is still developing (${topic.confidence}% confidence). It ticks once it reaches Supported (2 consecutive correct answers).`;
  }
  return topic.reason || `Not ticked yet — there is no evidence for "${topic.title}" yet. It ticks as soon as it reaches Supported in your Knowledge map.`;
}
/** How many milestones fit in a week, from the learner's weekly study time. */
export function milestonesPerWeek(hours: number | null | undefined): number {
  if (!hours) return 2;
  return hours <= 2 ? 1 : hours <= 5 ? 2 : hours <= 10 ? 3 : 4;
}
