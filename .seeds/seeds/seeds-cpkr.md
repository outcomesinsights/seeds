---
id: seeds-cpkr
title: Adversarial review of a deliberation before it becomes beads — Claude's judgment degrades, and seeds-to-beads is where a bad call stops being questionable
status: captured
type: idea
created_at: 2026-09-16T14:39:34.309564+00:00
updated_at: 2026-09-16T14:39:44.137045+00:00
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
---

Claude's judgment is not stable over time. It goes through stretches where it gets
noticeably dumber and starts making bad calls — and a deliberation session is exactly
where that damage is cheapest to catch and most expensive to miss, because every bad
call gets laundered into a bead and then into shipped code, carrying the authority of
"we decided this."

The proposal: at the end of a seeds feedback-loop session — **after the deliberation
has converged, before `seeds-to-beads` writes anything** — prompt the user to run an
adversarial agent review over the deliberation and the decisions it produced.

## What the reviewer looks for

Four distinct lenses, not one vague "critique this":

- **Gaps in the decisions** — what did we settle that we only *think* we settled?
  Questions raised and never landed, two seeds pointing in different directions,
  acceptance criteria that can't be made mechanical without picking a definition
  nobody picked.
- **Established best practice we missed** — is there a well-known way to do this that
  the deliberation never mentioned? Including practice already established *in this
  repo or this fleet* (trellises, briefings, prior seeds) that the session was blind to.
- **Existing solutions on the web** — designs, decisions, libraries, tools, prior art.
  Did we spend a session re-deriving something that ships as a flag on an existing tool?
- **Bad calls made under degradation** — reasoning that doesn't hold up when re-read
  cold by an agent that wasn't in the room and has no sunk cost in the conclusion.

The last one is the real motivation. The others are the ordinary value; this one is
why it needs to be *adversarial* and *fresh-context* rather than a self-review pass.
An agent that produced the reasoning is the worst judge of whether the reasoning is good.

## Why this moment

`seeds-to-beads` is the hinge. Before it, everything is still thinking and cheap to
revise. After it, the decisions are load-bearing: beads quote locked decisions with
their rationale explicitly so the executing agent *won't* re-open them. That's correct
design — and it means a bad call that gets past this point is deliberately protected
from second-guessing all the way to merge.

So the gate belongs here, and it should be a **prompt, not an automatic step** — the
user decides whether the deliberation was weighty enough to be worth the review.

## Open questions

- **Where does it live?** A step inside the `seeds-to-beads` skill (prompt before the
  analysis pass), a separate skill the user invokes, or a `seeds` subcommand — something
  like `seeds scrutinize <ids>`? A subcommand means it also runs on a deliberation that
  is never going to become beads.
- **What does it take as input?** A seed set? Everything touched this session? The
  session transcript too — the reasoning that never made it into a seed is where the
  bad calls hide?
- **What does the output become?** New seeds (a finding is deliberation, so it should
  be capturable as one), questions attached to the reviewed seeds (`seeds ask`), or a
  report the user reads and rules on? Probably: findings the user triages, and only the
  ones he accepts get written back.
- **How many reviewers, and how independent?** One agent with four lenses, or several
  with one lens each? The web-search lens has different tooling needs than the
  gaps-in-decisions lens.
- **Does it need to be able to say "this is fine"?** A reviewer that always finds
  something is a reviewer that gets ignored. It has to be allowed to come back empty.

## Related

`seeds winnow` already audits the thinking — neglect, contradiction, staleness, outcome
— but it audits the *corpus over time*, not a *session's conclusions at the moment of
handoff*, and it does no outside-world lookup at all. This is a different instrument
pointed at a different moment. Worth checking whether it's a winnow flavor or its own
thing.
