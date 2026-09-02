---
name: seeds-to-beads
description: Use when the user has reached agreement on a feature after a deliberation captured in seeds, and wants the relevant seeds turned into a set of beads (tasks) executable by a Sonnet-based agent. Consults the user on decisions the deliberation left open before writing each bead, unless invoked with `--autonomous`. Records each bead's originating seeds as a structured `Source:` field so the loop back to deliberation can be closed by lookup rather than by text-matching prose.
---

# Seeds → beads conversion

The user has deliberated a feature using seeds and now wants the agreed scope handed off as beads for execution by a Sonnet-based agent. Convert the relevant seeds into a set of beads following these principles:

- Separate actionable scope (decisions, agreed paths) from context (concerns, observations, refinements). Beads represent work; seeds carry the deliberation.
- Decompose into small, self-contained beads. Each bead should be doable in one focused effort.
- Pre-write content. If a bead requires a file with specific content, include the content verbatim in the bead description so the executing agent doesn't have to re-design.
- Acceptance criteria must be mechanically checkable (file exists, command exits 0, output contains string X).
- Set explicit dependencies between beads.
- After creating beads, land the plane: commit unstaged work into a clean tree.

## Consult before you create (default)

Converting a deliberation into beads surfaces decisions the deliberation never settled. The executing agent will have to make those calls anyway — alone, in a worktree, with no one to ask. **Put the question to the user before the bead is written, not after.** A question costs a sentence; a bead that ships with a guess baked into it costs a round of rework.

Ask when the decision is genuinely the user's to make:

- **Scope boundary** — does this belong in this bead, in a separate bead, or out of scope entirely?
- **Taste, UX, naming** — anything that lands on a surface a person reads: command and flag names, output wording, defaults.
- **Something the seeds left open** — the deliberation raised it and never landed it, or two seeds point in different directions.
- **Acceptance criteria that can't be made mechanical without picking a definition** — "works correctly" needs a *what counts as correct* before it becomes a check.
- **Sequencing that encodes a design commitment**, not just an ordering convenience.

Do not ask about:

- Anything the deliberation already settled. Re-opening a locked decision is the exact failure this skill exists to prevent.
- Bead decomposition, titles, wording, and other mechanical carving — that's your job.
- Anything you can answer by reading the repo.

How to ask:

- Do the analysis pass across all the seeds first, then batch the questions into as few rounds as possible. A drip of one-at-a-time interrupts is worse than a single round of four. A second round for questions that only become askable after an earlier answer is fine.
- Give concrete options with a recommendation, so "yeah, the first one" is a complete answer. Say what each option costs.
- Then write the beads.

What to do with the answer:

- Record the ruling in the bead as a locked decision **in the user's own words**, with its rationale — the same bar as *Capturing intent* below. Getting the judgment into the bead intact was the point of asking.
- If the answer settles something the originating seed had open, carry it back — `seeds answer <q-id> "…"`, or a note on the seed. The deliberation record shouldn't end up poorer than the beads it produced.

## `--autonomous`: convert in one pass

Invoked with `--autonomous` — or when the user says to just go, not to ask, or is away — make those calls yourself and create the whole set without stopping. This is the skill's prior behavior. It fits a mechanical conversion, a user who is AFK, or a case where speed matters more than precision.

Autonomous is not silent. Every call you would otherwise have asked about gets recorded as an explicit assumption in the bead (`Assumed: … — the deliberation didn't settle this`), and gathered into your closing summary, so the user can overturn one without reading every bead to find it.

## Capturing intent

Each bead should carry the *intent* behind the work, not just the task. When they exist in the deliberation, record:

- **Locked decisions + their rationale** — a settled choice stated as a decision *plus why* (e.g. "store `{}` not NULL — avoids null guards in views"). The rationale is load-bearing: it stops the executing agent from re-opening or "improving" a call the deliberation already settled.
- **Stakeholder voice on subjective calls** — for taste, scope, or UX decisions, quote the user verbatim rather than paraphrasing, so the judgment survives the handoff intact.
- **Seed lineage** — the originating seed IDs, written as a structured `Source:` field so the executor can recover full deliberation context and so the loop back to the seeds can be closed later by lookup rather than by guesswork. This one is not optional and not prose — see *Seed lineage: the `Source:` field* below.

Separate *motivation* (why the work is worth doing) from *constraints* (what's already been decided). Keep it proportional to the bead's weight — a one-line mechanical bead needs a line; a feature born of a long deliberation needs its decisions and the stakeholder's voice.

## Seed lineage: the `Source:` field

**Every bead this skill creates carries a `Source:` field naming the seeds it came from.** Not a seed ID dropped into a sentence somewhere in the description — a labelled field, in a fixed place, in a fixed shape.

The reason is a real failure. Lineage used to be prose, so the sibling skill `resolve-seeds-from-beads` had to recover it by text-matching seed IDs out of bead descriptions. On 2026-08-31 that reported `seeds-lcfa.1.1` (*"wire seeds sync into git hooks"*) as shipped, because every bead that happened to **mention** it had closed. The bead that closed had shipped a different, downstream fix; the seed's own work had never been started. A bead that mentions a seed is indistinguishable from a bead that implements it, and prose cannot be matched well enough to fix that. The field exists so the answer is recorded at conversion time, by you, who actually knows it — instead of being re-derived later by a reader who does not.

`resolve-seeds-from-beads` step 1 calls this the *structured lineage field* and treats it as its strong-evidence class. Same thing, same wording; do not coin a second name for it.

### Where it lives

**`bd`'s `--notes` field, as the first line.**

`notes` is a top-level key in `bd show --json` and in `.beads/issues.jsonl`, so reading lineage back is a field lookup rather than a grep across prose, and `bd show` renders a NOTES block where a person will see it. A line inside `--description` would be greppable too, but the description is exactly the prose field whose incidental seed mentions caused the over-claim above — putting the lineage there leaves the signal inside the noise it replaces. (`--metadata` also round-trips as real JSON and was weighed; it loses because the consumer already reads a `Source:` line, and one idea does not need two vocabularies.)

In practice that is one more flag on the create:

```bash
bd create "…" --description "…" --notes "Source: seeds-lcfa.1.1, seeds-187"
```

Anything else you put in notes — autonomous-mode `Assumed:` lines, design picks — goes **below** the lineage lines, after a blank line. Later `bd update --append-notes` appends to the end, so the lineage stays first on its own.

### The exact format

```
Source: seeds-lcfa.1.1, seeds-187
```

Precisely:

- The **first line** of `--notes`. Nothing above it, no leading whitespace.
- The literal label `Source:` followed by exactly one space.
- One or more seed IDs, separated by a comma and exactly one space — `, `. No other separator, no `and`, no bullets, no line wrapping.
- Each ID verbatim as `seeds show` reports it, dotted child suffixes included, matching `[a-z][a-z0-9]*-[a-z0-9]+(\.[0-9]+)*`.
- **Nothing else on the line.** No prose, no parentheticals, no trailing period, no explanation of what the seed said. That belongs in the description.

The grammar, in full: `Source: <id>[, <id>]*`

Bead IDs and seed IDs are shaped identically in this project — both tools derive the prefix from the project name, and that collision is known and staying. So the ID shape can never tell a reader which one it is looking at; **the field is what says these are seeds.** Never put a bead ID on a `Source:` line.

### Several originating seeds

Put every seed the bead **implements** on the one `Source:` line, most central first. One label, one line, however many IDs.

Seeds the bead merely **cites for context** — background it was written against, a concern it respects, a decision it inherits — do not belong on that line. Give them their own line directly beneath:

```
Source: seeds-lcfa.1.1, seeds-187
Context: seeds-152.5
```

`Context:` follows the same grammar as `Source:` — label, one space, IDs joined by `, `, nothing else on the line — and sits on the line immediately after it. Omit it entirely when there is nothing to cite; there is no `Context: none`.

Keeping them apart is the whole point. `Source:` is a claim that finishing this bead discharges those seeds, and a merely-cited seed must never come back as a candidate for resolution. When you are unsure which line a seed belongs on, it goes on `Context:` — an under-claimed seed costs one more pass of `resolve-seeds-from-beads`; an over-claimed one gets deliberation closed with nothing backing it.

### No originating seed

Write the line anyway, with the literal lowercase word:

```
Source: none
```

A bead with no seed behind it is unusual coming out of this skill — it means work the deliberation did not produce — but it happens, and it must be said explicitly. **Do not omit the line to mean the same thing.** An absent `Source:` means the bead predates this field; `Source: none` means a bead deliberately has no originating seed. Collapsing the two throws away the only signal that separates "we do not know" from "we checked".

### This is forward-only

Every bead written before this field existed carries prose lineage only, and those are most of the beads that will be resolved against for a long time. Nothing here backfills them, and no one should read a missing `Source:` as evidence about a bead's origins — it is evidence about the bead's age. `resolve-seeds-from-beads` handles that population by verifying candidates against shipped code instead; that is its job, not yours.

## Recording efficacy at resolution (suggested)

These beads close a loop that began in deliberation, so the place to learn whether they were *well-made* is when you later **resolve the originating seed(s)** — not the bead's own close reason, which reads as a success summary rather than a retrospective. When you resolve such a seed, consider adding a short, honest efficacy note to the resolution:

- **Tweaking needed?** none / minor / significant — did the beads need meaningful revision during implementation?
- **If so, was it catchable in planning?** *planning-miss* (a better bead would have caught it) vs *inherent unknown* (only discoverable by building it).
- **What a better bead would have said** — one line, when there's a lesson worth carrying forward.

Capture first, quantify later: this is a qualitative record of where planning helped or missed, not a metric. The `resolve-seeds-from-beads` skill walks this at resolution time; whether and how to formalize the note itself is still open (seeds-185).

Do this conversion once when invoked. Do not adopt the conversion behavior as a default for subsequent turns.
