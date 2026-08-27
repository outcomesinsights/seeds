---
name: seeds-to-beads
description: Use when the user has reached agreement on a feature after a deliberation captured in seeds, and wants the relevant seeds turned into a set of beads (tasks) executable by a Sonnet-based agent. Consults the user on decisions the deliberation left open before writing each bead, unless invoked with `--autonomous`.
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
- **Seed lineage** — cite the originating seed IDs (`Source: seeds-NNN`) so the executor can recover full deliberation context.

Separate *motivation* (why the work is worth doing) from *constraints* (what's already been decided). Keep it proportional to the bead's weight — a one-line mechanical bead needs a line; a feature born of a long deliberation needs its decisions and the stakeholder's voice.

## Recording efficacy at resolution (suggested)

These beads close a loop that began in deliberation, so the place to learn whether they were *well-made* is when you later **resolve the originating seed(s)** — not the bead's own close reason, which reads as a success summary rather than a retrospective. When you resolve such a seed, consider adding a short, honest efficacy note to the resolution:

- **Tweaking needed?** none / minor / significant — did the beads need meaningful revision during implementation?
- **If so, was it catchable in planning?** *planning-miss* (a better bead would have caught it) vs *inherent unknown* (only discoverable by building it).
- **What a better bead would have said** — one line, when there's a lesson worth carrying forward.

Capture first, quantify later: this is a qualitative record of where planning helped or missed, not a metric. The `resolve-seeds-from-beads` skill walks this at resolution time; whether and how to formalize the note itself is still open (seeds-185).

Do this conversion once when invoked. Do not adopt the conversion behavior as a default for subsequent turns.
