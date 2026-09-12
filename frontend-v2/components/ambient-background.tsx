"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { createTimeline } from "animejs";
import { motion, useMotionValue, useSpring, useTransform, useScroll } from "motion/react";
import { usePalette } from "./palette-provider";

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
  const calm = pathname !== "/";
  const isAurora = palette === "aurora";

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const spotRef = useRef<HTMLDivElement>(null);

  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const sx = useSpring(mx, { stiffness: 55, damping: 18 });
  const sy = useSpring(my, { stiffness: 55, damping: 18 });

  const { scrollYProgress } = useScroll();
  const parallaxY = useTransform(scrollYProgress, [0, 1], [0, -120]);

  const o1x = useTransform(sx, (v) => v * -36);
  const o1y = useTransform(sy, (v) => v * -26);
  const o2x = useTransform(sx, (v) => v * 30);
  const o2y = useTransform(sy, (v) => v * 20);
  const o3x = useTransform(sx, (v) => v * -20);
  const o3y = useTransform(sy, (v) => v * 32);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const nx = e.clientX / window.innerWidth - 0.5;
      const ny = e.clientY / window.innerHeight - 0.5;
      mx.set(nx);
      my.set(ny);
      if (spotRef.current) {
        spotRef.current.style.transform = `translate3d(${e.clientX - 380}px, ${e.clientY - 380}px, 0)`;
      }
    };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, [mx, my]);

  // ---------- constellation ----------
  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = window.innerWidth;
    let h = window.innerHeight;

    let accent: RGB = { r: 20, g: 163, b: 160 };
    let line: RGB = { r: 138, g: 148, b: 168 };
    let parts: P[] = [];
    let raf = 0;
    let running = true;
    let visible = !document.hidden;
    const mouse = { x: -9999, y: -9999 };
    const flow = { dx: 0.03, dy: -0.02, spread: 1 };

    function readTheme() {
      accent = hexToRgb(cssColor("--accent"));
      line = hexToRgb(cssColor("--text-3"));
    }

    function build() {
      readTheme();
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const target = calm ? 48 : 118;
      const count = Math.min(target, Math.max(24, Math.floor((w * h) / (calm ? 42000 : 21000))));
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
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < lineMax) {
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
      const tl = createTimeline({ loop: true, autoplay: true });
      tl.add(flow, { dx: 0.12, dy: -0.09, spread: 1.5, duration: 5200, ease: "inOutQuad" }, 0)
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
      window.removeEventListener("resize", onResize);
      window.removeEventListener("mousemove", onMouse);
      document.removeEventListener("mouseleave", onLeave);
      document.removeEventListener("visibilitychange", onVis);
      themeObserver.disconnect();
    };
  }, [calm, isAurora]);

  const orbDuration = calm ? 34 : 24;

  return (
    <div className="ambient" aria-hidden="true" style={{ position: "fixed", inset: 0, zIndex: 0, overflow: "hidden", pointerEvents: "none" }}>
      {/* parallax layer */}
      <motion.div style={{ position: "absolute", inset: 0, y: parallaxY }}>
        {isAurora ? (
          <>
            {/* slow energy ring */}
            <motion.div
              style={{
                position: "absolute",
                width: "130vmax",
                height: "130vmax",
                left: "50%",
                top: "48%",
                marginLeft: "-65vmax",
                marginTop: "-65vmax",
                borderRadius: "50%",
                background:
                  "conic-gradient(from 0deg, transparent 0deg, var(--glow-a) 40deg, transparent 90deg, var(--glow-b) 170deg, transparent 230deg, var(--glow-c) 300deg, transparent 360deg)",
                filter: "blur(70px)",
                opacity: 0.5,
              }}
              animate={{ rotate: 360 }}
              transition={{ duration: 70, repeat: Infinity, ease: "linear" }}
            />
            <motion.div
              style={{
                position: "absolute",
                width: "58vmax",
                height: "58vmax",
                left: "-16vmax",
                top: "-18vmax",
                borderRadius: "50%",
                background: "radial-gradient(circle, var(--glow-a), transparent 70%)",
                filter: "blur(64px)",
                x: o1x,
                y: o1y,
              }}
              animate={{ scale: [1, 1.22, 1], rotate: [0, 30, 0] }}
              transition={{ duration: orbDuration, repeat: Infinity, ease: "easeInOut" }}
            />
            <motion.div
              style={{
                position: "absolute",
                width: "50vmax",
                height: "50vmax",
                right: "-14vmax",
                top: "26vmax",
                borderRadius: "50%",
                background: "radial-gradient(circle, var(--glow-b), transparent 70%)",
                filter: "blur(64px)",
                x: o2x,
                y: o2y,
              }}
              animate={{ scale: [1.18, 0.9, 1.18], rotate: [0, -36, 0] }}
              transition={{ duration: orbDuration + 8, repeat: Infinity, ease: "easeInOut" }}
            />
            <motion.div
              style={{
                position: "absolute",
                width: "36vmax",
                height: "36vmax",
                left: "28vmax",
                bottom: "-14vmax",
                borderRadius: "50%",
                background: "radial-gradient(circle, var(--glow-c), transparent 70%)",
                filter: "blur(60px)",
                x: o3x,
                y: o3y,
              }}
              animate={{ scale: [1, 1.22, 1] }}
              transition={{ duration: orbDuration + 14, repeat: Infinity, ease: "easeInOut" }}
            />
          </>
        ) : (
          <>
            {/* obsidian sheen */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: "linear-gradient(180deg, rgba(255,255,255,0.085), transparent 46%)",
              }}
            />
            {/* energy ring (silver/gold) */}
            <motion.div
              style={{
                position: "absolute",
                width: "120vmax",
                height: "120vmax",
                left: "50%",
                top: "46%",
                marginLeft: "-60vmax",
                marginTop: "-60vmax",
                borderRadius: "50%",
                background:
                  "conic-gradient(from 0deg, transparent 0deg, var(--glow-a) 60deg, transparent 140deg, var(--glow-c) 230deg, transparent 320deg, transparent 360deg)",
                filter: "blur(80px)",
                opacity: 0.6,
              }}
              animate={{ rotate: -360 }}
              transition={{ duration: 90, repeat: Infinity, ease: "linear" }}
            />
            {/* top hairline — silver, gold when toggle on */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                height: 1,
                background: "linear-gradient(90deg, transparent, var(--accent-2), transparent)",
                opacity: 0.8,
              }}
            />
            <motion.div
              style={{
                position: "absolute",
                width: "44vmax",
                height: "44vmax",
                right: "-8vmax",
                top: "-12vmax",
                borderRadius: "50%",
                background: "radial-gradient(circle, var(--glow-a), transparent 70%)",
                filter: "blur(72px)",
                x: o1x,
                y: o1y,
              }}
              animate={{ scale: [1, 1.18, 1] }}
              transition={{ duration: orbDuration + 10, repeat: Infinity, ease: "easeInOut" }}
            />
          </>
        )}
      </motion.div>

      {/* constellation */}
      <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />

      {/* cursor spotlight */}
      <div
        ref={spotRef}
        style={{
          position: "absolute",
          width: 760,
          height: 760,
          borderRadius: "50%",
          background: isAurora
            ? "radial-gradient(circle, rgba(255,255,255,0.6), transparent 62%)"
            : "radial-gradient(circle, var(--accent-glow), transparent 62%)",
          opacity: isAurora ? 0.6 : 0.2,
          mixBlendMode: isAurora ? "overlay" : "screen",
          willChange: "transform",
        }}
      />

      {/* grain + vignette */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E\")",
          opacity: 0.045,
          mixBlendMode: "overlay",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: isAurora
            ? "radial-gradient(120% 120% at 50% 40%, transparent 50%, rgba(120,135,160,0.14) 100%)"
            : "radial-gradient(120% 120% at 50% 40%, transparent 46%, rgba(0,0,0,0.36) 100%)",
        }}
      />
    </div>
  );
}
