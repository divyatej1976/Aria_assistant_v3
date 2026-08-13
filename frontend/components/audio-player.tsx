"use client";

import { useEffect, useRef, useState } from "react";

import { api, apiBlob } from "../lib/api";

type Progress = { position_seconds: number; completed: boolean };

export function AudioPlayer({ artifactId }: { artifactId: string }) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [error, setError] = useState("");
  const audioRef = useRef<HTMLAudioElement>(null);
  const lastSaved = useRef(0);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [blob, progress] = await Promise.all([
          apiBlob(`/api/v1/audio/${artifactId}/play`),
          api<Progress>(`/api/v1/audio/${artifactId}/progress`),
        ]);
        if (!active) return;
        setAudioUrl(URL.createObjectURL(blob));
        if (progress.position_seconds > 0 && audioRef.current) {
          const audio = audioRef.current;
          audio.addEventListener(
            "loadedmetadata",
            () => {
              audio.currentTime = Math.min(progress.position_seconds, audio.duration || 0);
            },
            { once: true },
          );
        }
      } catch (requestError) {
        if (active) setError(requestError instanceof Error ? requestError.message : "Unable to load audio");
      }
    })();
    return () => {
      active = false;
    };
  }, [artifactId]);

  async function saveProgress(position: number, completed: boolean) {
    try {
      await api(`/api/v1/audio/${artifactId}/progress`, {
        method: "PUT",
        body: JSON.stringify({ position_seconds: Math.floor(position), completed }),
      });
    } catch {
      // Best effort.
    }
  }

  function onTimeUpdate() {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.currentTime - lastSaved.current >= 5) {
      lastSaved.current = audio.currentTime;
      void saveProgress(audio.currentTime, audio.duration !== undefined && audio.currentTime >= audio.duration - 1);
    }
  }

  function onPause() {
    const audio = audioRef.current;
    if (audio) void saveProgress(audio.currentTime, false);
  }

  async function review() {
    setError("");
    try {
      await api(`/api/v1/audio/${artifactId}/review`, { method: "POST" });
      setReviewed(true);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to record review");
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {audioUrl && (
        <audio
          ref={audioRef}
          controls
          className="w-full"
          src={audioUrl}
          onTimeUpdate={onTimeUpdate}
          onPause={onPause}
          onEnded={() => {
            const audio = audioRef.current;
            if (audio) void saveProgress(audio.currentTime, true);
          }}
        />
      )}
      <div className="flex gap-3">
        <button
          onClick={() => void review()}
          disabled={reviewed}
          className="px-4 py-2 rounded-full bg-tertiary-container text-on-tertiary-container text-label-md font-bold shadow-extruded btn-extruded disabled:opacity-60"
        >
          {reviewed ? "Reviewed" : "Mark as reviewed"}
        </button>
      </div>
      {error && <p className="text-label-md text-error" role="alert">{error}</p>}
    </div>
  );
}
