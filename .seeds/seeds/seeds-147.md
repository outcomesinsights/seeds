---
id: seeds-147
title: Lodestone / north-star marker for foundational project pillars
status: resolved
type: idea
created_at: 2026-05-22T16:59:50.397251+00:00
updated_at: 2026-08-31T21:34:46.502460+00:00
resolved_at: 2026-08-31T21:34:46.502451+00:00
resolution: "Shipped as 'seeds trellis' (bead seeds-d13). Efficacy: no tweaking to the mechanism; one divergence, and it is only the name — 'lodestone' became 'trellis', with the garden-term rename still live in seeds-198. What a better bead would have said: name it before building, since the verb is user-facing and the rename cost more than the feature. The risk this seed's child seeds-147.1 raised (lodestones over-channelling agent reasoning) is a usage question that only answers itself over time; it stays open deliberately."
tags:
  - meta
  - workflow
  - status
  - decision-weight
relationships:
  - target_id: seeds-148
    rel_type: questioned-by
    created_at: 2026-05-22T16:59:56.911511+00:00
  - target_id: seeds-149
    rel_type: questioned-by
    created_at: 2026-05-22T17:00:01.269462+00:00
  - target_id: seeds-150
    rel_type: questioned-by
    created_at: 2026-05-22T17:00:05.623267+00:00
  - target_id: seeds-151
    rel_type: relates-to
    created_at: 2026-05-22T17:13:11.356792+00:00
  - target_id: seeds-x6m0
    rel_type: relates-to
    created_at: 2026-08-27T13:41:49.018264+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Idea: introduce a marker — call it "lodestone" or "north star" — for seeds that represent foundational pillars of a project. Not a hard guardrail, but a heavily-weighted reference point that future deliberation should consult and respect.

## What it is

A lodestone is a seed that captures a load-bearing principle for a project. When a new idea, decision, or question "brushes against" a lodestone, seeds should surface that lodestone so the deliberator weighs it consciously. It biases the conversation toward coherence with established pillars without forbidding deviation.

## Examples (from real projects)

- **code_set_catalog**: a code set is only allowed a single vocabulary ID. All codes must share a vocabulary because a code set is the manifestation of a single clinical idea in that vocabulary. The catalog is a *clinical idea* catalog; code sets are renderings of those ideas per vocab. This is the heart of the project.
- **jigsaw**: responsible for *extracting* information from a claims database, but not for performing analysis. Analysis lives elsewhere.
- **seeds (this project)**: well-suited to warehousing half-baked, very nascent ideas — like this one. The friction floor is intentionally low.

## Why it matters

Projects accumulate ideas faster than they accumulate principles. Without a way to flag the principles, every new idea has to re-derive (or accidentally violate) the foundations. A lodestone marker says: "before resolving anything in this neighborhood, look here."

## Open shape — not yet decided

- Is lodestone a new **status** (alongside captured/exploring/deferred/resolved/abandoned)? Probably not — a lodestone is more permanent than a status; it persists past resolution.
- Is it a new **type** (alongside idea/question/decision/exploration/concern)? Plausible — feels closest to "decision" but elevated.
- Is it a **flag/marker** orthogonal to status and type? Likely the cleanest model — any seed can be promoted to lodestone.
- Or is it a **relationship** ("X is governed by lodestone Y")? Possibly, especially for surfacing during deliberation.

## What "given weight" might look like

- `seeds ready` and `seeds show` surface relevant lodestones for nearby work.
- `seeds prime` (AI context) emits the project's lodestones near the top.
- When resolving or abandoning a seed, prompt: "does this conflict with any lodestone?"
- Maybe a dedicated `seeds lodestones` view or `seeds north-stars` command.

## Promotion path

Lodestones probably emerge from resolved decisions or matured ideas, not from initial capture. A seed gets promoted to lodestone status after it's proven itself as load-bearing.

SHIPPED (2026-08, bead seeds-d13) — as `seeds trellis`, not "lodestone". The mechanism landed as designed: a matured seed is distilled into one weighted principle written into always-on project context (CLAUDE.md/AGENTS.md/README), and the seed resolves. Only the name diverged, and the naming question is still live in seeds-198 (sage/elder/garden-term rename).
