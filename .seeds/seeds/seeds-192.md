---
id: seeds-192
title: Optional 'surface the unknown-unknowns' interview pass as a seed hardens toward a feature (from Thariq's map-is-not-territory / Fable field guide)
status: captured
type: idea
created_at: 2026-07-10T17:16:31.713033+00:00
updated_at: 2026-08-31T20:02:45.943660+00:00
tags:
  - ai-ux
  - deliberation
  - unknown-unknowns
  - guided-interview
  - discovery
  - spec-boundary
  - generalization
  - external-inspiration
  - 2026-07-10
relationships:
  - target_id: seeds-151
    rel_type: relates-to
    created_at: 2026-07-10T17:17:20.144954+00:00
  - target_id: seeds-118
    rel_type: relates-to
    created_at: 2026-07-10T17:17:20.280514+00:00
  - target_id: seeds-147.1
    rel_type: relates-to
    created_at: 2026-07-10T17:17:20.425069+00:00
  - target_id: seeds-193
    rel_type: relates-to
    created_at: 2026-07-10T17:17:20.548111+00:00
  - target_id: seeds-194
    rel_type: questioned-by
    created_at: 2026-07-10T17:17:27.612357+00:00
  - target_id: seeds-195
    rel_type: questioned-by
    created_at: 2026-07-10T17:17:27.732993+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Could the "finding your unknowns" spirit from two Anthropic-adjacent articles become an *optional deepening pass* in seeds — a moment where, before a seed hardens into a feature, the tool interviews the user to surface unknown-unknowns and question assumptions? Captured as a rich area to explore later, NOT a decision.

## Provenance

Two explainX.ai articles (both fully present, read 2026-07-10):

- https://www.explainx.ai/blog/map-is-not-territory-fable-5-thariq-unknowns-2026
- https://www.explainx.ai/blog/field-guide-to-fable-thariq-shihipar-anthropic-ai-engineer-2026

Both are *secondhand recaps* of Thariq Shihipar's (Anthropic, Claude Code) AI Engineer talk + his own "field guide." Verify against his primary source before designing around specifics. The concrete method they describe:

- A known/unknown 2x2 (known-knowns = explicit content; known-unknowns = acknowledged gaps; unknown-knowns = intuitive taste, "know it when I see it"; unknown-unknowns = blind spots). Seeds today only serves the top-right cell (an attached question is a *known* unknown). The bottom row — taste you can't phrase, and blind spots you don't know to ask about — is what seeds has no mechanism to surface.
- Copy-paste prompts: a "blind spot pass" ("help me figure out my relevant unknown unknowns"), an "architecture interview" ("Interview me about this feature. Prioritize questions that would change the architecture."), and "give me four divergent framings to react to" (targets the taste quadrant).

## The proposal (one possible shape)

An OPT-IN guided pass that fires when a seed graduates from half-baked idea toward feature implementation — plausibly a last pass right before seeds-to-beads, and/or a deepening mode on `explore`. Its output would be seeds-native objects: new questions, considerations, surfaced assumptions — not a spec document. Explicitly NOT in the low-friction `jot` capture path.

## @aguynamedryan's angle (captured faithfully)

- Seeds stays a repository for half-baked ideas. This pass would apply only at the hardening transition, as an "have we dotted the i's" step.
- The current approach — flesh out in seeds, make high-level decisions, then lean on the "seeds-to-beads magic" — already gets the specification pretty much right *without* a dedicated intermediary tool. @aguynamedryan has NOT felt the need to step back from that. So this is at most a refinement of the deliberation phase, not a demand for a new spec tool.
- Genuine uncertainty: is this deliberation, or has it crossed into specification territory? @aguynamedryan senses seeds may be "right on the edge of where seeds ends and something like a specification tool begins," and has long wondered about a possible intermediary between seeds and beads (idea -> concrete spec -> implementation steps as a spectrum). This idea pokes at that boundary. (See the already-open seeds-118 / seeds-122 on a spec-ready graduation state.)
- STRONG conviction: seeds is a deliberation tool for *many kinds of projects*, not just software — a deliberation tool about anything, not only about software. The articles are software-engineering-heavy and existing-code-heavy; @aguynamedryan takes that as good pushback. Any adaptation must extract the *spirit* (guided interview, surface unknown-unknowns, question assumptions), not the code-specific tactics. See the shower-leak proof case (linked) for a non-software instance.

## How this lands against the existing DB (it was largely anticipated)

- External corroboration of seeds-151: "agents treat user context as gospel" IS the map-is-not-territory thesis, arrived at independently. An Anthropic Claude Code engineer reaching the same conclusion strengthens 151.
- Rides on seeds-151.1: agents don't surface their own doubts unless explicitly invited — the article's blind-spot-pass prompts are exactly such invitations. By 151.1's own heuristic ("does this help the agent *raise concerns* or just *retain context*? the first is more valuable"), an unknowns pass is the more-valuable kind of feature.
- The boundary question is seeds-118 / seeds-122 (spec-ready graduation). Working hypothesis: an unknowns pass is deliberation-deepening, sits *upstream* of the spec, and would make the seeds-to-beads output better rather than demanding a third tool — i.e., it reinforces the current two-tool approach.
- Counter-risk is seeds-147.1: a guided interview can over-channel reasoning and suppress fruitful exploration, or "lead the witness." Keep it questioning-oriented, not answer-prescribing.

## Caveats / concerns

1. Software-heavy source. The article's "read existing code as your map" and the PR "For agents" block are *specification* artifacts, not deliberation. Import only the questioning spirit, whose outputs are domain-agnostic (questions, assumptions), not the code tactics.
2. Boundary drift. Risk of nudging seeds into spec-tool territory. Proposed line: seeds surfaces and *holds open* questions; it should not become where you author the implementation-ready spec.
3. Low-friction ethos. Must be opt-in at the hardening boundary; never in `jot`.
4. Over-channeling (seeds-147.1). A structured interview could suppress exploration. Prefer "here are angles you may not have considered" over "here is what you should decide."
5. Secondhand source (see Provenance).

## Disposition

Captured as a rich, interesting area @aguynamedryan wants to explore *eventually*, not now. Open questions attached below. The two live ones: does it belong in seeds at all (or is it spec territory), and if it belongs, where in the lifecycle does it live.
