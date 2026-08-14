# ARIA — Manual QA Checklist

Automated checks cover the backend, migrations, the Playwright learning-flow +
accessibility smoke in CI (axe now fails on critical **and** serious), shared
date/error formatting, a source encoding guard (`scripts/check_mojibake.py`),
and cookie-only authentication. This checklist captures the manual UI quality
gate: accessibility and responsive behavior that still need human verification.
Run through it before treating a release as UI-complete.

## Accessibility

- [x] Keyboard: focus-visible ring added for all interactive elements
      (`globals.css`); the axe gate fails CI on critical/serious violations for
      the covered pages (landing, sign-in, sign-up, app, resources, learn,
      assess, progress). Still do a manual tab-through.
- [x] Icon-only buttons (notification bell, theme toggle, chat send) have
      accessible names/aria-labels; the notification popup now has
      `role="dialog"`, `aria-expanded`/`aria-controls`, and Escape-to-close.
- [x] Forms: visible labels and `role="alert"` error announcements are used
      consistently across workspace pages (verified by audit).
- [~] Color contrast: body text targets WCAG AA; error/success states pair
      color with text/icon — still requires a manual AA pass.
- [x] `prefers-reduced-motion: reduce` disables decorative animation via CSS.
- [ ] Screen reader pass on core flows (sign in, add material, take an assessment).

## Responsive

- [ ] Desktop (≥1024px): sidebar navigation; bento layouts on Dashboard/Progress render correctly.
- [ ] Tablet (~768px): layouts stack gracefully; no horizontal overflow.
- [ ] Mobile (≤480px): top header + bottom nav; tabs and cards stack; long Study conversations
      remain readable; no essential action exists only on hover.
- [ ] Study split-pane and Topology Map: usable at mobile widths (pan/scroll on the map, chat area
      has a sensible height).
- [ ] Theme toggle works in both dark and light at each breakpoint; dark theme uses
      dark translucent shadows (`.dark` variants).

## Core flows (spot check after any frontend change)

- [x] Sign up → onboarding → Mission Control. (automated Playwright smoke)
- [x] Add text → Ready chips; study Q&A; assessment generate → submit → results;
      progress renders. (automated `learning-flow.spec.ts`)
- [ ] Add PDF → Ready chips; failed upload shows Retry/Replace.
- [ ] Study follow-up keeps context; topology map renders.
- [ ] Progress: consistency/heatmap/badges update after an assessment + study + note review.
- [ ] Notes: create/edit/generate; revision queue; PDF download opens on phone + desktop.
- [x] Planner: add an exam; add a task (collapsible forms). (automated `planner.spec.ts`);
      reminder check → notification → bell unread still manual.
