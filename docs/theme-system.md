# ARIA — Theme System

**Status:** Frozen v1
**Scope:** UX / Visual Design
**Applies to:** ARIA web application, R0 and future releases

**Related:** Phase 2 (UX Architecture), Phase 10 (Technology Decisions), `TECH_STACK.md`

---

# Purpose

### Frontend motion extension — 5 October 2026

The learner frontend now adds a celestial studio motion layer to the existing Aurora, Noir, and optional Noir gold palettes. It uses palette tokens for borders, accents, and surfaces. Reading and assessment areas use static ambient backgrounds; dashboard and exploratory screens can retain restrained ambient movement.

Shared motion uses short component transitions, finite section entrances, animated progress updates, and selective SVG choreography. The knowledge constellation connects actual prerequisites and communicates states through icons and labels as well as color. Reduced-motion preferences update live and cover CSS, Anime.js, Motion, and canvas visuals. Hidden-page ambient work is stopped, and scoped timelines are cleaned up when components unmount.

Noir's secondary text token is raised to `#92928f` to preserve readable sidebar labels. Mobile active navigation uses a tinted surface and readable theme text instead of white text over light accent colors.

This document defines ARIA's dark and light visual themes, their shared constraints, accessibility requirements, component behavior, and switching rules.

ARIA uses **one product experience with two visual themes**. Dark and light mode must never become separate UX systems. Information architecture, navigation, interaction behavior, component semantics, content hierarchy, and user flows remain identical across themes.

The themes are visual expressions of the same ARIA design system.

---

# Theme Strategy

| Theme | Role | Decision |
|---|---|---|
| **Dark (Noir)** | Alternate experience | ✅ Fixed |
| **Light (Aurora)** | Primary/default experience | ✅ Fixed |
| **System** | Optional preference following OS/browser setting | 🟡 Supported if practical |

### Default

**Light Aurora is ARIA's default theme.**

Aurora provides the default bright learning studio. Learners can select Noir for a darker, calm visual environment; the choice persists in the browser.

Both palettes remain first-class experiences with the same learning flows and accessibility requirements.

---

# Core Principle

> **Same ARIA. Different surface.**

Changing the theme must not:

- change the user's workflow
- hide functionality
- change navigation
- change content hierarchy
- change component semantics
- change learning recommendations
- change learner state
- change application behavior

Only the visual presentation changes.

---

# Shared Design Language

Both themes share the following foundations:

- **Plus Jakarta Sans** typography
- 8px base spacing system
- responsive grid structure
- consistent component hierarchy
- consistent interaction states
- accessible focus states
- consistent iconography
- restrained visual effects
- strong information hierarchy
- ARIA's premium, technical, and calm personality

The themes may use different surface, text, border, and accent tokens, but semantic roles remain consistent.

---

# Dark Theme — Noir

## Design Intent

The dark theme represents ARIA's primary visual identity.

Its personality is:

- sleek
- premium
- calm
- sophisticated
- technical
- modern
- AI-native

The visual language should feel like a high-end digital learning environment rather than a conventional LMS or generic chatbot.

## Palette Direction

The dark theme uses deep charcoal/obsidian surfaces with restrained light typography and subtle architectural layering.

Reference design tokens from the current Stitch direction include:

- Base surface: `#131313`
- Lowest surface: `#0E0E0E`
- Low container: `#1C1B1B`
- Standard container: `#201F1F`
- High container: `#2A2A2A`
- Highest container: `#353534`
- Primary text: `#E5E2E1`
- Secondary text: `#C8C7BF`
- Outline: `#91918A`
- Outline variant: `#474741`

These values are design references, not a license to bypass semantic color tokens in implementation.

## Dark Theme Constraints

- Avoid saturated neon colors.
- Avoid excessive glow effects.
- Avoid using pure black for every surface.
- Preserve visible separation between adjacent surfaces.
- Use tonal layering instead of heavy shadows wherever possible.
- Keep secondary information visually subordinate without making it unreadable.
- Use animation and blur selectively.
- Do not allow the premium aesthetic to reduce accessibility.

## Dark Theme Depth

Depth should primarily come from:

1. tonal surface differences
2. restrained borders
3. controlled transparency where appropriate
4. subtle elevation
5. motion/state changes

Glassmorphism must remain selective rather than becoming the default treatment for every component.

---

# Light Theme — Aurora

## Design Intent

The light theme preserves ARIA's premium and technical identity while providing a brighter, high-clarity environment.

Its personality is:

- precise
- clean
- clinical
- tactile
- information-focused
- accessible

The light theme should feel like the same product viewed under a different lighting condition—not a separate brand.

## Palette Direction

The current Stitch direction uses an icy neutral foundation with white elevated surfaces and a restrained action accent.

Reference values include:

- Base surface: `#F7F9FB`
- Lowest surface: `#FFFFFF`
- Low container: `#F2F4F6`
- Standard container: `#ECEEF0`
- High container: `#E6E8EA`
- Highest container: `#E0E3E5`
- Primary text: `#191C1E`
- Secondary text: `#5B403F`
- Outline: `#8F6F6E`
- Outline variant: `#E4BEBC`

The current visual exploration also uses a restrained Swiss-red action accent. Accent colors must remain semantic and must not become decorative noise.

## Light Theme Constraints

- Maintain strong text/background contrast.
- Avoid excessive shadows.
- Keep elevated surfaces visually distinct from the base canvas.
- Avoid making every surface pure white.
- Preserve the same information hierarchy as dark mode.
- Avoid turning the interface into a conventional corporate dashboard.
- Keep accents limited to meaningful actions and states.

---

# Semantic Color Rules

Theme-specific colors must map to **semantic roles**, not hard-coded visual meanings.

Examples:

- `--color-background`
- `--color-surface`
- `--color-surface-elevated`
- `--color-text-primary`
- `--color-text-secondary`
- `--color-border`
- `--color-focus`
- `--color-accent`
- `--color-success`
- `--color-warning`
- `--color-error`
- `--color-info`

The exact RGB/HEX values may differ between themes while the meaning remains identical.

Success, warning, error, and informational states must **never rely on color alone**. Pair semantic color with at least one of:

- iconography
- text
- labels
- shape/state change
- accessible status messaging

---

# Accessibility Requirements

Accessibility overrides aesthetic preferences.

## Contrast

Normal text should meet at least **WCAG AA contrast requirements (4.5:1)**. Large text should meet the applicable WCAG AA threshold.

Interactive controls, focus indicators, borders, and meaningful non-text UI elements must maintain sufficient visual distinction.

## Focus

Every keyboard-accessible interactive element must have a clearly visible focus state in both themes.

Focus must not depend solely on a subtle color change.

## Motion

Animations must respect `prefers-reduced-motion`.

When reduced motion is enabled:

- disable decorative motion
- minimize transitions
- preserve functional state changes
- avoid parallax and unnecessary movement

## Readability

ARIA may use premium visual treatments, but long-form educational content must prioritize readability over aesthetics.

This is especially important in:

- Study Sessions
- Resource Viewer
- AI explanations
- Assessment feedback
- Progress explanations

---

# Typography

Both themes use **Plus Jakarta Sans** as the primary typeface.

## Core hierarchy

- Display / major headings: strong weight, tight tracking
- Section headings: bold and clearly separated
- Body text: comfortable line height for extended reading
- Labels: compact, structured, and readable
- Metadata: visually subordinate but still accessible

Reference body sizes:

- Body large: `18px`
- Body medium: `16px`
- Small label: `12–14px`

Long-form educational text should generally use generous line height around `1.5–1.6`.

---

# Spacing and Layout

Both themes use an **8px base spacing system**.

Responsive layout follows the ARIA design direction:

### Desktop

- 12-column grid
- approximately 24px gutters
- generous outer margins
- focused reading width for lessons

### Tablet

- 8-column grid
- reduced outer margins

### Mobile

- 4-column grid
- approximately 16–20px side margins

The theme must never change layout dimensions merely because the user switches between dark and light mode.

---

# Shape Language

ARIA uses a refined, soft-industrial shape language.

- Small controls: subtle rounding
- Cards: moderate rounding
- Larger containers: larger but controlled rounding
- Data visualizations: avoid unnecessary decoration
- Buttons and inputs: consistent geometry across themes

Theme switching must not alter component geometry.

---

# Component Rules

Every shared component must support both themes through semantic design tokens.

## Buttons

Primary and secondary button hierarchy must remain identical in both themes.

Primary buttons should have clear visual priority without excessive glow, gradients, or animation.

## Inputs

Inputs must clearly communicate:

- default
- hover
- focus
- filled
- disabled
- error

states in both themes.

## Cards

Cards should establish hierarchy through surface contrast, borders, and restrained elevation.

Avoid turning every card into a floating/glass element.

## Progress

Progress indicators should communicate actual learning progress and must not rely only on decorative animation.

## Charts

Charts must remain readable in both themes. Axes, labels, legends, and data points require sufficient contrast.

## Icons

Use Lucide React consistently. Icons should support meaning rather than act as decoration alone.

---

# Animation and Motion

Motion is part of ARIA's visual identity but must remain purposeful.

Use motion for:

- state transitions
- feedback
- navigation continuity
- learning progress
- meaningful interaction confirmation

Avoid:

- continuous decorative animation
- excessive particle effects
- distracting background motion
- animation that slows learning tasks

`Motion` is the primary interaction animation system. `Anime.js` may be used selectively for branding, onboarding, and specialized visual sequences.

All animation must respect reduced-motion preferences.

---

# Theme Switching

Theme switching should:

- preserve the current route
- preserve unsaved form state
- preserve scroll position where practical
- transition without flashing an incorrect theme
- persist the user's preference
- support system preference if enabled

The application should use `next-themes` or an equivalent implementation consistent with the frozen frontend stack.

Avoid theme-dependent business logic.

---

# R0 Constraints

The R0 implementation must not create separate dark-mode and light-mode component implementations.

Instead:

```text
Shared Component
      ↓
Semantic Design Tokens
      ↓
 ┌───────────────┐
 │               │
Dark Theme    Light Theme
```

R0 must prioritize:

1. one component system
2. semantic tokens
3. accessible contrast
4. theme parity
5. consistent behavior

Visual polish should never create duplicated application logic.

---

# ARIA Brand Constraint

ARIA should feel **premium and intelligent without becoming visually noisy**.

Avoid:

- generic AI purple-gradient branding
- excessive neon
- excessive glassmorphism
- excessive shadows
- decorative animation without purpose
- overly futuristic terminology in core user actions

ARIA's premium identity should come from:

- typography
- spacing
- hierarchy
- restraint
- motion quality
- surface treatment
- consistency

---

# Learner Experience Constraint

Theme design must never obscure ARIA's central product identity:

> **ARIA is an adaptive learning system, not a generic AI chatbot.**

The visual hierarchy must prioritize:

1. What the learner is learning
2. What ARIA currently knows about their progress
3. What the learner should do next
4. Why ARIA is recommending that action
5. The learning material and evidence supporting the interaction

Dark and light themes must communicate these priorities identically.

---

# Design Freeze

The following are frozen as the baseline theme direction:

- 🌑 Dark theme is the default.
- ☀️ Light theme is supported as a first-class alternative.
- Plus Jakarta Sans is the shared primary typeface.
- 8px spacing system is shared.
- Theme changes do not change UX behavior.
- Semantic tokens are required.
- WCAG-aware contrast and focus states are required.
- Reduced-motion support is required.
- Premium styling must remain restrained.
- Dark and light implementations must share the same component architecture.

Specific color values may evolve during implementation if accessibility or usability testing demonstrates a need, but any meaningful visual-system change should be documented rather than silently diverging from this baseline.

---

# Implementation Guidance

The frontend should implement themes using semantic CSS variables/design tokens rather than hard-coded theme-specific values inside individual components.

Example:

```css
:root {
  --color-background: ...;
  --color-surface: ...;
  --color-text-primary: ...;
  --color-accent: ...;
}

.dark {
  --color-background: ...;
  --color-surface: ...;
  --color-text-primary: ...;
  --color-accent: ...;
}
```

Components consume semantic tokens rather than knowing whether the application is currently dark or light.

---

# Acceptance Criteria

- [x] Dark theme defined as default.
- [x] Light theme defined as first-class alternative.
- [x] Shared visual language documented.
- [x] Theme-specific constraints documented.
- [x] Accessibility constraints documented.
- [x] Component parity rules documented.
- [x] Motion and reduced-motion rules documented.
- [x] Theme switching behavior documented.
- [x] R0 implementation constraints documented.

---

## Next

Use this document as the visual-theme baseline during frontend implementation in Phase 11.
