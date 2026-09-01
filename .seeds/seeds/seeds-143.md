---
id: seeds-143
title: "Prime guidance: describe primitives, not prescribe workflows"
status: resolved
type: decision
created_at: 2026-05-18T16:44:28.520608+00:00
updated_at: 2026-08-11T19:49:09.069955+00:00
resolved_at: 2026-08-11T19:49:09.069946+00:00
resolution: "Shipped. Verified: src/seeds/prime.py carries the digest and suggest guidance the arc added (beads xgp — prime project digest with counts, Recently Updated, Active Exploration, Open Questions, Top Tag Clusters, --no-digest opt-out; and c4b — 'seeds suggest' with FTS5 BM25 ranking, --limit/--open-only/--json).\n\nThe principle this seed argued for — prime should describe primitives rather than prescribe workflows — is visible in what shipped: the digest reports state, and suggest answers a question; neither dictates a sequence.\n\nEFFICACY: not assessed. Implemented in an earlier session; grading planning I did not observe would be fabrication. Resolved on verified end-state."
tags:
  - prime
  - design-principle
  - ai-ux
  - documentation
  - prime-guidance
relationships:
  - target_id: seeds-87
    rel_type: relates-to
    created_at: 2026-05-18T16:44:28.615719+00:00
  - target_id: seeds-21
    rel_type: relates-to
    created_at: 2026-05-18T16:44:28.719220+00:00
  - target_id: seeds-142
    rel_type: relates-to
    created_at: 2026-05-18T16:44:28.805862+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Decision (2026-05-18):** `seeds prime` should describe primitives, not prescribe workflows. Behavior changes that alter command semantics belong; opinionated 'do X before Y' framing does not.

**Triggering instance:** When shipping seeds-c4b (`seeds suggest`), I added a `### Before Creating (avoid duplicates)` section to prime with editorial framing — 'the dedup primitive for incorporating transcripts/notes,' 'see prior deliberation history,' etc. User pushed back: 'Is that even relevant to include in prime?'

**Why the framing was wrong:**

1. **Workflow prescription, not primitive description.** It told the agent *when* and *why* to use suggest, not just *what it does*. That's the agent's situational judgment, not a property of the command.

2. **Overweights one use case.** The 'before-create dedup' framing makes transcript-incorporation feel like *the* workflow. In reality, one-off captures via `seeds jot` skip dedup entirely and that's fine. Sometimes you genuinely know an idea is new.

3. **Death-by-a-thousand-sections risk.** Every new primitive could spawn its own 'how to use this' section. Prime balloons. Agents skim past walls of advice. The static text we already have (Core Rules, What to Capture) is the maximum dose of opinion the format should carry.

4. **Redundant with the digest.** Now that seeds-xgp puts existing seeds in front of the agent at session start, suggest's role is situational — it shines during multi-item ingestion but the digest may already be enough for one-off captures. Hardcoding 'use suggest first' is over-prescription.

**What stays in prime:**

- Command listings (what exists, brief description of what it does)
- Behavior changes that would surprise an agent (e.g. `--allow-unknown-refs` exists because create/update now reject unknown ID refs)
- The pre-existing 'What to Capture' guidance — that's a project-wide capture philosophy, not a workflow for one command

**What doesn't:**

- 'Before X, do Y' workflow recipes
- Editorial framing about why a command matters
- Use-case narration ('the dedup primitive for incorporating transcripts')

**The fix applied:** Folded `seeds suggest`, `seeds search`, and `seeds recent` into the existing 'Finding Work' section as peers of `seeds ready` / `seeds questions` / etc. Dropped the 'Before Creating' header entirely. Reduced the validation note on `create` to one line ('Bodies referencing unknown <prefix>-N IDs are rejected; pass --allow-unknown-refs to override') — that's behavior documentation, not workflow.

**General principle going forward:** When adding a primitive to seeds, the prime change is *one line per command in the right existing section*. If you're tempted to add a new section explaining *when* to reach for a command, write that as a seed/doc and link it from somewhere else — not from prime.

**Relates to:** seeds-87 (dynamic prime — this constrains what the dynamic part should contain), seeds-21 (AI natural adoption — primitives are how agents naturally adopt; workflow narration gets ignored).
