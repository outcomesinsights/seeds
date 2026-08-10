# Working with seeds (mostly via your AI)

> **Status:** Draft. Companion to the introducing-seeds blog post.
> Where the blog post is the _why_, this doc is the _how_. Read this once
> when you start using seeds. Skim it again a month later when you've
> formed habits and want to refine them.

This is not a CLI reference — that's the README. This is a guide to the
_workflow_ of using seeds with an AI agent driving most of the keystrokes.

## What seeds is, in one paragraph

Seeds is a place to put thoughts that aren't ready to be tasks. Each seed
has an ID, a title, a body, a status (`captured`, `exploring`, `resolved`,
`deferred`, `abandoned`), and optional tags, parents, children, and links
to other seeds. Questions are first-class objects you attach to seeds.
The whole graph lives in a tiny SQLite database under `.seeds/` plus a
git-trackable JSONL export. The CLI is a thin layer over the database; the
expectation is that an AI agent calls it on your behalf during normal
conversation.

## What it isn't

- **Not a todo list.** A seed has no deadline, no assignee, no priority. If
  you find yourself wanting those things, you have a task. Open it in beads
  or your issue tracker.
- **Not a notes app.** Notes are for content. Seeds are for content _plus
  a lifecycle_. If you don't care about whether a thought eventually
  reaches a conclusion, write a note.
- **Not a knowledge base.** Seeds capture deliberation as it happens.
  After-the-fact write-ups belong in your wiki / ADR repo / blog. Seeds
  feed those documents; they don't replace them.
- **Not a replacement for a planning conversation.** Seeds preserves a
  conversation; it doesn't generate one. You still have to think.

## How I actually use it (one worked example)

The way I use seeds may not be the way you'd use it. This workflow fits
the way *my* brain works — disorganized, divergent, allergic to ceremony,
prone to losing the thread if I don't externalize it. Hopefully it works
well enough for your brain too. If it doesn't, the design is loose enough
to bend.

What I'm really doing — under the workflow detail — is exploring the
deliberation space (the half-formed, half-rejected, half-revisited tangle
of thoughts that goes into designing anything nontrivial) while at the
same time **securing my thinking to the level of detail and permanence I
require in order to feel comfortable**. That sentence is the whole project.
Everything below is one person's working method. Borrow what fits.

### Step 0: dump the brain

When I start a new project, I fire up dictation software and I talk. About
the stray thoughts. About the weird ideas I'm half-embarrassed to say out
loud. About the main gist of what I want to do. About the directions I'm
considering and why. I don't try to be organized. I don't try to be
correct.

When the dump is done, I tell the agent: **"turn this into seeds."**

The agent reads the transcript and creates a batch of seeds. Some are
ideas. Some are decisions. Some are concerns. Some are open questions
attached to other seeds. Some are tagged. The structure is messy and
partial and exactly what I wanted.

### Step 1: the agent interviews me

After the initial pass, I invite the agent to ask me questions. About
things I said in the dump but didn't elaborate on. About things I _didn't_
say that the agent thinks need to be considered. About contradictions
between two different stray thoughts.

This is the part that took me a while to learn to invite. The default
shape of working with an AI is: I direct, it executes. The shape that
actually pays off here is: it asks, I answer (or admit I don't know).
**Generally the agent is right on** about what needs more thought. I'd
rather have the friction of being interviewed up front than the cost of
discovering a missed assumption six weeks in.

When I don't know, I say so. The agent will often record that as an open
question on the seed and move on. Some questions stay open for weeks.
That's fine.

### Step 2: triage and relationship

I'll suggest that some ideas need to be deferred. I'll suggest that
others can't be defined until earlier ones are. The agent flags things
for backlog, builds parent-child relationships, links related seeds. We
sift, sort, and prioritize together. Maybe a couple of iterations of
this.

### Step 3: the foundational-priority question

Eventually I ask:

> What decisions do you think need to be made now? What's foundational?

And here's the moment I find genuinely wild: **the agent figures it
out**. It will tell me which seeds are foundational — the ones whose
answers determine how every other seed gets handled. I don't know how
it knows. The seed graph evidently encodes enough structure that
"foundational" is a query the AI can answer just by looking at the
shape. I expected this to be hard. It isn't.

This is the seeds equivalent of `bd ready` — but instead of "what work
is unblocked?" the question is "what _understanding_ is blocking the
rest of the deliberation?" Different domain, same load-bearing role.

### Step 4: answer the foundational stuff (or chase it)

I work through the foundational seeds. Sometimes I have an answer.
Sometimes the agent suggests an answer of its own and I sanity-check
it. Sometimes I tell the agent: **"go investigate this"** — read the
docs, look at the code, run a small experiment, search the web — and
**come back with what you find written into the seed.**

The investigation getting incorporated back into seeds is the part I
love most. The agent doesn't just answer my question in chat (where
the answer evaporates at compaction time); it captures what it learned
_as part of the seed body_. Months later, when I or another agent revisit
that seed, **we have the same information that was on the table when the
decision was made.** Not a summary of it. Not a paraphrase. The actual
findings.

### Step 5: rinse, repeat, until enough

I cycle through that loop a couple of times. Each pass closes some
seeds, opens some new ones, deepens others. At some point — and there's
no formal threshold, I just feel it — we've done enough planning to
start building.

### Step 6: handoff to beads

When I'm ready to implement, I tell the agent:

> Make some beads out of these seeds.

Specifically the seeds that have resolved into "yes, we're doing this
and here's what it looks like." Those become bd issues with their
seed-body context attached, and we're off making implementation work
under beads.

The seeds don't go away. They sit there. When the implementation
surfaces something — a wrong assumption, a missed alternative, a
question that needs revisiting — I come back to seeds. New thoughts
get jotted; existing ones get updated; sometimes a resolved seed gets
reopened because reality disagreed with the plan. The implementation
informs the deliberation, which informs the next round of
implementation.

That's it. That's the whole rhythm. Most of it is conversation; the
seeds CLI runs underneath, called by the agent on my behalf. I almost
never type a `seeds` command.

---

## The mental model

Three shapes recur underneath that workflow.

### The inbox

You're talking through something with your AI. A tangent comes up that's
interesting but not now. The agent jots a seed:

```
seeds jot "Reconsider whether we want optimistic concurrency on the audit table"
```

That seed sits in `captured` until somebody (you or a future agent session)
picks it up. The point is _not losing the thought_, not organizing it.
Capture is liberal. You can prune later.

When you're ready, you triage:

- Promote to `exploring` if it's worth thinking through now
- `defer` it if it's not now-work
- `abandon` it if you've decided it isn't worth pursuing — _with a reason
  in the body_. Abandoned seeds are valuable! They prevent you from
  re-considering the same dead end next year.
- `resolve` it if it turns out the answer is obvious

### The deliberation tree

You're designing something nontrivial. The agent creates a parent seed for
the topic, then children for each sub-question or alternative considered:

```
seeds-a1b2: Should we use event sourcing for the audit log?
├── seeds-a1b2.1: Investigate event-sourcing libraries (exploration)
├── seeds-a1b2.2: Concern about migration cost (concern)
├── seeds-a1b2.3: Alternative: append-only table (idea)
└── seeds-a1b2.4: Decision: append-only table won (decision)
```

The parent seed can't be `resolved` while children are open (that's the
"blocked" state). When the dust settles, every child has a status, the
parent has a status, and the body fields tell the story.

This is the shape that pays off years later. When somebody asks "why did we
go with append-only?" the agent runs `seeds show seeds-a1b2` and the answer
is _right there_, with the alternatives that were considered and the
reasons they lost.

### The audit log

You're working through a long, fiddly process — an ETL, a data audit, a
migration. Every decision, discrepancy, and deferred question becomes a
seed. By the end of the work, the seed database is _the_ record of what
happened and why.

This shape works best when most seeds end up `resolved` or `abandoned`. A
healthy audit log has very few seeds left in `captured` at the end of a
work session — they got triaged.

## The few commands that matter

Most days you're using a small subset:

```sh
seeds jot "Quick thought"                       # capture
seeds create -t "Title" --type concern          # capture with metadata
seeds create -t "Sub" --parent seeds-a1b2       # child seed
seeds ask "Question?" --seed seeds-a1b2         # attach a question
seeds answer q-c3d4 "The answer"                # answer a question
seeds explore seeds-a1b2                        # claim it
seeds resolve seeds-a1b2                        # done
seeds defer seeds-a1b2                          # not now
seeds abandon seeds-a1b2                        # decided against
seeds list                                      # what's open
seeds show seeds-a1b2                           # one seed in detail
seeds tree                                      # hierarchy view
seeds prime                                     # context for an AI agent
seeds sync --flush-only                         # export to JSONL for git
```

You will rarely type any of these yourself. That is fine.

## How to get your AI to actually drive

The single most important integration is `seeds prime`. Run it at the start
of a session — or, better, configure your tool to run it automatically —
and pipe the output into the agent's context. The agent will know the
landscape: what's open, what's recently moved, what questions are
unanswered.

After that, the leverage comes from a few prompting patterns. None of these
are deep magic; they're just the patterns that work best in my experience.

**Tell the agent it's allowed to be liberal.** The default for an AI is to
ask permission before recording anything. You want the opposite: capture
liberally, because abandoned seeds are still useful. A project-level
instruction like

> Capture seeds aggressively as we discuss things. Don't ask first.
> Liberal capture is better than complete capture. Abandoned seeds
> are valuable.

removes a lot of friction. Adapt to taste.

**Tell the agent the difference between seeds and beads.** A common
failure mode early on is the agent putting half-formed thoughts into your
issue tracker, which pollutes it. Be explicit:

> Use seeds for ideas, deliberation, open questions, and rejected
> alternatives. Use beads only for concrete, actionable, ready-to-implement
> work. Most things start as seeds.

**Treat status changes as natural in conversation.** Don't be precious. If
you say "okay, we're going with append-only," the agent should resolve the
relevant seed and capture the chosen rationale in its body. If you say
"forget that, it's a bad idea," the agent should abandon it with a one-line
reason. Status changes are cheap.

**Use questions for things you don't know yet.** A seed body is for
deliberation; a question is for a specific thing-you-need-an-answer-to.
Questions block the parent seed from resolving until they're answered.
This is good pressure.

**Run `seeds prime` between sessions.** AI agents lose context between
conversations. Priming gets the new agent up to speed in seconds. Many
projects also wire `seeds prime` into a session-start hook.

## Patterns I've seen pay off

A few things you can borrow from how I run it day-to-day.

**The "rejected" tag.** When a seed is `abandoned`, also tag it
`rejected:<reason>`. A grep through your seed database for anything tagged
`rejected:` is the single most valuable artifact in the whole tool: it's a
queryable list of "things we tried and didn't go with." This is the cure
for re-fighting old arguments.

**The decision body template.** When the agent resolves a seed that
represents a decision, encourage it to body-format like:

```
**Decision:** Append-only audit table.
**Why:** Simpler operations, no concurrency surprises, fits team's existing
    Postgres expertise.
**Considered:** Event sourcing (rejected: migration cost), CDC (rejected:
    requires infra we don't have).
**Revisit if:** Audit log volume exceeds 10M rows/day.
```

Three minutes of structure here means you can rehydrate the decision in
ten seconds two years from now.

**Use parent seeds as topics.** A topic-level parent like "Authentication
strategy" with children for each sub-question keeps the deliberation
together and makes the eventual decision discoverable. You can resolve
the parent with a summary of the whole sub-tree once the children are
done.

**Backfill from existing artifacts.** If you're starting seeds in a
mature project, consider one-time backfilling from your closed GitHub
issues, your old `plans/` directory, your ADR repo. The fidelity is low,
but it gives the agent enough context to recognize "we considered that in
2023" when it comes up again. I've found this surprisingly worth the
hour or two.

## The one workflow rule that matters

**Capture before you forget; structure when you have time.**

If you find yourself in a planning conversation and you're not sure
whether to capture something — capture it. The cost of one extra seed is
a few seconds. The cost of a lost insight is sometimes years.

If you find yourself in a planning conversation and you're not sure how
to structure what you're capturing — capture it as `jot` and move on.
Tags, parents, links, types: all of it can be added later by you or by
an AI doing maintenance work for you.

This is the only rule that matters. Everything else is taste.

## When seeds is the wrong tool

A few cases where I either don't bother with seeds or actively avoid it:

- **Tight, unambiguous task.** "Fix the off-by-one in the date parser."
  Goes in beads/issues, not seeds. There's no deliberation here.
- **One-off scripts you'll never read again.** Scripts that exist to be
  run twice and thrown away don't need a deliberation log. The script is
  the artifact.
- **Anything tightly coupled to a chat that's about to close.** If the
  whole conversation will fit on one screen and lead to a single decision
  in five minutes, just have the conversation. Capture the decision in
  the artifact (commit message, PR description, ADR), not in a seed.
- **When the project doesn't outlive the session.** Throwaway prototypes
  don't need durable deliberation.

The hard cases are projects somewhere between "single decision" and
"long-running system." I default to using seeds, because it costs almost
nothing if I'm wrong and pays off enormously if I'm right. Your mileage
may vary.

## Maintenance

A few small habits keep the seed database healthy.

- **Sync at end of session.** `seeds sync --flush-only` writes the JSONL
  export so the day's deliberation is git-trackable. Commit it.
- **If a sync refuses, read what it names.** The export rewrites the JSONL
  wholesale from the database, so it stops rather than destroy a record the
  database has never seen — a merge conflict you resolved in the file, a hand
  edit, or a peer's seed that no import absorbed. Fold the content in
  (`seeds update <id> -a '<text from disk>'`, or `seeds import` for a record
  the database lacks entirely) and re-run. `--allow-divergence` skips the
  check and destroys that content; it is not a shortcut past the message.
- **Triage `captured` seeds occasionally.** Once a week or so, ask the
  agent to walk the captured list and either promote, defer, or abandon
  each one. Things shouldn't sit in captured for months.
- **Resolve loudly.** When a seed reaches a conclusion, the body should
  capture the _why_. A resolved seed with a one-word body is no better
  than no seed at all.
- **Tag deliberately, not exhaustively.** Tags are for filtering, not
  for taxonomy completeness. Don't try to build a full ontology.

## Notes for the agent

A short block you can adapt and drop into your project's `AGENTS.md` or
equivalent:

> ### seeds usage
>
> When discussing design, planning, or open questions in this project,
> capture seeds liberally as we work. Don't ask first. Use:
>
> - `seeds jot "..."` for fast capture
> - `seeds create -t "..." --type <idea|question|decision|exploration|concern>`
>   for structured capture
> - `seeds ask "..." --seed <id>` for open questions tied to a seed
> - `seeds explore | resolve | defer | abandon <id>` for status changes —
>   move state when the conversation makes the new state correct, even
>   without explicit user request
> - `seeds prime` at the start of a new session to ingest deliberation
>   context
>
> Use seeds for ideas, deliberation, open questions, rejected
> alternatives. Use beads/issues only for concrete actionable work.
> Most things start as seeds.
>
> When abandoning a seed, _always_ include the reason in the body. When
> resolving a decision, include `Decision / Why / Considered / Revisit if`
> in the body. Abandoned seeds and rejected alternatives are valuable —
> they prevent re-litigation later.

## Where to go next

- The blog post (`docs/blog-introducing-seeds.md`) for the why.
- The README for the CLI reference.
- `docs/seeds-philosophy-research.md` for the deeper origin/philosophy
  notes.
- The seeds-about-seeds database (try `seeds list` in this repo) for the
  most heavily-dogfooded example you'll find.
