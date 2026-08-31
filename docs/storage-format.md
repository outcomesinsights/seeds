# The seeds on-disk storage format

**Status: frozen.** This is the normative description of `.seeds/seeds/<id>.md`,
the only store after the 0.7 storage overhaul.

It is frozen because phases 2, 3 and 4 of `plans/storage-overhaul.md` — the
reader/writer, `seeds check`, and the converter — are each an *independent*
implementation of this format. If they disagree, the converter writes files the
checker calls clean and the reader misreads. Nothing below is a suggestion, and
nothing below may be changed by a single implementation noticing it would be
convenient.

The deliberation is not repeated here. `plans/storage-overhaul.md` is the build
plan and carries the phase ordering and what is deliberately not being done;
`seeds-sdhc` and its children carry the arguments. This document is their
normative form.

## 1. Layout

```
.seeds/
  seeds/
    seeds-sdhc.md
    seeds-sdhc.3.md
    seeds-lcfa.6.1.md
    …
  seeds.jsonl        # frozen after conversion; see §11
```

Every seed is exactly one file. There is no index, no database, no manifest, and
no second copy of anything. The directory listing *is* the seed set.

### 1.1 The path rule

    .seeds/seeds/<id>.md

The filename stem is the id **verbatim, dots included** — `seeds-lcfa.6.1` is
stored at `.seeds/seeds/seeds-lcfa.6.1.md`. There is no escaping, no directory
nesting per level, and no transformation of any kind.

This is load-bearing. `seeds show <id>` computes the path by string
concatenation and performs a single file read; that property is the reason this
layout was chosen over every alternative, and any change that makes the path a
search instead of a computation breaks it.

Ids match `^[a-z][a-z0-9-]*-[0-9a-z]+(\.[0-9]+)*$` — a lowercase prefix, a
base36 token (or a grandfathered decimal one), and an optional dotted child
path. All-lowercase means the format is safe on case-insensitive filesystems.

**The filename carries identity and nothing else** (`seeds-sdhc.4`). Every other
structural fact — hierarchy, relationships, status — is stored in frontmatter
and cross-checked by `seeds check`. Deriving structure from a path is what sank
directory-as-state, and it fails the same way here: `seeds-lcfa.*.md` also
matches grandchildren, and excluding them means counting dots, which is parsing
structure back out of a name.

## 2. File anatomy

A seed file is YAML frontmatter followed by a markdown body:

```markdown
---
id: seeds-sdhc.4
title: Filenames carry identity only
status: resolved
type: decision
parent: seeds-sdhc
created_at: 2026-08-28T14:02:11.481293+00:00
updated_at: 2026-08-31T09:41:07.220118+00:00
resolved_at: 2026-08-31T09:41:07.220118+00:00
tags:
  - storage
  - format
relationships:
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T14:02:11.481293+00:00
---

Settles seeds-sdhc's open items #3 and #4…
```

Mechanically:

- **UTF-8**, no BOM. **LF** line endings. The file ends with exactly one newline.
- Byte 0 is the first `-` of the opening `---`. Nothing precedes it — no blank
  line, no comment, no shebang.
- The frontmatter is delimited by a line containing exactly `---` to open and a
  line containing exactly `---` to close. No `...` document terminator.
- Exactly one blank line separates the closing `---` from the body. A file whose
  body is empty ends after that blank line's newline.
- Everything after that blank line, verbatim, is the body.

## 3. Frontmatter fields

| key | YAML type | required |
| --- | --- | --- |
| `id` | string | always |
| `title` | string | always |
| `status` | string, closed set | always |
| `type` | string, open vocabulary | always |
| `parent` | string | iff the id is dotted |
| `created_at` | timestamp | always |
| `updated_at` | timestamp | always |
| `resolved_at` | timestamp | iff `status` is terminal |
| `resolution` | string | optional |
| `tags` | block sequence of strings | optional |
| `relationships` | block sequence of mappings | optional |
| `converted_at` | timestamp | written by the converter only |

Keys are emitted in exactly that order. Order is not semantic — a reader must
not depend on it — but a *writer* must produce it, so that re-writing an
unchanged seed is a byte-level no-op and a real edit shows as a small diff.

**Optional fields are omitted when empty.** A writer never emits `tags: []`,
`resolution: ""`, or an empty block sequence. Absent and empty are the same
state, and having one representation for it is what makes the format
byte-idempotent.

**Unknown keys are an error**, not something to preserve or ignore. See §7.

### `id` (string, required)

The seed's identifier. Must equal the filename stem. A file whose `id`
disagrees with its name is a violation, not a rename to be inferred.

### `title` (string, required)

One line, non-empty, plain text. Not a path, not a URL — those are the
plausibility checks `seeds check` exists for (`seeds-wurl` clobbered 83 titles
into filesystem paths, and every one of them parsed perfectly).

The title lives here and **only** here. The body must not repeat it as a
heading; `seeds show` prints the title from frontmatter, and a duplicate H1
prints it twice.

### `status` (string, required)

A **closed** set. Exactly one of:

`captured` · `exploring` · `deferred` · `resolved` · `abandoned`

`resolved` and `abandoned` are the terminal states.

The vocabulary is closed and stays closed. This asymmetry with `type` is
deliberate: `status` values drive `list`, `ready`, `blocked`, and every
lifecycle transition, where `type` drives almost nothing. Recorded in
`seeds-ebg1` so the proposal is not made a third time.

### `type` (string, required)

An **open** vocabulary. The five standard values are `idea`, `question`,
`decision`, `exploration`, `concern`; any string round-trips. Only `question`
carries behaviour (`seeds ask`/`answer`, `seeds questions`, prime's
open-questions section). `seeds doctor` reports non-standard values and
`seeds retype` remaps them; neither rejects one.

The frontmatter key is `type`, mapping to `Seed.seed_type` in `models.py` and to
`seed_type` in the legacy JSONL. The reader and writer own that translation;
nothing else may guess at it.

### `parent` (string)

**Required when the id is dotted, forbidden when it is not.** `seeds-sdhc.4`
carries `parent: seeds-sdhc`; `seeds-sdhc` carries no `parent` key at all.

The redundancy with the dotted id is deliberate, and it is cheap because it is
checked. It exists so `get_children` is a frontmatter read rather than a glob
that has to count dots to exclude grandchildren. `seeds check` verifies three
things: the `parent` value agrees with the dotted id, the parent file exists,
and no cycle exists.

### `created_at`, `updated_at`, `resolved_at`, `converted_at` (timestamps)

ISO 8601, **always timezone-aware, always normalized to UTC**, as
`datetime.isoformat()` emits it:

    2026-08-31T09:41:07.220118+00:00

A naive timestamp — no offset — is a **read error**. The JSONL importer
interprets naive input as UTC to avoid losing a third-party record; that
leniency does not carry into this format, because there is no third party
writing it. The converter normalizes naive values once, on the way in.

- `created_at` — when the seed was first written. Never changes.
- `updated_at` — the last write. Must be `>= created_at`. A freshly created
  seed mirrors `created_at` exactly rather than taking a second clock reading,
  so `updated_at == created_at` means "never edited" and is a meaningful test.
- `resolved_at` — **required iff `status` is `resolved` or `abandoned`;
  forbidden otherwise.** Re-resolving re-stamps it.
- `converted_at` — stamped **once, by the converter**, on the file it emits from
  the pre-0.7 store. It is never written by an ordinary edit and never updated.
  It is what lets `seeds history` know where to switch sources: the seed's own
  file history back to `converted_at`, then the JSONL's history before it. A
  file created after conversion has no `converted_at` and its whole history is
  in its own file.

### `resolution` (string, optional)

Free text recording *why* a seed reached its terminal state. Omitted when
empty. Only meaningful alongside a terminal `status`, but carrying one on a
non-terminal seed is a smell rather than a violation — it is usually a seed
someone reopened.

### `tags` (block sequence of strings, optional)

See §4. Omitted entirely when the seed has no tags.

### `relationships` (block sequence of mappings, optional)

See §5. Omitted entirely when the seed has no edges.

## 4. Block sequences, always

**Every multi-value field is a YAML block sequence — one value per line. The
flow form is never written and is a read error.**

```yaml
tags:
  - storage
  - format
```

not

```yaml
tags: [storage, format]
```

Two independent reasons, and both were required for the rule to be worth
freezing:

1. @aguynamedryan ruled on it 2026-08-28 — *"inline doesn't read better to my
   eyes — blocks for frontmatter"*.
2. It merges better. One value per line means two hosts adding different tags
   touch different lines and git merges them cleanly. The inline form puts both
   edits on one line and collides, which is the entire class of pain this
   storage change exists to remove.

Sequence order is preserved as written and is not otherwise meaningful. A writer
emits `tags` in the order it holds them; it does not sort, and it does not
de-duplicate silently — a duplicate tag is a `check` finding.

## 5. Relationships

An edge is stored as a mapping in the `relationships` sequence:

```yaml
relationships:
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T14:02:11.481293+00:00
```

| key | type | required |
| --- | --- | --- |
| `target_id` | string (a seed id) | yes |
| `rel_type` | string, closed set | yes |
| `created_at` | timestamp | yes |

`created_at` is the edge's own creation time, not either seed's, and it is the
same value at both ends.

### 5.1 Both ends, always

**Every edge is written at both ends.** A `relates-to` between A and B appears
in A's file naming B *and* in B's file naming A.

The alternative — store each edge once and derive the inverse — was rejected.
`seeds show <id>` is the most common read, "what relates to this" is part of its
answer, and deriving it means a corpus scan on every invocation. That forfeits
the one-file-read property the whole format was chosen for.

The cost is real and is accepted knowingly: two writes with no transaction can
leave a half-edge that renders from A and not from B. That is *mechanically
verifiable*, which is the trade this architecture makes everywhere else — SQLite
mitigated it with a transaction, files mitigate it with detection. `seeds link`
writes both ends and re-reads both files to confirm symmetry before returning,
so the window is one process, and a one-sided edge is a `check` violation.

### 5.2 Only symmetric types may be stored at both ends

Writing an edge at both ends is only unambiguous when the far end can say what
it holds. **A symmetric type stores itself at both ends. A directional type
stores a named inverse at the far end.** Without a named inverse, symmetry
checking cannot tell which of the two files is the wrong one.

| stored at the near end | stored at the far end | direction |
| --- | --- | --- |
| `relates-to` | `relates-to` | symmetric |
| `questions` | `questioned-by` | directional |
| `answers` | `answered-by` | directional |

Those five strings are the closed set of legal `rel_type` values.
`questioned-by` and `answered-by` are storage-side names introduced by this
document to satisfy the both-ends rule; today's `RelationType` in `models.py`
carries only `relates-to`, `questions`, and `answers`, so phase 2 adds the two
inverses when it builds the writer. Adding a sixth type in future means adding
its inverse in the same change — a directional type with no inverse cannot be
stored in this format at all.

The symmetry rule `seeds check` enforces: for every edge in A naming B with type
`T`, B's file contains an edge naming A with type `inverse(T)` and an identical
`created_at`. `seeds check` additionally verifies that `target_id` names a file
that exists — the foreign key SQLite used to enforce becomes a file-existence
test.

## 6. The body, and the supersede marker

The body is ordinary markdown. The format imposes exactly one piece of structure
on it.

### 6.1 The marker

A position that has been moved past is **marked in place**, immediately after
the heading it retires:

```markdown
## Dolt would give us cell-level merge
> [!SUPERSEDED] 2026-08-28 — ordinary git line-merge surfaces same-field
> collisions too, so the 120 MB dependency bought nothing.

…original section text, untouched…
```

Grammar:

- The marker is a blockquote line matching `^> \[!SUPERSEDED\] ` — GitHub alert
  syntax, which renders as a blockquote in every markdown viewer, needs no
  extension, and greps cleanly.
- It must be **the first non-blank line after the heading it retires**. A marker
  anywhere else is a violation; there is no floating supersession.
- Then a date, `YYYY-MM-DD` — the day the position was retired.
- Then ` — ` (space, em dash, space).
- Then the **reason clause, which is mandatory** and non-empty. `seeds check`
  enforces its presence. A bare marker loses the *why*, and a conclusion without
  its reason invites re-litigation — a heading saying "Python" invites an agent
  to propose Go next month.
- The marker may wrap onto further `> ` blockquote lines; the reason clause is
  everything from the em dash to the end of the blockquote.

### 6.2 The scope rule

**Scope runs from the marker to the next heading of the same or higher level.**

That is the entire parse rule. Concretely: given a marker under an `h2`, the
superseded scope ends at the next `h1` or `h2`, or at end of file. Deeper
subsections (`h3`, `h4`) fall *inside* the scope along with their text.

Only ATX headings (`#` … `######` followed by a space, at the start of a line)
count. A `#` inside a fenced code block is not a heading and does not close a
scope; a parser that ignores fences will truncate scopes at the first shell
comment in an example.

### 6.3 Why in place, and not a fold

Relocating superseded text to a `## Superseded` section at the bottom was
rejected. It is a large diff for a semantic no-op, it destroys narrative order,
it forces an ordering decision among superseded chunks, and it makes `git log -p`
on that region unreadable — the very command the history story depends on.

It is also worse for the naive reader, which was the fold's own argument. A grep
hit inside a fold lands with no indication it is dead text. With an in-place
marker, the retiring line sits a few lines above every hit in the section, so
context arrives with the match.

Supersession is marked by the agent that learned the old claim was wrong, in the
same edit — not by a later review pass. That agent has the context to write the
reason clause in one line; a reviewer three weeks later has to reconstruct it and
will write something vaguer. This is why there is no `tend` verb: with marking at
write time there is nothing editorial left for it to do, and the noticing
function lives in `check --smells`.

### 6.4 Body emptiness

The format permits an empty body — structurally, the body region simply has no
bytes. Whether that is acceptable is a `check` question, not a parse question:
`plans/storage-overhaul.md` phase 3 lists an empty body as a violation, and 31
of this repo's 312 seeds currently have one, so the converter and the checker
have to rule on those together rather than each assuming the other handled it.

## 7. Locked decisions

These are settled. They are stated here so a later reader does not reopen them.

### Reads are strict

A read that cannot fully understand a file **fails loudly and names the file**.
It does not skip a field, coerce a value, guess at an unknown key, or return a
partial seed.

Files-as-truth makes every command a parser. A lenient read therefore
reintroduces exactly the silent wrongness this whole change exists to escape —
the store looking fine while carrying something wrong. Strictness is survivable
only because `seeds check` exists: a strict read blowing up on the first bad file
is not the operator's only feedback channel, because `check` names every bad file
in one pass with a remediation per finding.

### Corrections replace in place; reasoning accumulates

Two different things, two different treatments, and confusing them is how a
store becomes either a lie or an unreadable pile.

- **A fact that turned out false is fixed in place.** The prior value is in git.
  Carrying a wrong number forward costs context and risks an agent acting on it.
- **A position that was moved past is marked, never deleted.** It is what stops
  the question being re-litigated. Deleting the losing argument means someone
  makes it again next month.

### Nothing is destroyed; the RENDER is what is selective

No command removes text from a seed file to tidy it. There is no compaction pass,
no archival fold, no summarising rewrite.

Selectivity lives entirely in the reader:

- `seeds show <id>` renders **live** content — the whole body except the text
  inside superseded scopes, with each retired heading and its marker line still
  shown, so the reader can see that something was retired and why.
- `seeds show <id> --full` renders everything, marker scopes included.

### Writes are atomic

Write to a temp file **in `.seeds/seeds/` itself**, then `os.replace()` it into
position. Same directory means same filesystem, which is what makes the replace
atomic; a temp file in `/tmp` silently degrades to a copy. Never open the real
path for writing.

A reader therefore always sees either the whole previous file or the whole new
one, never a truncated one — including a reader in another process, and including
the case where the writer is killed mid-write.

## 8. What is deliberately not in this format

- **No `format_version` field.** The frozen format is the format; the tracked
  tree and its git history are the compatibility story. A future format change is
  a converter's job — the same job phase 4 is doing now — not a discriminator
  every reader has to branch on forever.
- **No derived or cached anything.** No index file, no `.seeds/` manifest, no
  counts. The defect this replaces was precisely a derived store authorized to
  overwrite a durable one; reintroducing any derived artifact reintroduces the
  question of which one is right.
- **No per-seed directory, and no entry files.** Git is already the append-only
  store. Building a second one in the working tree pays for the history twice, on
  every read, forever.
- **No open `status` vocabulary.** See §3.

## 9. Repo-level configuration

The project prefix lives in a small tracked **`.seeds/config.yaml`**, alongside any
future repo-level settings:

    prefix: seeds

Ruled by @aguynamedryan, 2026-08-31. Until then it lived in the SQLite `config`
table (`db.get_prefix`, db.py:316), which phase 5 deletes.

It is **not** a frontmatter field, because it is a property of the project rather
than of any seed — 312 copies of one value would only drift. And it is **not**
derived from seed filenames, tempting though that is: a repo with no seeds yet has
no prefix to read, so `seeds init` would have nothing to record and the first
`seeds jot` would not know what to name its file.

## 10. Why the checker matters to this document

Almost every rule above is stated as "X is a violation". That is not decoration:
this format buys its simplicity by moving guarantees that SQLite enforced
structurally — foreign keys, transactions, a closed status column — into
verification after the fact. `seeds check` is where those guarantees now live,
and a rule here with no corresponding check is not enforced by anything.

The checker is itself code that can be silently wrong, so it is tested on
hand-built bad inputs with hand-computed expectations.

## 11. The JSONL after conversion

`.seeds/seeds.jsonl` stops being written on conversion day. **Its git history
stays load-bearing forever and must never be filtered out of the repository as
cleanup.** `seeds history` reads it for everything before `converted_at`, and
`seeds-wurl` proved that git was the only source that held the truth when both
live stores agreed and both were wrong.

Machine consumers are served by `seeds export --json`, a pipe to stdout, not a
tracked file.
