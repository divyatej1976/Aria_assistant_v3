import Link from "next/link";

import { ThemeToggle } from "../components/theme-toggle";

const capabilities = [
  {
    icon: "description",
    title: "PDF-to-Knowledge",
    body: "Upload raw academic papers or textbooks. ARIA instantly deconstructs the document into atomic concepts, removing fluff and extracting only functional knowledge.",
    span: "md:col-span-1",
  },
  {
    icon: "fact_check",
    title: "Evidence from Your Study",
    body: "ARIA records your assessments, notes, and reviews as evidence, then adapts what you study next. External academic-database research is a planned future capability.",
    span: "md:col-span-2",
    evidence: true,
  },
  {
    icon: "hub",
    title: "Topological Mapping",
    body: "Visualize your understanding. ARIA generates interactive nodes of related concepts, showing you exactly where gaps in your knowledge exist and how to bridge them efficiently.",
    span: "md:col-span-3",
    map: true,
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background text-on-background font-sans antialiased">
      {/* Top nav */}
      <nav className="bg-surface text-primary w-full h-16 sticky top-0 z-50 border-b border-surface-variant shadow-[0_4px_24px_rgba(209,217,230,0.3)] flex justify-between items-center px-container-padding">
        <div className="flex items-center gap-4">
          <span className="text-headline-md font-extrabold text-secondary tracking-tight">ARIA</span>
        </div>
        <div className="flex items-center gap-element-gap">
          <ThemeToggle />
          <Link href="/app" className="interactive-extruded w-10 h-10 rounded-full shadow-extruded flex items-center justify-center text-on-surface-variant hover:opacity-80 transition-opacity bg-surface">
            <span className="material-symbols-outlined">account_circle</span>
          </Link>
        </div>
      </nav>

      <main className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-24">
        {/* Hero */}
        <section className="flex flex-col lg:flex-row items-center gap-12 lg:gap-24 mb-32">
          <div className="flex-1 space-y-8 z-10 relative">
            <div className="inline-block px-4 py-2 rounded-full shadow-extruded bg-surface-container-lowest text-label-md text-secondary">
              Mastery through Adaptation
            </div>
            <h1 className="text-headline-xl lg:text-[64px] lg:leading-[72px] text-on-background max-w-2xl">
              Master any subject with AI that adapts to your unique learning path.
            </h1>
            <p className="text-body-lg text-on-surface-variant max-w-xl">
              ARIA adapts to your study history: it grounds answers in your own material,
              checks understanding with assessments, and shows you what to review next.
            </p>
            <div className="flex flex-col sm:flex-row gap-6 pt-4">
              <Link
                href="/signup"
                className="btn-extruded bg-surface shadow-extruded px-8 py-4 rounded-xl text-label-md text-aria-red flex items-center justify-center gap-2 w-full sm:w-auto border border-surface-variant"
              >
                Initialize Learning Journey
                <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
              </Link>
              <Link
                href="/signin"
                className="btn-extruded bg-surface shadow-extruded px-8 py-4 rounded-xl text-label-md text-on-surface flex items-center justify-center gap-2 w-full sm:w-auto"
              >
                Read Protocol
              </Link>
            </div>
          </div>
          <div className="flex-1 w-full relative h-[400px] lg:h-[600px] rounded-[2rem] shadow-extruded bg-surface p-8 overflow-hidden flex items-center justify-center">
            <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-secondary to-transparent"></div>
            <div className="relative w-full h-full flex items-center justify-center">
              <div className="absolute w-64 h-64 border-2 border-dashed border-outline-variant rounded-full animate-[spin_30s_linear_infinite]"></div>
              <div className="absolute w-48 h-48 border-2 border-dashed border-secondary/30 rounded-full animate-[spin_20s_linear_infinite_reverse]"></div>
              <div className="z-10 bg-surface shadow-extruded w-32 h-32 rounded-full flex flex-col items-center justify-center gap-2">
                <span className="material-symbols-outlined text-4xl text-secondary">psychology</span>
                <span className="text-label-sm text-on-surface-variant">User Input</span>
              </div>
              <div className="absolute top-[20%] right-[20%] z-10 bg-surface shadow-extruded w-24 h-24 rounded-full flex flex-col items-center justify-center gap-1 opacity-90">
                <span className="material-symbols-outlined text-2xl text-tertiary">analytics</span>
                <span className="text-label-sm text-[10px] text-center px-2 text-on-surface-variant">Pattern Analysis</span>
              </div>
              <div className="absolute bottom-[20%] left-[20%] z-10 bg-surface shadow-extruded w-24 h-24 rounded-full flex flex-col items-center justify-center gap-1 opacity-90">
                <span className="material-symbols-outlined text-2xl text-aria-red">auto_awesome</span>
                <span className="text-label-sm text-[10px] text-center px-2 text-on-surface-variant">Path Adaptation</span>
              </div>
            </div>
          </div>
        </section>

        {/* Capabilities bento */}
        <section className="mb-32">
          <div className="text-center mb-16">
            <h2 className="text-headline-lg text-on-background mb-4">Core Capabilities</h2>
            <p className="text-body-md text-on-surface-variant max-w-2xl mx-auto">
              The cognitive engine powering your accelerated learning.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {capabilities.map((capability) => (
              <div
                key={capability.title}
                className={`bg-surface shadow-extruded rounded-3xl p-8 h-full flex flex-col btn-extruded ${capability.span}`}
              >
                <div className="w-12 h-12 rounded-2xl shadow-injected bg-surface-container-low flex items-center justify-center mb-6">
                  <span className="material-symbols-outlined text-secondary">{capability.icon}</span>
                </div>
                <h3 className="text-headline-md text-on-background mb-4">{capability.title}</h3>
                <p className="text-body-md text-on-surface-variant flex-grow">{capability.body}</p>
                {capability.evidence && (
                  <div className="mt-auto h-32 rounded-2xl shadow-injected bg-surface-container-lowest p-4 flex items-center">
                    <div className="flex gap-4 w-full justify-between items-center z-10 px-4">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-secondary text-sm">fact_check</span>
                        <span className="text-label-sm text-on-surface-variant">Recording evidence from your sessions…</span>
                      </div>
                      <div className="flex gap-2">
                        <div className="w-8 h-8 rounded-full shadow-extruded-sm flex items-center justify-center bg-surface text-green-600">
                          <span className="material-symbols-outlined text-[16px]">check</span>
                        </div>
                        <div className="w-8 h-8 rounded-full shadow-extruded-sm flex items-center justify-center bg-surface text-green-600">
                          <span className="material-symbols-outlined text-[16px]">check</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                {capability.map && (
                  <div className="mt-6 flex-1 w-full h-64 bg-surface-container-low rounded-2xl shadow-injected relative overflow-hidden flex items-center justify-center border border-surface-variant">
                    <div className="absolute w-24 h-24 bg-surface shadow-extruded rounded-full flex items-center justify-center z-20">
                      <span className="text-label-sm text-secondary">Core Concept</span>
                    </div>
                    <div className="absolute w-16 h-16 bg-surface shadow-extruded rounded-full z-10 translate-x-20 -translate-y-12"></div>
                    <div className="absolute w-12 h-12 bg-surface shadow-extruded rounded-full z-10 -translate-x-24 translate-y-8"></div>
                    <div className="absolute w-10 h-10 bg-surface shadow-extruded rounded-full z-10 translate-x-12 translate-y-20"></div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-surface-container-low text-on-surface-variant text-label-sm w-full py-8 border-t border-outline-variant flex flex-col md:flex-row justify-between items-center px-container-padding gap-element-gap">
        <div className="text-label-md font-bold text-secondary">ARIA</div>
        <div className="flex flex-wrap justify-center gap-6">
          <Link href="/signin" className="hover:text-primary transition-colors">Sign In</Link>
          <Link href="/signup" className="hover:text-primary transition-colors">Sign Up</Link>
        </div>
        <div className="text-on-surface-variant">© {new Date().getFullYear()} ARIA. All rights reserved.</div>
      </footer>
    </div>
  );
}
