---
id: seeds-2g8u
title: 'seeds check --gate re-refuses an unrelated commit after a confirmed mass change: what should the gate compare when the store equals HEAD?'
status: resolved
type: question
created_at: 2026-11-03T14:30:24.754835+00:00
updated_at: 2026-11-03T14:40:04.416056+00:00
resolved_at: 2026-11-03T14:40:04.416044+00:00
resolution: 'Ruled (a): --gate drops the HEAD~1 fallback; plain --against-git keeps it. Built under bead seeds-fn85.'
---

## The report

The roobetl session reported this on 2026-11-03 at Ryan's request (seeds 0.7.1, titan). roobetl's pre-commit runs `seeds check --gate`.

- roobetl commit 792706c appended dated notes to 15 of 46 seeds. It was committed with `SEEDS_GATE_CONFIRM=1`, as intended, and merged into main as 8ccd5bd.
- The next commit, on a branch cut from 8ccd5bd, changed only a CSV file. No seed file was staged or modified.
- The gate refused it as a mass field rewrite of 15 of 46 bodies. The agent committed it with `SEEDS_GATE_CONFIRM=1` (roobetl 55eef56). It did not use `--no-verify`.
- The gate printed:

```
seeds check --against-git: 46 seed(s) at HEAD~1, compared with HEAD.
```

The reporter's point: after any confirmed mass seed change, the next commit, whatever it touches, needs `SEEDS_GATE_CONFIRM=1`. That trains agents to set the variable by habit, which weakens the guard.

## Verified in the code (main at 162b7c9)

`check_against_git` in `src/seeds/check.py` compares the working store with HEAD. When the two are equal, it falls back to HEAD~1 against HEAD. The docstring gives the reason: seeds-wurl needed an audit of a rewrite that was already committed and survived three days.

In a pre-commit hook, that fallback judges the commit that already exists, not the commit being made. After a merge commit, HEAD~1 is the first parent, so the merge of a confirmed mass change makes the next unrelated commit fail too.

This is known and was accepted twice:

- seeds-7q8g's measurement (2026-09-30) notes that a legitimate `seeds rename-prefix` in marketscan_mdcd "keeps failing until the next commit moves HEAD".
- Bead seeds-1pwc (2026-10-27, from gator) hit the second refusal at push. Its fix changed only the refusal text. `GATE_REFUSAL` in `cli.py` now says: "Expect to confirm twice for one rewrite."

roobetl is the third repo to report it. The cost is no longer one extra confirmation per rewrite. It is a confirmation on an unrelated commit, which teaches the escape as routine.

## Not ruled. Directions

(a) `--gate` drops the HEAD~1 fallback. When the store equals HEAD, the gate has nothing to judge against git and passes. Plain `seeds check --against-git` keeps the fallback as the audit that seeds-wurl needed. Cost: a pre-push gate with a clean tree no longer re-judges anything. A mass change that enters through a path that runs no pre-commit hook (a merge, a cherry-pick, a rebase) is then caught by nothing automatic.

(b) The gate judges the right range for its hook. Pre-commit compares the index with HEAD. Pre-push compares the pushed range, for example `@{upstream}..HEAD` or the merge base with the default branch, with HEAD. Cost: more code, and a hook that runs `just ci` does not tell the gate which hook it is in. A confirmed change is still judged twice: once at commit and once at push.

(c) Record the confirmation in history. A confirmed commit carries a trailer such as `Seeds-Gate-Confirmed: 1`, and the fallback skips a HEAD (or a merged range) whose commits carry it. Cost: a pre-commit hook cannot write the commit message, so this needs a `prepare-commit-msg` or `commit-msg` hook, which gator's standard does not install. It is the most machinery.

Lean: (a). The gate exists to stop a rewrite at the commit that makes it. The audit of history is a different job, and plain `--against-git` already does it. If the hole for hook-less paths matters, add the pushed-range check from (b) to pre-push later, as its own decision.

Also noted, not part of the fork: the gate reads the working tree, not the index. Under the pre-commit framework, unstaged changes are stashed, so the two agree there. A hook outside that framework can judge unstaged edits.

Defect bead: seeds-fn85.

RULED 2026-11-03 (Ryan): direction (a). `seeds check --gate` drops the HEAD~1 fallback. When the seed store equals HEAD, the gate does no git comparison and passes. Plain `seeds check --against-git` keeps the fallback as the history audit that seeds-wurl needed. Ryan accepted the cost: a mass change that enters through a merge, cherry-pick or rebase is not caught automatically. Build work is bead seeds-fn85.
