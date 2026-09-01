---
id: seeds-ebg1
title: "Adversarial review of the append-only storage proposal: git is already the append-only store, and materializing it in the working tree bills every future reader"
status: captured
type: concern
created_at: 2026-08-28T17:09:27.758353+00:00
updated_at: 2026-08-31T20:02:48.379782+00:00
tags:
  - storage
  - append-only
  - adversarial-review
  - context-cost
  - git
  - validation
  - 2026-08-28
relationships:
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-08-28T17:09:42.584115+00:00
  - target_id: seeds-1x6b
    rel_type: relates-to
    created_at: 2026-08-28T17:09:42.703585+00:00
  - target_id: seeds-dgyw
    rel_type: relates-to
    created_at: 2026-08-28T17:09:42.816681+00:00
  - target_id: seeds-lcfa.6.1
    rel_type: relates-to
    created_at: 2026-08-28T17:09:42.933080+00:00
  - target_id: seeds-lcfa.4
    rel_type: relates-to
    created_at: 2026-08-28T17:09:43.051031+00:00
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.197703+00:00
  - target_id: seeds-bp0s
    rel_type: relates-to
    created_at: 2026-08-28T17:57:43.983308+00:00
  - target_id: seeds-lyej
    rel_type: relates-to
    created_at: 2026-08-29T02:28:28.699948+00:00
  - target_id: seeds-wurl
    rel_type: relates-to
    created_at: 2026-08-31T20:05:40.886339+00:00
  - target_id: seeds-sdhc.1
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.387636+00:00
  - target_id: seeds-sdhc.2
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.767259+00:00
  - target_id: seeds-sdhc.4
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.474691+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

An adversarial agent was commissioned 2026-08-28 (at @aguynamedryan's explicit request) to attack the directory-per-seed + timestamped-entries proposal explored in seeds-fkb8. It read the storage seeds, the incident report, and the source. Its findings are recorded here because several of them change the decision, and two are live defects at HEAD.

## The verdict that reframes the proposal

**Git is already the append-only store, and building a second one in the working tree pays for the history twice.** `git log -p -- <path>` costs zero tokens until someone asks for it. An entry file costs tokens on *every* read, forever, whether or not the text is still true. seeds-lcfa.4 already claimed the history win as free via `git log -p`; materializing entries in the working tree is taking that win and paying for it anyway.

Measured on this corpus: 300 records, 506,510 chars of content — roughly **127k tokens for the whole corpus**. Median seed 960 chars, p90 4,599, max 15,024. Append-only guarantees that number rises monotonically, per seed, forever, against an owner who is currently hitting weekly token limits.

**The proposed resolution: a mutable head plus an append-only archive.** One rewritable "current understanding" file per seed that `seeds show` and grep read by default; timestamped entries that are append-only and read only on demand (`--history`, `--since`). Audit trail kept, git-diff readability kept, default read bounded. The commit hook then guards entries only, and rewriting the head becomes the normal verb rather than the thing you confirm.

This is better than either position in the discussion it reviewed: stronger than pure append-only (which bills every reader) and stronger than the supersession-marker idea (which keeps retracted text in the default read path).

## Two live defects at HEAD, both verified

**1. `seeds-fkb8` existed only in the gitignored `.seeds/seeds.db`.** The seed carrying this entire deliberation's argument for durability was sitting in the volatile half, never exported, never committed. Caught by the agent, confirmed, and flushed. Doctor *did* warn ("JSONL may be stale") — the peer session had replaced the mtime check with an ID-set comparison earlier the same day, which is what made it visible.

**2. @markdanese's bug still reproduces verbatim, with `status` instead of `seed_type`.** `SeedStatus` remains a closed `Enum` (`models.py:15`) parsed eagerly at `export.py:460` and `export.py:510`. `seed_type` was opened to an arbitrary string; `status` was not. A record carrying `"status": "in-progress"` kills `seeds sync` with a raw ValueError and every record below it never imports — the exact five-week failure, unfixed.

**3. A permanent deadlock, reproduced.** An agent appends to a record's `content` in the JSONL without bumping `updated_at` — the single likeliest direct-edit shape. Import skips it (not strictly newer, `export.py:533-560`); export refuses it (DB content no longer prefixes disk content, `export.py:215`); `seeds sync` exits 1 forever until a human hand-merges. Doctor reports agreement throughout, because its check compares ID *sets* and never content — while `find_divergence`, which detects exactly this, sits unused in the same codebase. The mtime proxy was replaced by an ID proxy; it is a better proxy and still a proxy. The printed remediation asks for the entire body pasted back through argv, which on a 15KB seed is both a token bill and a truncation risk.

## Failure modes of directory-per-seed nobody had named

- **Add/add conflicts.** Two entries created in the same second, or on two hosts, collide on one filename. Git cannot auto-merge two blobs at one new path, and the cheapest resolution an agent reaches for — `git checkout --ours` — silently destroys a whole entry. That is precisely the loss append-only exists to prevent, reintroduced at the merge layer. Adding a host/random discriminator fixes it and breaks chronological filename ordering, which the design assumes.
- **No delete verb exists.** `db.delete_seed` (`db.py:477`) has no callers outside its module and there is no CLI command. Under files, `rm -rf <seed-dir>` becomes the delete verb by default, and a hook watching only `M` waves wholesale destruction through. Gate `D` and `R` as well, and name the sanctioned delete verb first.
- **Relationships are stored twice with no symmetry check.** 509 rows for ~255 logical edges. `seeds link A B` becomes two directory writes with no transaction; a crash or a one-sided merge yields a half-edge that renders from A and not from B, with doctor's orphan check reporting clean. Storing each edge once instead means `seeds show` needs a corpus scan — contradicting seeds-lcfa.6's "`seeds show` becomes one file read".
- **`rename-prefix` becomes structurally illegal** — it rewrites every ID reference inside every body (`db.py:1061`) and is already the sole caller passing `allow_divergence=True`.
- **Redaction fights the hook.** A pasted secret would live in the working tree *and* in history, and the only repair — deleting the entry file — is exactly what the hook flags.
- **Clock skew loses its guard.** `FUTURE_TIMESTAMP_TOLERANCE` (`export.py:23-34`) exists because a future timestamp poisons a seed permanently. Delete the import and that check has no home; a future-dated entry sorts last forever with nothing detecting it.

## The best missed opportunity

**Reconstruct the entry log from git history.** 96 commits have touched `.seeds/seeds.jsonl`, one line per record, so every commit's diff for a given ID yields the exact appended text with a real date and a real author. That builds a genuine entry log with genuine provenance from data that already exists — and lets the new layout be built and inspected against real history *before* anything is committed to. It also makes `seeds show --since <my-last-read>` real: head plus only what is new, which is the frugality answer.

Also surfaced: per-entry authorship free via `git blame`; entry-level addressing (cite `seeds-lcfa.6#3` instead of paying for a whole 15KB seed — the frugality tax in its purest form); and `has_been_edited()` becoming `len(entries) > 1` instead of the timestamp-equality hack guarded by a `UNSET_TIMESTAMP` sentinel (`models.py:510`).

## Assumptions it caught in both participants

- **The observed incident was an agent doing something the CLI refused.** `seeds create --type context` was rejected by Click, so the agent went around it. That gap has since been closed twice — the vocabulary opened, and `seeds update --type` added, whose own docstring (`cli.py:1060`) says its absence "is how the malformed records in seeds-1x6b got in". One data point of direct editing has already been converted into a missing verb. Count how often direct editing is the *only* way to do the thing before rebuilding storage around it.
- **seeds already behaves append-only.** `db_extends_disk`'s docstring records that **41 of 42** content-changing edits across 67 commits were literal appends. The discipline is already the practice, which weakens the claim that a new layout is what delivers it.
- **There has never been a second writer in this repo.** All 96 commits touching the JSONL have one author. Multi-writer merge is real for @markdanese and for cross-host use, but the observed pain here — twice — is **validation, not merging**. Do not price a rewrite as if it were the pain that actually happened.
- **"Files-as-truth removes the derived store from the write path"** removes *this* one; an FTS index or the cross-repo JSONL export puts one back. What actually changes is that derived stores stop being *authorized to write*. That is the real defensible thesis and it is far cheaper to reach than a rewrite.

## Search regressions not previously costed

Porter stemming is a casualty, not just ranking: ripgrep has no stemmer, so "merging" stops finding "merge". And the count-based ranking proposed in discussion is actively perverse — it ranks by churn, rewards the most-revised seed, and counts hits inside text that has since been retracted. What would be discarded is not bare bm25 but `suggest`'s bm25 × tag-overlap × recency with a dynamic noise floor (`db.py:1173-1262`), plus `sanitize_fts_query`, which exists because this project's hyphenated vocabulary was a syntax error to MATCH. If ranking survives, rank the head, not the archive.

## Recommended sequencing

1. **Fix what is broken at HEAD before any layout work** — doctor calls `find_divergence`; `import_records` accumulates per-record failures instead of raising; open or guard `SeedStatus` on read. That is the entire observed incident class, twice reproduced, in roughly 50 lines.
2. **Settle the parse policy for unrecognized field values on read**, because files-as-truth makes every command a parser — a bad value stops being a `sync` problem and becomes a `list` / `show` / `ready` / `prime` problem on every invocation. Unless reads go lenient, which is the silent wrongness this rewrite exists to escape.
3. **Reconstruct the entry log from the 96 commits** and look at the result before designing on top of it.
4. **Then** the layout — head + archive, edges stored once with a doctor symmetry check, `D`/`R` gated, and a named redaction verb.

Relates to seeds-fkb8, seeds-1x6b, seeds-dgyw, seeds-lcfa.6.1, seeds-lcfa.4.

## Both defects fixed at HEAD, one recommendation rejected (peer session, commit 55bf114, 2026-08-28)

Both reproduced exactly as described, then fixed:

- **`seeds doctor` now calls `find_divergence`**, so it is green exactly when `sync` succeeds — by construction rather than by a second approximation. A test asserts that property directly rather than the symptom. The ID-set check it replaced was itself a recent improvement over the mtime check; swapping one proxy for a better proxy was still a proxy.
- **`MalformedRecordError`** now names the record number, its id, the failing field, and how many records already landed, instead of a raw traceback.

**REJECTED, and the reasoning is load-bearing: "give `status` the same open vocabulary as `seed_type`" is wrong.** The asymmetry is deliberate, not an oversight. `seed_type` could open because only `question` carries behaviour — the other four are display strings. `SeedStatus` values *drive* behaviour: `list` excludes terminal seeds by default, `ready` and `blocked` filter on it, and the resolve/defer/abandon transitions switch on it. An arbitrary status string would break lifecycle logic **silently**, which is worse than the crash it replaces. So for status the whole fix is the import-fragility question, never an open vocabulary. Recorded here so this proposal is not made a third time.

**Deliberately not done:** accumulating failed records instead of raising. That is seeds-hao9, which @aguynamedryan left open on purpose; settling it via a defect report would have been settling it by stealth. What shipped is policy-neutral — the traceback was indefensible under either answer.

## New evidence that reframes seeds-hao9

**Today's behaviour is neither option that question poses.** An unreadable record aborts where it stands, so records *above* it are committed and records *below* are not — partial-import-then-abort. Transactional means all-or-nothing; best-effort means skip and continue; the current code does neither. Whichever way it lands, behaviour changes. That is a stronger and verified argument, replacing the vaguer "the import is fragile".

## The strongest concrete argument for the storage direction

**The content-divergence deadlock is a property of rewriting one file wholesale from a database — not a property of file-based storage.** Under per-seed directories with a mutable body and history read from `git log -p`, a body edit is just a file edit: there is no wholesale rewrite, so the failure mode does not exist to be guarded against.

This matters because of *provenance of evidence*. It comes from a defect that actually happened, twice, and was reproduced at HEAD — rather than from the multi-host merge scenario this repo has never experienced (all 96 commits touching the JSONL have a single author). The adversarial review warned specifically against pricing the rewrite as though merging were the observed pain. This is the argument that survives that objection.

## Still open

The divergence refusal's remediation still instructs the operator to run `seeds update <id> --replace -c '<on-disk text><newer text>'` — pasting an entire body through argv, which on a 15KB seed is both a large token cost and a truncation risk. Being filed separately.
