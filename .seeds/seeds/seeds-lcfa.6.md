---
id: seeds-lcfa.6
title: "Per-seed files + DuckDB: the split is right, but DuckDB is a cross-project READER, not a replacement store"
status: captured
type: exploration
parent: seeds-lcfa
created_at: 2026-08-26T03:58:49.667056+00:00
updated_at: 2026-09-01T15:56:08.830877+00:00
tags:
  - duckdb
  - per-seed-files
  - storage
  - sqlite
  - cross-project
  - measured
  - fts
  - 2026-08-25
relationships:
  - target_id: seeds-183
    rel_type: relates-to
    created_at: 2026-08-26T03:58:56.216433+00:00
  - target_id: seeds-42
    rel_type: relates-to
    created_at: 2026-08-26T04:01:42.547832+00:00
  - target_id: seeds-02ur
    rel_type: relates-to
    created_at: 2026-08-26T04:03:23.872421+00:00
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-08-28T16:33:00.221537+00:00
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.653428+00:00
  - target_id: seeds-29ar
    rel_type: relates-to
    created_at: 2026-09-01T15:56:08.828435+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Asked whether storing each seed as its own JSONL file would let DuckDB read the directory as a table and let us drop SQLite entirely. Prototyped and measured on titan, 2026-08-25, against a scratch copy of the real 280-seed database (never against .seeds/ itself).

IT WORKS, AND IT WORKS WELL. Exploded seeds.jsonl into 280 per-seed files; `read_json_auto('<dir>/*.jsonl', union_by_name=true)` reads them as one table in 54 ms and infers the schema perfectly — including `tags varchar[]` and `relationships struct(target_id varchar, rel_type varchar, created_at timestamp)`. Nested structure is handled natively, which is strictly better than SQLite, where relationships need their own table.

BUT DUCKDB IS NOT WHAT MAKES IT POSSIBLE. Measured, same 280 files:
- pure Python, read every file and filter: 47 ms total (most of it interpreter startup)
- DuckDB CLI, same query: 60 ms
At 18x scale — 5,040 synthesized seed files, 23 MB on disk:
- pure Python: 297 ms
- DuckDB: 427 ms
Python wins at both scales because the work is file I/O, not query planning. And a real CLI can beat its own baseline badly: `seeds show <id>` becomes ONE file read, not a scan of anything. So at the scale seeds operates at, "drop SQLite" does not mean "swap in DuckDB" — it means DELETE THE PERSISTENCE LAYER and read the directory. DuckDB earns no place in the hot path.

WHAT SQLITE IS ACTUALLY DOING THAT PYTHON IS NOT: full-text search. `db.py:159-190` defines a `seeds_fts` FTS5 virtual table plus insert/update triggers. That is the one genuine feature that disappears with the DB, and it needs an answer before anyone deletes anything: DuckDB's fts extension, a brute-force scan (fine at 280, tolerable at 5k), or a small inverted index rebuilt on write.

WHERE DUCKDB IS GENUINELY THE RIGHT TOOL — cross-project querying, which is exactly seeds-183. Measured: one statement globbing 13 repos under ~/projects/outins/, 1,161 seeds total, 57 ms, with `filename=true` yielding a repo column:
  SELECT regexp_extract(filename,'outins/([^/]+)/',1) AS repo, count(*), sum(status='captured')
  FROM read_json_auto('/home/ryan/projects/outins/*/.seeds/seeds.jsonl', union_by_name=true, filename=true)
  GROUP BY 1 ORDER BY 2 DESC;
Top of the list: code_set_catalog 393 seeds (212 open), seeds 280 (164), code_collector 163 (116), habituate 58 (41).
Two things follow. First, this is a real new capability neither SQLite-per-repo nor pure Python gives, and it answers a question already sitting open in seeds-183. Second and more important: IT ALREADY WORKS ON TODAY'S SINGLE-FILE JSONL. It needs no per-seed split, no schema change, and no code change — the duckdb CLI is already installed (v1.5.2). So this win is available immediately and is completely orthogonal to the storage decision.

DEPENDENCY NOTE: the duckdb Python wheel is 21 MB (1.5.5, cp313 manylinux). Six times smaller than dolt's 120 MB, but not nothing against a tool whose runtime dependency list is about to be just `click`. And since the cross-project win is achievable by invoking the duckdb CLI or documenting the query, it may need no dependency at all — ship a recipe, not an import.

COSTS OF THE PER-SEED SPLIT, measured: 280 files occupy 1.3 MB against the single JSONL's 572 KB — roughly 2.3x, from 4 KB block granularity on small files. 5,040 files reach 23 MB. Git handles thousands of small files without complaint (that is what a source tree is), but it is a larger working-tree surface and every seeds write becomes a file write plus a git-visible path.

INCIDENTAL FINDING while poking at the schema: the `questions` table holds 36 rows with legacy `q-XXXX` ids pointing at legacy `seed-XXXX` ids, created between 2026-01-28 and 2026-03-11. Neither id form appears anywhere in seeds.jsonl. I checked whether the content was lost before raising an alarm — it was not: the question TEXT is present in the JSONL, migrated to question-seeds under the v2 format. So those 36 rows are orphaned pre-migration leftovers, dead weight to drop, not data at risk. Worth cleaning up whenever the schema is next touched.

WHERE THIS LEAVES THE ARGUMENT: per-seed files were already option C in seeds-lcfa.4, recommended because git becomes the merge engine and `git log -p` becomes the per-seed history. This prototype adds that the SQLite removal it implies is real and cheap at our scale, that FTS is the only genuine casualty, and that DuckDB belongs in the story as a cross-repo reader answering seeds-183 rather than as the new store.
