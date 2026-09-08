---
id: seeds-dv6r.1
title: Prettier breaks 54 of 1,324 seed files; the fix is the writer, and there are two break classes not one
status: captured
type: concern
parent: seeds-dv6r
created_at: 2026-09-08T21:02:17.201968+00:00
updated_at: 2026-09-08T21:02:28.169534+00:00
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
