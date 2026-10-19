"use client";

import { useEffect, useRef, useState, useSyncExternalStore, type CSSProperties, type ReactNode } from "react";
import { MotionConfig, motion, useInView } from "motion/react";

function subscribeMotion(callback: () => void) {
  const query = window.matchMedia("(prefers-reduced-motion: reduce)");
  query.addEventListener("change", callback);
  return () => query.removeEventListener("change", callback);
}

// The server renders a static version; browser preferences are observed live.
export function useMotionPreference() {
  return useSyncExternalStore(subscribeMotion,
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => true);
}

function subscribeVisibility(callback: () => void) {
  document.addEventListener("visibilitychange", callback);
  return () => document.removeEventListener("visibilitychange", callback);
}

export function usePageVisible() {
  return useSyncExternalStore(subscribeVisibility, () => !document.hidden, () => true);
}

export const spatialTransition = { type: "spring" as const, stiffness: 380, damping: 34 };

export function MotionProvider({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user" transition={spatialTransition}>{children}</MotionConfig>;
}

export function Reveal({ children, className = "", delay = 0 }: {
  children: ReactNode; className?: string; delay?: number;
}) {
  // CSS keeps SSR content visible and respects reduced motion before hydration.
  return <div className={`motion-reveal ${className}`} style={{ "--reveal-delay": `${Math.min(delay, 240)}ms` } as CSSProperties}>{children}</div>;
}

/** Counts from 0 to `value` once the element scrolls into view. With motion
 * disabled it stays at `value` and never animates. */
function useCountUp(value: number, enabled: boolean) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.5 });
  const [animated, setAnimated] = useState(0);
  useEffect(() => {
    if (!enabled || !inView) return;
    const start = performance.now();
    const duration = 750;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      setAnimated(Math.round(value * (1 - Math.pow(1 - t, 3))));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, inView, enabled]);
  return { ref, display: enabled ? animated : value };
}

export function ProgressRing({ value, label, caption = "strong", size, tone = "accent", text }: {
  value: number; label: string; caption?: string; size?: number; text?: string;
  tone?: "accent" | "success" | "warning" | "danger";
}) {
  const reduced = useMotionPreference();
  const percent = Math.max(0, Math.min(100, Math.round(value)));
  const circumference = 2 * Math.PI * 48;
  const { ref, display } = useCountUp(percent, !reduced);
  const style = size ? ({ width: size, height: size } as CSSProperties) : undefined;
  return (
    <div ref={ref} className={`learning-ring ring-tone-${tone}`} role="img" aria-label={text ? `${text} ${caption}` : `${percent}% ${label}`} style={style}>
      <svg viewBox="0 0 120 120" aria-hidden="true">
        <circle cx="60" cy="60" r="48" className="ring-track" />
        <motion.circle cx="60" cy="60" r="48" className="ring-value"
          strokeDasharray={circumference}
          initial={reduced ? false : { strokeDashoffset: circumference }}
          whileInView={{ strokeDashoffset: circumference * (1 - percent / 100) }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: reduced ? 0 : 0.85, ease: [0.22, 1, 0.36, 1] }} />
      </svg>
      <div className="ring-label"><strong>{text ?? <>{display}<small>%</small></>}</strong>{caption && <span>{caption}</span>}</div>
    </div>
  );
}
