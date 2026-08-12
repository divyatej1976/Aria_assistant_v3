# ARIA — Manual QA Checklist

Automated checks cover the backend, migrations, and a Playwright browser/accessibility smoke in
CI. This checklist captures the manual UI quality gate: accessibility and responsive behavior
that still need human verification. Run through it before treating a release as UI-complete.

## Accessibility

- [ ] Keyboard: tab through the landing, sign-in, sign-up, and `/app` pages. Focus must move in a
      logical order with a clearly visible focus ring on every interactive element.
- [ ] Icon-only buttons (notification bell, theme toggle, chat send) have accessible names/aria-labels.
- [ ] Forms: every input has a visible label; validation errors are announced (`role="alert"`) and
      not conveyed by color alone.
- [ ] Color contrast: body text meets WCAG AA (4.5:1); error/success states pair color with text/icon.
- [ ] `prefers-reduced-motion: reduce` disables decorative animation (spin, pulse).
- [ ] Screen reader pass on core flows (sign in, add material, take an assessment).

## Responsive

- [ ] Desktop (≥1024px): sidebar navigation; bento layouts on Dashboard/Progress render correctly.
- [ ] Tablet (~768px): layouts stack gracefully; no horizontal overflow.
- [ ] Mobile (≤480px): top header + bottom nav; tabs and cards stack; long Study conversations
      remain readable; no essential action exists only on hover.
- [ ] Study split-pane and Topology Map: usable at mobile widths (pan/scroll on the map, chat area
      has a sensible height).
- [ ] Theme toggle works in both dark and light at each breakpoint.

## Core flows (spot check after any frontend change)

- [ ] Sign up → onboarding → Mission Control.
- [ ] Add text + PDF → Ready chips; failed upload shows Retry/Replace.
- [ ] Study: grounded Q&A with sources; follow-up keeps context; topology map renders.
- [ ] Assessment: generate → question flow → submit confirm → results.
- [ ] Progress: consistency/heatmap/badges update after an assessment + study + note review.
- [ ] Notes: create/edit/generate; revision queue; PDF download opens on phone + desktop.
- [ ] Planner: add an exam; reminder check creates a notification; bell shows unread.
