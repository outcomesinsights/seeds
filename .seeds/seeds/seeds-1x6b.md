---
id: seeds-1x6b
title: "First external bug report (@markdanese): one bad JSONL record silently froze sync for a month, and doctor said it was fine"
status: captured
type: concern
created_at: 2026-08-28T13:05:57.565844+00:00
updated_at: 2026-08-31T20:02:46.548093+00:00
tags:
  - bug
  - sync
  - import
  - doctor
  - silent-failure
  - data-integrity
  - external-report
  - 2026-08-28
  - markdanese
relationships:
  - target_id: seeds-3uir
    rel_type: questioned-by
    created_at: 2026-08-28T13:06:03.709179+00:00
  - target_id: seeds-tct2
    rel_type: questioned-by
    created_at: 2026-08-28T13:06:03.826598+00:00
  - target_id: seeds-hao9
    rel_type: questioned-by
    created_at: 2026-08-28T13:06:03.948228+00:00
  - target_id: seeds-dgyw
    rel_type: relates-to
    created_at: 2026-08-28T13:28:43.205699+00:00
  - target_id: seeds-h9cl
    rel_type: relates-to
    created_at: 2026-08-28T13:59:44.681781+00:00
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-08-28T16:33:00.455262+00:00
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-08-28T17:09:42.703585+00:00
  - target_id: seeds-lyej
    rel_type: relates-to
    created_at: 2026-08-29T02:28:28.585699+00:00
  - target_id: seeds-wurl
    rel_type: relates-to
    created_at: 2026-08-31T20:05:40.576442+00:00
  - target_id: seeds-sdhc.1
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.513012+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

The first bug report seeds has received from someone other than its author. Relayed by @aguynamedryan from @markdanese, verbatim:

> "Your first seeds bug report."

> "Seeds sync had been silently broken since July 22 — an agent in those sessions invented a context seed type the CLI doesn't support, so every sync since failed and this machine's DB was 40 seeds behind. Fixed: converted those 11 records to exploration, upgraded the CLI (0.3.3 → 0.5.0), resynced — 156 seeds, doctor clean."

Roughly five weeks of deliberation not reaching his database, discovered by accident.

## Reproduced at HEAD

Not a 0.3.3 problem that 0.5.0 fixed. In an isolated SEEDS_DIR with a JSONL of four records, the second carrying seed_type "context":

- `seeds sync` dies with an uncaught `ValueError: 'context' is not a valid SeedType` and a raw Python traceback. It exits 1, so a script would notice, but a human sees a stack trace with no record ID and no instruction.
- **The two good records AFTER the bad one never import.** `import_records` walks the file in order and `SeedType(data["seed_type"])` raises on the way through, so one poison line permanently blocks every record below it. This is the mechanism behind "40 seeds behind" — it is not a count of what broke, it is a count of everything filed after the first bad line.
- **`seeds doctor` printed "✓ JSONL is up to date", "✓ 7 passed", and exited 0** while the database held 1 of the 4 records in the file.

## The real defect is the health check, not the enum

The enum error is loud. What made this last five weeks is that the tool you run to ask "is my sync healthy?" answers from a proxy. cli.py's sync check is:

    if jsonl_mtime >= db_mtime:  check_pass("JSONL is up to date")

It compares mtimes and never looks at content. That is not merely weak — it is anti-correlated with this failure. A failed import leaves the JSONL holding records the DB lacks, i.e. JSONL newer than DB, which is exactly the state doctor certifies as healthy. @markdanese's "doctor clean" after the repair proves nothing; doctor was clean throughout the outage too.

This is the failure mode the data-pipeline standard already warns about in another context: the stale-check is itself code that can be silently wrong, and measuring a convenient proxy reports green while the artifact is broken. seeds has its own instance of it.

## Where the bad record came from

The CLI cannot create one — `seeds create --type context` is rejected by Click's choice validation. So an agent wrote `.seeds/seeds.jsonl` directly, or fed hand-authored JSONL through `seeds import`. The JSONL is a plain text file in a repo that agents edit; that is the unvalidated door, and it will be used again.

Note what this means for @markdanese's fix: converting the 11 records unblocked him, but nothing stops the next invented type from freezing his sync the same way, just as quietly.

## Open design questions (see attached)

Three forks worth settling before any code: what an unrecognized type should do to the record and to the rest of the import; whether doctor should compare content and fail loudly; and whether import should be transactional. Related: [[seeds-cyy]] covers import/round-trip docs.
