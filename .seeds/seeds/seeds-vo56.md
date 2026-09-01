---
id: seeds-vo56
title: Agents cite seed IDs with no gloss, and @aguynamedryan can't follow — the instruction to fix this exists and is being ignored
status: captured
type: concern
created_at: 2026-08-12T13:25:30.217775+00:00
updated_at: 2026-08-31T18:04:24.855543+00:00
tags:
  - ai-ux
  - agent-behavior
  - discoverability
  - seed-identity
  - recurring
relationships:
  - target_id: seeds-2
    rel_type: relates-to
    created_at: 2026-08-12T13:25:46.227486+00:00
  - target_id: seeds-32ai
    rel_type: relates-to
    created_at: 2026-08-12T13:29:18.335195+00:00
  - target_id: seeds-x6m0
    rel_type: relates-to
    created_at: 2026-08-27T13:41:48.728490+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan, 2026-08-12:

> "one of the issues I'm having with seeds is that it has a tendency to refer to various seeds by ID without explaining what they are as though I'm going to remember that... it doesn't provide me any other detail other than just referring to X521. I've tried in my user-level claude.md file to remind Claude I need a small amount of explanation about a given seed when it's asking me questions about it. So I can remember what it's talking about. But it's still not working really well. And so I wonder if there should actually be a proper field that it would surface for me each time."

His own objection to the field, raised in the same breath:

> "that context or summary might need to be recomputed every time seeds go to update the body of a seed. And those two items could end up getting out of sync... that seems to bring its own level of problems."

## The proposal is a data fix for a behavioural failure

Two measurements suggest a new field would not help.

**1. The summary field already exists. It is called `title`.** Across the real 270-seed database: median title length **74 characters**; only **2** titles under 25 chars, and both are test fixtures (`Child seed (depth 1)`). So 268 of 270 seeds already carry a descriptive one-liner. Sampling this session's own seeds — "seeds update -c silently replaces deliberation content — one character from -a, no warning, no confirmation" — the titles are not merely adequate, they are better glosses than a hand-written `summary` field would likely be, because they were written when the thought was fresh.

**2. The instruction already exists and is well-phrased.** `~/.claude/CLAUDE.md:161`: *"When you reopen or reference older work, restate its context — I almost certainly don't remember the seed or bead that produced it."* Plus lines 159-160: *"Don't make me run `bd show` / `seeds show` to follow along"* and *"Give me a one-line summary per item."*

So: the data is present, the rule is written, and the behaviour still fails. Adding a field would introduce the drift @aguynamedryan already flagged AND not address the actual failure, which is that an agent does not bother to look up context it already has cheap access to.

**I am the offender, and this session is the evidence.** Across a long working session I wrote `seeds-6hj5`, `seeds-tk5y`, `seeds-agk.2`, `seeds-819` at @aguynamedryan repeatedly, glossing them only sometimes and inconsistently — while his instruction to do exactly that sat in my context the whole time.

## Hypothesis for WHY the existing rule fails

It is phrased as a **principle**, which requires a judgement call at every mention: is this "older work"? Does this reference need "restating"? An agent mid-flow answers "no, they just read that two messages ago" — which is true in the moment and false by the next session, or after a compaction, or when @aguynamedryan steps away for an hour.

A **format rule** has no judgement step: *never emit a bare seed or bead ID in prose; always `seeds-tk5y ("the -c footgun")`.* Either the parenthetical is there or it visibly is not. Mechanical rules survive attention pressure in a way principles do not.

That is a hypothesis, not a finding — the instruction may be failing for some other reason (buried among many; user-level file weighted lower than project-level; too far from where the behaviour occurs).

## Options worth weighing (none decided)

1. **Format rule instead of a principle.** Rewrite the existing instruction as a mechanical output format with an example. Cheapest; testable next session; addresses the diagnosis above directly.
2. **Make it a trellis** — this project invented that mechanism for exactly this (a durable principle future work is trained along, living in always-on context). But note the failure is cross-project, so the project-level CLAUDE.md is the wrong home; the user-level file is right and is already where it lives.
3. **A `summary`/`gloss` field.** @aguynamedryan's original idea. Costs: duplicates `title`, drifts on every body edit (his own objection), and does not fix a behaviour that already ignores an existing field. Would only help if something FORCED its display.
4. **Force the display.** Make the seeds CLI expand bare IDs — e.g. `seeds show` and `prime` render `seeds-tk5y ("title")` — so the gloss is in the agent's context at the moment of use rather than requiring a lookup. Does not fix prose an agent types in chat, which is where the failure actually happens.
5. **Shorten the ask.** @aguynamedryan may not need a full restatement — just enough to recognise it. `id ("five-word gloss")` may be the whole fix, and is far more likely to be complied with than "restate its context."

## The uncomfortable part

Option 1 and option 5 are behavioural, and behavioural fixes have already failed once here. Preferring them because they are cheap risks repeating the same failure. Whether to escalate to something structural — a field, or forced display — is the real open question, and it turns on whether the existing instruction failed because it was *wrong* or because it was *ignorable*.
