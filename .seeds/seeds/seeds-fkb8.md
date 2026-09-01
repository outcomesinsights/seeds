---
id: seeds-fkb8
title: "The storage smell named precisely: the derived store is authorized to destroy the durable one, and JSONL is the wrong format for a file agents edit"
status: captured
type: exploration
created_at: 2026-08-28T16:32:53.991031+00:00
updated_at: 2026-08-31T20:02:48.672541+00:00
tags:
  - storage
  - sqlite
  - jsonl
  - per-seed-files
  - format
  - agents
  - data-loss
  - critique
  - 2026-08-28
relationships:
  - target_id: seeds-lcfa
    rel_type: relates-to
    created_at: 2026-08-28T16:32:59.990049+00:00
  - target_id: seeds-lcfa.4
    rel_type: relates-to
    created_at: 2026-08-28T16:33:00.104473+00:00
  - target_id: seeds-lcfa.6
    rel_type: relates-to
    created_at: 2026-08-28T16:33:00.221537+00:00
  - target_id: seeds-lcfa.6.1
    rel_type: relates-to
    created_at: 2026-08-28T16:33:00.336067+00:00
  - target_id: seeds-1x6b
    rel_type: relates-to
    created_at: 2026-08-28T16:33:00.455262+00:00
  - target_id: seeds-dgyw
    rel_type: relates-to
    created_at: 2026-08-28T16:33:00.569601+00:00
  - target_id: seeds-183
    rel_type: relates-to
    created_at: 2026-08-28T16:33:00.683797+00:00
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-08-28T17:09:42.584115+00:00
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.079982+00:00
  - target_id: seeds-wurl
    rel_type: relates-to
    created_at: 2026-08-31T20:05:40.699629+00:00
  - target_id: seeds-sdhc.1
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.266165+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan reopened the storage question on 2026-08-28 after @markdanese's bug report (seeds-1x6b), asking for critique of a proposal: drop SQLite entirely, make git-tracked JSONL (or per-seed JSONL files) the single source of truth, and use DuckDB when database-shaped queries are needed. This seed is the critique.

## Three premises in the framing needed correcting

Established by a parallel session's repro at HEAD and by reading the code, not assumed:

- **"Nothing pushes JSONL changes into seeds" is false.** `seeds sync` imports JSONL -> DB and then exports (cli.py:1558). The push-back path exists and is exactly what broke. The accurate complaint is that nothing validates the file and the import aborts on the first unparseable record.
- **The incident was not a silent overwrite.** `SeedType("context")` raised an uncaught ValueError; `import_records` walks the file top to bottom, so it died there and every record below never imported. "40 seeds behind" is not a count of what broke — it is everything filed after the first poison line.
- **No data was lost.** The JSONL held the complete copy; the DB was the deficient side.

## The reframe that matters — and it strengthens the proposal

**On 0.3.3, the crash is what saved @markdanese's data.** The import died, so the export never ran. Had the import instead skipped that record silently, the export would have rewritten the JSONL wholesale from a database forty seeds stale and destroyed five weeks of deliberation. The fragility and the safety were the same line of code.

So the defect is not "two sources of truth drift apart." Stated precisely:

> **The derived store is authorized to overwrite the durable one wholesale, and no cheap check tells you when it has gone stale.**

Every export is a full-file rewrite from the DB. Any condition that leaves the DB stale converts the next *successful* export into a deletion event. seeds survived this one by crashing rather than by design. The v0.5.0 divergence guard (bfb518e) narrows the window but does not change the shape: it guards the export while the import crashes first, and it did not exist on @markdanese's 0.3.3 at all.

This is the real argument for files-as-truth: it removes the derived store from the write path entirely, rather than adding another guard to it.

## Critique: "a JSONL or a set of JSONL files" are not variants of one idea

The difference is the whole design, and the single-file option preserves the defect intact:

- **Single file:** every write rewrites all ~300 records; an agent editing one seed rewrites a file holding 299 others; two hosts editing different seeds collide on adjacent lines. The destruction surface is unchanged.
- **Per-seed files:** a stale writer can destroy one seed rather than the corpus; different-seed edits never touch the same file, so git merges them cleanly; a genuine same-seed collision surfaces as an ordinary git conflict a human or agent can read.

**The single-file JSONL is the problem; SQLite is merely what makes that file derived.** Already recorded as seeds-lcfa.4 option C (recommended, git as the merge engine) and prototyped in seeds-lcfa.6.

## DuckDB: already measured, and the answer is no — for storage

seeds-lcfa.6, measured on titan 2026-08-25 against a scratch copy:
- 280 seeds: pure Python 47 ms, DuckDB 60 ms
- 5,040 seeds: pure Python 297 ms, DuckDB 427 ms

Python wins at both scales because the work is file I/O, not query planning, and `seeds show <id>` degenerates to a single file read rather than a scan. So "drop SQLite" does not mean "swap in DuckDB" — it means **delete the persistence layer**.

DuckDB's genuine place is cross-project querying (seeds-183): 13 repos, 1,161 seeds, 57 ms — and it already works on today's single-file JSONL with no code change and no dependency, by invoking the CLI. Ship a recipe, not a 21 MB wheel.

## The argument nobody had named: the format is the public API

**If files are the source of truth and agents edit them natively, the on-disk format becomes the public API — and JSONL is a bad API for that.**

A seed's content is multi-paragraph markdown. In JSONL it is a single line with every newline escaped. That is the artifact every stranger's agent would be asked to hand-edit correctly, and @markdanese's incident began with precisely that write. @aguynamedryan's own observation is the durable constraint here: agents reaching into data files is native behaviour, and the training that suppresses it is per-owner and does not travel. Design for the agent that has never read the docs.

Markdown-with-frontmatter per seed (`.seeds/seeds/<id>.md`) makes a correct edit the default rather than a lucky outcome: content is the body with no escaping, `git diff` is readable, and `git log -p -- .seeds/seeds/<id>.md` IS the seed's field-level evolution — the history win seeds-lcfa.4 noted, for free and with no Dolt.

**So the decision to settle is not "drop SQLite." It is: what on-disk format survives being edited by an agent that has never read our docs?** Answer that and the storage question largely dissolves — the store follows from the format, not the other way round.

## Pushback on sequencing — the one place I would slow this down

An incident is the best moment for a guardrail and the worst for a rewrite. Both of these are true at once:

- The architecture change *eliminates the class*, and with two users this is the cheapest it will ever be to do.
- Shipping a storage rewrite hot to the user who just got burned is how incident #2 happens. seeds-02ur (36 orphaned rows from the v2 question-seeds migration) is standing evidence that migrations here leave debris.

Proposed order:

1. **`seeds doctor` must compare content, not mtimes.** It compares `jsonl_mtime >= db_mtime` and never reads the file, which is *anti-correlated* with this failure: a failed import leaves the JSONL newer than the DB — exactly the state doctor certifies as healthy. It was clean throughout the five-week outage, and it printed "✓ JSONL is up to date" for me on 2026-08-28 with no way for me to know whether that was true. This is the highest-value fix and it is independent of the architecture decision. It is also a textbook instance of the failure the data-pipeline standard already warns about: a stale-check measuring a convenient proxy and reporting green while the artifact is broken.
2. **Then the format decision** (markdown+frontmatter vs JSONL per seed), with the FTS usage question from seeds-lcfa.6.1 answered first — and that one is a usage question, not a technical one.
3. **Then the store removal**, which by then is mostly mechanical.

## On FTS, honestly

seeds-lcfa.6.1 calls it the one real casualty and is right. One data point from 2026-08-28: `seeds suggest` surfaced seeds-74.2/74.2.1 on a query written for this session, prior art neither participant had in context — a genuine win. But the match was a four-word title/tag overlap that substring-plus-recency would almost certainly have found too. At ~300 seeds, ranking is a convenience rather than a capability. Noting this cuts against my own preference: ranked search is nicer to use, and it still does not justify keeping a store.

Relates to seeds-lcfa, seeds-lcfa.1, seeds-lcfa.4, seeds-lcfa.6, seeds-lcfa.6.1, seeds-1x6b, seeds-dgyw, seeds-183.
