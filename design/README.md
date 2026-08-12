# Design assets

The wireframe archives live in `design/wireframes/` and are **git-ignored** (they are large
binary archives kept locally for design reference). This file documents where they are and what
they contain.

## Wireframes

- `design/wireframes/stitch_aria_adaptive_learning_wireframes.zip`
- `design/wireframes/stitch_aria_adaptive_learning_wireframes (3).zip`

Both are the same "Stitch" ARIA adaptive-learning wireframe set, each containing a
`DESIGN.md` (the **Extruded Light** neomorphic design system: colors, Plus Jakarta Sans
typography, spacing, extruded/injected shadows) and one `code.html` + `screen.png` per screen:

- `landing_entry` — landing page
- `onboarding` — "Neural Initialization" setup
- `learning_dashboard` — "Mission Control" dashboard
- `knowledge_map` — Neural Topology Map
- `study_session` — split-pane Study
- `learner_progress` — Progress & Assessment

The frozen visual baseline that governs the implementation is `docs/theme-system.md`
(dark default + light theme). The implemented UI lives in `frontend/` and follows these
wireframes via the Tailwind tokens in `frontend/tailwind.config.ts`.
