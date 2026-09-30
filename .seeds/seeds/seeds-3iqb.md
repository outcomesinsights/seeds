---
id: seeds-3iqb
title: The body-discard guard should protect a body written at create time, not only an edited one
status: captured
type: decision
created_at: 2026-09-30T13:19:57.775133+00:00
updated_at: 2026-09-30T13:19:57.775133+00:00
---

The body-discard guard on `seeds update --content` protects a body only after the seed has been edited since creation (`has_been_edited`: `updated_at != created_at`). A body written at `seeds create` time is replaceable with no warning and no `--replace`. The guard's own docstring gives the reason: a never-edited seed "has never been added to", so replacing it is the botched-capture or encoding-repair case.

## What changed our understanding

Agents now write the whole deliberation at create time, in one shot. The cutting and glean skills create seeds with `--content-file` bodies. So "never edited" no longer implies "nothing to lose".

- In this repo's store on 2026-09-30, 30 of 340 seeds had a body never edited after creation: median 365 characters, 8 over 2,000.
- conceptql-a5f was one of these. Its measured deliberation was wiped by `seeds update <id> --append --allow-unknown-refs --content-file F`: `--append` swallowed the next flag, and nothing refused append plus replace. That path is closed by bead seeds-4s8 (defects A and B). Once it lands, the remaining exposure is an explicit `--content` on a never-edited seed, which is the "-c sits one key from -a" slip the guard exists for.

## Options weighed

1. Guard every non-empty body; `--replace` is the only way to discard one.
2. A grace window: unguarded for a few minutes after creation, when botched captures actually get fixed. Rejected: the rule depends on the clock, which is harder to test and harder to explain in an error message.
3. Keep the timestamp rule and rely on A+B. Rejected: it leaves the create-time body, often the whole deliberation, as the one unguarded case.

## Decision (Ryan, 2026-09-30): option 1

The guard's test becomes "a non-empty body exists", not "the body was edited". This matches the principle already in its docstring: the gate is whether deliberation exists, never how much of it there is. A botched capture costs one `--replace`, and the error prints the exact command. `has_been_edited` stays for whatever else reads it, but no longer decides this guard.

Checked before ruling: no skill shipped in the package creates a seed and then replaces its body, so none breaks. README.md (around line 128) and the `update` help describe the old rule and must change with it.
