---
id: seeds-rkt6
title: A pre-commit hook cannot be repaired by an unstaged edit to its own config — the stash hides the fix from the run that needs it
status: captured
type: concern
created_at: 2026-09-02T16:23:14.869193+00:00
updated_at: 2026-09-02T16:23:33.839351+00:00
tags:
  - pre-commit
  - hooks
  - stash
  - tooling
  - rollout
  - "0.7"
  - measured
  - 2026-09-02
relationships:
  - target_id: seeds-dv6r
    rel_type: relates-to
    created_at: 2026-09-02T16:23:33.691447+00:00
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-09-02T16:23:33.838493+00:00
---

Reported by the codesets session on 2026-09-02, after it cost that session a wasted run. Found during the 0.7 conversion rollout, and it generalises well past seeds.

## The trap

A repo's `.pre-commit-config.yaml` calls a command that no longer exists. The fix is to edit that config. **But the fix cannot take effect on the commit that carries it**, because pre-commit **stashes unstaged changes and runs the hooks against the stashed-away tree** — i.e. against the OLD config. So the hook that is already broken runs again, fails again, and the repair sitting right there in the working tree is inert.

The peer's words: *"the config that repairs it is present and inert."*

## Why it bit here

0.7 deleted `seeds sync`. Four repos on titan called it from a pre-commit hook, so committing broke in all four the moment the new binary landed. The fix — swapping it for `seeds check` — is a one-line edit to the very config pre-commit is about to stash.

**The escape is to STAGE the config fix before committing.** `git add .pre-commit-config.yaml` first, and pre-commit runs the new config. Staged changes are not stashed; that is the whole distinction.

## Why it is worth recording rather than shrugging at

The failure presents as *"my hook is still broken after I fixed it"*, which reads as the fix being wrong rather than un-applied. That is a debugging dead end — you go re-read a correct edit looking for a mistake that is not in it. The diagnosis is not in the config, it is in pre-commit's stash semantics, which is not where anyone looks.

It also has the shape this project keeps naming: **the mechanism that is supposed to protect you is the one hiding the repair.** Same family as a gate measuring something adjacent to what it claims to verify — here, a gate running against a tree that is not the one you are committing.

## Generalisation, which is the part worth keeping

**Any pre-commit hook that validates or invokes tooling defined in the repo cannot be repaired by an unstaged edit to its own definition.** That covers the hook config itself, a linter's config the hook reads, a script under `scripts/` the hook calls, and a justfile recipe it shells out to. In every case: stage the repair first, or the run you are trying to fix is the run that ignores it.

## Second finding from the same session, unrelated mechanism, same blast radius

`git add -A` in a converted repo sweeps the entire new `.seeds/seeds/` tree — 436 files in code_set_catalog — into whatever unrelated commit is being made. The peer caught it and backed it out before it landed. **An untracked directory of several hundred small files is effectively invisible in a `git status` glance**, which is exactly the condition under which `-A` is reached for. Worth knowing for the window between converting a repo and committing the conversion.

Relates to seeds-dv6r, seeds-sdhc.
