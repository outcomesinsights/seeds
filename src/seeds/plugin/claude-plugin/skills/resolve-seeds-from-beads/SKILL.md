---
name: resolve-seeds-from-beads
description: Use after an implementation session, once the user is satisfied with the shipped feature, to close the seeds->beads loop — reconcile what actually shipped against the deliberation, capture learnings and an efficacy note back into the originating seeds, then resolve them. Every candidate is verified against shipped code before it is offered for resolution.
---

# Beads done → resolve the seeds

The feature built from a seeds→beads handoff is finished and the user is satisfied. Close the loop back to deliberation. This is the symmetric bookend of the `seeds-to-beads` skill: that skill carried intent *out* to execution; this one carries what was learned *back* before resolving.

Work through it once, with the user, when invoked. Do not adopt it as a default for later turns.

## The rule this skill exists to hold

**A closed bead is a hint about where to look. It is never evidence that the work happened.** Resolving a seed asserts that deliberation has been discharged into code, so the only thing that can back that assertion is the code. Every step below is downstream of this: bead status finds candidates, shipped code confirms them.

## 0. One feature, or a backlog?

Check the size of what you have been pointed at before starting.

- **One just-finished feature** — a handful of seeds behind a session's work. That is what this skill is for; continue to step 1.
- **A backlog** — dozens of stale seeds across unrelated threads, with no single feature in view. That is **triage, not loop-closing**, and it is a different operation (`winnow`, the corpus audit). Say so rather than grinding through it: this skill reconciles deliberation against a specific shipped thing, and pointed at forty unrelated candidates it degrades into exactly the mentions-and-closed guessing that step 2 exists to stop.

If it is a backlog, tell the user the count, say plainly that this is the wrong instrument for it, and offer to scope down to one feature you *can* verify. Do not quietly do a worse job at a bigger task.

## 1. Find the originating seeds — and say how strong the link is

Recover which seeds this work came from, then **state the strength of the evidence you recovered it with**, because the next step depends on it:

- **A structured lineage field** on the bead (`Source: seeds-NNN`, written by newer runs of `seeds-to-beads`) — the link is asserted. Still verify in step 2, but the candidate list is trustworthy.
- **Prose mentions** of seed IDs inside bead descriptions — the link is *inferred by text-matching*. This is the common case: every bead written before the structured field existed has prose lineage only, and those are most of the beads you will be resolving against. Text-matching finds beads that *mention* a seed, which is a strictly weaker claim than beads that *implemented* it.
- **Neither** — ask the user which seeds the feature traces back to.

Say which of these you are working from, out loud, in your first report to the user. When the evidence is weaker than the method assumes, the failure is not the weak evidence — it is proceeding as though it were strong without saying so.

`seeds show` each candidate to recall what was deliberated and concluded.

## 2. Verify each candidate against shipped code

**Before a seed is offered for resolution, point at the code that discharges it.** Not the bead's close reason, not its status — the artifact.

For each candidate:

1. **Name the artifact the seed's conclusion implies** — the file, function, flag, config entry, command, or test that has to exist if this seed shipped. If you cannot name one, you do not understand the seed well enough to resolve it.
2. **Go look at it in the working tree.** Read the file. Run the command. Grep for the symbol.
3. **Read the actual diff of the closing bead**, not its summary — `git log --grep=<bead-id>`, `git show`. A close reason is written to sound finished; a diff is what landed.
4. **A candidate survives only if you can point at the code.** Report the pointer alongside the candidate so the user can check it in a glance: `seeds-abc — shipped, see src/seeds/export.py:120`.

Sort the candidates into three piles and show all three:

- **Verified** — the behaviour is in the tree, with a pointer. Eligible for resolution.
- **Not shipped** — the bead closed, but the seed's own work is absent. Leave open, and say what is missing.
- **Cannot tell** — the seed's conclusion is not the kind of thing that leaves a trace you can find. Leave open and ask the user; do not resolve on a guess.

Being slow here is the point. A candidate you dropped costs one more run of this skill. A seed you resolved falsely is deliberation deleted from the record with nothing backing it, and nothing will ever flag it again.

### Worked example: the false positive this step was added for

On 2026-08-31 this skill reported `seeds-lcfa.1.1` — *"wire seeds sync into git hooks"* — as shipped. Every bead that mentioned that seed had closed, so text-matching called it done. But the closed bead, `seeds-ww8`, had shipped a *different, downstream* fix; it merely referenced the seed in passing. The seed's actual work had never been started.

Thirty seconds of verification settled it: open `.pre-commit-config.yaml` and look for a seeds hook. There was none — not a wrong one, none at all.

**Mentions-and-closed is not shipped.** The two are only correlated, and this skill is the one place in the seeds→beads loop where treating them as equivalent goes unnoticed: it closes deliberation, and nothing downstream re-opens it.

## 3. Reconcile deliberation against what shipped

For the candidates that survived step 2, compare the seeds' conclusions with what was actually built — the real diff, and any tweaks or last-minute changes made mid-implementation. Surface each meaningful divergence to the user.

For divergences worth keeping, **append** them to the relevant seed with `seeds update <id> --append` — never `-c/--content`, which *replaces* and would destroy the original deliberation. Both the original reasoning and "what we actually did in the end" should stay legible. Propose the reconciliation; let the user confirm it. Capture only what's genuinely new — don't restate what the seed already says.

A seed from the **not shipped** pile is also worth an append: recording that the work is still outstanding, and which bead was mistaken for it, is more valuable than silence.

## 4. Capture an efficacy note

For the feature (or per seed), record a short, honest note on how the planning held up:

- **Tweaking needed?** none / minor / significant.
- **If so, was it catchable in planning?** planning-miss (a better bead would have caught it) vs inherent unknown (only discoverable by building it).
- **What a better bead would have said** — one line, when there's a lesson worth carrying forward.

Qualitative capture, not a metric (see seeds-185).

## 5. Resolve

Resolve each **verified** seed with `seeds resolve <id> -r "<outcome + efficacy note>"`. Cite the code pointer from step 2 in the resolution text, so the claim stays auditable after the session ends. Resolve children before parents — a seed with unresolved children is blocked.

Leave genuinely open threads unresolved rather than forcing closure — and that includes everything from the *not shipped* and *cannot tell* piles. Ending a run with fewer resolutions than candidates is the correct outcome, not a shortfall.
