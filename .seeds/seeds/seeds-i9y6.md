---
id: seeds-i9y6
title: 'Agents drift to capturing deliberation in beads, and skip seeds: why, and what in prime or hooks would stop it'
status: captured
type: question
created_at: 2026-09-30T18:05:35.254896+00:00
updated_at: 2026-09-30T18:05:35.254896+00:00
tags:
  - cutting
---

**What we were discussing:** In the week to 2026-09-30, agents working in the seeds repo have repeatedly captured open design questions as BEADS, often writing "Not ruled. Directions: (a)… (b)…" into a bead's design field, where they should have been seeds. They also skip the seed step entirely and go straight from a finding to a bead. This contradicts Ryan's standing rule: deliberate in seeds, promote to beads once agreed, implement from beads. Ryan asked (2026-09-30): "over the last week, you seem to be leaning towards using beads for capturing deliberation and/or just jump to beads without seeds first -- what's changed inside you or beeds prime or seeds prime or what to make this happen?"

**Why it came up:** At the end of a resolve-seeds-from-beads sweep (2026-09-30), the agent filed four gap beads. Ryan asked: "you've made beads, but some of these look like they might require deliberation?" The agent agreed that two were really design questions: seeds-w9h (deleting one seed file is undetected; options were a staged-diff violation, `seeds delete`/`seeds redact` verbs, or both) and seeds-dcn (the seeds-check commit gate exists only in the seeds repo; options were shipping the hook, a `seeds hook` command, or doctor running check). Both had been written as beads with option lists. The agent proposed turning them into child seeds of seeds-sdhc.2 and seeds-sdhc; that was not yet done when this cutting was taken.

**Established so far (the same session is the evidence):**

- The same pattern recurred all session. Every cross-session bug report arrived framed as "file it however seeds tracks bugs (bead or seed; your call)", and each time the agent chose a bead and put the unresolved design fork in its design field: seeds-nnp ("OPEN FORK, which Ryan rules on"), seeds-4s8 ("Not yet ruled. Suggested direction"), seeds-7ib ("Not yet ruled. Direction to weigh"), seeds-e4q and seeds-mwf ("Direction (not ruled)"). The bead was right for the defect. The fork inside it was deliberation, and it had no seed. The one decision that DID become a seed, seeds-3iqb, did so only because Ryan said "capture as seeds".
- Priming is asymmetric, verified 2026-09-30 on titan. `bd prime` is injected at SessionStart by the beads plugin's hook: this session's context opened with "SessionStart:startup hook success: [bd prime]". `seeds prime` is injected by nothing. The seeds plugin ships no hooks (no src/seeds/plugin/claude-plugin/hooks/), and neither ~/.claude/settings.json nor the repo's .claude/settings\*.json runs it at SessionStart. So every session starts with beads' workflow in context and none of seeds'.
- `bd prime` itself pulls design work into beads. Its injected text includes, verbatim: "`bd create --design=\"decisions\"` - Record design decisions" and "**Tip**: When creating multiple issues/tasks/epics, use parallel subagents". Nothing in it says where UNdecided design belongs.
- The standing rule lives only in Ryan's global CLAUDE.md ("Deliberate → Beads → Implement"; "Confirming a decision … captures it in a seed; it does NOT authorize building it"). The seeds repo's own principle (seeds-gi9k) says guidance an agent needs must ship IN the package (prime, --help, error text), because a CLAUDE.md reaches one machine. So the seed-first rule is exactly the kind of guidance that principle says must not live only in CLAUDE.md.

**Open — the question this is parked on:** Which of these explains the drift, and what fixes it?

1. The priming asymmetry (bd prime injected, seeds prime not). Candidate fix: ship a SessionStart hook in the seeds plugin that runs `seeds prime`, the way beads does.
2. bd prime's `--design "Record design decisions"` line inviting forks into beads. Candidate fix: something in seeds prime (and so injected) that names the boundary: an UNRULED option list is a seed; a bead's design field holds only ruled decisions.
3. The handoff framing ("bug report… file it") pulling toward the task tracker. Candidate fix: split a report into a bead for the defect plus a seed (or a `seeds ask` on an existing seed) for any fork it contains.
4. A model-side change the agent cannot observe about itself. Not checkable from inside a session. Checkable across sessions via Clancey: search past transcripts for when "Not ruled" and "Directions:" started appearing in `bd create` calls, and compare with harness or plugin version changes.
   The fix probably ships in the seeds package, per seeds-gi9k. Related: seeds-12 (the seeds→beads handoff umbrella).
