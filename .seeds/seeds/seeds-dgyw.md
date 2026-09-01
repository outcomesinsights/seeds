---
id: seeds-dgyw
title: Should seeds guard the JSONL write door, given agents edit it directly?
status: deferred
type: question
created_at: 2026-08-28T13:28:39.249184+00:00
updated_at: 2026-08-31T20:02:48.240710+00:00
tags:
  - prevention
  - jsonl
  - validation
  - agents
  - sync
  - deferred
  - 2026-08-28
relationships:
  - target_id: seeds-1x6b
    rel_type: relates-to
    created_at: 2026-08-28T13:28:43.205699+00:00
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-08-28T16:33:00.569601+00:00
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-08-28T17:09:42.816681+00:00
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.991923+00:00
  - target_id: seeds-sdhc.2
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.893176+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Split out of [[seeds-1x6b]] (@markdanese's report) so the detection fixes could ship without waiting on this.

`.seeds/seeds.jsonl` is a plain text file in a repo agents edit directly. That is how a `context` seed_type got in — the CLI itself rejects it. Opening the type vocabulary removes that specific poison, but not the general one: an agent can still write a record with a missing required field, a malformed timestamp, or a broken relationship, and the first time anyone finds out is when something downstream trips over it.

Options, unexamined:
- A `seeds validate` / `seeds import --check` that a pre-commit hook can run, so a poisoned JSONL never gets committed.
- Schema validation on read, with a repair suggestion rather than a crash.
- Teach agents the format through the plugin/prime output, so fewer bad writes happen in the first place.
- Nothing: accept that hand-edited JSONL can be malformed, and rely on doctor to surface it after the fact.

Note the tension with what was just decided: doctor became the place divergence and vocabulary drift surface, which is detection *after* the write. This question is whether prevention *before* the write is worth its complexity. Related: [[seeds-hao9]] (should import be transactional) is the same question from the read side.

## RULED (@aguynamedryan, 2026-08-28): defer to 0.7, built once as `seeds check`

Nothing ships for this in 0.6. The write door gets guarded in 0.7, as a `seeds check` verb against the **markdown** format, wired into a git pre-commit hook.

**The reasoning:** a JSONL write-door validator guards a file that 0.7 deletes. Building it now means building it twice, and the second build is against a different format with different failure modes. The options listed above were all framed around JSONL validity; under per-seed markdown files the interesting checks are different ones (frontmatter well-formedness, relationship symmetry, orphaned children, supersession markers).

**Pre-commit is the right gate, and this is settled rather than assumed.** Claude Code's `PostToolUse` hooks fire on the Write/Edit *tools*; an agent using `bash -c 'cat > file'`, `sed -i`, or a Python one-liner never touches those tools and never fires the hook. Tool-level hooks are therefore advisory. Everything reaches a commit eventually, so the git hook is the only durable gate.

**Accepted cost:** the JSONL is unguarded for the whole 0.6 life. This is tolerable because 0.6 ships the *detection* half — doctor now compares content and calls `find_divergence`, and malformed records name themselves — so a bad write is loudly discoverable even though it is not prevented.

**Carried into 0.7:** `seeds check` must gate `D` and `R` in `git diff --name-status`, not just `M`. There is no `delete` verb (`db.delete_seed`, db.py:477, has no callers outside its module), so `rm -rf <seed-file>` would otherwise become the de facto delete verb and pass a modification-only gate unchallenged.

This question stays **deferred** rather than resolved — the design question it asks is now live in 0.7's scope, not closed.
