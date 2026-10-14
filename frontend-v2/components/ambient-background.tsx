"use client";

import { useEffect, useRef, useSyncExternalStore } from "react";
import { usePathname } from "next/navigation";
import { createTimeline } from "animejs";
import { usePalette } from "./palette-provider";
import { useMotionPreference, usePageVisible } from "./motion-system";

const subscribeMounted = () => () => {};
const subscribeCompact = (callback: () => void) => {
  const query = window.matchMedia("(max-width: 768px)");
  query.addEventListener("change", callback);
  return () => query.removeEventListener("change", callback);
};

type RGB = { r: number; g: number; b: number };

function hexToRgb(hex: string): RGB {
  const m = hex.trim().match(/^#?([0-9a-f]{6})$/i);
  if (m) {
    const n = parseInt(m[1], 16);
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
  }
  const rgb = hex.trim().match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
  if (rgb) return { r: +rgb[1], g: +rgb[2], b: +rgb[3] };
  return { r: 140, g: 150, b: 165 };
}

function cssColor(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

type P = { x: number; y: number; vx: number; vy: number; r: number; tw: number; streak?: boolean };

export function AmbientBackground() {
  const pathname = usePathname();
  const { palette } = usePalette();
  // Defer motion/canvas visuals until after hydration: SSR and the first
  // client render return the same static placeholder, so motion style
  // serialization and stored-theme branches can never mismatch.
  const mounted = useSyncExternalStore(subscribeMounted, () => true, () => false);
  const compact = useSyncExternalStore(subscribeCompact, () => window.matchMedia("(max-width: 768px)").matches, () => true);
  const calm = pathname !== "/";
  const isAurora = palette === "aurora";
  const reducedMotion = useMotionPreference();
  const pageVisible = usePageVisible();
  const quiet = pathname === "/app/learn" || pathname === "/app/assess";

  const canvasRef = useRef<HTMLCanvasElement>(null);

  // ---------- constellation ----------
  useEffect(() => {
    if (reducedMotion || quiet || !mounted || !pageVisible) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, compact ? 1 : 2);
    let w = window.innerWidth;
    let h = window.innerHeight;

    let accent: RGB = { r: 20, g: 163, b: 160 };
    let line: RGB = { r: 138, g: 148, b: 168 };
    let parts: P[] = [];
    let raf = 0;
    let running = true;
    let visible = !document.hidden;
    let timeline: ReturnType<typeof createTimeline> | undefined;
    const mouse = { x: -9999, y: -9999 };
    const flow = { dx: 0.03, dy: -0.02, spread: 1 };

    function readTheme() {
      accent = hexToRgb(cssColor("--accent"));
      line = hexToRgb(cssColor("--text-3"));
    }

    function build() {
      if (!canvas || !ctx) return;
      readTheme();
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const target = compact ? (calm ? 10 : 18) : calm ? 18 : 24;
      const count = Math.min(target, Math.max(compact ? 8 : 12, Math.floor((w * h) / 60000)));
      const streakRate = isAurora ? 0.12 : 0.18;
      parts = Array.from({ length: count }, () => {
        const streak = Math.random() < streakRate;
        const sp = streak ? 3.4 : 1;
        return {
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 0.28 * sp,
          vy: (Math.random() - 0.5) * 0.28 * sp,
          r: (1 + Math.random() * (calm ? 1.4 : 2.2)) * (streak ? 1.4 : 1),
          tw: Math.random() * Math.PI * 2,
          streak,
        };
      });
    }

    function draw(t: number) {
      if (!ctx) return;
      ctx.clearRect(0, 0, w, h);
      const lineMax = 140;
      const alphaBase = calm ? 0.75 : 1;

      for (const p of parts) {
        p.x += p.vx + flow.dx;
        p.y += p.vy + flow.dy;
        if (p.x < -30) p.x = w + 30;
        if (p.x > w + 30) p.x = -30;
        if (p.y < -30) p.y = h + 30;
        if (p.y > h + 30) p.y = -30;

        const ddx = p.x - mouse.x;
        const ddy = p.y - mouse.y;
        const d2 = ddx * ddx + ddy * ddy;
        if (d2 < 20000) {
          const d = Math.sqrt(d2) || 1;
          const force = (1 - d / 142) * 0.8;
          p.x += (ddx / d) * force;
          p.y += (ddy / d) * force;
        }
      }

      // connection lines
      for (let i = 0; i < parts.length; i++) {
        const a = parts[i];
        for (let j = i + 1; j < parts.length; j++) {
          const b = parts[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const distanceSquared = dx * dx + dy * dy;
          if (distanceSquared < lineMax * lineMax) {
            const d = Math.sqrt(distanceSquared);
            const alpha = (1 - d / lineMax) * 0.22 * flow.spread * alphaBase;
            ctx.strokeStyle = `rgba(${line.r},${line.g},${line.b},${alpha})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      // dots + streaks
      for (const p of parts) {
        if (p.streak) {
          const tail = 54;
          const g = ctx.createLinearGradient(p.x, p.y, p.x - p.vx * tail, p.y - p.vy * tail);
          const a = isAurora ? 0.42 : 0.6;
          g.addColorStop(0, `rgba(${accent.r},${accent.g},${accent.b},${a})`);
          g.addColorStop(1, `rgba(${accent.r},${accent.g},${accent.b},0)`);
          ctx.strokeStyle = g;
          ctx.lineWidth = 1.6;
          ctx.beginPath();
          ctx.moveTo(p.x - p.vx * tail, p.y - p.vy * tail);
          ctx.lineTo(p.x, p.y);
          ctx.stroke();
        }
        const pulse = 0.55 + 0.45 * Math.sin(t * 0.0016 + p.tw);
        const alpha = Math.min(0.5 * pulse * flow.spread * alphaBase, 0.8);
        ctx.fillStyle = `rgba(${accent.r},${accent.g},${accent.b},${alpha})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    function loop(t: number) {
      if (!running || !visible) return;
      draw(t);
      raf = requestAnimationFrame(loop);
    }

    const onResize = () => {
      w = window.innerWidth;
      h = window.innerHeight;
      build();
      if (reduced) draw(0);
    };

    build();

    if (reduced) {
      draw(0);
    } else {
      raf = requestAnimationFrame(loop);
      timeline = createTimeline({ loop: true, autoplay: visible });
      timeline.add(flow, { dx: 0.12, dy: -0.09, spread: 1.5, duration: 5200, ease: "inOutQuad" }, 0)
        .add(flow, { dx: -0.08, dy: 0.06, spread: 0.8, duration: 5200, ease: "inOutQuad" }, 2600)
        .add(flow, { dx: 0.04, dy: -0.03, spread: 1.15, duration: 5200, ease: "inOutQuad" }, 5200);
    }

    const onMouse = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };
    const onLeave = () => {
      mouse.x = -9999;
      mouse.y = -9999;
    };
    const onVis = () => {
      visible = !document.hidden;
      if (visible) timeline?.resume();
      else { timeline?.pause(); cancelAnimationFrame(raf); }
      if (visible && !reduced) {
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(loop);
      }
    };

    const themeObserver = new MutationObserver(() => readTheme());
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "class"] });

    window.addEventListener("resize", onResize);
    window.addEventListener("mousemove", onMouse);
    document.addEventListener("mouseleave", onLeave);
    document.addEventListener("visibilitychange", onVis);

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      timeline?.cancel();
      window.removeEventListener("resize", onResize);
      window.removeEventListener("mousemove", onMouse);
      document.removeEventListener("mouseleave", onLeave);
      document.removeEventListener("visibilitychange", onVis);
      themeObserver.disconnect();
    };
  }, [calm, compact, isAurora, mounted, reducedMotion, quiet, pageVisible]);

  const staticScene = !mounted || reducedMotion || quiet || !pageVisible;
  return (
    <div className={`ambient ${staticScene ? "ambient-static" : compact ? "ambient-compact" : "ambient-workspace"}`}
      aria-hidden="true" style={{ position: "fixed", inset: 0, zIndex: 0, overflow: "hidden", pointerEvents: "none",
        background: "radial-gradient(ellipse at 15% 10%, var(--glow-a), transparent 65%), radial-gradient(ellipse at 90% 75%, var(--glow-b), transparent 65%), radial-gradient(ellipse at 45% 100%, var(--glow-c), transparent 70%)" }}>
      {!staticScene && <canvas ref={canvasRef} style={{ position: "absolute", inset: 0 }} />}
    </div>
  );
}
