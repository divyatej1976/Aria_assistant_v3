"use client";

import { useEffect, useRef, useState } from "react";
import { useMotionPreference } from "./motion-system";

const BARS = 28;

/** Live bars that follow the microphone level: tall while you speak, flat when you pause. */
export function MicWaveform({ stream }: { stream: MediaStream }) {
  const reduced = useMotionPreference();
  const [levels, setLevels] = useState<number[]>(() => Array(BARS).fill(0.08));
  const [seconds, setSeconds] = useState(0);
  const frame = useRef(0);

  useEffect(() => {
    const started = Date.now();
    const clock = window.setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 500);
    if (reduced) return () => window.clearInterval(clock);
    const AudioCtx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return () => window.clearInterval(clock);
    let audio: AudioContext;
    let analyser: AnalyserNode;
    try {
      audio = new AudioCtx();
      analyser = audio.createAnalyser();
      analyser.fftSize = 256;
      audio.createMediaStreamSource(stream).connect(analyser);
    } catch {
      return () => window.clearInterval(clock); // still show the timer and pulsing dot
    }
    const data = new Uint8Array(analyser.fftSize);
    const history: number[] = Array(BARS).fill(0.08);
    let last = 0;
    const tick = (now: number) => {
      frame.current = requestAnimationFrame(tick);
      if (now - last < 60) return; // ~16 updates a second keeps it smooth and cheap
      last = now;
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (const value of data) sum += ((value - 128) / 128) ** 2;
      const rms = Math.sqrt(sum / data.length);
      history.shift();
      history.push(Math.min(1, 0.08 + rms * 4)); // speech sits around 0.05–0.2 RMS
      setLevels([...history]);
    };
    frame.current = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame.current);
      window.clearInterval(clock);
      void audio.close();
    };
  }, [stream, reduced]);

  const time = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  return (
    <div className="mic-wave" role="status" aria-label={`Recording, ${time}`}>
      <span className="mic-wave-dot" aria-hidden="true" />
      <span className="mic-wave-bars" aria-hidden="true">
        {levels.map((level, i) => <i key={i} style={{ transform: `scaleY(${level})` }} />)}
      </span>
      <span className="mic-wave-time">{time}</span>
    </div>
  );
}
