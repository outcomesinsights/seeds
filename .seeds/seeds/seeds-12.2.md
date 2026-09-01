---
id: seeds-12.2
title: "Seeds as philosophy vs tool: the deliberation layer argument"
status: captured
type: exploration
parent: seeds-12
created_at: 2026-02-24T17:05:24.873205+00:00
updated_at: 2026-02-26T16:37:35.640571+00:00
tags:
  - existential
  - beads
  - philosophy
relationships:
  - target_id: seeds-89
    rel_type: relates-to
    created_at: 2026-02-24T17:05:24.873205+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Even if beads can technically do everything seeds does, there's an argument for keeping them separate based on cognitive purpose:

**The deliberation layer argument:**
When you're deciding *what* to build, you shouldn't be in the same mental space as *tracking* what to build. Mixing deliberation artifacts with implementation tasks muddies both. A developer looking at `bd ready` wants actionable work items, not half-formed questions about whether the architecture is right.

**Counter-argument:**
Beads' wisp/mol/proto phase system already creates this separation. Wisps are ephemeral thinking; molecules are committed work. The phase metaphor *is* the deliberation/implementation boundary, just expressed differently.

**The ConPort distinction (seed-c989.4):**
ConPort stores conclusions; seeds tracks the journey. Does beads track the journey? Its event/history system records state changes, but that's audit logging, not deliberation capture. Seeds' content field holds *prose reasoning* — the "why we considered X and rejected it" narrative. Beads issues have descriptions but aren't designed for evolving narrative content.

**Possible outcomes:**
1. Seeds remains separate — deliberation tool that hands off to beads
2. Seeds becomes a beads "mode" or plugin — same backend, different UX/philosophy
3. Seeds' ideas get absorbed into beads piecemeal — seeds withers
4. Seeds pivots to what beads can't do — domain-agnostic deliberation (RPGs, house projects, life decisions)
