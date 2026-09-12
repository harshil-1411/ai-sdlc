---
name: design-system-discovery
description: Establish what design system, component library, and UI conventions a repository actually uses, and record them so UI work extends the system instead of inventing parallel components. Use this during repository onboarding, before any UI or frontend planning, whenever a new component is proposed, and whenever someone asks what the design conventions are. Trigger on plain questions too: "what component library do we use", "what UI kit", "what CSS framework", "do we have a design system" — even when a README or style guide appears to already answer it. Do not assume a component library — find it.
---

# Design system discovery

The most common agent failure in UI work is inventing a component that already exists,
slightly differently. That is how design systems rot.

## Do not offer — run

Do not ask "would you like me to run design-system discovery?". If UI or frontend
work is planned, a new component is proposed, or someone asks what the design
conventions are, and no profile exists, run the survey and answer from its results.

## Find the source of truth

1. **Is the design system a package?** A dependency on an internal component library
   is the strongest signal. Record the package, its version, and where its
   documentation lives.
2. **Is it in-repo?** A `components/` or `ui/` directory with primitives, a theme file,
   design tokens (colour, spacing, typography scales), or a Storybook config.
3. **Is it in the design tool only?** If the canonical design exists in a design tool
   with no code counterpart, say so — that is a gap, and UI work will drift.
4. **What are the tokens?** Colour, spacing, typography, radius, elevation, breakpoints.
   Record where they are defined and whether raw values are permitted anywhere.
5. **What are the conventions?** Naming, file layout, styling approach, state handling,
   form patterns, error and empty states, loading behaviour.
6. **Accessibility baseline.** What standard is claimed, what is actually tested, and
   with what tooling. Record the gap honestly if there is one.

## Ask when unclear

If two component libraries are present, or if in-repo components duplicate the package
components, that is an `[ASK]` — it usually means a migration nobody finished, and the
answer changes how every UI plan is written.

## Output

Write `.evidence/context/design-system.md`. It must let a session answer, without
guessing: *does a component for this already exist, and if I need a new one, what does
it have to look like and where does it go?*

## Standing rule for all UI work

Extend before you add. A new component requires a written justification in `plan.md`
naming the existing components considered and why each was insufficient.
