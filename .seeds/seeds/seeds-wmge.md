---
id: seeds-wmge
title: 'A write on an unknown seed ID fails invisibly when stderr is silenced: suggest near IDs, and tell agents not to silence writes'
status: captured
type: idea
created_at: 2026-11-05T13:57:41.923391+00:00
updated_at: 2026-11-05T13:57:41.923391+00:00
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

1. **Did-you-mean IDs.** On a not-found ID, print the closest existing IDs,
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
