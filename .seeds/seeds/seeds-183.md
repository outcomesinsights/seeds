---
id: seeds-183
title: "seeds: do we need a single-location / cross-project way to query all seeds?"
status: resolved
type: question
created_at: 2026-06-23T20:43:33.749099+00:00
updated_at: 2026-09-01T15:56:08.968408+00:00
resolved_at: 2026-09-01T13:37:44.550977+00:00
resolution: "Answered (@aguynamedryan, 2026-09-01): NO single-location store is needed, and no new code. Measured from 14 months of transcripts: 35 genuine cross-repo seeds queries across 18 sessions — under one a day, and 9 of those were us building seeds rather than using it. Of the ~26 real ones, roughly 88% came from habitat sessions (codesets 13, vocabulary 5) or transcript work in oimnibus (5), which confirms @aguynamedryan's own hunch that this is habitat/transcript-seeds behaviour rather than a general seeds need.\n\nWhat decided it was reading what those commands actually DO. Nearly all are full-text search — 'grep -ci adjudicat' across repos, 'grep -rlno mark-review-2026-08-2[0-9]', 'grep -oiE .{100}(immutab|invalidate and replace)' across habitat members, and 'which members have .seeds'. Structured querying was 2-3 calls out of 26. So the demand was never for a queryable single store; it was for grep across many repos.\n\nAnd the 0.7 markdown tree serves that BETTER than the JSONL did: 'rg -l term ~/projects/outins/*/.seeds/seeds/' puts the seed id in the file path and gives real context lines, where the JSONL returned a 120-character slice of an escaped single line. Conversion is an upgrade for this workflow, not a break.\n\nResolution: document the rg recipe (in seeds prime and the habitat CLAUDE.md) and add nothing. 'seeds export --json' stays for the structured minority — it is a stdout pipe, so it costs no second store and no sync — but it is NOT load-bearing for cross-repo work, and its docstring currently over-claims that '13 repos of cross-project query depend on it'. That correction is filed.\n\nEfficacy: the seed did its job by staying open. Had it been closed by assumption in June, the answer would have been 'yes, build a store' — which is what the JSONL already was, and what this whole overhaul removed."
tags:
  - seeds-feature
  - cross-project
  - query
  - architecture
  - 2026-06-23
relationships:
  - target_id: seeds-181.2
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.518789+00:00
  - target_id: seeds-129
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.543013+00:00
  - target_id: seeds-181
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.646580+00:00
  - target_id: seeds-182
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.765221+00:00
  - target_id: seeds-lcfa.6
    rel_type: relates-to
    created_at: 2026-08-26T03:58:56.216433+00:00
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-08-28T16:33:00.683797+00:00
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.880531+00:00
  - target_id: seeds-29ar
    rel_type: relates-to
    created_at: 2026-09-01T15:56:08.966177+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Captured 2026-06-23 from docs/sower.txt. A seeds-the-project question, surfaced by sower's need to query many repos. Kept in this repo (it is about seeds, not sower).

Routing across many projects raises whether seeds should be restructured so all the information can be queried from one place:

> "Maybe do we need to restructure seeds so that we can more easily query just a single location for all this information? I don't know. ... I don't know how big of a how big of a database it needs to keep track of for seeds."

Options to explore:
(A) Leave seeds per-project; sower fans out and queries each repo's db/jsonl directly (possibly over SSH to remote servers).
(B) A router-side aggregation layer that indexes many repos into one queryable location; repos stay authoritative.
(C) A shared "global seeds sources" store — the new-concept option already floated in seeds-129 (approach 3) for multi-project source docs.
(D) Each repo emits only a self-summary (the separate self-summary feature) and the router aggregates summaries, not full databases.

Relates to the multi-project source-document concern (seeds-129).

## Related
seeds-129


--- ANSWERED IN PRACTICE (2026-08-25, out of the Dolt storage deliberation) ---

Yes, and it is already available with no code change and no new dependency. Measured on titan while prototyping seeds-lcfa.6: the duckdb CLI (v1.5.2, already installed) globs every repo's tracked JSONL into one table, with `filename=true` supplying the project column.

  SELECT regexp_extract(filename, 'outins/([^/]+)/', 1) AS repo,
         count(*) AS seeds,
         sum(CASE WHEN status='captured' THEN 1 ELSE 0 END) AS open
  FROM read_json_auto('/home/ryan/projects/outins/*/.seeds/seeds.jsonl',
                      union_by_name=true, filename=true)
  GROUP BY 1 ORDER BY 2 DESC;

Result: 13 repos, 1,161 seeds, 57 ms. code_set_catalog 393 (212 open), seeds 280 (164), code_collector 163 (116), habituate 58 (41), oimnibus 52 (40), outcomesinsights.github.io 50 (12), ohdsi_supplemental_vocabs 34 (8), vocabulation 31 (4), epc 30 (29), litmine 29 (23), pman 29 (15), vocabulary_formats 12 (9).

Schema inference is automatic and correct, including `tags varchar[]` and the nested `relationships` struct. `union_by_name=true` absorbs repos on different format versions.

WHAT THIS CHANGES ABOUT THE QUESTION: the cross-project view does not need a single location, a central server, a registry, or a new store. It needs a query over files git already tracks in every repo. That is a much smaller answer than this seed anticipated.

OPEN CHOICE, and it is a packaging question rather than a capability one: ship this as a documented recipe against the duckdb CLI (zero dependency), or as a `seeds` subcommand that imports duckdb (a 21 MB wheel against a runtime dependency list that is about to be just `click`). The recipe is the cheaper default; the subcommand only earns its weight if cross-project querying becomes routine.

Also worth noting for whoever picks this up: the repo list here is a hardcoded glob of ~/projects/outins/*. A real cross-project story needs to decide how projects are discovered — which is the same registry problem raised in the sower seeds (seeds-181.2).
