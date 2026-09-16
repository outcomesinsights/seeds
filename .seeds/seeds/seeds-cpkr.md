---
id: seeds-cpkr
title: Adversarial review of a deliberation before it becomes beads — Claude's judgment degrades, and seeds-to-beads is where a bad call stops being questionable
status: exploring
type: idea
created_at: 2026-09-16T14:39:34.309564+00:00
updated_at: 2026-09-16T14:52:43.517505+00:00
tags:
  - adversarial-review
  - seeds-to-beads
  - quality-gate
  - deliberation
  - prior-art
  - agent-degradation
relationships:
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-09-16T14:39:44.136175+00:00
  - target_id: seeds-veup
    rel_type: questioned-by
    created_at: 2026-09-16T14:52:42.350237+00:00
  - target_id: seeds-xiqc
    rel_type: questioned-by
    created_at: 2026-09-16T14:52:42.770752+00:00
  - target_id: seeds-ryfk
    rel_type: questioned-by
    created_at: 2026-09-16T14:52:43.175112+00:00
---

Claude's judgment is not stable over time. It goes through stretches where it gets
noticeably dumber and starts making bad calls — and a deliberation session is exactly
where that damage is cheapest to catch and most expensive to miss, because every bad
call gets laundered into a bead and then into shipped code, carrying the authority of
"we decided this."

The proposal: an adversarial review over a converged deliberation and the decisions it
produced — asked as a question at the start of `seeds-to-beads`, and invocable at any
other time.

## Why this moment

`seeds-to-beads` is the hinge. Before it, everything is still thinking and cheap to
revise. After it, the decisions are load-bearing: beads quote locked decisions with
their rationale explicitly so the executing agent *won't* re-open them. That is correct
design — and it means a bad call that gets past this point is deliberately protected
from second-guessing all the way to merge.

## Settled

- **A question, not an automatic step.** Asked at the start of `seeds-to-beads`; the
  user decides whether the deliberation was weighty enough to be worth the review.
  Also invocable directly, at any point in a deliberation.

- **Output is a report, nothing else.** Findings are triaged by the user, accepted or
  rejected, and only then written back — as new seeds or as updates to existing ones.
  The reviewer has NO write authority to the corpus.

  The argument is stronger than convenience: the reviewer is also Claude, running on
  the same model in the same degraded stretch. A reviewer that can write to the corpus
  is the original problem one layer up, with more authority. No write access is the
  containment.

- **`seeds ask` is an output of triage, not of review.** An accepted finding that is
  genuinely still open becomes a question on the seed; an accepted finding that is
  settled becomes a body update. This is what keeps question volume from getting
  obnoxious — it is bounded by what the user accepts, not by what the reviewer emits.

- **Allowed to come back empty**, and worth counting: a reviewer that never comes back
  empty is a rubber stamp pointed the other way.

- **Verb + skill, following the house pattern.** `glean` and `winnow` are each a
  deterministic command plus a judging skill, and both commands say the same thing in
  their help text: *nothing here judges a candidate and nothing here calls a model.*
  So `seeds scrutinize` assembles the dossier — the seed set, their links, questions
  still open, beads already citing them — and stops. The skill dispatches the reviewers
  and presents findings.

  Wrinkle worth naming: winnow's verb walks a 692-edge graph and glean's diffs a
  transcript, so each has real narrowing to do. Scrutinize's hardest lens — prior art
  on the web — has no deterministic narrowing at all, so its verb may be thin. It still
  earns its place for the reason glean's skill bans context-gleaning: it makes the input
  reproducible, instead of the reviewer working from whatever is left in an agent's head.

## The transcript question, and the correction it forced

An earlier framing of this seed proposed feeding the reviewer the session transcript,
"because the reasoning that never made it into a seed is where the bad calls hide."
That framing is unnerving for the right reason — if the deliberation is being captured
properly, there should be nothing in the transcript that is not in the corpus.

Both halves are true, and the resolution is that **the capture gap already has an
instrument**. `seeds glean` exists entirely for it: it reads the transcript for questions
raised, decisions with rationale, figures somebody measured, and corrections the user
made, then subtracts everything a seed already says. Its docstring puts one ordinary
session at 502KB across 256 turns. Its skill forbids gleaning from the agent's own
context, because summarization drops exactly what glean exists to recover — exact
figures, verbatim quotes, and things mentioned but never acted on.

So scrutinize should NOT take a transcript; it would rebuild glean badly. The boundary:
**glean runs first, scrutinize audits what got recorded.** At most, scrutinize notices
the session was never gleaned and says so before it starts. That makes "all the reasoning
is already in the seeds" an enforceable precondition rather than an aspiration — and lets
scrutinize assume a complete corpus because something upstream checked.

## The lenses, and how many reviewers

Two reviewers, split on tooling and on required ignorance — not one, and not one per lens:

- **Outside-in** — established best practice (including practice already established in
  this repo or fleet: trellises, briefings, prior seeds), and existing solutions on the
  web: designs, decisions, libraries, tools. Needs web search. Benefits from knowing
  nothing about our habits.
- **Inside-out** — gaps in what we actually settled, two seeds pointing in different
  directions, acceptance criteria that cannot be made mechanical without a definition
  nobody picked, and reasoning that does not survive a cold re-read by an agent with no
  sunk cost in the conclusion. Needs the seeds read closely. No web.

One agent holding all the lenses budget-splits and produces one shallow finding per lens,
because it is filling in a form. One agent per lens makes the two outside lenses and the
two inside lenses each do the same reading twice, and hands triage a pile of duplicates.
Two is where the tooling and the required ignorance genuinely differ.

They must not see each other's findings, or the second anchors on the first.

**The outside reviewer should be given the problem, not our solution.** Show it our
decision and it grades our decision. Show it only what we were trying to do and it
proposes independently — and the divergence between its proposal and ours IS the finding.

## The uncomfortable part

The premise is that Claude degrades in stretches. A reviewer running on the same model in
the same stretch is degraded too. What actually survives that, honestly:

- **Fresh context** — removes sunk cost in the conclusion. Real, and independent of
  degradation.
- **Web lookup** — imports information from outside the session entirely. Real.
- **Two independent reviewers** — a weak vote, but better than one.
- **"Adversarial" as a prompt adjective** — survives nothing on its own.

This raises the floor. It does not guarantee one, and the design should not be written
as though it does.

## Related

`seeds winnow` audits the thinking — neglect, contradiction, staleness, outcome — but it
audits the *corpus over time*, not a *session's conclusions at the moment of handoff*,
and it does no outside-world lookup at all. Different instrument, different moment.
Worth deciding whether scrutinize's inside-out lens should just call winnow's
contradiction flavor scoped to the seed set rather than re-deriving it.
