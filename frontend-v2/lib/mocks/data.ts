// @deprecated — Mock/demo data only. Do NOT import from production screens.
// Production screens must use real `api()` calls. This file is quarantined
// to lib/mocks/ and blocked via ESLint `no-restricted-imports`.

export type Learner = {
  name: string;
  username: string;
  email: string;
  learningVector: string;
  mastery: string;
  goal: string;
};

export type Notification = {
  id: string;
  title: string;
  body: string;
  read: boolean;
  icon: "calendar" | "clock" | "check" | "flame" | "file";
  at: string;
};

export type Deadline = {
  id: string;
  title: string;
  date: string;
  daysLeft: number;
  pct: number;
  reminderDays: number;
  topics: { t: string; c: boolean }[];
};

export type Task = {
  id: string;
  title: string;
  due: string;
  done: number;
  total: number;
};

export type Badge = {
  id: string;
  title: string;
  icon: "book" | "target" | "flame" | "lightbulb" | "trophy" | "trend";
  gradient: string;
};

export type Concept = {
  name: string;
  state: "SUPPORTED" | "DEVELOPING" | "NEEDS_REVIEW" | "UNKNOWN";
  confidence: number;
  reason: string;
};

export type Artifact = {
  id: string;
  title: string;
  kind: "audio" | "note" | "resource";
  meta: string;
  duration?: string;
};

export const learner: Learner = {
  name: "Divya Tejaswi",
  username: "divyatejaswi",
  email: "divya@example.com",
  learningVector: "Python Functions & Data Structures",
  mastery: "Intermediate",
  goal: "Master DSA and crack technical interviews",
};

export const notifications: Notification[] = [
  { id: "n1", title: "Exam reminder", body: "Data Structures exam in 2 days — 4 topics left to cover.", read: false, icon: "calendar", at: "2h ago" },
  { id: "n2", title: "Task due today", body: "Complete Python DSA — 2 of 5 steps done.", read: false, icon: "clock", at: "6h ago" },
  { id: "n3", title: "Daily digest", body: "You studied 3 topics yesterday. Keep the streak alive!", read: false, icon: "flame", at: "1d ago" },
  { id: "n4", title: "Assessment ready", body: "Your Python Fundamentals result is in: 82%.", read: true, icon: "check", at: "2d ago" },
];

export const home = {
  streak: 7,
  todayActive: true,
  continue: { title: "Python — Functions & Scope", roadmap: "Python Roadmap", pct: 67, last: "Yesterday" },
  upcoming: [
    { title: "Python Assessment", sub: "20 Questions · Medium", tag: "Tomorrow" },
    { title: "Data Structures Exam", sub: "5 Topics checklist", tag: "18 Aug" },
  ],
  adaptation: "Focus on Searching and Sorting next — they are your weakest uncovered topics.",
};

export const deadlines: Deadline[] = [
  {
    id: "d1",
    title: "Data Structures",
    date: "18 August 2026",
    daysLeft: 2,
    pct: 65,
    reminderDays: 5,
    topics: [
      { t: "Arrays & Memory", c: true },
      { t: "Strings & Two-Pointers", c: true },
      { t: "Binary Searching", c: false },
      { t: "QuickSort & MergeSort", c: false },
      { t: "Hashing & HashMaps", c: false },
      { t: "Binary Trees", c: false },
    ],
  },
  {
    id: "d2",
    title: "DBMS",
    date: "25 August 2026",
    daysLeft: 9,
    pct: 28,
    reminderDays: 7,
    topics: [
      { t: "ER Models", c: true },
      { t: "SQL Queries", c: true },
      { t: "Normalization", c: false },
      { t: "Transactions", c: false },
      { t: "Indexing", c: false },
    ],
  },
];

export const tasks: Task[] = [
  { id: "t1", title: "Complete Python DSA", due: "Today", done: 2, total: 5 },
  { id: "t2", title: "Finish ML Module", due: "24 Aug", done: 4, total: 8 },
];

export const progress = {
  overall: 72,
  study: 68,
  assess: 82,
  activeDays: 142,
  currentStreak: 7,
  longestStreak: 21,
  weekly: [24, 38, 52, 34, 72, 58, 80],
};

export const badges: Badge[] = [
  { id: "b1", title: "First Study", icon: "book", gradient: "linear-gradient(135deg,#34d399,#0ea5e9)" },
  { id: "b2", title: "First Assessment", icon: "target", gradient: "linear-gradient(135deg,#fbbf24,#f97316)" },
  { id: "b3", title: "7 Day Streak", icon: "flame", gradient: "linear-gradient(135deg,#fb923c,#ef4444)" },
  { id: "b4", title: "Knowledge Builder", icon: "lightbulb", gradient: "linear-gradient(135deg,#a78bfa,#ec4899)" },
  { id: "b5", title: "Goal Getter", icon: "trophy", gradient: "linear-gradient(135deg,#e2b93b,#d97706)" },
  { id: "b6", title: "Getting Better", icon: "trend", gradient: "linear-gradient(135deg,#38bdf8,#6366f1)" },
];

export const evidence = [
  { id: "e1", concept: "Functions", source: "Study session · Python Functions", verdict: "Supported", when: "2h ago" },
  { id: "e2", concept: "Loops", source: "Assessment · Python Fundamentals", verdict: "Supported", when: "Yesterday" },
  { id: "e3", concept: "Recursion", source: "Chat · DSA Arrays", verdict: "Developing", when: "3d ago" },
];

export const concepts: Concept[] = [
  { name: "Functions", state: "SUPPORTED", confidence: 0.92, reason: "Correct on 3 assessments; strong chat coverage." },
  { name: "Loops", state: "SUPPORTED", confidence: 0.88, reason: "Consistent evidence across study + assessment." },
  { name: "Recursion", state: "DEVELOPING", confidence: 0.61, reason: "Recent practice, needs more review." },
  { name: "Searching", state: "NEEDS_REVIEW", confidence: 0.42, reason: "Missed binary-search questions." },
  { name: "Sorting", state: "NEEDS_REVIEW", confidence: 0.4, reason: "Concept coverage low." },
  { name: "Hashing", state: "UNKNOWN", confidence: 0.1, reason: "No evidence yet." },
];

export const assessments = [
  { id: "a1", title: "Python Fundamentals", meta: "20 Q · Medium", score: 82, correct: 16, total: 20, time: "17 min", feedback: ["Strong grasp of loops and scope.", "Revise *args, **kwargs and exception handling.", "Retest after review."] },
  { id: "a2", title: "SQL Basics", meta: "15 Q · Easy", score: 76, correct: 11, total: 15, time: "9 min", feedback: ["Solid Joins & Group By.", "Filtering needs a little polish."] },
];

export const sessionMessages = [
  { role: "user", content: "Can you explain *args and **kwargs in simple terms?" },
  {
    role: "aria",
    content:
      "In Python, **args collects extra positional arguments into a tuple, and **kwargs collects extra keyword arguments into a dictionary. Together they make functions flexible:\n\n```python\ndef greet(*names):\n    for n in names:\n        print(\"Hi\", n)\n```",
    sources: ["Python Notes · chunk 4", "Chat History · earlier reply"],
    fallback: false,
  },
];

export const materials = {
  resources: [
    { id: "r1", title: "Python Notes", src: "Chat History", format: "PDF", icon: "file" },
    { id: "r2", title: "SQL Revision", src: "Source Notes", format: "Word", icon: "file" },
    { id: "r3", title: "Python Cheat Sheet", src: "LLM Notes", format: "MD", icon: "zap" },
  ],
  notes: [
    { id: "n1", title: "Python Functions — Complete Notes", session: "Python Functions & Scope", type: "Complete Notes", due: "Review due in 2d" },
    { id: "n2", title: "SQL Joins — Quick Revision", session: "SQL Joins", type: "Quick Revision", due: "Review due in 5d" },
  ],
};

export const audio = [
  { id: "au1", title: "Python Functions", source: "Chat History", duration: "12 min", type: "Complete Notes" },
  { id: "au2", title: "SQL Joins", source: "Notes", duration: "6 min", type: "Quick Revision" },
  { id: "au3", title: "DSA Exam Overview", source: "Syllabus", duration: "9 min", type: "Summary" },
];

export const roadmapTiers = [
  { name: "1 · Fundamentals", icon: "book", nodes: [{ name: "Python Basics", items: ["Syntax & Variables", "Data Types"] }, { name: "Control Flow", items: ["if / elif / else", "Loops"] }, { name: "Functions", items: ["def & return", "*args / **kwargs"] }] },
  { name: "2 · Intermediate", icon: "zap", nodes: [{ name: "OOP & Classes", items: ["Classes & Objects", "Inheritance"] }, { name: "Modules & Packaging", items: ["import", "Virtual Envs"] }, { name: "File I/O", items: ["Reading Files", "try / except"] }] },
  { name: "3 · Advanced", icon: "trophy", nodes: [{ name: "Decorators", items: ["Function Decorators"] }, { name: "AsyncIO", items: ["async / await"] }, { name: "APIs with FastAPI", items: ["Endpoints", "Pydantic Models"] }] },
];

export const workflows = [
  { id: "w1", name: "Generate Roadmap", status: "COMPLETED", step: "3/3", agent: "Planner", at: "2d ago" },
  { id: "w2", name: "Syllabus Analysis", status: "RUNNING", step: "2/4", agent: "Analyzer", at: "now" },
  { id: "w3", name: "Notes Generation", status: "WAITING_APPROVAL", step: "3/3", agent: "Writer", at: "1h ago" },
];

export const approvals = [
  { id: "ap1", workflow: "Notes Generation", action: "Publish revision notes", detail: "Python Functions — Complete Notes", status: "PENDING" },
];

export const audit = [
  { id: "ad1", agent: "Planner", action: "generated", detail: "Roadmap from goal", at: "2d ago" },
  { id: "ad2", agent: "Analyzer", action: "synced", detail: "5 concepts updated", at: "now" },
];
