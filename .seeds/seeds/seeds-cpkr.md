---
id: seeds-cpkr
title: Adversarial review of a deliberation before it becomes beads — Claude's judgment degrades, and seeds-to-beads is where a bad call stops being questionable
status: exploring
type: idea
created_at: 2026-09-16T14:39:34.309564+00:00
updated_at: 2026-09-16T15:07:01.591479+00:00
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
  - target_id: seeds-r8mb
    rel_type: questioned-by
    created_at: 2026-09-16T15:07:01.223028+00:00
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

- **A skill with no verb, for now.** `glean` and `winnow` are each a deterministic
  command plus a judging skill, and both commands say the same thing in their help text:
  *nothing here judges a candidate and nothing here calls a model.* This does not follow
  that pattern, because it has nothing deterministic to narrow: winnow's verb walks a
  692-edge graph and glean's diffs a 502KB transcript, while a `scrutinize` verb would
  only gather files the skill can gather itself — and the hardest lens, prior art on the
  web, cannot be narrowed deterministically at all.

  The argument for a verb was reproducible input, the same reason glean's skill bans
  context-gleaning. Not enough on its own. A verb can be added later if the skill turns
  out to need one; a verb written now would be a wrapper around `ls`.

- **Compose the existing verbs; do not re-derive their work by reading** (seeds-ryfk).
  Contradiction and staleness within the seed set come from `seeds winnow` scoped to
  those seeds; the capture gap comes from `seeds glean`, upstream. Necessary but not
  sufficient — winnow's contradiction flavor only compares seeds *already linked*, and a
  contradiction inside one session's output is exactly the case where nobody drew the
  edge. Composing narrows the reviewer's read; it does not replace it.

- **A missing glean warns, it does not block** (seeds-veup). Scrutinize says the session
  was never gleaned, then proceeds. A hard gate would make the tool unusable
  mid-deliberation, which is one of the moments it was asked for.

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
**glean runs first, scrutinize audits what got recorded.**

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

### Outside-in runs in two phases (seeds-xiqc)

1. **Propose blind.** Given ONLY the problem statement — not our solution — it proposes
   independently and reports what the outside world already does about this problem.
2. **Critique ours.** Then it is shown our solution and critiques it directly.

The order is the whole design. Its proposal exists before it has seen ours, so it cannot
be a graded reaction to ours; the divergence between the two is a real finding. And phase
two still buys the direct critique that a problem-only review never produces.

The cost is a commitment effect: having proposed, it may defend its own proposal rather
than assess ours on the merits. It must be told explicitly that phase one is not a
position to defend, and that agreeing with us in phase two is a valid outcome.

### The problem statement is written by the calling agent (seeds-r8mb)

Not by the user, and not captured as a first-class field at the start of a deliberation —
that would be a format change across ~18 stores for a speculative benefit.

Leakage is handled by instructing the reviewer rather than by trying to produce a clean
statement, because a clean one is not available: the calling agent is the same degraded
agent that produced the solution. The instruction has to go past "be skeptical of proposed
solutions," which only catches EXPLICIT leakage. The damaging leak is VOCABULARY — a
statement written after the fact inherits the terms and the carve-up of the solution we
landed on, and the reviewer never notices, because there is nothing to be skeptical of,
only a frame it accepts.

This seed demonstrates it. A problem statement written now would likely say "a deliberation
needs a review before it becomes beads" — which already presupposes a review, a discrete
step, and a gate at a hinge. A reviewer handed the actual problem (Claude's judgment
degrades in stretches, and bad calls get locked into beads deliberately protected from
re-opening) might not propose a review at all: it might propose making beads cheaper to
re-open, or not locking decisions in the first place, or checkpointing somewhere else.
That whole class of answer is invisible to a reviewer handed our framing, and skepticism
does not recover it.

Three requirements, in order of what they buy:

1. **Restate before proposing.** The reviewer states the problem in its own words first,
   and flags any term in the statement that presupposes an approach. The restatement is a
   cheap finding on its own — if it differs from ours, we learn something before a single
   proposal exists.
2. **Name nothing that does not already exist.** A mechanical test the calling agent
   applies to its own draft. "seeds-to-beads locks decisions and the executing agent will
   not re-open them" is a fact; "the review step" is leakage. Catches most vocabulary
   leaks without judgment.
3. **Be deeply skeptical of any solution the statement proposes**, and say so explicitly.

Good enough, not clean — the reviewer is told to treat the statement as contaminated and
to say where.

## The uncomfortable part

The premise is that Claude degrades in stretches. A reviewer running on the same model in
the same stretch is degraded too. What actually survives that, honestly:

- **Fresh context** — removes sunk cost in the conclusion. Real, and independent of
  degradation.
- **Web lookup** — imports information from outside the session entirely. Real.
- **Two independent reviewers** — a weak vote, but better than one.
- **Composed deterministic verbs** (`winnow`, `glean`) — do not degrade at all. This is
  an argument for pushing as much of the review as possible into them.
- **"Adversarial" as a prompt adjective** — survives nothing on its own.

This raises the floor. It does not guarantee one, and the design should not be written
as though it does.

## Running it (recovered by glean, 2026-09-16)

- **The session that deliberated cannot run the review.** Both reviewer roles have
  preconditions that session fails by construction: inside-out needs fresh context with no
  sunk cost in the conclusion, and outside-in phase one must not have seen our solution.
  The deliberating agent has seen all of it. So the skill dispatches subagents with clean
  context — it does not review in-line — and that is a hard requirement, not a preference.
  It is also the one requirement most likely to be quietly skipped, because reviewing
  in-line is cheaper and looks identical in the output.
- **Do not deliberate further before running it.** Every additional settled decision is
  more of our vocabulary for the reviewer to argue against, and the questions most worth
  asking are the ones a blind proposal might reach on its own. Settling "is a review even
  the right shape" before phase one destroys the experiment. The review is a thing to run
  EARLY on a converged deliberation, not after polishing it.
- **The framing itself is authored by the agent under suspicion.** In this deliberation
  every question and every option menu was written by the assistant; the user ruled, and
  some of those rulings changed the design — but he chose from lists one agent composed.
  That is the blindness the proposal targets, operating on the proposal. It is an argument
  for running the review early and for weighting phase-one divergence heavily.

## Worked test: the problem statement for this seed, written under rule 2

Rule 2 says the statement may name nothing that does not already exist. Applied to this
seed's own problem, that produces:

> Claude's output quality varies over time. There are stretches where its judgment is
> measurably worse and it makes calls that do not hold up, and neither the model nor the
> person working with it reliably notices during the stretch.
>
> Deliberation in this project is captured with `seeds`: a session produces seeds holding
> decisions and their rationale, plus questions attached to them. When the user is
> satisfied, the `seeds-to-beads` skill converts that deliberation into beads. Beads carry
> each locked decision *with its rationale*, explicitly so the agent executing the bead
> will not re-open it — the skill's own text names re-opening a locked decision as the
> failure it exists to prevent. Execution then happens in a worktree, by a Sonnet agent,
> alone, with no one to ask.
>
> What follows from that today:
>
> - A decision made during a degraded stretch is indistinguishable in the corpus from one
>   made well. Both are a seed body stating a conclusion with a rationale.
> - `seeds-to-beads` propagates it faithfully, and the rationale it attaches actively
>   discourages the executing agent from questioning it.
> - `seeds winnow` can find contradictions, but only between seeds already linked, and
>   only as a corpus-over-time audit. `seeds check` and `seeds doctor` are about files and
>   store health. Nothing in the toolchain compares a decision against anything outside
>   the session that produced it.
> - Nothing in the toolchain consults the outside world at all. A session can spend itself
>   re-deriving something that already ships as a flag on an existing tool, and the corpus
>   will record the derivation as a sound decision.
> - The user does not read seed or bead bodies; he rules on what is put in front of him.
>   A bad call nobody surfaces is not caught downstream by a human reader.
>
> When this goes wrong, the bad call reaches shipped code carrying the authority of a
> settled decision, and the machinery built to protect good decisions from churn protects
> this one just as well.

**The rule is usable.** It is a real constraint and it is writable against — it forces
prose about symptoms and existing machinery, which is what was wanted.

**Where it bit.** Every attempt to write "before the handoff" or "at the hinge" had to be
dropped. That temporal framing presupposes a checkpoint, and a checkpoint is not a thing
that exists — it is a location our solution invented. The rule caught it each time.

**It got longer, not shorter.** With no solution to gesture at, the failure has to be
enumerated instead of alluded to. That is a feature.

**It exposed two things our framing hid.** First, that the user does not read bodies — a
fact about the human loop our design assumed silently, and one that opens answers we never
considered, like changing what gets surfaced to him rather than adding an agent. Second,
that "nothing consults the outside world" is a property of the whole toolchain, not of this
moment — which suggests the fix may not belong at `seeds-to-beads` at all. A blind reviewer
handed this statement would plausibly not propose a review step.

**The limitation found.** Rule 2 constrains vocabulary, not emphasis. Which existing facts
went into the statement was still chosen by the agent that has the solution in mind, and a
different agent would have listed different ones. Selection leakage survives the rule
intact, and rule 1 — restate and flag presupposing terms — is what has to catch the residue.

## Still open

- Nothing blocking. Ready to promote to beads when the user says so.

## Related

`seeds winnow` audits the thinking — neglect, contradiction, staleness, outcome — but it
audits the *corpus over time*, not a *session's conclusions at the moment of handoff*,
and it does no outside-world lookup at all. Different instrument, different moment;
scrutinize now composes it rather than competing with it.
