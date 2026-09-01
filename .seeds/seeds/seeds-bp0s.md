---
id: seeds-bp0s
title: seeds should RENDER a seed's history from git rather than expose git log -p — the archive is faithful, the reader is what's missing
status: captured
type: idea
created_at: 2026-08-28T17:57:27.110472+00:00
updated_at: 2026-08-31T20:02:47.887387+00:00
tags:
  - history
  - git
  - rendering
  - cli-verb
  - context-cost
  - deliberation
  - 2026-08-28
relationships:
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T17:57:43.869395+00:00
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-08-28T17:57:43.983308+00:00
  - target_id: seeds-152.5
    rel_type: relates-to
    created_at: 2026-08-28T17:57:44.097380+00:00
  - target_id: seeds-sdhc.3
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.250075+00:00
  - target_id: seeds-sdhc.5
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.692717+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Split out of seeds-sdhc, where it was buried in a paragraph about storage. @aguynamedryan's idea, 2026-08-28:

> "If what you're presenting to me is that git log -p produces clunky output, then perhaps seeds itself would rely on the history of a file, but it would get a complete history, including all the details before they are compacted and steamrolled and flattened. But seeds could somehow manufacture a more pleasing history or more digestible history for itself or for an LLM."

## Why this matters more than it looks

It changes the safety calculus of every editorial act on a seed. The objection to compressing or superseding anything on disk is that "it's still in git" is a promise nobody can cash: reconstructing a deliberation from a series of raw diffs is hard for a human, unnatural for an agent, and something no agent does unprompted. So pruned material is *functionally* gone whatever git retains.

**seeds never has to show `git log -p`. It reads the same commits and renders them.** Once a good reader exists, the archive stops being theoretical — and marking something superseded becomes reversible in practice, not just in principle.

## Shape

A `seeds history <id>` verb that walks the commits touching `.seeds/seeds/<id>.md` and renders the seed's evolution for a reader rather than for a diff tool. Something closer to:

    2026-08-25  added: the Dolt ledger measurement (+340 words)
    2026-08-27  corrected: "120 MB" -> "21 MB" in the dependency note
    2026-08-28  superseded: the append-only entry-file proposal

rather than raw unified diffs. Two audiences with different needs: a human asking "how did we get here", and an agent that needs the journey without paying for every intermediate revision.

## Open questions

- **Granularity.** Per-commit is the natural unit but commits bundle several seeds. Does the render need per-seed commit filtering, or per-section attribution via `git blame`?
- **Summarising the diffs is itself an editorial act** — the same hazard flagged for compression. A render that smooths away the specific and keeps the generic is worse than raw diffs. Does the verb summarise, or only structure and label?
- **Cost.** Walking history for a seed with many commits is more work than reading the file. Probably fine at this scale, but it is the one operation whose cost scales with age rather than size.
- Does it belong in the CLI at all, or is it a skill? Per seeds-152.5's cut: walking git and structuring output is deterministic (verb); deciding what a change *meant* is judgment (skill). Likely a verb that emits structure, with any narration left to the caller.

## Dependency

Only meaningful once history is genuinely in git rather than materialised in the working tree — i.e. downstream of the storage direction in seeds-sdhc. Under today's single-JSONL layout a seed's history is interleaved with 300 others on adjacent lines, so per-seed history is not cleanly extractable. That is also the strongest argument that this verb is *enabled* by the storage change rather than merely coexisting with it.

Relates to seeds-sdhc, seeds-ebg1, seeds-152.5.
