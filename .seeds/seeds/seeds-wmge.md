---
id: seeds-wmge
title: 'A write on an unknown seed ID fails invisibly when stderr is silenced: suggest near IDs, and tell agents not to silence writes'
status: captured
type: idea
created_at: 2026-11-05T13:57:41.923391+00:00
updated_at: 2026-11-05T14:13:57.352589+00:00
tags:
  - agent-ux
  - errors
  - prime
---

## Origin

GitHub issue #44 (Mark Danese, 2026-11-05) and a comment on it. The issue is
mostly about `seeds search` needing ripgrep. Commit bf830c6 fixed that part
with a Python fallback. This seed holds the other part: a write that names a
seed ID that does not exist.

## The defect shape

A write on an unknown ID exits 1 and changes nothing. That is correct. The
problem is what an agent sees. When the agent sends stderr to /dev/null, the
refusal is invisible, and the agent believes the write happened. Mark
reproduced it on 0.7.1:

```
$ seeds resolve observatory-1.6.3.9999 -r "test" >/dev/null 2>&1
exit=1          # and you saw nothing

$ seeds resolve observatory-1.6.3.9999 -r "test"
Error: Seed 'observatory-1.6.3.9999' not found.
```

`answer`, `link` and `defer` behave the same. Mark's comment adds that
`seeds convert` leaves the ID space mixed. Converted seeds keep numeric tree
positions (as deep as 14 segments, `1.6.3.80.2.2.1.2.2.1.1.1.1.1`), and new
roots are alphabetic (`<prefix>-juq`). A dropped or doubled segment still looks
like a valid ID.

## Measured on titan transcripts (2026-11-05)

Script and log: `claude_stuff/searchbench/notfound2.py`,
`claude_stuff/notfound2-20261105-055541.log` (not committed).

- 86 distinct `Error: Seed '<id>' not found.` refusals reached an agent.
  These are the visible ones only.
- 138 seeds write commands sent stderr to /dev/null (`>/dev/null 2>&1`, `&>`
  or `2>/dev/null`). A refusal on any of them was invisible.
- 191 more sent only stdout to /dev/null. A refusal on those stays visible.
- None of the 86 refusals were on a deep numeric ID. Mark's mixed-ID concern
  comes from a converted store that titan does not have.

## RULED 2026-11-05 (Ryan)

Both directions from the issue comment go into this seed:

1. **Did-you-mean IDs** (replaced 2026-11-05 by exact checks; see below). On a not-found ID, print the closest existing IDs,
   for example `did you mean <prefix>-1.6.3.143?`.
2. **Prime guidance.** `seeds prime` gets one line: do not send a write's
   stderr to /dev/null, because a refusal exits 1 and becomes invisible. The
   form that keeps the refusal is `out=$(seeds ... 2>&1) || echo "$out"`.

This ruling records the direction. It does not authorize the build.

## Not ruled

- How to rank near IDs: edit distance (`difflib.get_close_matches` is in the
  standard library), shared prefix, or both. A dropped segment in a dotted ID
  may rank better by segment comparison than by character distance.
- How many suggestions to print, and whether to print none when nothing is
  close.
- Which commands get it. Every command that prints `not found` is a
  candidate: `show`, `resolve`, `abandon`, `defer`, `explore`, `update`,
  `answer` (question IDs), `link` (both ends), and `create --parent`.

## RULED 2026-11-05 (Ryan): exact checks replace the edit-distance suggestion

This replaces direction 1 of the first ruling (did-you-mean by closest IDs).
Direction 2, the `seeds prime` line against silenced stderr, stands.

### Why: what the 86 refusals were

Each of the 86 not-found refusals in titan transcripts was classified against
the current store of the session's working directory, and each candidate was
looked up with `bd show` in that repo. Scripts: `claude_stuff/searchbench/nfclass.py`,
`nfclass_bd.py`. Logs: `claude_stuff/nfclass-20261105-060110.log`,
`claude_stuff/nfclass-bd-20261105-060511.log` (not committed).

| Cause                          | Count                          | Example                                                                        |
| ------------------------------ | ------------------------------ | ------------------------------------------------------------------------------ |
| A bead ID passed to seeds      | at least 29, probably about 36 | `csc-36hz` is a bead                                                           |
| An ID in the wrong form        | about 16 distinct IDs          | `176` for `csc-176`; `seeds~cpkr` for `seeds-cpkr`; `seeds-060` for `seeds-60` |
| A seed in another repo's store | 3                              | `vfm-6x1` exists in vocabulary_formats                                         |
| No similar ID anywhere         | about 15                       | `agent-a3a646c9701200f5e`, `demo-2`                                            |
| The ID exists now              | 8                              | probably created after the attempt                                             |

Edit distance (`difflib.get_close_matches`, cutoff 0.8) found a "near match"
for 24 refusals. 18 of the 24 were bead IDs: `csc-36hz` gave seed `csc-36`,
`csc-8ar7` gave `csc-87`. The other 6 also look accidental, because hash
suffixes are random (`hm-ash` gave `hm-sh2`). Only `seeds-060` gave a
plausible answer (`seeds-60`). An agent that receives a wrong suggestion can
act on it and write to the wrong seed, which is worse than the refusal.

Most refusals were reads: `show` 43, `link` 6, `update` 3, `defer` 1, and 31
that the script could not attribute to one command.

### The three checks, in order, on a not-found seed ID

1. **Bead check.** If `bd` finds the ID in this repo, say that it is a bead,
   not a seed, and name `bd show <id>`. Reuse `seeds.beads.query_bead_ids`,
   which already returns `None` when beads cannot be consulted. On `None`,
   print nothing extra.
2. **Wrong-form check.** Try fixed corrections and suggest an ID only when a
   seed with exactly that ID exists: add the store prefix to a bare number
   (`176` to `<prefix>-176`), change `~` to `-`, and drop leading zeros from a
   numeric segment (`seeds-060` to `seeds-60`). No edit distance.
3. **Prefix check.** If the ID's prefix is not this store's prefix, say which
   prefix this store uses.

The refusal still exits 1, and the extra lines go to stderr with it.
