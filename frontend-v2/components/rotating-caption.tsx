"use client";

import { useEffect, useRef, useState } from "react";

export function RotatingCaption({
  phrases,
  interval = 3200,
}: {
  phrases: string[];
  interval?: number;
}) {
  // Single state object; effects only schedule timers (no synchronous setState).
  const [{ index, fading }, setPhase] = useState({ index: 0, fading: false });
  const elRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const fadeTimer = window.setTimeout(() => {
      setPhase((s) => ({ ...s, fading: true }));
    }, interval);
    const rotateTimer = window.setTimeout(() => {
      setPhase((s) => ({ index: (s.index + 1) % phrases.length, fading: false }));
    }, interval + 450);
    return () => {
      window.clearTimeout(fadeTimer);
      window.clearTimeout(rotateTimer);
    };
  }, [index, phrases.length, interval]);

  useEffect(() => {
    const el = elRef.current;
    if (!el) return;
    const spans = el.querySelectorAll<HTMLSpanElement>(".cw");
    const raf = requestAnimationFrame(() => {
      requestAnimationFrame(() => spans.forEach((s) => s.classList.add("in")));
    });
    return () => cancelAnimationFrame(raf);
  }, [index]);

  const words = phrases[index]?.split(" ") ?? [];

  return (
    <span
      ref={elRef}
      style={{
        opacity: fading ? 0 : 1,
        transition: "opacity .45s var(--spring)",
      }}
    >
      {words.map((w, i) => (
        <span key={`${index}-${i}`} className="cw">
          {w}
        </span>
      ))}
    </span>
  );
}