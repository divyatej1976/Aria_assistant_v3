"use client";

import { useEffect, useRef, useState } from "react";
import { api, apiUpload, ApiError } from "@/lib/api";

export type QuizSetupValues = {
  source: "library" | "chats" | "topic" | "weak";
  sessionIds: string[];
  topic: string;
  format: "mcq" | "true_false" | "short_answer" | "mixed";
  count: number;
  difficulty: "easy" | "medium" | "hard";
  timing: "none" | "total" | "per_question";
  minutes: number;
  seconds: number;
  reveal: "practice" | "exam";
};

export const DEFAULT_SETUP: QuizSetupValues = {
  // Matches the "Quick practice" preset.
  source: "library", sessionIds: [], topic: "", format: "mcq", count: 5, difficulty: "medium",
  timing: "none", minutes: 10, seconds: 45, reveal: "practice",
};
export const MAX_QUESTIONS = 50;
const SETUP_KEY = "aria.quiz-setup";

/** Last settings, so the next quiz is one tap. Chats and topic are per-quiz and not remembered. */
export function savedSetup(): QuizSetupValues {
  try {
    const saved = JSON.parse(window.localStorage.getItem(SETUP_KEY) ?? "null") as Partial<QuizSetupValues> | null;
    return saved ? { ...DEFAULT_SETUP, ...saved, sessionIds: [], topic: "" } : DEFAULT_SETUP;
  } catch {
    return DEFAULT_SETUP;
  }
}

export function rememberSetup(values: QuizSetupValues): void {
  try {
    window.localStorage.setItem(SETUP_KEY, JSON.stringify({ ...values, sessionIds: [], topic: "" }));
  } catch {}
}

export function setupRequest(contextId: string, v: QuizSetupValues) {
  const limit = v.timing === "total" ? v.minutes * 60 : v.timing === "per_question" ? v.seconds : null;
  return {
    context_id: contextId, format: v.format, question_count: v.count, difficulty: v.difficulty,
    source: v.source, session_ids: v.source === "chats" ? v.sessionIds : [], topic: v.source === "topic" ? v.topic : null,
    timing: v.timing, time_limit_seconds: limit, reveal: v.reveal,
  };
}

export function setupProblem(v: QuizSetupValues, libraryReady: boolean | null): string | null {
  if (v.source === "chats" && v.sessionIds.length === 0) return "Choose at least one chat.";
  if (v.source === "topic" && !v.topic.trim()) return "Type a topic.";
  if (v.source === "library" && libraryReady === false) return "Your library has no ready files yet. Pick chats or a topic instead, or add a file in Library.";
  if (v.count < 1 || v.count > MAX_QUESTIONS) return `Choose between 1 and ${MAX_QUESTIONS} questions.`;
  return null;
}

type Chat = { id: string; title?: string | null; message_count?: number };

type Preset = { name: string; hint: string; values: Pick<QuizSetupValues, "format" | "count" | "difficulty" | "timing" | "minutes" | "reveal"> };
const PRESETS: Preset[] = [
  { name: "Quick practice", hint: "5 questions, answers as you go",
    values: { format: "mcq", count: 5, difficulty: "medium", timing: "none", minutes: 10, reveal: "practice" } },
  { name: "Topic test", hint: "10 mixed questions, answers at the end",
    values: { format: "mixed", count: 10, difficulty: "medium", timing: "none", minutes: 10, reveal: "exam" } },
  { name: "Mock exam", hint: "20 mixed questions, 30 minutes, answers at the end",
    values: { format: "mixed", count: 20, difficulty: "hard", timing: "total", minutes: 30, reveal: "exam" } },
];
// Stored as easy / medium / hard; learners see Basic / Medium / Advanced.
export const LEVEL_NAMES: Record<QuizSetupValues["difficulty"], string> = { easy: "Basic", medium: "Medium", hard: "Advanced" };
const FORMAT_NAMES: Record<QuizSetupValues["format"], string> = {
  mcq: "Multiple choice", true_false: "True or false", short_answer: "Short answer", mixed: "Mixed questions",
};

function matches(values: QuizSetupValues, preset: Preset): boolean {
  const v = preset.values;
  return values.format === v.format && values.count === v.count && values.difficulty === v.difficulty
    && values.timing === v.timing && values.reveal === v.reveal && (v.timing !== "total" || values.minutes === v.minutes);
}

function summary(v: QuizSetupValues): string {
  const timer = v.timing === "total" ? `${v.minutes} min` : v.timing === "per_question" ? `${v.seconds}s per question` : "No timer";
  const level = LEVEL_NAMES[v.difficulty];
  return `${FORMAT_NAMES[v.format]} · ${v.count} questions · ${level} · ${timer} · ${v.reveal === "practice" ? "Answers as you go" : "Answers at the end"}`;
}

function Choice<T extends string>({ label, value, options, onChange }: {
  label: string; value: T; options: { value: T; label: string; hint?: string }[]; onChange: (v: T) => void;
}) {
  return (
    <fieldset className="quiz-choice">
      <legend className="field-label">{label}</legend>
      <div className="quiz-choice-row" role="radiogroup" aria-label={label}>
        {options.map((option) => (
          <button key={option.value} type="button" role="radio" aria-checked={value === option.value}
            className={`tag-chip${value === option.value ? " tag-chip-selected" : ""}`}
            title={option.hint} onClick={() => onChange(option.value)}>
            {option.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export function QuizSetup({ contextId, values, onChange, libraryReady = null, libraryFiles = null, onLibraryChanged }: {
  contextId: string; values: QuizSetupValues; onChange: (v: QuizSetupValues) => void; libraryReady?: boolean | null;
  libraryFiles?: { id: string; title: string }[] | null; onLibraryChanged?: () => void;
}) {
  const [uploading, setUploading] = useState("");
  const [uploadError, setUploadError] = useState("");
  // Quiz straight from a document: it goes to the library, where every quiz and chat can use it.
  const uploadToLibrary = async (file: File) => {
    const isPdf = file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf";
    const title = file.name.replace(/\.[^/.]+$/, "") || "Document";
    const query = `context_id=${contextId}&title=${encodeURIComponent(title)}`;
    setUploading(file.name); setUploadError("");
    try {
      const saved = await apiUpload<{ processing_status: string; error_detail?: string | null }>(
        `/api/v1/resources/${isPdf ? "pdf" : "image"}?${query}`, file, isPdf ? "application/pdf" : (file.type || "image/png"));
      if (saved.processing_status !== "READY") setUploadError(saved.error_detail ?? "That file could not be read. Try a clearer PDF or photo.");
      onLibraryChanged?.();
    } catch (error) {
      setUploadError(error instanceof ApiError ? error.message : "The upload failed. Please retry.");
    } finally {
      setUploading("");
    }
  };
  const [chats, setChats] = useState<Chat[] | null>(null);
  // The chat list loads after the learner may already have changed settings; read the latest ones.
  const latest = useRef({ values, onChange });
  useEffect(() => { latest.current = { values, onChange }; });
  const set = <K extends keyof QuizSetupValues>(key: K, value: QuizSetupValues[K]) => onChange({ ...values, [key]: value });

  useEffect(() => {
    let cancelled = false;
    api<Chat[]>(`/api/v1/study/sessions?context_id=${contextId}`)
      .then((list) => {
        if (cancelled) return;
        const usable = list.filter((chat) => (chat.message_count ?? 0) > 1);
        setChats(usable);
      })
      .catch(() => { if (!cancelled) setChats([]); });
    return () => { cancelled = true; };
  }, [contextId]);

  // No ready files but some chats (the usual new learner): quiz on the latest chat, ready in one tap.
  const switched = useRef(false);
  useEffect(() => {
    const { values: now, onChange: apply } = latest.current;
    if (switched.current || libraryReady !== false || !chats?.length || now.source !== "library") return;
    switched.current = true;
    apply({ ...now, source: "chats", sessionIds: now.sessionIds.length ? now.sessionIds : [chats[0].id] });
  }, [libraryReady, chats]);

  const chooseSource = (source: QuizSetupValues["source"]) => onChange({
    ...values, source,
    sessionIds: source === "chats" && values.sessionIds.length === 0 && chats?.length ? [chats[0].id] : values.sessionIds,
  });

  return (
    <div className="quiz-setup">
      <Choice label="Quiz me on" value={values.source} onChange={chooseSource} options={[
        { value: "library", label: "My library", hint: "Files and notes shared with every chat" },
        { value: "chats", label: "My chats", hint: "Pick the conversations to quiz on" },
        { value: "topic", label: "A topic", hint: "Type any topic" },
        { value: "weak", label: "My weak spots", hint: "Topics your past quizzes showed need review" },
      ]} />
      {values.source === "chats" && (
        <div className="quiz-chats">
          {chats === null ? <p className="field-help">Loading your chats…</p>
            : chats.length === 0 ? <p className="field-help">No chats yet. Talk to ARIA in Learn first.</p>
            : chats.map((chat) => (
              <label key={chat.id} className="quiz-chat">
                <input type="checkbox" checked={values.sessionIds.includes(chat.id)} onChange={(e) => set("sessionIds",
                  e.target.checked ? [...values.sessionIds, chat.id] : values.sessionIds.filter((id) => id !== chat.id))} />
                <span>{chat.title ?? "Untitled chat"}</span>
              </label>
            ))}
        </div>
      )}
      {values.source === "library" && (
        <div className="quiz-library">
          {libraryFiles && libraryFiles.length > 0 && (
            <p className="field-help">Questions will cover: <b>{libraryFiles.map((file) => file.title).join(", ")}</b></p>
          )}
          <label className={`btn btn-secondary${uploading ? " is-busy" : ""}`}>
            <input type="file" accept=".pdf,application/pdf,image/*" hidden disabled={!!uploading}
              onChange={(e) => { const file = e.target.files?.[0]; e.target.value = ""; if (file) void uploadToLibrary(file); }} />
            {uploading ? `Reading ${uploading}…` : libraryFiles?.length ? "Add another file" : "Upload a file to quiz on"}
          </label>
          {uploadError && <p className="field-help" role="alert">{uploadError}</p>}
        </div>
      )}
      {values.source === "topic" && (
        <input className="input" aria-label="Topic" placeholder="e.g. Python decorators" maxLength={300}
          value={values.topic} onChange={(e) => set("topic", e.target.value)} />
      )}

      <fieldset className="quiz-choice">
        <legend className="field-label">Quiz style</legend>
        <div className="quiz-presets" role="radiogroup" aria-label="Quiz style">
          {PRESETS.map((preset) => (
            <button key={preset.name} type="button" role="radio" aria-checked={matches(values, preset)}
              className={`plan-option${matches(values, preset) ? " selected" : ""}`} onClick={() => onChange({ ...values, ...preset.values })}>
              <b>{preset.name}</b><span>{preset.hint}</span>
            </button>
          ))}
        </div>
        <p className="field-help quiz-summary">{summary(values)}</p>
      </fieldset>

      <details className="quiz-customize">
        <summary>Customize</summary>
      <Choice label="Question type" value={values.format} onChange={(v) => set("format", v)} options={[
        { value: "mcq", label: "Multiple choice" },
        { value: "true_false", label: "True or false" },
        { value: "short_answer", label: "Short answer", hint: "Type the answer; marked by meaning, not exact spelling" },
        { value: "mixed", label: "Mixed" },
      ]} />

      <div className="quiz-count">
        <label className="field-label" htmlFor="quiz-count">Questions</label>
        <div className="quiz-choice-row">
          {[5, 10, 20].map((n) => (
            <button key={n} type="button" className={`tag-chip${values.count === n ? " tag-chip-selected" : ""}`} onClick={() => set("count", n)}>{n}</button>
          ))}
          <input id="quiz-count" className="input quiz-number" type="number" min={1} max={MAX_QUESTIONS}
            aria-label="Number of questions" value={values.count}
            onChange={(e) => set("count", Math.max(1, Math.min(MAX_QUESTIONS, Number(e.target.value) || 1)))} />
          <span className="field-help">up to {MAX_QUESTIONS}</span>
        </div>
      </div>

      <Choice label="Difficulty" value={values.difficulty} onChange={(v) => set("difficulty", v)} options={[
        { value: "easy", label: "Basic" }, { value: "medium", label: "Medium" }, { value: "hard", label: "Advanced" },
      ]} />

      <Choice label="Timer" value={values.timing} onChange={(v) => set("timing", v)} options={[
        { value: "none", label: "No timer" },
        { value: "total", label: "Whole quiz" },
        { value: "per_question", label: "Each question" },
      ]} />
      {values.timing === "total" && (
        <label className="quiz-inline">
          <input className="input quiz-number" type="number" min={1} max={240} aria-label="Minutes for the whole quiz"
            value={values.minutes} onChange={(e) => set("minutes", Math.max(1, Math.min(240, Number(e.target.value) || 1)))} /> minutes in total
        </label>
      )}
      {values.timing === "per_question" && (
        <label className="quiz-inline">
          <input className="input quiz-number" type="number" min={10} max={600} aria-label="Seconds per question"
            value={values.seconds} onChange={(e) => set("seconds", Math.max(10, Math.min(600, Number(e.target.value) || 10)))} /> seconds per question
        </label>
      )}

      <Choice label="Show answers" value={values.reveal} onChange={(v) => set("reveal", v)} options={[
        { value: "practice", label: "After each question", hint: "Practice: learn as you go" },
        { value: "exam", label: "At the end", hint: "Exam: check yourself before a test" },
      ]} />
      </details>
    </div>
  );
}
