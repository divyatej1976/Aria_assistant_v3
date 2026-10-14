"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { animate, createScope } from "animejs";
import { Icon, type IconName } from "./icons";
import { useMotionPreference } from "./motion-system";

export type MapConcept = { concept_id: string; concept_name: string; state: string; confidence: number; reason: string };
type Evidence = { concept_id: string; signal: string; valid: boolean };

const STATES: Record<string, { label: string; color: string; icon: IconName }> = {
  SUPPORTED: { label: "Supported", color: "var(--success-strong)", icon: "check" },
  DEVELOPING: { label: "Developing", color: "var(--accent-strong)", icon: "activity" },
  NEEDS_REVIEW: { label: "Needs review", color: "var(--danger-strong)", icon: "refresh" },
  UNTESTED: { label: "Untested", color: "var(--text-2)", icon: "target" },
};
const stateOf = (concept: MapConcept) => STATES[concept.state] ?? { label: concept.state.replaceAll("_", " "), color: "var(--text-2)", icon: "target" as IconName };

export function KnowledgeConstellation({ concepts, visible, prerequisites, evidence, unavailable = 0 }: {
  concepts: MapConcept[]; visible: MapConcept[]; prerequisites: Record<string, string[]>; evidence: Evidence[]; unavailable?: number;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [view, setView] = useState<"graph" | "list">("graph");
  const [zoom, setZoom] = useState(1);
  const [group, setGroup] = useState(0);
  const graphRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const reduced = useMotionPreference();
  const sorted = useMemo(() => [...concepts].sort((a, b) => a.concept_id.localeCompare(b.concept_id)), [concepts]);
  const visibleIds = new Set(visible.map(concept => concept.concept_id));
  const groups = Math.max(1, Math.ceil(sorted.length / 60));
  const requestedGroup = Math.min(group, groups - 1);
  const firstMatch = sorted.findIndex(concept => visibleIds.has(concept.concept_id));
  const activeGroup = sorted.slice(requestedGroup * 60, requestedGroup * 60 + 60).some(concept => visibleIds.has(concept.concept_id)) || firstMatch < 0 ? requestedGroup : Math.floor(firstMatch / 60);
  const matchingGroups = [...new Set(sorted.flatMap((concept, index) => visibleIds.has(concept.concept_id) ? [Math.floor(index / 60)] : []))];
  const previousGroup = matchingGroups.filter(index => index < activeGroup).at(-1);
  const nextGroup = matchingGroups.find(index => index > activeGroup);
  const changeGroup = (next: number) => {
    setGroup(next);
    viewportRef.current?.scrollTo({ top: 0, left: 0, behavior: "instant" });
  };
  const layout = useMemo(() => {
    const nodes = sorted.slice(activeGroup * 60, activeGroup * 60 + 60);
    const height = nodes.length <= 8 ? 480 : Math.max(480, Math.ceil(nodes.length / 4) * 135 + 100);
    const positions = new Map(nodes.map((node, index) => {
      const angle = (index / nodes.length) * Math.PI * 2 - Math.PI / 2;
      return [node.concept_id, nodes.length === 1 ? { x: 450, y: 240 } : nodes.length <= 8
        ? { x: 450 + 310 * Math.cos(angle), y: 240 + 160 * Math.sin(angle) }
        : { x: 120 + (index % 4) * 210 + (Math.floor(index / 4) % 2) * 30, y: 90 + Math.floor(index / 4) * 135 }];
    }));
    return { positions, height };
  }, [sorted, activeGroup]);
  const selected = visible.find(concept => concept.concept_id === selectedId) ?? null;
  const relatedIds = new Set(selected ? [selected.concept_id, ...(prerequisites[selected.concept_id] ?? []), ...concepts.filter(c => prerequisites[c.concept_id]?.includes(selected.concept_id)).map(c => c.concept_id)] : []);
  const edges = visible.flatMap(concept => [...new Set(prerequisites[concept.concept_id] ?? [])]
    .filter(id => id !== concept.concept_id && visibleIds.has(id) && layout.positions.has(id) && layout.positions.has(concept.concept_id))
    .map(id => ({ from: id, to: concept.concept_id })));
  const edgeKey = edges.map(edge => `${edge.from}:${edge.to}`).sort().join("|");

  useEffect(() => {
    if (!graphRef.current || reduced || view !== "graph" || !edgeKey) return;
    const scope = createScope({ root: graphRef }).add(() => {
      animate(".concept-edge", { strokeDashoffset: [1, 0], duration: 750, ease: "outCubic" });
    });
    return () => scope.revert();
  }, [edgeKey, reduced, view]);

  return (
    <section className="constellation" aria-label="Concept explorer">
      <div className="constellation-toolbar">
        <div><p className="eyebrow">YOUR IDEAS, CONNECTED</p><p className="constellation-caption">{visible.length} concepts · {edges.length} visible prerequisite connections</p></div>
        <div className="constellation-controls" role="group" aria-label="Map view">
          <button className="btn btn-ghost" aria-pressed={view === "graph"} onClick={() => setView("graph")}><Icon name="target" size={15} /> Constellation</button>
          <button className="btn btn-ghost" aria-pressed={view === "list"} onClick={() => setView("list")}><Icon name="list" size={15} /> List</button>
        </div>
      </div>
      {unavailable > 0 && <p className="map-data-notice" role="status">Prerequisite data is unavailable for {unavailable} concepts. Only confirmed connections are shown.</p>}
      {concepts.length > 60 && <p className="map-data-notice">Explore groups of up to 60 concepts. Connections within the current group are drawn; all recorded prerequisites remain available in concept details.</p>}
      <div className="constellation-body">
        <div className="constellation-explorer">
          {view === "graph" ? <>
            {groups > 1 && <div className="constellation-toolbar" role="group" aria-label="Concept groups">
              <button className="btn btn-ghost" disabled={previousGroup === undefined} onClick={() => { if (previousGroup !== undefined) changeGroup(previousGroup); }}>Previous group</button>
              <span role="status">Group {activeGroup + 1} of {groups}</span>
              <button className="btn btn-ghost" disabled={nextGroup === undefined} onClick={() => { if (nextGroup !== undefined) changeGroup(nextGroup); }}>Next group</button>
            </div>}
            <div className="map-zoom" role="group" aria-label="Zoom controls"><button className="btn btn-ghost" aria-label="Zoom out" disabled={zoom <= .75} onClick={() => setZoom(value => Math.max(.75, value - .25))}>−</button><button className="btn btn-ghost" aria-label="Reset zoom" onClick={() => setZoom(1)}>{Math.round(zoom * 100)}%</button><button className="btn btn-ghost" aria-label="Zoom in" disabled={zoom >= 1.5} onClick={() => setZoom(value => Math.min(1.5, value + .25))}>+</button></div>
            <div ref={viewportRef} className="constellation-viewport" tabIndex={0} role="region" aria-label="Scrollable concept constellation">
              <div style={{ width: 900 * zoom, height: layout.height * zoom }}>
                <div ref={graphRef} className="constellation-canvas" style={{ width: 900, height: layout.height, transform: `scale(${zoom})`, transformOrigin: "top left" }}>
                  <svg width="900" height={layout.height} aria-hidden="true" className="constellation-lines">
                    {edges.map(edge => {
                      const from = layout.positions.get(edge.from)!;
                      const to = layout.positions.get(edge.to)!;
                      const highlighted = selected && (edge.from === selected.concept_id || edge.to === selected.concept_id);
                      return <path key={`${edge.from}:${edge.to}`} className={`concept-edge${highlighted ? " highlighted" : ""}`} d={`M ${from.x} ${from.y} Q ${(from.x + to.x) / 2 + 35} ${(from.y + to.y) / 2 - 35} ${to.x} ${to.y}`} pathLength="1" strokeDasharray="1" fill="none" />;
                    })}
                  </svg>
                  {sorted.filter(concept => visibleIds.has(concept.concept_id) && layout.positions.has(concept.concept_id)).map(concept => {
                    const position = layout.positions.get(concept.concept_id)!;
                    const state = stateOf(concept);
                    return <button key={concept.concept_id} className={`concept-node${selected?.concept_id === concept.concept_id ? " selected" : ""}${selected && !relatedIds.has(concept.concept_id) ? " subdued" : ""}`} style={{ left: position.x, top: position.y, "--node-color": state.color } as CSSProperties} aria-label={`${concept.concept_name}, ${state.label}`} aria-pressed={selected?.concept_id === concept.concept_id} onClick={() => setSelectedId(concept.concept_id)}><span className="concept-node-icon"><Icon name={state.icon} size={17} /></span><strong>{concept.concept_name}</strong><span>{state.label}</span></button>;
                  })}
                </div>
              </div>
            </div>
            <p className="map-help">Select a concept to explore its evidence. Connections represent prerequisites. Scroll to explore the canvas.</p>
          </> : <ul className="concept-list">{visible.map(concept => {
            const state = stateOf(concept);
            return <li key={concept.concept_id}><button className={`concept-list-item${selected?.concept_id === concept.concept_id ? " selected" : ""}`} aria-pressed={selected?.concept_id === concept.concept_id} onClick={() => setSelectedId(concept.concept_id)}><Icon name={state.icon} size={18} /><span><strong>{concept.concept_name}</strong><span>{state.label} · {concept.confidence}% confidence</span></span><Icon name="arrow" size={15} /></button></li>;
          })}</ul>}
        </div>
        <aside className="concept-details" aria-label="Selected concept details" aria-live="polite">
          {selected ? <>
            <p className="eyebrow">A CLOSER LOOK</p><h2>{selected.concept_name}</h2><span className="concept-state-label"><Icon name={stateOf(selected).icon} size={16} /> {stateOf(selected).label}</span><p>{selected.reason}</p><p className="concept-confidence">{selected.confidence}% confidence in this state</p>
            <h3>Prerequisites</h3>{prerequisites[selected.concept_id] === undefined ? <p>Prerequisite data is unavailable.</p> : prerequisites[selected.concept_id].length === 0 ? <p>No prerequisites recorded.</p> : <ul>{prerequisites[selected.concept_id].map(id => <li key={id}>{concepts.find(c => c.concept_id === id)?.concept_name ?? "Concept outside this map"}</li>)}</ul>}
            <h3>Learning evidence</h3>{evidence.filter(item => item.concept_id === selected.concept_id).length === 0 ? <p>No evidence recorded yet.</p> : <ul>{evidence.filter(item => item.concept_id === selected.concept_id).slice(0, 5).map((item, index) => <li key={index}>{item.signal} · {item.valid ? "Valid" : "Invalid"}</li>)}</ul>}
            <Link href="/app/learn" className="btn btn-primary">Continue studying <Icon name="arrow" /></Link>
          </> : <div className="concept-detail-empty"><Icon name="sparkles" size={28} /><h2>Follow a connection.</h2><p>Choose a concept to see its learning state, prerequisites, and supporting evidence.</p></div>}
        </aside>
      </div>
    </section>
  );
}
