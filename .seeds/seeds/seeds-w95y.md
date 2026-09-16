---
id: seeds-w95y
title: Three stale, mutually inconsistent corpus measurements in winnow's own docs — the staleness detector cannot see its own docstring
status: captured
type: concern
created_at: 2026-09-16T16:07:25.002928+00:00
updated_at: 2026-09-16T16:08:40.022581+00:00
tags:
  - winnow
  - staleness
  - documentation
  - measurement
  - defect
relationships:
  - target_id: seeds-cpkr
    rel_type: relates-to
    created_at: 2026-09-16T16:08:39.818409+00:00
---

The corpus measurement quoted in winnow's own documentation is stale, and the repo
disagrees with itself about it in three places:

- `src/seeds/winnow.py:21` — "314 seeds and 692 edges — 692 comparisons rather than
  roughly 49,000"
- `src/seeds/cli.py:2327` — repeats the 692 figure in the command's help text
- `src/seeds/plugin/claude-plugin/skills/winnow/SKILL.md:45,58` — "314 seeds, 427 edges"

Measured live on 2026-09-16: `seeds winnow: 333 seed(s), 444 edge(s)`.

Three numbers, none of them current, in the documentation of the one flavor built to
catch **a conclusion resting on a figure that has moved**. Winnow's staleness flavor
exists for exactly this shape and cannot see its own docstring.

The figure is load-bearing where it gets quoted: it is the evidence that winnow "has
something deterministic to narrow," which is the comparison other design arguments lean
on. A 2026-09-16 deliberation took the largest of the three disagreeing numbers and used
it as current.

Worth fixing as a bead, and worth asking the broader question: a measurement embedded in
prose has no owner and no expiry. Whether these should be computed at runtime, asserted
by a test, or simply dated where they are written is the actual decision.

**The three figures were corrected 2026-09-16** to the live measurement (333 seeds, 444
edges, ~55,000 pairs avoided) and the two load-bearing ones now carry the date they were
measured, so the next reader can see how old the claim is instead of inferring it. Full
suite green afterwards: 1416 passed, 1 skipped.

That is the symptom treated, not the cause. The seed stays open on the real decision:
a measurement embedded in prose has no owner and no expiry, and dating it only makes the
staleness *visible* rather than impossible. Computing it at runtime in the help text, or
asserting it in a test that fails when the corpus moves past a tolerance, would both make
it self-maintaining — and both have costs (a help string that hits the disk; a test that
fails for a reason nobody did anything wrong to cause).

Found by the inside-out reviewer in the 2026-09-16 adversarial review of \[[seeds-cpkr]\].
