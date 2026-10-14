"use client";

import { useEffect, useRef, useState } from "react";
import { animate, createScope, stagger } from "animejs";
import { useHydrated } from "@/lib/use-hydrated";
import { Icon } from "./icons";
import { useMotionPreference } from "./motion-system";

export function ConstellationWordmark() {
  const root = useRef<HTMLDivElement>(null);
  const reduced = useMotionPreference();
  useEffect(() => {
    if (!root.current || reduced) return;
    const scope = createScope({ root }).add(() => {
      animate(".wordmark-connection", { strokeDashoffset: [1, 0], opacity: [0, .55], duration: 750, delay: stagger(35), ease: "outCubic" });
      animate(".wordmark-star", { scale: [.6, 1], opacity: [.2, 1], duration: 650, delay: stagger(18), ease: "outCubic" });
      animate(".wordmark-sky", { opacity: [.7, 0], duration: 250, delay: 650, ease: "outCubic" });
    });
    return () => scope.revert();
  }, [reduced]);
  return <div className="constellation-wordmark" ref={root}>
    <svg viewBox="0 0 520 180" aria-hidden="true" className="wordmark-sky">
      {["M30 140 L72 30 L110 140 M48 95 L94 95", "M165 140 L165 35 L205 35 Q245 35 245 65 Q245 95 205 95 L165 95 M205 95 L250 140", "M300 35 L330 35 M315 35 L315 140 M300 140 L330 140", "M380 140 L420 30 L465 140 M397 95 L447 95"].map((d, index) => <path key={index} className="wordmark-connection" d={d} pathLength="1" strokeDasharray="1" fill="none" />)}
      {[[30,140],[72,30],[110,140],[165,140],[165,35],[205,35],[245,65],[250,140],[315,35],[315,140],[380,140],[420,30],[465,140]].map(([cx,cy], index) => <circle key={index} cx={cx} cy={cy} r="3" className="wordmark-star" />)}
    </svg>
    <h1 className="wordmark studio-wordmark" style={{ fontSize: "clamp(64px,14vw,120px)" }} aria-label="ARIA">{"ARIA".split("").map((letter, index) => <span aria-hidden="true" key={index} style={{ animationDelay: `${.12 + index * .06}s` }}>{letter}</span>)}</h1>
  </div>;
}

const SAMPLES = [
  { title: "Database design", steps: ["Tables & keys", "Dependencies", "Normalization"], question: "Why does normalization matter?", answer: "Imagine storing a customer's address in every order. Updating it means changing many rows. Separating customers and orders gives that address one clear home." },
  { title: "Linear algebra", steps: ["Vectors", "Linear combinations", "Transformations"], question: "What does a matrix do to a vector?", answer: "Think of a vector as an arrow. A matrix can stretch, rotate, or shear that arrow. Looking at how it moves the basis vectors helps you understand the whole transformation." },
  { title: "Python", steps: ["Variables", "Functions", "Problem solving"], question: "When should I write a function?", answer: "When a task has a clear purpose, a function gives it a name. You can call it again with different inputs, test it separately, and make your program easier to follow." },
];
const STAGES = ["Your path", "A conversation", "Connected ideas"];

export function LearningPreview() {
  const hydrated = useHydrated();
  const [topic, setTopic] = useState(0);
  const [stage, setStage] = useState(0);
  const sample = SAMPLES[topic];
  return <section className="learning-preview" aria-labelledby="preview-title">
    <div className="preview-heading"><div><p className="eyebrow">A GLIMPSE INSIDE ARIA</p><h2 id="preview-title">A question becomes a journey.</h2><p>Explore an illustrative sample of the learning experience.</p></div><label className="preview-topic">Sample topic<select className="input" disabled={!hydrated} value={topic} onChange={event => setTopic(Number(event.target.value))}>{SAMPLES.map((item,index) => <option key={item.title} value={index}>{item.title}</option>)}</select></label></div>
    <div className="preview-stage-controls" role="group" aria-label="Sample learning stage">{STAGES.map((label,index) => <button key={label} disabled={!hydrated} aria-pressed={stage === index} onClick={() => setStage(index)}><span>0{index+1}</span>{label}<Icon name="arrow" size={15} /></button>)}</div>
    <div className="preview-scene route-arrival" key={`${topic}:${stage}`}>
      {stage === 0 ? <ol className="preview-roadmap">{sample.steps.map((step,index) => <li key={step}><span className="preview-step">{index+1}</span><div><span className="eyebrow">CHAPTER 0{index+1}</span><h3>{step}</h3><p>{index === 0 ? "Build your foundation" : index === 1 ? "Make the connections" : "Put your ideas to work"}</p></div></li>)}</ol>
      : stage === 1 ? <div className="preview-conversation"><p className="preview-question">{sample.question}</p><div className="preview-answer"><span className="eyebrow"><Icon name="sparkles" size={14} /> ARIA · SAMPLE RESPONSE</span><p>{sample.answer}</p></div></div>
      : <div className="preview-concepts"><svg viewBox="0 0 600 200" aria-hidden="true"><path d="M100 100 Q210 20 300 100 T500 100" fill="none" pathLength="1" /></svg>{sample.steps.map((step,index) => <div key={step} className="preview-concept"><Icon name={index === 0 ? "book" : index === 1 ? "activity" : "sparkles"} size={23} /><h3>{step}</h3><span>Sample concept</span></div>)}</div>}
    </div>
    <p className="preview-disclaimer">Illustrative sample content. Your learning path and evidence are personalized inside ARIA.</p>
  </section>;
}
