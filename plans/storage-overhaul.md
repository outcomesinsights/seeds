# Storage overhaul: SQLite + single JSONL → one markdown file per seed

Target release: **0.7**. Dogfooded on this repo and used in anger before any
public release.

This is the build plan. The deliberation behind it lives in seeds and is not
repeated here — `seeds-lcfa` and its children (the Dolt investigation and what
it ruled out), `seeds-fkb8` (the critique that named the smell), `seeds-ebg1`
(the adversarial review), `seeds-sdhc` (where the direction landed, including
two self-corrections), and `seeds-sdhc.1` through `.5` (the settlements this
plan builds from). `seeds-wurl` is the incident that set the bar for the
conversion and detection tooling.

## What is being replaced, and why

Today: SQLite (`.seeds/seeds.db`, gitignored) is the working store, and a single
tracked `.seeds/seeds.jsonl` is the durable one. The defect, stated precisely in
`seeds-fkb8`:

> The derived store is authorized to overwrite the durable one wholesale, and no
> cheap check tells you when it has gone stale.

Every export is a full-file rewrite from the DB, so any condition that leaves the
DB stale turns the next *successful* export into a deletion event. seeds survived
its one real incident by crashing rather than by design.

After: `.seeds/seeds/<id>.md` — YAML frontmatter plus a markdown body — is the
only store. Nothing is derived, nothing is authorized to overwrite anything, and
a same-seed collision on two hosts is an ordinary git conflict a human can read.

## The format

Settled. Freeze it in `docs/storage-format.md` before any code is written.

- **One file per seed: `.seeds/seeds/<id>.md`.** The filename is the id verbatim,
  dots included (`seeds-lcfa.6.1.md`), so `seeds show <id>` computes its path and
  is a single file read. The filename carries identity and nothing else
  (`seeds-sdhc.4`).
- **YAML frontmatter, block sequences for every multi-value field** — ruled on
  reading preference, and it happens to merge better, since one value per line
  means two hosts adding different tags touch different lines.
- **`parent:` is an explicit field** even though the id is dotted, so
  `get_children` is never a glob that has to count dots to exclude grandchildren.
- **Relationships are stored at both ends.** Only symmetric edge types may be;
  a directional type needs a named inverse at the far end (`seeds-sdhc.4`).
- **Supersession is marked in place**, immediately after the heading it retires,
  with a mandatory reason clause (`seeds-sdhc.3`):

      ## Dolt would give us cell-level merge
      > [!SUPERSEDED] 2026-08-28 — ordinary git line-merge surfaces same-field
      > collisions too, so the 120 MB dependency bought nothing.

  Scope is from the marker to the next heading of the same or higher level. That
  is the entire parse rule.
- **Corrections replace in place; reasoning accumulates.** A fact that turned out
  false is fixed, with the prior value in git. A position we moved past is marked,
  never deleted — it is what stops the question being re-litigated.
- **Writes are atomic:** write to a temp file, `os.replace()` into position. One
  line, and it is all that survives of the Maildir detour.
- **Reads are strict.** Files-as-truth makes every command a parser, so a lenient
  read reintroduces exactly the silent wrongness this change exists to escape
  (`seeds-sdhc.2`).

## Phases

Ordered by what blocks what.

### 1. Freeze the format spec

`docs/storage-format.md`: file layout, every frontmatter field with its type and
whether it is required, the block-sequence rule, the supersede marker grammar and
its scope rule, the id→path rule, and the relationship representation with its
symmetry requirement. Nothing below starts until this is written down, because
phases 2, 3 and 4 are each an independent implementation of it.

### 2. Reader/writer module

The single door every command goes through. Strict parse, atomic write. No
command touches a seed file directly.

### 3. `seeds check`

**Before the converter, because the converter calls it.**

Two tiers, one implementation, three entry points — by hand, the git pre-commit
hook, and inside the converter against its own output (`seeds-sdhc.2`).

*Violations* (exit non-zero, block the commit): frontmatter that will not parse;
a `status` outside the closed set; a title that is a filesystem path, a URL, or
empty; an empty body; git conflict markers left in a file; `updated_at` before
`created_at`; a future timestamp; a `parent` that disagrees with the dotted id,
names a missing file, or forms a cycle; a relationship naming a file that does not
exist; a one-sided edge; a `[!SUPERSEDED]` marker with no reason clause.

*Smells* (report only, never fail): a long body with many commits of history and
no supersession marker; a body byte-identical to another seed's. This tier is
where `tend` ends up — with marking moved to write time there is nothing editorial
left for it to do, so `tend` collapses into `check --smells` rather than shipping
as its own verb (`seeds-sdhc.3`).

*`check --against-git`*: diff every field against its value at the previous commit
and flag mass single-field changes. This is the detector that would have caught 83
titles turning into paths in under a second (`seeds-wurl`). It is also the right
hook gate — a commit rewriting 87 files has no cheap human review — and gating
that shape subsumes gating `D` and `R` in `git diff --name-status`, so `rm` does
not become the de facto delete verb.

**Test it on hand-built bad inputs with hand-computed expectations.** The
data-pipeline standard applies directly: the code deciding "clean" is itself code
that can be silently wrong, and this one is load-bearing for the conversion.

### 4. The converter

Requirements in full in `seeds-sdhc.1`. In short:

- Input is **`DB ∪ JSONL`**, per id and per field — never "convert the DB, then
  reconcile the JSONL", which would rebuild the derived-overwrites-durable shape
  inside the migration itself.
- Classify every id into four divergence cases and auto-resolve only three:
  DB-only, JSONL-only, and DB-content-extends-disk. **A genuine fork — neither
  side a prefix of the other — is never auto-resolved.**
- A fork **converts to a file, not an error**: `<id>.md` with both bodies and git
  conflict markers, resolved in an editor with ordinary merge tooling. Today the
  same situation is a deadlock the operator clears by hand-rebuilding the body and
  handing it back — better than it was, since `ccee855` moved that off argv and
  onto `--content-file`, but still a manual reconstruction where a conflict file
  would be a normal edit.
- **Mine the JSONL's commit history** as the repair oracle. `seeds-wurl` proves
  both live stores can agree and both be wrong; git was the only source that held
  the truth.
- **Round-trip verification is part of the converter**: re-read the emitted tree,
  rebuild the record set, diff field-by-field against the union input, fail on any
  difference outside an explicit normalization allowlist, then run `check` on the
  output before the source store is left alone.
- **Re-runnable means byte-idempotent** — a second run on an unchanged store
  leaves `git diff` empty.
- **Non-destructive**: write the tree alongside the existing store and never
  delete the source until ruled. Reverting is `rm -rf .seeds/seeds/`.
- It is a **shipped, tested verb**, not a `scripts/` one-shot. 13 repos on titan
  carry a `.seeds/`, and @markdanese converts on a schedule and version we do not
  choose. `seeds-02ur` — 36 orphaned rows still sitting here from the v2
  question-seeds migration — is what a one-shot leaves behind.

Fixtures: this repo, plus a synthetic repo built to exhibit all four divergence
cases at once.

### 5. Command cutover, and three deletions

Every verb reads and writes the tree. SQLite deleted. `seeds search` becomes
ripgrep with the status filter inline (measured at 17 ms across 303 files).

Three things are removed rather than ported. Each was already ruled; this is the
cheapest moment to execute all three, because otherwise the overhaul pays to
carry them across.

- **`seeds suggest` and the FTS5 machinery behind it** — `Database.suggest`
  (db.py:1173), `sanitize_fts_query`, and the `seeds_fts*` tables.
  @aguynamedryan ruled it out 2026-08-31, and the usage evidence supports it:
  roughly 15 genuine invocations across 5 sessions in the whole project
  transcript history, mostly agent-initiated during dedup passes. `seeds-fkb8`
  had already judged its one real win — surfacing seeds-74.2 on a query nobody
  had in context — as something substring-plus-recency would likely have found
  too. Porter stemming is a genuine casualty ("merging" stops finding "merge"),
  and it is accepted: grep tested *broader* than FTS on a real query, 72 hits vs
  77, and found one FTS missed.
- **The web UI** — `seeds serve`, `src/seeds/web.py`, and the four templates.
  Ruled dead 2026-08-25 in `seeds-rlc2` ("never used, never went anywhere") and
  never executed, so the overhaul would otherwise port a killed feature to a new
  storage format.
- **The legacy `questions` table** — all 36 rows are orphaned, verified
  2026-08-31, so the table is entirely debris from the v2 question-seeds
  migration (`seeds-02ur`). The converter drops it rather than translating it.
  Note that `doctor` reports "549 relationships, no orphans" while this table is
  100% orphaned, because nothing checks it — one more argument for the
  plausibility tier in phase 3.

**`tend` is dropped as a planned verb.** It was never built, so there is no code
to remove — but it should not be built either. With supersession marked at write
time (`seeds-sdhc.3`) nothing editorial is left for it, and the noticing function
lives in `check --smells`.

### 6. `seeds history`

Structures and labels; never summarises (`seeds-sdhc.5`). Reads **both sides of
the conversion** — the seed's own file history back to the conversion commit, then
the JSONL's history before it, joined into one list, with the converter stamping
`converted_at` so the reader knows where to switch. Measured: 113 commits walked
for one seed in 1.3 s.

Consequence to state loudly in the docs: **the JSONL stops being written, but its
history stays load-bearing forever and must never be filtered out of git as
cleanup.**

### 7. `seeds export --json`

A pipe to stdout, not a tracked file. **This ships in 0.7, not later** — 13 repos
of cross-project query (`seeds-183`) break on conversion day otherwise. Killing
the tracked JSONL costs availability, not speed; the 35 ms frontmatter scan
answers the wrong objection, because today `grep` and DuckDB work against the
JSONL with seeds not installed and no parser written.

### 8. Pre-commit hook

Runs `check`. Gates the mass-rewrite shape, and `D`/`R` with it. Detection at
commit is not immutability — an agent can read corrupt state at any point before
the commit fires — but it bounds damage to one working session rather than five
weeks, and it is the only durable gate: tool-level hooks miss any agent that
writes through `bash`, `sed`, or a Python one-liner, which is most of them.

### 9. Dogfood

Convert this repo. Use it. Keep the old store until ruled otherwise.

## What is deliberately not being done

- **No append-only entry files.** Git is already the append-only store; building a
  second one in the working tree pays for the history twice — on every read,
  forever (`seeds-ebg1`).
- **No Dolt, and no Go rewrite to get embedded Dolt** (`seeds-lcfa.3`,
  `seeds-lcfa.5`). Ordinary git line-merge surfaces same-field collisions, which
  is the behaviour Dolt was wanted for.
- **No DuckDB as a store.** Measured slower than pure Python at both 280 and 5,040
  seeds, because the work is file I/O, not query planning (`seeds-lcfa.6`). Its
  place is cross-project reading, over the phase 7 pipe.
- **No synthetic commits replaying history during conversion** — see phase 6.
- **No `status` with an open vocabulary.** The asymmetry with `seed_type` is
  deliberate: `seed_type` could open because only `question` carries behaviour,
  while `status` values drive `list`, `ready`, `blocked`, and every lifecycle
  transition. Recorded in `seeds-ebg1` so the proposal is not made a third time.
