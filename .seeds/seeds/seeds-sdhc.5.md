---
id: seeds-sdhc.5
title: seeds history structures and never summarises, and it reads across the conversion — so the JSONL's history must outlive the JSONL
status: captured
type: decision
parent: seeds-sdhc
created_at: 2026-08-31T20:09:39.157465+00:00
updated_at: 2026-08-31T20:09:48.024295+00:00
tags:
  - storage
  - history
  - git
  - rendering
  - conversion
  - measured
  - "0.7"
  - 2026-08-31
relationships:
  - target_id: seeds-bp0s
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.692717+00:00
  - target_id: seeds-sdhc.1
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.826477+00:00
  - target_id: seeds-wurl
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.956658+00:00
  - target_id: seeds-152.5
    rel_type: relates-to
    created_at: 2026-08-31T20:09:49.064092+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Settles seeds-sdhc's open item #6 and answers the two open questions seeds-bp0s left. Also corrects a claim in seeds-bp0s that turned out to be wrong, and the correction changes the conversion design.

## Structure only. The verb never summarises.

seeds-bp0s asked: "does the verb summarise, or only structure and label?" **Only structure.**

Summarising is the same editorial hazard seeds-sdhc's reversal just rejected on disk — a rolling summary of a deliberation is a decision log, which is what seeds exists not to be. Producing one on read has that defect plus a new one: it is non-deterministic and unauditable, so two runs can disagree about what the journey was and neither is checkable.

This is also just seeds-152.5's cut applied cleanly: walking git and labelling changed fields is deterministic, so it is a verb. Deciding what a change *meant* is judgment, so it belongs to the caller reading the output in context.

## seeds-bp0s's dependency claim is wrong, and that is load-bearing

> [!SUPERSEDED] 2026-08-31 — see the measurement below.

seeds-bp0s concluded that per-seed history "is not cleanly extractable" under today's layout because a seed's history "is interleaved with 300 others on adjacent lines", and therefore that the verb is *enabled* by the storage change.

That is true of the raw diffs and false of the history. A seed is one line, so materialising `.seeds/seeds.jsonl` at each commit and pulling the record by id yields a clean per-seed revision list with real dates and authors. **Measured 2026-08-31: 113 commits walked for one seed in 1.3 s**, producing exactly the render seeds-bp0s asked for:

    2026-08-25  Ryan Duryea   content,created_at,id,relationships   chore(seeds): capture seeds-lcfa — Dolt as s
    2026-08-26  Ryan Duryea   content,updated_at                    docs(seeds): correct the beads-has-no-Dolt-r
    2026-08-31  Ryan Duryea   content,title,updated_at              chore(seeds): attribute Ryan as @aguynamedry
    2026-08-31  Ryan Duryea   title,updated_at                      fix(seeds): restore the 83 titles clobbered

The last two rows are the title incident (seeds-wurl) and its repair, surfaced automatically.

## Consequence: the verb reads two sources, and the conversion does not need to replay history

The problem this dissolves: writing 306 markdown files in one conversion commit gives every seed a one-entry history, orphaning ~113 commits of real deliberation on the day the format is supposed to make history *better*.

The expensive answer would be replaying the JSONL history as synthetic per-file commits. Rejected — it means ~113 fabricated commits appended to main in every repo that converts, and there is no honest way to do it that does not either rewrite history or lie about dates.

**The cheap answer: `seeds history` reads both sides of the conversion.** The seed's own file history back to the conversion commit, then the JSONL's history before it, joined into one list. The converter stamps `converted_at` so the reader knows where to switch. No synthetic commits, no rewriting, no per-repo flag, and the pre-conversion record stays exactly as truthful as it was.

**A constraint this creates, worth stating before someone tidies it away:** the JSONL stops being *written*, but its history remains load-bearing forever. It must never be filtered out of git history as cleanup. seeds-sdhc's ruling that "the single JSONL is killed outright" is about the working tree, not about the past.

## The remaining open question from seeds-bp0s

Granularity — per-commit versus per-section attribution via `git blame` — is deferred, not settled. Per-commit is what the measurement above implements and is enough to ship; `git blame` per section is a refinement that only becomes possible after conversion, and it should be judged on the real thing rather than in advance.

Relates to seeds-bp0s, seeds-sdhc, seeds-sdhc.1, seeds-wurl, seeds-152.5.
