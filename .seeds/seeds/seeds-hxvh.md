---
id: seeds-hxvh
title: seeds glean is blind to subagent transcripts — the glob is one level deep
status: captured
type: concern
created_at: 2026-09-16T16:06:50.817253+00:00
updated_at: 2026-09-23T16:02:47.119042+00:00
tags:
  - glean
  - transcripts
  - subagents
  - capture-gap
  - defect
relationships:
  - target_id: seeds-cpkr
    rel_type: relates-to
    created_at: 2026-09-16T16:08:39.351740+00:00
---

`seeds glean` cannot see subagent transcripts, so everything an agent works out in a
dispatched sub-agent is invisible to the capture instrument.

`list_transcripts` (`src/seeds/glean.py:156-175`) resolves the project's transcript
directory and then globs one level:

```
paths = sorted(
    (path for path in directory.glob(f"*{TRANSCRIPT_SUFFIX}") if path.is_file()),
    key=lambda path: path.stat().st_mtime,
)
```

A non-recursive glob. Sub-agent transcripts are written under a `subagents/`
subdirectory of the session, so they match nothing — including under `--all`, which is
supposed to be the historical catch-up pass.

**Why it matters more than it looks.** Dispatching sub-agents is now routine, and the
reasoning that happens inside one is exactly the material glean exists to recover: figures
somebody measured, a constraint stated once, a question raised and dropped. None of it
reaches the corpus except as whatever the parent agent chose to relay — and the glean
skill's own argument for existing is that summarization drops "exact figures, verbatim
user quotes, and things mentioned but never acted on."

Surfaced by the 2026-09-16 adversarial review of \[[seeds-cpkr]\], whose own two reviewers
are an instance: ~11k words of review reasoning, unreachable by glean, preserved only
because the parent extracted the transcripts by hand.

**Second defect found in the same neighbourhood, 2026-09-17** (bead `seeds-kmx`, fixed in
8c61e10): `project_slug` preserved underscores while Claude Code converts them to hyphens,
so glean resolved the transcript *directory* wrong for every repo with an underscore in
its path — most of the fleet. Different bug, same surface: transcript discovery has now
been wrong about *where* to look and wrong about *how deep* to look.

Both survived for the same reason, and it is the reason worth keeping. The underscore rule
was asserted by a test — `test_project_slug_flattens_the_path_and_keeps_underscores` —
written from the convention that was true when it was written, using the one directory on
disk that still spells it the old way. The suite was green and proved nothing. Whoever
fixes the glob depth should treat the fixture as the deliverable, not the fix: a fixture
that resembles the real filesystem is what neither defect had.

Open question before fixing: recursing the glob would also sweep every sub-agent from
every unrelated task, which may be the wrong default. A `--subagents` flag, or gleaning
sub-agents only for sessions already being gleaned, may be the right shape.

## Diagnosed properly, 2026-09-23 — it is TWO defects, not one

Measured on this machine's store for this project.

**1. Discovery.** `list_transcripts` globs one level, and sub-agents write to
`<session-id>/subagents/agent-*.jsonl`. Counted here: 43 session transcripts, 14
of them with a `subagents/` directory, **189 sub-agent transcripts** — sub-agents
outnumber sessions roughly 4:1.

**2. Parsing, which is the one that matters.** Even handed the path directly,
`parse_transcript` returns **0 turns**. Every record in a sub-agent transcript
carries `isSidechain: true`, and `glean.py:319` skips exactly that. The three
sub-agents this session dispatched hold 101, 96 and 35 role-bearing turns; all
of them are discarded.

The docstring explains the skip this way:

```
Sidechain entries — a sub-agent's own conversation — are skipped: they are
a different session's deliberation, and the sub-agent's transcript is
gleanable on its own terms.
```

**That second path was never built.** The skip is justified by a capability that
does not exist. And the skip is also dead code where it runs: the parent
transcript for this session holds 1,840 normal records and **zero** sidechain
records, so the filter defends the parent against something the parent never
contains. Sub-agent turns live only in `subagents/*.jsonl`. There is no shortcut
of "just stop skipping sidechains in the parent" — the content is not there.

## The scoping objection this seed recorded was wrong

It read: "recursing the glob would also sweep every sub-agent from every
unrelated task, which may be the wrong default. A `--subagents` flag ... may be
the right shape." That assumed a flat pool. The layout nests sub-agents **under
their parent session's own directory**, so gleaning session X naturally reaches
only X's sub-agents. Scoping is free and no flag is needed for it.

So: **reading sub-agents should be the default** (@aguynamedryan's lean,
2026-09-23), and the cost is two small changes rather than a new interface.

## The one genuinely open question: attribution

A sub-agent has no human in it. Its `user` turns are the parent's dispatch
prompt and tool results, not anything a person said. Glean's extractors include
"corrections the user made" and "decisions with their rationale" — run
unmodified over a sub-agent transcript, an orchestrating agent's instruction
gets surfaced as if the user had said it. That is the same mis-attribution
class this project already guards against elsewhere, and it is worse here
because the candidate is offered for capture into the durable record.

Options: label sub-agent candidates as agent-origin and let the reviewer weigh
them; or run a reduced extractor set over sub-agents (decisions and
measurements, not user-corrections); or fold each sub-agent's FINAL report only,
which is the part the parent acted on. Undecided.

Volume is the secondary consideration: at ~4:1, a `--all` historical pass grows
several-fold.

## Ruling, 2026-09-23 — and what gates it

@aguynamedryan, verbatim:

> "Yeah, let's just incorporate the final report. Provide an opportunity to
> actually incorporate sub-agent stuff. I think actually one of the things we
> need to do before we make a final decision on any of this is to look through
> and see whether or not there's anything worth gleaning from sub-agents versus
> if we just ignored, continued to ignore their conversations by default."

Three parts:

1. **Attribution: fold each sub-agent's FINAL REPORT** — the part the parent
   actually received and acted on — not its whole conversation.
2. **An opt-in to go deeper** — a way to incorporate the rest of a sub-agent's
   transcript when someone wants it.
3. **Neither is the default until measured.** Before deciding whether glean
   reads sub-agents by default at all, look at what they would actually yield
   against simply continuing to ignore them.

Part 3 gates parts 1 and 2. The study comes first.

## The yield study, 2026-09-23 — what sub-agents would actually add

Run over every sub-agent this project's sessions ever dispatched, reusing glean's
own extractor and corpus diff. Logs and the two scripts are in `claude_stuff/`
(`subagent-yield-20260923-085519.md`, `final-report-fate-20260923-085717.md`) so the study can be re-run on another repo —
one project with unusually strong capture discipline is not a sample to generalize
from.

**Population, corrected.** Not "189 sub-agent transcripts": 188 agents across 14
sessions — 85 ordinary sub-agents at `<session>/subagents/agent-*.jsonl`, plus
**103 from a single workflow run** one level deeper, at
`<session>/subagents/workflows/wf_*/agent-*.jsonl` (the 189th file is that run's
`journal.jsonl`). Two nesting depths; an implementation must handle both.

### 1. Through glean's own extractor, sub-agents add almost nothing

|                                                                  | candidates  |
| ---------------------------------------------------------------- | ----------- |
| parent transcripts, today                                        | 613 new     |
| + sub-agent FINAL reports                                        | 25 marginal |
| + sub-agent FULL transcripts                                     | 35 marginal |
| sub-agent "user" turns = the ORCHESTRATOR, surfaced as the human | **1,127**   |

Read by hand, all 25 final-report candidates: 21 are receipts (commit SHAs,
"59 -> 59 seeds, check clean", exit codes), 2 were already captured under
different phrasing (containment 0.8 misses a paraphrase), 1 is design rationale
already durable in a docstring, and the 1 real finding (an empty-body premise
contradicted by 31 of 312 seeds) had reached the corpus through the parent anyway
(seeds-tz66, and the ruling in check.py). The workflow run is the extreme: 103
agents, 1 final-report candidate, 893 mis-attributed.

### 2. But that partly measures glean, not sub-agents

Glean extracts only figures, marked lines and turn-ending questions from assistant
speech, and a final report is mostly ASSERTIONS. So the second pass ignored the
extractor and asked where each of 2,911 final-report sentences ended up:

| fate                         | sentences   |
| ---------------------------- | ----------- |
| in a seed                    | 96 (3%)     |
| in the parent's conversation | 1,700 (58%) |
| neither                      | 1,115 (38%) |

"Neither" overstates: paraphrase defeats containment, and some landed in docs
rather than seeds. By agent kind it splits cleanly:

- **Bead-process agents**: what is unseen is receipts — test counts, commands run.
  No capture value; it belongs in a bead's close reason.
- **Research and review agents**: what is unseen is substantive. The workflow's
  deep-research agents found that ClearFairy "empirically validates that captured
  deliberation conditions agent output better than the final decision" — squarely
  seeds' own thesis — and it is in **no seed and no repo file**; the synthesis doc
  dropped it. This session's inside-out review had findings that were never
  triaged (no rule defines "the seed set under review").

So sub-agents do hold capture-worthy material, concentrated in research and review
agents, **in a form glean's extractor is built never to see**.

### 3. The leak: glean is ALREADY reading sub-agent reports, as the human

Background agents deliver their final report as a `<task-notification>` inside a
USER turn, and `task-notification` is not in glean's scaffold list. Across this
project's 43 parent transcripts, 101 user turns carry one; only 18 are flagged
isMeta (which glean skips). **178 of the 583 user-speaker candidates glean produces
— 31% — are sub-agent report text**, with the decision and correction rules firing
on it. The mis-attribution this seed was designing around is live today.
`<cross-session-message>` is safe: all 25 are isMeta.

### 4. What that means for the design

Every sub-agent's final report is **already in the parent transcript** — a
`<task-notification>` for background agents, an Agent `tool_result` for foreground
ones. "Fold the final report" needs no `subagents/` directory at all; it needs
glean to recognize those two shapes and attribute them as sub-agent reports rather
than dropping one and misreading the other. `subagents/**` matters only for the
opt-in.

## Ruled after the study, 2026-09-23

1. **`subagents/` stays ignored by default.** Final reports already reach glean
   through the parent transcript; reading whole sub-agent transcripts adds 35
   mostly-noise candidates and 1,127 orchestrator lines shown as the user's.
2. **Sub-agent reports are recognized and LABELLED, not dropped and not misread.**
   A `<task-notification>` result (background) and an Agent `tool_result`
   (foreground) become sub-agent-report turns, classified by the rules for agent
   speech, never the rules for the user's. This is "fold the final report", and it
   fixes the 31% leak rather than hiding it.
3. **The opt-in is `seeds glean --subagents`, and it surfaces WHOLE reports.** It
   reads `subagents/**` (both layouts) and lists each final report whose content is
   mostly not in the corpus, entire, for the glean skill to judge. Sentence
   extraction is the wrong tool here: the value in a research or review report is
   its assertions, which is exactly what glean's extractor is built not to see.
