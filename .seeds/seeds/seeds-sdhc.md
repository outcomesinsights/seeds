---
id: seeds-sdhc
title: "Storage direction after the Maildir turn: per-seed directories, a MUTABLE body holding current understanding, history from git log -p, and metadata as a collapse-log"
status: captured
type: decision
created_at: 2026-08-28T17:36:24.994445+00:00
updated_at: 2026-09-01T05:24:08.549827+00:00
tags:
  - storage
  - maildir
  - per-seed-files
  - mutable-head
  - metadata
  - git-history
  - merge-union
  - detection
  - context-cost
  - 2026-08-28
relationships:
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.079982+00:00
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.197703+00:00
  - target_id: seeds-lcfa.1
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.309903+00:00
  - target_id: seeds-lcfa.3
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.421897+00:00
  - target_id: seeds-lcfa.4
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.537186+00:00
  - target_id: seeds-lcfa.6
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.653428+00:00
  - target_id: seeds-lcfa.6.1
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.767861+00:00
  - target_id: seeds-183
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.880531+00:00
  - target_id: seeds-dgyw
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.991923+00:00
  - target_id: seeds-bp0s
    rel_type: relates-to
    created_at: 2026-08-28T17:57:43.869395+00:00
  - target_id: seeds-lyej
    rel_type: relates-to
    created_at: 2026-08-29T02:28:28.812679+00:00
  - target_id: seeds-wurl
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.011821+00:00
  - target_id: seeds-dv6r
    rel_type: relates-to
    created_at: 2026-09-01T05:24:08.547579+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Where the storage deliberation landed on 2026-08-28, after the critique in seeds-fkb8 and the adversarial review in seeds-ebg1. Direction and leanings, not a ratified build spec.

## The reversal: append-only is the WRONG direction for seed bodies

@aguynamedryan's position after reading the adversarial review, and it reverses the direction the discussion had been heading:

> "git log -p ... provides us the history, and we no longer have to be precious about append-only. And in fact, append-only is the wrong direction if we want context to represent current understanding."

The reasoning is **context economy, which is now a first-class constraint** (token burn roughly tripled; weekly limits being hit). A file that holds current understanding is smaller to read and leads to more correct conclusions than one that also carries every superseded position. Measured for scale: the corpus is ~506,510 chars of content, about **127k tokens**, and append-only guarantees that only grows.

**@aguynamedryan's own worked example.** The project once considered writing seeds in Go (for embedded Dolt), then abandoned it when Dolt was dropped. In normal conversation nobody should have to re-read the Go deliberation. If the question genuinely reopens, that is what the abandoned material is for — but it should not enter context by default.

## The shape: Maildir

Maildir (Bernstein, qmail, ~1995) is the proven prior art. Directory per unit; `tmp/`, `new/`, `cur/`.

**Lessons that transfer directly:**

- **Atomic write via rename.** Write the full file to `tmp/<name>`, then `rename()` into place. Rename is atomic on POSIX, so a reader never sees a half-written file. This is crash-safety without transactions — the answer to "what if seeds dies mid-write" once SQLite's atomicity is gone.
- **Unique names that cannot collide:** `<timestamp>.<pid>_<counter>.<hostname>`. Time alone is insufficient. **This is the fix for the add/add conflict** the adversarial review raised — two hosts writing in the same second produce different filenames, so git sees two adds at two paths and merges both rather than conflicting.

**The lesson that does NOT transfer: state in the path.** Maildir encodes state by renaming, and can do so because *nothing references a message by path*. Seeds reference each other constantly — 509 relationship rows, every citation by ID. See the pushback below.

## Layout as it stands

- **`body.md` — a mutable head.** Current understanding, rewritten freely. History via `git log -p -- seeds/<id>/body.md`. This is where the frugality win lives, because bodies are the large objects (median 960 chars, p90 4,599, max 15,024).
- **`metadata.jsonl` — an append-log with collapse semantics** (@aguynamedryan's proposal). Each line is a dated *partial* write; reading collapses them, most recent value winning per property. A seed created 2026-08-25 with `status: captured` and appended 2026-08-28 with `status: exploring` collapses to `exploring`, and the history is inline.

**Why append-only is right here and wrong for bodies: size and merge-need.** Metadata lines are ~200 bytes; twenty status/tag changes is ~4KB, so the "you pay for history on every read" objection that governs bodies does not bite. And it buys something bodies do not need.

## Verified: `merge=union` gives cell-level merge with no dependency

Tested 2026-08-28 on a scratch repo. With one line in `.gitattributes`:

    *.jsonl merge=union

two hosts appending different metadata lines merged with **zero conflict** — git concatenated both sides; collapse-by-timestamp then resolves order.

**This solves seeds-lcfa.1's problem 2**, the whole-record last-write-wins that silently discards one host's edit when two hosts touch different fields of the same seed. Under collapse semantics both survive, because each line carries only what it changed. That is cell-level merge — the one thing Dolt uniquely offered (seeds-lcfa.3) — obtained from a git config line, no 120 MB dependency, no Go rewrite.

**Carry-over requirement:** keep `FUTURE_TIMESTAMP_TOLERANCE` (export.py:23). Collapse-by-timestamp means a future-dated line wins forever, and seeds has been bitten by exactly this before.

## Pushback recorded: directory-as-state

@aguynamedryan leans toward encoding status in the directory structure (`captured/`, `resolved/`, `abandoned/`) so that abandoned seeds are demoted in search and never pollute context. The goal is right; the mechanism has two concrete costs:

- **It breaks the history mechanism just adopted.** A status change becomes a directory rename. `git log --follow` is the only way across a rename, it accepts only a *single file* path (not directories), and it is heuristic. A seed moving `captured/ -> exploring/ -> resolved/` has its history split across three paths, read by the very command chosen to be the history.
- **Path-from-ID is lost.** `seeds show seeds-147` can no longer compute a path; it must scan every state directory or consult an index — and an index is a derived store, reintroduced.
- Merge gets uglier: two hosts moving one seed to *different* states is a rename/rename conflict.

**Cheaper way to the same goal:** filter on the status field. Measured — reading only frontmatter/metadata across 300 seeds to filter by a field takes **8.8 ms**. Filtering costs milliseconds and keeps paths stable; moving files costs the history trail.

## Detection is the enforcement strategy

@aguynamedryan's strong lean, and it replaces prevention:

> "we should check to see if metadata is being violated somehow and whatever other adherence we might want to enforce ... a check that's easily done."

**A `seeds check` verb, called by a git pre-commit hook and by `doctor` — one implementation, two entry points, also runnable by hand.**

**Answering @aguynamedryan's question about write hooks: yes, agents bypass them.** Claude Code's `PostToolUse` hooks fire on the Write/Edit *tools*. An agent using `bash -c 'cat > file'`, `sed -i`, or a Python one-liner never touches those tools and never fires the hook — most of this very session ran through Bash. So tool-level hooks are advisory, and **the git pre-commit hook is the only durable gate**, because everything reaches a commit eventually.

Accepted limitation: pre-commit is detection *at commit*, not immutability. An agent can read corrupted state at any point before the commit fires. This is not closable, but it bounds damage to one working session rather than five weeks.

## Smaller rulings

- **No `delete` verb exists** (`db.delete_seed`, db.py:477, has no callers outside its module) and @aguynamedryan is content with that — but the hook must gate `D` and `R` in `git diff --name-status`, not just `M`, or `rm -rf <seed-dir>` becomes the de facto delete verb.
- **The single JSONL goes.** It does not vanish entirely: it survives *demoted* from source of truth to a published artifact, because the cross-repo query in seeds-183 (13 repos, 1,161 seeds, 57 ms) globs it. "Files are truth" and "still export a JSONL" are both true.
- **BM25 is implementable in-house.** FTS5 is `tokenize='porter unicode61'` (db.py:161) — Porter stemming plus bm25, not fuzzy and not semantic. Measured against grep on "context": FTS 77 hits, grep 72, and **grep found one FTS missed** (seeds-151.2, "contextual" — Porter has no `-ual` rule). For prefix-sharing English, substring grep is *broader* than Porter. What SQLite uniquely provides is ranking, not recall.

## The open question @aguynamedryan is genuinely unsure about

> "Are we shooting ourselves in the foot by suppressing the history or making it harder to reach? I don't know how useful it's been for seeds in the past."

He notes that when an agent cites a seed at him, he has never once considered whether it was historical or current understanding. **That is evidence for the head model** — if the distinction never mattered in practice, the history was not doing work in the default read path.

**The one specific failure to guard against: a head that records conclusions without their reasons invites re-litigation.** A head saying "Python" invites an agent to propose Go next month. A head saying "Python; Go was only ever on the table for embedded Dolt, which we dropped" immunizes it in one clause.

So the head is not a summary — it is a **distillation carrying enough *why* to prevent re-derivation**. That is exactly the shape of a trellis line, and seeds already has that verb. The head is a trellis for the seed itself.

Relates to seeds-fkb8, seeds-ebg1, seeds-lcfa.1, seeds-lcfa.3, seeds-lcfa.4, seeds-lcfa.6, seeds-lcfa.6.1, seeds-183, seeds-dgyw.

## CORRECTION (2026-08-28): the merge=union claim above is over-stated

The claim "this delivers cell-level merge — the one thing Dolt uniquely offered" is wrong as written. Split it:

- **Different fields, two hosts — a genuine win, and it is the actual complaint in seeds-lcfa.1 problem 2.** Host A changes tags while host B changes status; union merge lands both lines and collapse keeps both values. Today's whole-record LWW discards one of them silently. This part holds.
- **Same field, two hosts — NOT a win, and not Dolt parity.** Both lines land, and collapse-by-timestamp picks a winner **silently**. That is last-write-wins again, merely at field granularity instead of record granularity. Dolt's distinguishing behaviour is surfacing a genuine same-field collision as a conflict for a human to resolve, and union merge plus timestamp collapse does not do that.

So the honest claim is: **it upgrades whole-record LWW to per-field LWW.** Real, valuable, and much cheaper than Dolt — but not the same thing.

Worth noting this reproduces an error seeds had already documented about a different technology: seeds-lcfa.4 says of cr-sqlite that "CRDT convergence means it never reports a conflict; it silently picks a winner by CRDT rule ... that is NOT the 'surface a real collision for a human to resolve' behaviour Dolt gives." The same critique applies to timestamp collapse, and it was not noticed the second time around.

## The clock-skew hazard is worse than a carried-over constant

`FUTURE_TIMESTAMP_TOLERANCE` (export.py:23) exists because a future-dated record became **permanently authoritative**: every later local edit stamps `now`, which is earlier, so the poisoned record outranks all real work forever. Under collapse-by-timestamp this returns in full, and there is no longer an import step where the existing guard could run.

So the requirement is not "carry the constant over". **The collapse function itself must define what it does with a future timestamp** — refuse it, clamp it, or quarantine the line — and that has to be settled before collapse semantics are built, not after.

## The resolution: union merge is the transport, collapse is the POLICY

Git's union driver simply hands both sides' lines to us with no conflict. What happens next is entirely seeds' own code, so conflict-surfacing is recoverable rather than lost:

- If each metadata line carries a **host/writer id** (Maildir-style naming already requires one), collapse can detect that two *different hosts* set the *same field* with no causal ordering between them, and surface that as a conflict instead of silently picking.
- That recovers most of the behaviour Dolt was wanted for, in our code, with the git config line doing only the part git is good at.

The design consequence: **the metadata line schema must include a writer identity from the start.** Retrofitting it later means every pre-existing line is unattributable and collapse cannot distinguish "the same host edited twice" from "two hosts collided".

## CORRECTION (2026-08-28, later): "mutable head holding current understanding" is the wrong frame

@aguynamedryan's objection, and it is the strongest one raised in the whole deliberation:

> "If seeds now is attempting at all times to capture the current state of a seed, it feels like that is an effort to maintain a rolling summary of the deliberation. Isn't what a seed is really about."

**He is right.** The project's thesis is that the deliberation *is* the artifact, not the decision (seeds-176.9: "intent falls out of seeds — the decision is the easy downstream byproduct"). A continuously-rewritten head holding current understanding is a decision log — precisely what seeds exists not to be. And "the history is in `git log -p`" was oversold: reconstructing a deliberation from diffs is hard for a human, unnatural for an agent, and something no agent does unprompted, so anything pruned is *functionally* gone whatever git retains.

**The framing that replaces it: nothing is ever destroyed; the RENDER is what is selective.**

- The file **accumulates**. Deliberation piles up faithfully — which is already the working practice, as this very seed demonstrates.
- Superseded material is **marked, not deleted** — a `## Superseded` fold at the bottom, or a marker on a section.
- `seeds show` renders the live part by default; `seeds show --full` renders everything; `seeds history` renders the git evolution (see the separate seed for that verb).
- **Corrections are the sole exception that replaces.** A fact that turned out false is fixed in place, with the prior version in git. Carrying a wrong number forward costs context *and* risks an agent acting on it, so this is the one edit that should be destructive.

**The distinction that makes this work — corrections replace, reasoning accumulates.** "Dolt is 120MB" that turned out wrong gets fixed. "We wanted Dolt for cell-level merge and dropped it when git's line merge gave us the same thing" is never deleted — it is *why* the decision is what it is, and it is what stops the question being re-litigated. @aguynamedryan's own Go example proves it: the reasoning ("Go was only ever on the table for embedded Dolt") is one clause and stays forever; the paragraphs of Go tradeoffs compress, because the conclusion plus its reason carries them.

**Where frugality actually comes from in this model: the reader being selective, not the file being small.** That is @aguynamedryan's original position — the interface is where the guardrails live — arriving from the opposite direction. An agent that greps gets the whole file, but superseded material sits at the bottom under a clear heading, so even a naive read hits live content first.

**Consequence for `tend`:** the earlier framing — "accumulate during deliberation, then compress at tend time into conclusions" — made tending *an act of destruction*, the moment the journey is shredded and the verdict kept. @aguynamedryan recoiled at exactly this and was right to. Under the corrected model, tending never destroys; it marks supersession, reversibly and visibly in the diff. And `tend` may well be the wrong vehicle regardless: the agent that just learned an old claim was wrong is better placed to mark it superseded than a reviewer three weeks later. Open.

## The single JSONL is killed outright (@aguynamedryan, ruled)

Not demoted to a published artifact — **removed**. The claim in the body above that it "survives, demoted" is superseded.

**Measured at cross-repo scale, 2026-08-28:** 1,212 markdown files, frontmatter-only scan, **35 ms** — against the 57 ms the DuckDB-over-JSONL path measured for 1,161 seeds in seeds-lcfa.6. Reading the markdown directly is *faster* than the thing the JSONL existed to enable. The JSONL only ever looked necessary because it was already there.

So **seeds-183 needs a reader, not a file**: glob `~/projects/outins/*/.seeds/seeds/*.md` and parse frontmatter — the same code path as the local status filter, one implementation rather than two. If ad-hoc SQL is wanted later, **make the export a pipe, not a file**: `seeds export --json` to stdout, fed to DuckDB on demand. Nothing tracked, nothing to diverge, nothing to destroy.

## Two further simplifications from @aguynamedryan's pushback

**Single file per seed, not a directory.** Two files (body + metadata) meant two passes and ID bookkeeping to filter by status. YAML frontmatter at the top of `body.md` collapses it to one file and one ripgrep pipeline. Measured on the real corpus: `rg -l '<term>' $(rg --files-without-match '^status: abandoned' <dir>)` — **17 ms** across 303 files, one pass, no ID bookkeeping.

**Metadata in frontmatter, NOT a collapse-log.** The collapse-log was reinventing, worse, what git already does. Tested:
- two hosts change *different* frontmatter properties -> **merges cleanly**, both survive;
- two hosts change the *same* property -> **conflict surfaced** with markers for a human to resolve.

That second case is the Dolt behaviour that `merge=union` plus timestamp collapse could not deliver, and ordinary git line-merge gives it for free. It also deletes a hazard class: with no collapse-by-timestamp, **timestamps stop being authority**, so `FUTURE_TIMESTAMP_TOLERANCE` has no reason to exist rather than needing to be carried forward.

One format consequence: **frontmatter line granularity IS merge granularity.** `tags: [a, b, c]` on one line means two hosts adding different tags collide; a block sequence merges cleanly. Decide deliberately for the multi-value fields.

## Maildir was over-applied

@aguynamedryan: "Maildir is actually trying to solve a series of problems that I'm not concerned about." Correct. Its lessons — collision-proof names for many files per seed, state encoded in renames — were solving the *entry-file* problem, and entry files are gone. What survives is not Maildir at all but ordinary correct file writing: write to a temp file, `os.replace()` into position (atomic on POSIX). One line. Keep the technique, drop the framework.

## The design as it now stands

- `.seeds/seeds/<id>.md` — YAML frontmatter plus markdown body, accumulating, with a superseded fold
- History: rendered by seeds from git, not read raw from `git log -p`
- Merge: ordinary git line-merge; genuine collisions surfaced to a human
- Search: ripgrep, one pass, status filter inline
- **Gone:** SQLite, the tracked JSONL, entry files, per-seed directories, collapse semantics, the union driver, timestamp authority, `FUTURE_TIMESTAMP_TOLERANCE`, the content-divergence deadlock, and the wholesale-rewrite destruction surface

## Frontmatter multi-value fields: BLOCK sequences (@aguynamedryan, ruled 2026-08-28)

> "inline doesn't read better to my eyes -- blocks for frontmatter"

So `tags`, and any other multi-value field, use YAML block sequences:

    tags:
      - lodestone
      - storage

not `tags: [lodestone, storage]`. This is the reading-preference call, and it happens to be the better merge behaviour too: one value per line means two hosts adding different tags touch different lines and merge cleanly, where the inline form would collide on the single line.

## Release plan (@aguynamedryan, 2026-08-28)

- **0.6 — detection and doctoring only.** Everything that addresses the current architecture's failures ships here. Mostly already landed: 72 commits since v0.5.0, including `doctor` comparing content instead of mtimes and then calling `find_divergence` outright, `MalformedRecordError` naming the record that breaks an import, the open type vocabulary with `update --type` and `retype`, and two breaking guards on `sync` and `answer`.
- **0.7 — the storage format change.** @aguynamedryan dogfoods the conversion and sustained use on his own seeds **before any public release**.

**Requirement that falls out of dogfooding on this repo:** `.seeds/` here is the real design database, so the converter must be **re-runnable and non-destructive** — read the existing store, write the markdown tree alongside it, and never delete the source until @aguynamedryan says so. Reverting is then `rm -rf .seeds/seeds/`. seeds-02ur (36 orphaned rows left by the v2 question-seeds migration) is standing evidence that migrations here leave debris.

## The design is NOT finished — what still blocks 0.7

Settled: one file per seed, frontmatter with block sequences, no SQLite, no tracked JSONL, history rendered from git, nothing destroyed with supersession marked, corrections replace while reasoning accumulates, ordinary git line-merge, ripgrep search, atomic write via temp-plus-rename, export as a pipe.

Still open, roughly in the order they block each other:

1. **Parse policy for invalid field values on read.** The adversarial review put this before the layout, and it is right: files-as-truth makes *every* command a parser, so a bad value stops being a `sync` problem and becomes a `list` / `show` / `ready` / `prime` problem on every invocation. Going lenient reintroduces exactly the silent wrongness this change exists to escape. Related: seeds-hao9, whose current behaviour is partial-import-then-abort, which is neither option that question poses.
2. **The supersede marker's concrete form** — a `## Superseded` fold at the bottom, or a per-section marker. This determines the parser and what `seeds show` renders by default.
3. **Where relationships live.** 509 rows today. In the frontmatter of both ends means two writes with no transaction and the symmetry risk the review raised; in one end with the inverse derived means a corpus scan, which contradicts "`seeds show` is one file read".
4. **Child IDs as filenames.** 75 of 304 IDs are dotted (`seeds-lcfa.6.1`). Fine on every filesystem in play, but `get_children` becomes a glob that must exclude grandchildren, and it should be decided whether hierarchy lives in the filename or in frontmatter.
5. **Who marks supersession, and when.** `tend` was designed as a review-and-rule pass, but the agent that just learned a claim was wrong is better placed than a reviewer three weeks later.
6. **`seeds history`: summarise or only structure?** See seeds-bp0s — summarising is the same editorial hazard just avoided on disk.
7. **What `seeds check` checks**, and gating `D` and `R` in the hook, not just `M` — otherwise `rm -rf <seed-file>` is the de facto delete verb.
8. **The migration itself**, including whether to mine the 96 commits of `seeds.jsonl` history to reconstruct genuine per-seed history with real dates and authors.
