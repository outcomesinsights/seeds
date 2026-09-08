---
id: seeds-dv6r.1
title: Prettier breaks 54 of 1,324 seed files; the fix is the writer, and there are two break classes not one
status: captured
type: concern
parent: seeds-dv6r
created_at: 2026-09-08T21:02:17.201968+00:00
updated_at: 2026-09-08T21:14:01.921837+00:00
tags:
  - storage
  - format
  - tooling
  - prettier
  - canonicality
  - 2026-09-08
relationships:
  - target_id: seeds-bwce
    rel_type: questioned-by
    created_at: 2026-09-08T21:02:27.748556+00:00
  - target_id: seeds-rgt4
    rel_type: questioned-by
    created_at: 2026-09-08T21:02:27.956543+00:00
  - target_id: seeds-7v9p
    rel_type: questioned-by
    created_at: 2026-09-08T21:02:28.168680+00:00
---

Measured 2026-09-08 with prettier 3.6.2, default settings (no config file), over a
copy of every seed store on titan: **1,324 files across 13 repos. 54 of them stop
parsing after `prettier --write`.** Two independent causes, not one.

This extends seeds-dv6r from "repo-wide tools reach into the store" to something
sharper: **the bytes the writer emits are not a fixed point of the ecosystem's
default markdown formatter.** Exclusion (`.prettierignore`) was the assumed
defence in dv6r. @aguynamedryan inverted it — fix the writer so no exclusion is
needed — and that is the better frame, because an excluded store is still a store
whose canonical form disagrees with every tool that will ever walk the tree.

## Class A — the separator after the closing `---` (44 files)

§2 says a body-less file ends after the blank line following the closing `---`,
i.e. `---\n\n`. Prettier strips trailing blank lines, leaving `---\n`, and the
strict read then refuses it:

    parse-error: no blank line between the closing '---' and the body

Cascades: seeds whose relationships point at an unparseable file then fail
`relationship-target-missing` (oimnibus: 4 parse errors + 4 cascaded = 8).

Measured, all three forms through prettier 3.6.2:

| form | | result |
| --- | --- | --- |
| `---\n\n` | current body-less | blank line stripped — NOT a fixed point |
| `---\n` | proposed body-less | unchanged |
| `---\n\nbody\n` | bodied | unchanged |

@aguynamedryan's rule, 2026-09-08: **the writer emits `---\n` for an empty body.**
The alternative that was proposed first and withdrawn was liberal-read /
canonical-write (accept `---\n`, keep emitting `---\n\n`). It is worse on three
counts: the writer would keep emitting a form prettier disagrees with, so every
formatter run re-dirties the store forever; two accepted spellings of one thing;
and it weakens §7's locked "reads are strict" to paper over what is really a
writer bug. Bodied files are already a fixed point of both seeds and prettier —
this is the only place the two disagree about layout.

Blast radius, body-less files per store: seeds 22 · epc 10 · code_set_catalog 5 ·
oimnibus 4 · habituate 2 · ohdsi_supplemental_vocabs 1.

## Class B — frontmatter scalar re-quoting (10 files). The chosen fix does not cover this.

Not previously seen, because oimnibus happens to have zero of them. Prettier
formats the frontmatter as YAML, and rewrites a double-quoted scalar whose *only*
escapes are `\"` into the single-quoted form:

    resolution: "he said \"yes\" today"      ->      resolution: 'he said "yes" today'

`_decode_scalar` accepts the plain and double-quoted forms and nothing else, so
this is a hard parse error, on a file that has a body and is otherwise ordinary:

    parse-error: field 'resolution': scalar starts with the YAML indicator "'"

Affected: seeds 3 (seeds-147.3, seeds-169, seeds-199) · code_set_catalog 4 ·
epc 1 · code_collector 1 · vocabulary_formats 1. All of them `resolution:` values
that quote somebody verbatim — i.e. exactly the long, carefully-worded records the
format exists to keep.

Prettier's rule, established by fixture (fixed point unless noted):

| value contains | double-quoted form | single-quoted form |
| --- | --- | --- |
| no `"` | kept | n/a |
| `"` only | **rewritten to single** | kept |
| `"` and `'` | **rewritten to single, `''`-doubled** | kept |
| `"` plus any `\n` `\t` `\\` `\uXXXX` escape | kept | n/a |

So it is not "prefer single quotes"; it is **prefer whichever quoting needs no
backslash escapes**, which is an ordinary YAML-emitter convention rather than a
prettier quirk. That means a writer rule matching it is available: emit
single-quoted (with `''` doubling) when the value contains `"` and needs no other
escape, double-quoted otherwise — one canonical spelling per value, still a
function of the value, and a fixed point of default prettier. It costs a second
accepted quoting form in the reader, which is a §7 question.

## The detector gap

`seeds check --smells` did not fire `tool-config-includes-store` on oimnibus.
`_TOOL_CONFIGS` looks for `.prettierrc` / `.prettierrc.*` / `prettier.config.*`;
oimnibus configures prettier **only** as a `package.json` dependency, which is
prettier's config-less mode and its whole selling point. The detector's blind spot
is the common case. Same shape for markdownlint and cspell, which are also
normally installed through `package.json`.

## What was reported as breakage and withdrawn — @aguynamedryan was right twice

1. `*emphasis*` -> `_emphasis_` in 32 bodies. Identical markdown, not corruption.
   Most of what prettier did to bodies is an improvement — it inserts the blank
   line between a paragraph and a following list, which is proper CommonMark and
   ambiguous without it.
2. Bare paths escaped: `_by_slug/` -> `\_by_slug/`. Rendering the unescaped line
   through CommonMark applies no emphasis, so the escape was defensive, not a fix
   for live breakage. The body was leaning on subtle flanking rules and prettier
   made them explicit. Root cause is an unfenced literal path — backticks survive
   any formatter. If the backslash bothers a reader, `seeds show` should render
   markdown rather than the repo banning the formatter.
3. A hand-aligned two-column block collapsed to single spaces. Column alignment
   is not a markdown construct; a real table or a fenced block survives untouched.

All three are "the seed body was written badly and prettier did the right thing",
not format problems. **The body is stored opaquely and seeds cannot distinguish an
edited body from an authored one**, so those 32 rewrites produced zero smells —
§9.1's second layer does not cover body content, by construction. That is what
`content-rewritten-without-a-timestamp-bump` (still unbuilt, see dv6r's
correction) is for.

A `.prettierignore` excluding `.seeds/` was added to oimnibus and then reverted on
@aguynamedryan's instruction: its justification was 1-3, which do not stand, and
excluding the store would only have preserved the badly-written bodies.

## VERIFIED (2026-09-08): both fixes together make the FORMAT a complete fixed point

@aguynamedryan ruled: chase class B. Simulated it — re-rendered all 1,324 files
with `_encode_scalar` carrying the escape-minimizing quote rule and with a
body-less file ending at `---\n`, then ran `prettier --write` over the result:

**0 of 1,324 files changed in the frontmatter or the separator.** Not one. So the
goal *"a seed file is left unchurned and undamaged by prettier"* is achievable and
these two writer changes achieve it — at the format layer, which is the layer
seeds owns and the only layer where prettier can break a *parse*.

No migration is needed for the files already on disk. An old `---\n\n` body-less
file still parses under the new reader (trailing blank lines are normalized, §2),
and an old `"...\"..."` scalar still parses too, so nothing breaks and nothing has
to be rewritten on a schedule: the next `seeds` write renders the file canonical,
and a prettier run gets there by itself. The only cost of leaving them is that
`check --smells` reports `non-canonical-bytes` on 44 files until they are touched,
which is a reason to run one read-and-rewrite pass, not a correctness need.

## The limit: the BODY is not a fixed point and cannot be made one

Same measurement, body layer: **961 of 1,324 bodies are rewritten** by one
prettier pass.

- **868** are pure re-spelling — `*em*` -> `_em_`, `+` list markers -> `-`,
  defensive `\_` escapes. Identical rendered markdown.
- **85** differ only by list-marker respelling under a looser comparison.
- **82** have 1-3-space-indented non-list lines flattened, which is where the real
  damage lives.
- **26 oscillate**: a second prettier pass changes them again. That is *perpetual*
  churn, unlike the format-layer churn the writer fix removes.

Confirmed damage, seeds-183: a 2-space-indented SQL block — indented, never
fenced, so CommonMark reads it as a paragraph — was flattened to column 0 and its
literal asterisks re-spelled as underscores. `count(*)` became `count(_)`;
`/home/ryan/projects/outins/*/.seeds/seeds.jsonl` became `outins/_/`. The SQL is
now wrong. seeds-147.3 shows the oscillation mechanism: pass 1 writes `_human_`,
pass 2 re-parses that against the underscores in `code_set_catalog` and emits
`code*set_catalog's ... \_human*`.

This is the same root cause as the withdrawn findings 1-3 — a body written in a
way that leans on CommonMark's ambiguities, which a fence would have settled — but
unlike them it is genuine corruption rather than a re-spelling, so it cannot be
waved off. **Seeds cannot fix it in the writer.** The body is arbitrary prose
stored opaquely; making it a prettier fixed point would mean adopting prettier's
markdown normalization as part of the format, i.e. a node dependency in the
writer, which is not on the table.

So the exclusion tier is not obsolete after all — it just changes meaning.
`tool-config-includes-store` stops being the defence for the *format* (the writer
fix is) and becomes the defence for *body content*, which is exactly the third
rule dv6r's correction identified as missing and unbuilt
(`content-rewritten-without-a-timestamp-bump`).
