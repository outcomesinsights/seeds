---
id: seeds-152.4
title: "Skill: 'seeds-to-beads' transition — prompt macro to frame the seeds→beads conversion workflow"
status: resolved
type: idea
parent: seeds-152
created_at: 2026-05-27T19:05:16.254643+00:00
updated_at: 2026-08-31T21:34:46.737334+00:00
resolved_at: 2026-08-31T21:34:46.737325+00:00
resolution: "Shipped (beads seeds-3p4, seeds-738, seeds-pfx) as the seeds-to-beads skill, carrying the pattern this seed described: separate actionable scope from context, decompose into self-contained beads with concrete paths and mechanical acceptance criteria, record dependencies, and land on a clean tree. Efficacy: none. Refinements arrived later as their own seeds rather than as tweaks — seeds-186 (intent-capture guidance) and seeds-w42l (consult the user on unsettled decisions), both still open."
tags:
  - skill
  - workflow
  - seeds-to-beads
  - transition
  - handoff
relationships:
  - target_id: seeds-186
    rel_type: relates-to
    created_at: 2026-06-24T16:47:32.139471+00:00
  - target_id: seeds-187
    rel_type: relates-to
    created_at: 2026-06-24T17:55:16.369148+00:00
  - target_id: seeds-w42l
    rel_type: relates-to
    created_at: 2026-08-27T14:19:31.963845+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

A second prompt-macro skill candidate. The user has a recurring workflow: after a deliberation reaches "we agree on a path forward," they want the relevant seeds turned into a set of beads (tasks) that a Sonnet-based agent can execute safely, successfully, and completely. Then land the plane to a clean working tree.

## The pattern

1. Identify which seeds are actionable (decisions, agreed scope) vs which are context (concerns, observations, refinements)
2. Decompose the actionable scope into small, self-contained beads
3. Each bead has:
   - Concrete file paths and content templates (no open design choices)
   - Mechanical acceptance criteria
   - Explicit dependencies on other beads
   - Cited seed IDs for deliberation context the executing agent might need
4. Set the dependency graph
5. Land the plane — commit any unstaged work into a clean tree

## Scope question (real tension with [[decision-skills-are-prompt-macro-scale]])

This workflow is multi-step and arguably workflow-engine scale. The prompt-macro stance from seeds-152.2 says skills are 3–10 lines of markdown framing — not orchestration.

Resolution: ship a thin prompt macro that *frames* the principles for the conversion task and lets the executing agent figure out the details. Something like:

> "The user has reached a point of agreement and wants the relevant seeds converted into beads for execution by a Sonnet-based agent. Follow these principles: decompose into self-contained beads; each bead should have concrete file paths, embedded content templates, and checkable acceptance criteria; cite seed IDs for context; set explicit dependencies; avoid leaving open design choices for the executing agent. After creating beads, land the plane (commit cleanly)."

If this framing is insufficient in practice — if Sonnet (or whichever model) repeatedly produces beads that violate these principles — that's evidence for either (a) tightening the macro or (b) escalating to workflow-engine scale. Until then, macro suffices.

## Status

Filed as stretch scope for the initial skill spike. Build the feedback skill first; if that goes smoothly, add this as a second macro under the same plugin.
