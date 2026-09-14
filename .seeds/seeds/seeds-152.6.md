---
id: seeds-152.6
title: resolve-seeds-from-beads assumes the session that shipped the work; the real use is a cold sweep of recently-closed beads
status: captured
type: concern
parent: seeds-152
created_at: 2026-09-14T03:43:33.629403+00:00
updated_at: 2026-09-14T03:43:38.956190+00:00
tags:
  - skills
  - resolve-seeds-from-beads
  - seeds-to-beads
  - lineage
  - sweep
  - session-coupling
  - measured
  - 2026-09-13
relationships:
  - target_id: seeds-taff
    rel_type: questioned-by
    created_at: 2026-09-14T03:43:38.955024+00:00
---

`resolve-seeds-from-beads` is written for the case where the feature *just* shipped in the
session you are sitting in. Ryan's actual use is the opposite: he runs it infrequently, and
when he does, his intent is "walk the beads that closed recently and find the seeds they
discharge." The skill has no mechanism for that, and step 0 actively refuses it.

## Where the mismatch lives

- **Step 1 has no discovery step.** It says "recover which seeds this work came from" and
  offers three evidence classes, but no way to *enumerate* candidates. It assumes the agent
  was present for the implementation and can recall. Cold, its only fallback is "ask the user"
  — which is exactly the lookup Ryan invoked the skill to avoid doing himself.
- **Step 0 bounces the sweep as a backlog.** It splits the world into "one just-finished
  feature" (proceed) and "dozens of stale seeds across unrelated threads" (go run `winnow`).
  A time-windowed sweep of recently-closed beads is neither. It is still bead-anchored and
  still code-verifiable; it just spans several features instead of one. Conflating it with
  corpus triage is what makes the skill push back on its own primary use.

## Measured state of this repo, 2026-09-13

The discovery primitive exists — `bd list --status=closed --closed-after=<date>` — and the
data supports a sweep today, but not by the route the skill expects.

```
closed beads since 2026-08-25 ............................. 69
beads (of 175 total) carrying a `Source:` notes field ....... 0
distinct tracker IDs mentioned in bead desc/notes .... 171
  resolve to a seed file, not a bead ....................... 80
  resolve to a bead, not a seed ............................ 60
  ambiguous (exists as both) ................................ 0
  neither ................................................... 31
mentioned seeds still non-terminal ........................ 36
  ...where every mentioning bead is closed ................. 20
  ...with a mentioning bead closed since 2026-08-25 ........ 12
```

Two things fall out of that.

**The `Source:` field is 0-for-175.** Step 1 treats it as the strong-evidence class and
\[[seeds-152.4]\]'s skill was written to emit it, but no bead in this repo has one. The
strong path is theoretical; prose is the only lineage that exists. That is not an argument
against the field — it is an argument that sweep mode must work without it for a long while.

**Prose lineage is mechanically disambiguable, and the skill does not know it.** Bead IDs and
seed IDs share a shape, which is why `seeds-to-beads` warns that prose cannot be matched
reliably. But shape is not the only signal available: an ID that resolves to a seed file and
*not* to a bead is a seed reference. On this corpus that decides every one of the 171 — zero
collisions. The rule is cheap, local, and turns "unmatchable prose" into a usable candidate
list.

## Proposed shape

Rewrite step 0 from a two-way fork into three modes, and give the sweep a real step 1:

1. **Session mode** — today's behaviour, unchanged.
2. **Sweep mode** — take a window; list beads closed in it; extract IDs from `Source:` /
   `Context:` first and prose second; drop IDs that resolve to a bead; keep seeds still
   non-terminal. Hand each survivor to steps 2-5 **completely unchanged.**
3. **Backlog** — still routed to `winnow`, but on a sharper test than "dozens," since a
   legitimate sweep spans many features.

The load-bearing claim is that discovery and verification are separable. Steps 2-5 — name the
artifact, read the diff, sort into verified / not-shipped / cannot-tell — are the valuable
part of this skill and they do not care how a candidate arrived. Only step 1 is
session-coupled. Fixing step 1 does not weaken the discipline that step 2's worked example
(the `seeds-lcfa.1.1` false positive) exists to enforce; if anything a cold sweep needs it
more, because nothing in the agent's memory is propping up a bad candidate.

## Open question

How does sweep mode choose its window with no marker to anchor on? Candidates: ask the user;
default to ~30 days; infer from the most recent `resolved` timestamp in the seed store; or
write a marker at the end of each run. Not ruled.

## Related

\[[seeds-160]\] (retrospective outcome — did the resolved decision pan out?) and
\[[seeds-161]\] (seeds under-captures what we learned by trying) are the adjacent thread: both
are about what happens *after* resolution, where this is about reaching resolution at all
when the session that did the work is long gone.
