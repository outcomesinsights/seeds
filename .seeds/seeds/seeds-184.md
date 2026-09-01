---
id: seeds-184
title: "Investigation: how seeds' intent lands in beads, and whether bead efficacy is measurable"
status: captured
type: exploration
created_at: 2026-06-24T16:47:31.252459+00:00
updated_at: 2026-06-24T16:47:31.252471+00:00
tags:
  - intent
  - beads
  - seeds-to-beads
  - metrics
  - investigation
relationships:
  - target_id: seeds-185
    rel_type: questions
    created_at: 2026-06-24T16:47:31.691257+00:00
  - target_id: seeds-161
    rel_type: relates-to
    created_at: 2026-06-24T16:47:31.797077+00:00
  - target_id: seeds-89
    rel_type: relates-to
    created_at: 2026-06-24T16:47:31.897568+00:00
  - target_id: seeds-186
    rel_type: relates-to
    created_at: 2026-06-24T16:47:32.010657+00:00
  - target_id: seeds-w42l
    rel_type: relates-to
    created_at: 2026-08-27T14:19:32.196272+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Investigated 2026-06-23/24: what the seeds->beads handoff actually carries as "intent," and whether we can tell which intent format yields better implementations.

INTENT FORMATS seen in real beads (code_set_catalog + seeds' own .beads):
1. Pain/evidence -- motivation with concrete signal (counts, dates, bug instances). Good for deciding to DO the work; weak for the executor.
2. Locked-decision + rationale -- e.g. csc-65.1 "store {} not NULL -- avoids null guards." Pre-empts re-litigation; strongest executor signal.
3. Verbatim stakeholder voice -- quotes the user on taste/scope/UX calls (csc-zyk). Survives handoff better than paraphrase.
4. Sequencing justification -- "Why this issue exists / until this lands nothing builds on it." Helps the orchestrator order work.
Backbone across all: motivation + a citation back into the seed graph. ~63% of CSC beads carry seed lineage; explicit "## Why" headings are rarer (14/192 in CSC, 7/83 in seeds).

MEASURABILITY -- we CANNOT tell retrospectively which format implemented "better":
- No outcome variance in bead data: 190/192 CSC beads closed, 0 reopens, 0 comments anywhere, ~1 status transition each. Nothing to correlate against.
- Confounded anyway: rich-intent beads come from the deepest deliberations, which also got better scope + acceptance criteria. Intent format is a proxy for deliberation quality, not an isolated variable.
- close_reason is genre-poisoned: written as a victory lap ("shipped; specs green; merged"), not an honest retro. Divergence surfaces only when someone volunteered it -- e.g. csc-pj2: the bead assumed a "+ New Code Set" button that does not exist in a read-only alpha; the implementer caught it and re-placed the CTA. Exactly "implementation needed tweaking the planning could've caught" -- captured by accident, not design.

IMPLICATION: to learn whether beads are well-made, capture an honest efficacy note when the loop closes (seed resolution); the bead's own close_reason will not tell us. Open question attached.

A concrete instance of seeds-161 (we under-capture what we LEARNED by trying) and an application of seeds-89 (formalizing investigation capture). Handoff context: seeds-12. Provisional guidance from this was popped into the seeds-to-beads SKILL.md.
