---
name: resolve-seeds-from-beads
description: Use to close the seeds->beads loop — reconcile what actually shipped against the deliberation, capture learnings and an efficacy note back into the originating seeds, then resolve them. Works two ways — right after an implementation session, or cold as a periodic sweep over recently-closed beads (walk the beads that closed recently and find the seeds they resolve, close the loop on what shipped since last time), where `seeds candidates` recovers the lineage nobody remembers. Every candidate is verified against shipped code before it is offered for resolution.
---

# Beads done → resolve the seeds

Work built from a seeds→beads handoff has shipped. Close the loop back to deliberation. This is the symmetric bookend of the `seeds-to-beads` skill: that skill carried intent *out* to execution; this one carries what was learned *back* before resolving.

**You do not have to have been there.** The common invocation is not "we just finished a feature" but "it has been a few weeks — walk the beads that closed and find the seeds they resolve." Step 0 picks the mode; step 1b handles the cold case without asking you to remember anything.

Work through it once, with the user, when invoked. Do not adopt it as a default for later turns.

## The rule this skill exists to hold

**A closed bead is a hint about where to look. It is never evidence that the work happened.** Resolving a seed asserts that deliberation has been discharged into code, so the only thing that can back that assertion is the code. Every step below is downstream of this: bead status finds candidates, shipped code confirms them.

## 0. Which mode are you in?

Three shapes of work arrive here, and only the first two belong to this skill.

- **Session mode** — one just-finished feature, a handful of seeds behind work you were present
  for. You already know roughly which seeds are in play. Go to step 1a.
- **Sweep mode** — you are running this cold, weeks after the fact, to walk the beads that closed
  recently and find the seeds they discharge. Nobody remembers the lineage; that is the point.
  This is bead-anchored and code-verifiable exactly like session mode — it merely spans several
  features instead of one. Go to step 1b.
- **Backlog** — stale seeds across unrelated threads with *no closed beads behind them*. That is
  **triage, not loop-closing**, and it belongs to `winnow`, the corpus audit.

**The test that separates sweep from backlog is provenance, not volume.** A sweep can legitimately
surface forty candidates — a busy month has that many closed beads — and it is still this skill's
job, because every one of them traces to a bead that closed. A backlog is seeds with nothing
downstream to check them against; no amount of care here can verify those, because there is no
diff to read. Count closed beads, not seeds, when deciding.

If it is a backlog, say so, name the count, and offer `winnow` instead. Do not quietly do a worse
job at a bigger task.

## 1a. Session mode: recover the seeds from what you remember

Recover which seeds this work came from, then **state the strength of the evidence you recovered it
with**, because step 2 depends on it. The three classes are in step 1c. If you cannot recover
lineage at all, ask the user which seeds the feature traces back to — or switch to sweep mode,
which does not need you to remember.

`seeds show` each candidate to recall what was deliberated and concluded.

## 1b. Sweep mode: let the verb find the candidates

Do not try to recall anything. `seeds candidates` reads closed beads and names the still-open seeds
they cite:

```
bd list --status=closed --json | seeds candidates -
```

Pass the **full** closed set, not a pre-narrowed one — bead IDs and seed IDs are shaped identically,
and the only thing that tells them apart is whether an ID resolves to a seed file and *not* to a
bead, which needs the bead IDs present. The verb defaults to a 30-day window; `--since 90d` or
`--since 2026-06-01` widens it.

**Read the window line back to the user, every time.** The window is stateless by design (ruled
2026-09-13), so a gap longer than it silently misses its early span. That line is the only thing
that makes the hole visible, and reporting candidates without it hides exactly what the operator
needs in order to ask for a wider pass.

The verb also prints what it deliberately withheld — seeds cited on a `Context:` line, seeds
already resolved, IDs that name nothing in this store. Do not go fishing in those piles. They are
shown so the withholding is auditable, not so you can re-admit them.

Then `seeds show` each candidate and carry the whole list into step 2. **Every one of them still
gets verified against code.** A cold sweep needs that more than session mode does, not less:
nothing in your memory is propping up a bad candidate, so the output's evidence class is all you
have until you go and look.

## 1c. Say how strong the lineage is

Whichever mode you came from, **your first report to the user names the evidence class**, because
step 2's burden of proof depends on it. In sweep mode the verb has already labelled each candidate;
use its labels rather than re-deriving them.

- **`[source]` — a structured lineage field** on the bead (`Source: seeds-NNN`, written by newer
  runs of `seeds-to-beads`). The link is *asserted by whoever converted the seed*. Still verify in
  step 2, but the candidate list is trustworthy.
- **`[prose]` — seed IDs matched out of bead descriptions**. The link is *inferred by text-matching*.
  Text-matching finds beads that **mention** a seed, which is a strictly weaker claim than beads
  that **implemented** it.
- **Neither** — ask the user which seeds the feature traces back to.

**Expect prose, and do not read a missing `Source:` as evidence about a bead's origins — it is
evidence about the bead's age.** Measured on the seeds project 2026-09-13: **0 of 175** beads
carried a `Source:` field, while 103 mentioned a seed in prose. Every bead written before that
field existed has prose lineage only, and those will be most of what you resolve against for a long
time. Treating the structured field as the normal path returns an empty answer on a corpus with a
dozen real candidates in it.

When the evidence is weaker than the method assumes, the failure is not the weak evidence — it is
proceeding as though it were strong without saying so.

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
