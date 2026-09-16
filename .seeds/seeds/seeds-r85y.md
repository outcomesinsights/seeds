---
id: seeds-r85y
title: 'Test the degradation premise before building on it: make efficacy notes mandatory and sweep 90 days of closed beads'
status: captured
type: exploration
created_at: 2026-09-16T16:06:50.429626+00:00
updated_at: 2026-09-16T16:08:38.117943+00:00
tags:
  - efficacy
  - outcome-data
  - premise
  - falsifiability
  - adversarial-review
  - bead-specificity
relationships:
  - target_id: seeds-cpkr
    rel_type: relates-to
    created_at: 2026-09-16T16:08:37.923764+00:00
---

Both reviewers of seeds-cpkr reached this independently, without seeing each other:
**the degradation premise has zero recorded instances.** No worked example exists of a
decision that shipped out of a deliberation and turned out wrong because the judgment
that produced it was degraded. Compare `seeds-to-beads`, which justifies its own
existence with a dated, named failure (the 2026-08-31 `seeds-lcfa.1.1` over-claim).
That is the bar this project set for itself and the premise does not clear it.

The one real data point points the other way. `seeds-gf69`'s resolution carries a full
worked efficacy note — *"Tweaking needed: minor-to-moderate. Three planning misses, one
inherent unknown"* — and every miss is attributable to **bead specificity**, not to
degraded judgment:

1. A self-contradictory acceptance criterion: `grep -q 'x86_64-darwin' flake.nix` had to
   find nothing, while the same ruling required a comment explaining the removal. Any
   useful comment contains the string.
2. A removal audit that swept `*.nix` and `*.md` for references to a deleted derivation
   but not the `Justfile`, whose recipe hand-rewrote `version` and `hash` inside it.
3. A shape-assumption bug fixed in one place without sweeping for the same assumption
   elsewhere — the second site was strictly worse, renumbering whole databases.

Only the fourth item is classed as uncatchable by a better bead. `seeds-cb6r` reads the
same way: *"a genuine PLANNING MISS, not an inherent unknown."*

**The work.** Run `resolve-seeds-from-beads` in sweep mode over roughly 90 days of closed
beads with the efficacy note made MANDATORY rather than suggested, and classify each miss
on one extra axis: *would a cold reader with no sunk cost have caught this?* Coverage
today is a handful of seeds out of 333, so the instrument exists, is unfinished, and has
never been read as a series.

**What the outcome decides.** If roughly twenty beads produce no miss a cold reader would
have caught, the premise behind seeds-cpkr is in trouble and that proposal should scope
down to its outside-in / prior-art lens alone — which stands without any degradation
premise, because reinvention is a knowledge gap rather than a judgment gap. If the sweep
produces three to five such instances, seeds-cpkr is obviously worth building and this
seed has paid for itself.

Either way this is the instrument that makes seeds-cpkr falsifiable. Shipping a detector
with no outcome trace means that in six months nobody can answer "did it catch anything,"
which is the documented path to a gate everybody quietly stops running.

Accepted from the 2026-09-16 adversarial review of \[[seeds-cpkr]\], priority 1 in both
reviewers' rankings.
