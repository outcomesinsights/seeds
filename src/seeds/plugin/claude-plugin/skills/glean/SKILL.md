---
name: glean
description: Use at the end of a working session, or whenever the user asks what a session worked out that never got captured — "glean this session", "what did we miss?", "anything we didn't capture?", "harvest this conversation". Runs `seeds glean` over the session transcript, judges which of its candidates are real deliberation, and offers the survivors for review one at a time.
---

# Glean a session

A working session settles things the corpus does not hold: a figure someone measured, a
constraint stated in passing, a question raised and dropped. `seeds glean` is the
deterministic half of recovering them — it resolves the transcript, extracts candidates and
diffs them against the corpus. This skill is the judgment half: decide which candidates are
real, and offer those for review.

Do this once, when invoked. Do not adopt it as a default for later turns.

## Never glean from your own context

**Run the verb. Do not summarize the conversation from what you can still see.** This is
the one rule the skill exists to hold.

Your context is not the session. Post-compaction context is summarized, and what
summarization drops is exact figures, verbatim user quotes, and things mentioned but never
acted on — precisely the set glean exists to recover. The failure is silent and
shape-dependent: gleaning from context looks fine in a short session and fails in the long
ones that need it most, and the output is indistinguishable either way.

Say it plainly because it has been got wrong before: **"just analyse the conversation
already in the model's context, it's simpler" was the standing conclusion here for roughly
six months** (seeds-74.2.2), and was overturned on 2026-09-01 in favour of reading the
transcript (seeds-74.2.1). Do not reintroduce it. The size argument that used to justify it
is also gone — this project's own transcript is 5.3MB across 251 turns, and the verb hands
back 96 candidates in 13KB. You never see the transcript.

## 1. Run the verb

    seeds glean

It resolves the current session from `$CLAUDE_CODE_SESSION_ID` — never from the
most-recently-modified file, which on a host running several agents is routinely somebody
else's. Also available: `--session <id>` for a specific one, `--force` when the session is
already recorded in `.seeds/gleaned.jsonl` and the command reports nothing to do, and
`--all --since 30d` for a bounded historical pass.

**Do not pass `--auto` here.** It files every candidate unreviewed (tagged `auto-gleaned` so
a bulk pass can be audited or reverted). It is for historical sweeps; in an interactive
glean the review *is* the skill.

What comes back: a header with turn and candidate counts, then candidates grouped by kind —
`chain` (a question, its answer and the decision that followed), `decision`, `question`,
`clarification`, `measurement`, `note` — each as `turn N · speaker` and the text. Then an
`already captured` block naming the seed each suppressed candidate matched.

## 2. Judge — most candidates are not worth a seed

The verb errs toward offering; the cutting is yours. Measured on one 384-turn session: 67
candidates, of which a handful deserved a seed. Expect to drop the large majority, and say
so plainly rather than padding the list to look productive.

**Keep** a candidate when it carries something the repo cannot give back:

- a decision *with its rationale* — why this and not the other thing
- a figure somebody actually measured, with what it was measured on
- a constraint, principle, or preference the user stated
- a correction that changed the mental model, not just the next step
- a question raised and never answered, or a thing mentioned and never acted on
- a `chain` — these are usually the richest, since the reasoning is already assembled

**Drop** work-order traffic and reports of work:

- "let's cut a new version and push", "can we do full CI locally first?" — sequencing, spent
- assistant turns ending "Want me to X?" that the session then answered
- verification output pasted back from a sub-agent's report. These arrive labelled `user`
  because the speaker field records who *typed* the turn, not who authored the text
- anything already in the code, the docs, or a commit message
- anything whose only value was getting the next step to happen

The test: would somebody opening this seed cold in three months learn something they could
not recover from the repository?

Read the `already captured` block as a cue, not as noise. If a survivor sharpens,
qualifies, or contradicts a seed listed there, the right move is `seeds update <id> --append
"…"` on that seed — not a second seed saying nearly the same thing. Likewise, cluster
several candidates circling one idea into a single seed instead of filing near-duplicates.

## 3. Offer the survivors, one at a time

Suggest-and-review is the default and stays the default however long the list is. For each
survivor, show what you propose to write — title, type, the body in brief, and the turn it
came from — and take **y / n / edit**:

- **y** — file it as shown
- **n** — drop it, and do not offer it again this pass
- **edit** — the user rewrites the title, the body, or the type; file what they say

One at a time, and nothing written before it has been answered. A batch presented for a
single yes is not a review.

## 4. File what survived

`seeds jot "<the thought>"` is right for a one-liner — a title-only seed is a legitimate
shape, not an unfinished one. For anything with a body:

    seeds create -t "<title>" --type <decision|question|exploration|concern|idea>
    seeds update <id> --content-file <path>

The second step keeps a multi-paragraph body out of argv (`seeds create` takes only `-c`,
which is fine for a short one). Write the turn reference into the body, and **quote the user
verbatim** wherever the wording is the point — glean exists because paraphrase loses exactly
that.

Close by naming what you filed and what you dropped. A candidate that was judged and
discarded should be visibly discarded, not silently missing.
