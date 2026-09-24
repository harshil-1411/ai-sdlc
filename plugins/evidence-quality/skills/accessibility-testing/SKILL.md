---
name: accessibility-testing
description: Test user interfaces against the team's accessibility conformance target (for example WCAG 2.2 AA) by combining automated scanning with the manual keyboard, screen-reader, zoom/reflow and contrast checks automation cannot make, and record the results as evidence. Use this whenever someone asks about accessibility, a11y, WCAG, Section 508, EN 301 549, the European Accessibility Act, screen readers, keyboard navigation, colour contrast, axe or Lighthouse accessibility scores, a VPAT or accessibility conformance report, or when a change adds or modifies UI. Read the conformance target and tools from the repository profile — never assume them.
---

# Accessibility testing

Read `.evidence/context/test-strategy.md` for the conformance target and the tools,
`design-system.md` for the component library (fixing an accessible component fixes
every screen that uses it), and `compliance.md` for any legal or contractual
accessibility obligation.

**If no conformance target is recorded, that is an `[ASK]`.** Do not assume "WCAG AA".
The level, version and legal driver change what counts as a pass.

## Automated scanning finds only part of the problems

Automated rule engines (axe-core and tools built on it, Lighthouse, Pa11y, platform
linters) reliably catch missing alt text, missing form labels, some contrast failures,
invalid ARIA and duplicate IDs. They **cannot** judge whether alt text is meaningful,
whether focus order makes sense, whether a custom widget works with a screen reader,
or whether an error is announced. Published estimates put automated coverage at well
under half of WCAG success criteria.

So: **a clean automated scan is necessary, not sufficient.** Never report a UI as
conforming on the basis of an automated scan alone.

## Automated layer

- **Lint** at authoring time where the framework has an a11y lint plugin.
- **Component tests**: scan each design-system component in each of its states
  (default, focus, error, disabled, open). This catches issues once, at the source.
- **Journey scans**: an automated scan on each critical page inside the E2E suite
  (`e2e-ui-testing`).
- **Blocks vs informs**: new violations at the conformance level in scope block on
  the PR. Best-practice and non-target-level findings inform. Existing violations
  follow the same baseline-and-ratchet approach as `static-analysis`.

## Manual layer, for every UI change

Record each check as pass, fail or not applicable for the changed screens:

1. **Keyboard only**: every interactive element is reachable with Tab/Shift+Tab and
   usable with Enter/Space/arrow keys. The focus order follows the visual order.
   The focus indicator is always visible. There are no keyboard traps. Modals trap focus
   while open and return it when closed. Skip links work.
2. **Screen reader**: use at least one screen reader and browser pair from the profile
   (for example NVDA or JAWS with Chrome/Firefox, VoiceOver with Safari, TalkBack on
   Android). Check that names, roles and states are announced correctly, headings and
   landmarks give a usable outline, dynamic updates and errors are announced (live
   regions), and images have meaningful or empty alt text as appropriate.
3. **Zoom and reflow**: 200% text zoom, and 400% / 320-CSS-pixel reflow, without
   loss of content or two-dimensional scrolling.
4. **Contrast and colour**: text and non-text contrast meet the target. No
   information is conveyed by colour alone. Check in every theme, including dark
   mode and high-contrast modes.
5. **Motion and timing**: `prefers-reduced-motion` is respected, nothing flashes
   more than three times a second, and time limits can be extended.
6. **Forms and errors**: labels are persistent (not placeholder-only), errors are
   specific, linked to their field and announced, and the required state is
   conveyed in a way other than colour.
7. **Target size** for pointer inputs meets the target level.

Automate what can be automated (focus order and keyboard paths can be scripted in
E2E), but a screen-reader walkthrough stays manual and carries the tester's name.

## People with disabilities

Where the profile schedules it, usability sessions with assistive-technology users
find what conformance checks miss. Record findings as issues against the
requirement, like any other defect.

## Evidence

Per change: automated scan reports (tool, version, rule set, pages/components
scanned), the manual checklist with tester name, date, assistive technology and
browser versions, and screenshots or recordings where the evidence profile requires
them. For a conformance report (VPAT/ACR), each success criterion links to the
evidence that supports its claim.

## Never

- Never claim conformance from an automated scan alone.
- Never assume the conformance level or version.
- Never fix a violation by hiding the element from assistive technology
  (`aria-hidden`, `role="presentation"`) when the element carries meaning.
- Never add ARIA where native HTML semantics would do. Bad ARIA is worse than none.
