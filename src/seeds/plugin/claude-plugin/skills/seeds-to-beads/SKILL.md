---
name: seeds-to-beads
description: Use when the user has reached agreement on a feature after a deliberation captured in seeds, and wants the relevant seeds turned into a set of beads (tasks) executable by a Sonnet-based agent.
---

# Seeds → beads conversion

The user has deliberated a feature using seeds and now wants the agreed scope handed off as beads for execution by a Sonnet-based agent. Convert the relevant seeds into a set of beads following these principles:

- Separate actionable scope (decisions, agreed paths) from context (concerns, observations, refinements). Beads represent work; seeds carry the deliberation.
- Decompose into small, self-contained beads. Each bead should be doable in one focused effort.
- Pre-write content. If a bead requires a file with specific content, include the content verbatim in the bead description so the executing agent doesn't have to re-design.
- Acceptance criteria must be mechanically checkable (file exists, command exits 0, output contains string X).
- Set explicit dependencies between beads.
- After creating beads, land the plane: commit unstaged work into a clean tree.

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
