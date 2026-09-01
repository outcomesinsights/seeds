---
id: seeds-lcfa.4
title: "Python-friendly alternatives to Dolt: cr-sqlite, the SQLite session extension, and git-as-merge-engine"
status: captured
type: exploration
parent: seeds-lcfa
created_at: 2026-08-26T03:51:50.041008+00:00
updated_at: 2026-08-26T20:23:54.885659+00:00
tags:
  - alternatives
  - crsqlite
  - crdt
  - session-extension
  - apsw
  - sqlite
  - merge
  - python
  - researched
  - 2026-08-25
relationships:
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-08-28T16:33:00.104473+00:00
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-08-28T17:09:43.051031+00:00
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.537186+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Asked whether something Dolt-like exists that is friendlier to Python. Researched 2026-08-25. Short answer: nothing gives the FULL Dolt package (branches + cell merge + SQL time travel) embedded in Python, but two options give the merge half, and a third gets both halves with no new dependency at all.

FIRST, THE NEGATIVE RESULT, now sourced rather than assumed:
- doltpy is DEPRECATED. DoltHub's own guidance is to start `dolt sql-server` and connect with any Python MySQL client, using Dolt stored procedures and system tables for the version-control features. That is exactly the server-lifecycle cost in the ledger (seeds-lcfa.3).
- doltcli / lumicks-doltcli wrap the CLI and shell out; last release July 2023. Unmaintained, and it inherits the measured ~90 ms per invocation.
- Surveying the 2026 field (TerminusDB, immudb, lakeFS, DuckDB, chDB) turns up no embedded Python database combining versioning, time travel, and merge. Dolt remains close to unique in cell-wise diff and merge, and it is Go.

OPTION A — cr-sqlite (vlcn-io/cr-sqlite). The closest thing to "Dolt's merge, minus Dolt."
A runtime-loadable SQLite extension that upgrades a table to CRDT-backed storage, letting independently-written databases merge without conflicts. Because it is a plain SQLite extension it works from any language that can load one — Python included, via `sqlite3.Connection.load_extension()`. Actively maintained, corporate sponsorship (Turso, Fly.io, Electric SQL, Expo, Reflect).
- Gets us: convergent multi-writer merge at cell granularity. That is exactly the correctness core of problem 2 in seeds-lcfa.1.
- Cost: a compiled extension per platform (a .so/.dylib to ship or build), so the wheel stops being pure Python — but this is a few MB, not 120.
- The real design mismatch to think through: cr-sqlite syncs by exchanging CHANGESETS between peers, not by merging a file in git. Making it fit our model means exporting changesets to something git-tracked and applying them on pull — a different sync design than today's export-whole-file. Worth noting CRDT convergence means it never reports a conflict; it silently picks a winner by CRDT rule. That is better than today's silent whole-record LWW (it is at least per-cell and deterministic across hosts), but it is NOT the "surface a real collision for a human to resolve" behaviour Dolt gives.

OPTION B — the SQLite session extension, via APSW.
Session is part of SQLite itself: it records changesets and applies them to another database with a conflict handler, explicitly modelled on patch and on version-control merge. Python's stdlib `sqlite3` does not expose it; APSW (rogerbinns/apsw) does, including the full conflict-type vocabulary (DATA, NOTFOUND, CONFLICT, CONSTRAINT, FOREIGN_KEY) and the OMIT/REPLACE/ABORT responses. APSW is actively maintained and versioned in lockstep with SQLite.
- Gets us: real conflict DETECTION with a handler we control — a human-resolvable conflict rather than a silent drop.
- Cost: swapping `sqlite3` for `apsw` (9 sqlite3 call sites, so small), plus designing the changeset exchange, plus APSW as a compiled dependency.
- Known sharp edges to test rather than trust: reported quirks where REPLACE yields SQLITE_CONSTRAINT with no change applied, and OMIT deletes the row. If we go here, the conflict handler needs hand-built test fixtures with hand-computed expected results.

OPTION C — make git the merge engine: one file per seed. No new dependency whatsoever.
Replace the single `seeds.jsonl` with a directory of per-seed files, and let git merge them. Merge granularity becomes exactly the file/line split we choose, so two hosts editing different seeds never touch the same file, and two hosts editing different FIELDS of one seed touch different lines and merge cleanly. A genuine same-field collision becomes an ordinary git conflict in a readable text file that a human or an agent can resolve — which is the behaviour we actually want and the one CRDTs deliberately do not give.
- It also delivers the on-thesis history win from the ledger for free: `git log -p -- .seeds/seeds/<id>.md` IS the field-level evolution of that seed, with authorship and dates, no `dolt_log` required.
- It makes the SQLite DB a pure derived index, rebuildable from files at any time. That kills the "which side is the source of truth, and did I remember to import" ricketiness at its root rather than papering it with hooks.
- Costs: the export/import layer gets rewritten, `seeds.jsonl` consumers change, and a directory of hundreds of files is a bigger git surface than one line-per-record file. Also loses the single-file convenience for anything that reads the JSONL wholesale.

HOW THEY RANK AGAINST THE ACTUAL PAIN (seeds-lcfa.1):
Option C addresses both problems at once and adds no dependency, and it is the only option that also delivers the history win. Option B is the surgical fix if we want to keep one DB file and just stop losing edits. Option A is the most powerful merge but its convergence model conflicts with wanting a human to see a collision. All three are strictly cheaper than 120 MB, and none of them require Go.


--- SOURCES (recorded 2026-08-26; the research was done 2026-08-25 and the
    links were left in the session instead of the seed) ---

The negative result on Python bindings above was sourced, not assumed. The
citations:
- doltpy (deprecated): https://github.com/dolthub/doltpy
- doltcli (last release July 2023): https://github.com/dolthub/doltcli
- DoltHub's supported-clients guidance, which is what redirects Python users to
  `dolt sql-server` plus any MySQL client:
  https://docs.dolthub.com/sql-reference/supported-clients/clients
- cr-sqlite: https://github.com/vlcn-io/cr-sqlite
- Simon Willison's build/run notes on cr-sqlite:
  https://til.simonwillison.net/sqlite/cr-sqlite-macos
- SQLite session extension: https://sqlite.org/sessionintro.html
- APSW: https://rogerbinns.github.io/apsw/apsw.html

Nothing in the survey has changed as of 2026-08-26 - this is a citation
backfill, not a new finding. The one thing worth re-checking before any decision
rests on it is whether doltpy or doltcli has moved, since both were already
stale when surveyed and a revival is the only development that would reopen
option 2 in the ledger (seeds-lcfa.3).
