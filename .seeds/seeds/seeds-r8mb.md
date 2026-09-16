---
id: seeds-r8mb
title: 'Who writes the problem statement that outside-in phase one depends on, and how is our solution kept out of it? The seeds are solution-shaped by the time scrutinize runs, so a statement distilled from them leaks our answer and collapses phase one back into grading. Options: the skill drafts it and the user confirms; the user writes it; or it is captured at the START of a deliberation, before a solution exists, as a first-class field.'
status: resolved
type: question
created_at: 2026-09-16T15:07:01.221569+00:00
updated_at: 2026-09-16T15:20:35.864545+00:00
resolved_at: 2026-09-16T15:20:35.864533+00:00
relationships:
  - target_id: seeds-cpkr
    rel_type: questions
    created_at: 2026-09-16T15:07:01.223028+00:00
---

The calling agent writes it. The user does not, and seeds does not grow a problem-statement
field at the start of a deliberation — that is a format change across ~18 stores for a
speculative benefit.

Leakage is handled by instructing the reviewer, not by trying to produce a clean statement.
But the instruction has to be stronger than "be skeptical of proposed solutions," because
that only catches EXPLICIT leakage — a statement that says "we need a review step" is
obvious and easy to discount. The damaging leak is VOCABULARY: a statement written after
the fact inherits the terms and the carve-up of the solution we landed on, and the reviewer
never notices because there is nothing to be skeptical of, only a frame it accepts.

This seed demonstrates it. A problem statement written now would likely say "a deliberation
needs a review before it becomes beads" — which already presupposes a review, a discrete
step, and a gate at a hinge. A reviewer handed the actual problem ("Claude's judgment
degrades in stretches, and bad calls get locked into beads that are deliberately protected
from re-opening") might not propose a review at all. It might propose making beads cheaper
to re-open, or not locking decisions in the first place, or checkpointing somewhere else
entirely. That whole class of answer is invisible to a reviewer handed our framing, and
skepticism does not recover it.

So three requirements, in order of how much they buy:

1. **The reviewer restates the problem in its own words before proposing anything**, and
   flags any term in the statement that presupposes an approach. The restatement is itself
   a cheap finding: if it differs from ours, we have learned something before a single
   proposal exists.
2. **The statement may name nothing that does not already exist.** A mechanical test the
   calling agent can apply to its own draft. "seeds-to-beads locks decisions and the
   executing agent will not re-open them" is a fact. "the review step" is leakage. This
   catches most vocabulary leaks without judgment.
3. **Be deeply skeptical of any solution the statement proposes**, and say so explicitly —
   the original instruction, kept for the explicit case.

Accepted as good-enough rather than clean. The calling agent is the same degraded agent
that produced the solution, so it cannot write a genuinely uncontaminated statement; the
mitigation is that the reviewer is told to treat the statement as contaminated and to
say where.
