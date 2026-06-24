---
name: resolve-seeds-from-beads
description: Use after an implementation session, once the user is satisfied with the shipped feature, to close the seeds->beads loop — reconcile what actually shipped against the deliberation, capture learnings and an efficacy note back into the originating seeds, then resolve them.
---

# Beads done → resolve the seeds

The feature built from a seeds→beads handoff is finished and the user is satisfied. Close the loop back to deliberation. This is the symmetric bookend of the `seeds-to-beads` skill: that skill carried intent *out* to execution; this one carries what was learned *back* before resolving.

Work through it once, with the user, when invoked. Do not adopt it as a default for later turns.

## 1. Find the originating seeds

Recover which seeds this work came from — read the completed beads' `Source: seeds-NNN` lineage, or ask the user which seeds the feature traces back to. `seeds show` each to recall what was deliberated and concluded.

## 2. Reconcile deliberation against what shipped

Compare the seeds' conclusions with what was actually built — the beads' outcomes, the real diff, and any tweaks or last-minute changes made mid-implementation. Surface each meaningful divergence to the user.

For divergences worth keeping, **append** them to the relevant seed with `seeds update <id> --append` — never `-c/--content`, which *replaces* and would destroy the original deliberation. Both the original reasoning and "what we actually did in the end" should stay legible. Propose the reconciliation; let the user confirm it. Capture only what's genuinely new — don't restate what the seed already says.

## 3. Capture an efficacy note

For the feature (or per seed), record a short, honest note on how the planning held up:

- **Tweaking needed?** none / minor / significant.
- **If so, was it catchable in planning?** planning-miss (a better bead would have caught it) vs inherent unknown (only discoverable by building it).
- **What a better bead would have said** — one line, when there's a lesson worth carrying forward.

Qualitative capture, not a metric (see seeds-185).

## 4. Resolve

Resolve each seed with `seeds resolve <id> -r "<outcome + efficacy note>"`. Resolve children before parents — a seed with unresolved children is blocked. Leave genuinely open threads unresolved rather than forcing closure.
