---
id: seeds-9gr8
title: The converter's v1 remediation names a command that cannot be run, and the nearest one that can destroys the store
status: captured
type: concern
created_at: 2026-09-09T19:29:34.691858+00:00
updated_at: 2026-09-09T19:29:34.691858+00:00
tags:
  - convert
  - legacy
  - remediation
  - data-loss
  - 2026-09-09
---

Found 2026-09-09 while reviving two dormant `experts/` repos on titan. The
converter refuses a v1 JSONL and tells the operator how to fix it. The
instruction it gives cannot be followed, and the nearest thing that can be
followed **destroys the store**.

## What it says

```
line 1 is format_version None, and the converter reads version 2 only. A v1
record has to be migrated first, and seeds no longer can: `seeds import` was
the migration ... Run `uvx seeds==0.6.1 import` against this file, then convert
```

## Why that cannot work, measured

- **`seeds` is not on PyPI.** `uvx seeds==0.6.1` fails outright:
  `Because there is no version of seeds==0.6.1 ... your requirements are unsatisfiable`. The repo is private and has never been published.
- **0.6.1 was never released.** The tags are v0.5.0, v0.6.0, v0.7.0a2. The
  version named in the advice does not exist in any form.
- **Built from the local tag, `import` does nothing.** `uvx --from git+file:///…/seeds@v0.6.0 seeds import` against seer's store:
  `Imported: 0 created, 0 updated, 7 skipped` — every record skipped, because
  the DB rows are fresher than their JSONL records and import is
  last-write-wins.
- **`sync` — the obvious next thing to reach for — CRASHES AND TRUNCATES.**
  `seeds sync` on the same store dies with `sqlite3.OperationalError: no such table: relationships`, and leaves `seeds.jsonl` at **zero rows**. Run on a
  scratch copy, so nothing was lost. Run on the real store, following this
  advice, it would have emptied the file whose history is the only record of
  everything before `converted_at`.

That last one is the reason this is a defect rather than a typo: the advice
sends an operator toward a command that eats the data the message is trying to
protect.

## What actually works, and what the advice should say

Both stores converted cleanly once the v1 JSONL was set aside:

1. Check the JSONL holds no id the database lacks — for both stores it held
   exactly the same 7 and 158 ids, so the database was a superset.
2. Retire the v1 JSONL: `git rm --cached .seeds/seeds.jsonl && rm .seeds/seeds.jsonl`. Its git HISTORY stays, which is what `seeds history`
   reads for anything before a seed's `converted_at`.
3. `seeds convert`, which then reads the database alone — and, since the same
   day's fix, carries the legacy `questions` table across instead of dropping
   it.

Where the JSONL holds ids the database does not, there is no automated path and
the message should say so rather than name a command.

## The shape worth remembering

A remediation string is code that never runs. Nothing type-checks it, no test
exercises it, and it rots the moment the thing it names moves — here it named a
version that was never cut, of a package that was never published, and it had
presumably never been executed by anyone. The same is true of every "run X to
fix this" in the codebase.

Worth a `check`-style audit of remediation text: every command a message tells
an operator to run should be one somebody has actually run.
