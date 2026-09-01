---
id: seeds-45
title: "Concern: seed exploration may generate exponential growth without convergence"
status: captured
type: concern
created_at: 2026-01-28T20:59:43.550599+00:00
updated_at: 2026-02-24T17:05:56.024219+00:00
tags:
  - workflow
  - philosophy
relationships:
  - target_id: seeds-14
    rel_type: relates-to
    created_at: 2026-01-28T05:55:38.391240+00:00
  - target_id: seeds-46
    rel_type: relates-to
    created_at: 2026-01-28T20:59:43.550599+00:00
  - target_id: seeds-50
    rel_type: relates-to
    created_at: 2026-01-28T20:59:43.550599+00:00
  - target_id: seeds-86
    rel_type: relates-to
    created_at: 2026-01-28T20:59:43.550599+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Observed pattern: exploring 1 seed surfaces 3 new questions → 3 new seeds → exponential growth.

Possible interpretations:
1. **Greenfield effect** - mapping unexplored territory, will eventually converge as space fills in
2. **Design flaw** - tool incentivizes fragmentation without convergence pressure
3. **Natural deliberation** - thinking is divergent before convergent; early expansion is healthy

Test: at session end, check if seeds tell coherent story or scattered fragments.

Related: our 'favor smaller seeds' decision may amplify this effect.



---
**Completion criteria (consolidated from seed-15c1):**

From spec_first_pass.md, deliberation is (naively) complete when:
- All questions have been answered
- Constraints have been listed
- Proposed approaches have been evaluated (why adopted or not)

Review process pattern observed:
1. Ask for list of undecided/open items
2. First item surfaces with questions
3. Some questions relevant now, others backlogged
4. Process: asking questions → finding answers → brainstorming alternatives → listing constraints → exploring topic space

This is a possible 'convergence signal' - we know we're converging when these criteria start being met.



---
**Possible convergence mechanisms (consolidated from seed-5c7b):**

If exponential growth is a problem, possible mechanisms:
- **Collapse**: merge multiple seeds into one summary seed
- **Supersede**: mark seed as 'replaced by X'
- **Good enough**: explicit 'resolved with uncertainty' status
- **Periodic review**: prune/archive seeds no longer relevant

Current MVP has: resolve, abandon, defer. May need to expand this vocabulary.


---
**Beads provides a concrete convergence mechanism (Feb 2026):**

Beads v0.50+ added `supersedes` as a first-class relationship type with auto-close semantics — when seed A supersedes seed B, B is automatically closed. This is exactly the convergence pressure this seed identified as missing. Combined with `duplicates` (also auto-closes), beads now has two built-in mechanisms that reduce the active set without manual pruning.

For seeds, implementing `supersedes` would directly address the exponential growth concern: as deliberation converges, new decisions naturally supersede older explorations, closing them automatically. The growth isn't the problem — the lack of automated convergence is.
