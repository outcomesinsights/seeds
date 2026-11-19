---
id: seeds-kadx
title: seeds init leaves .seeds/seeds/ empty, so git drops it and a worktree of a new project reads as uninitialized
status: captured
type: question
created_at: 2026-11-19T04:52:06.002813+00:00
updated_at: 2026-11-19T04:52:12.731350+00:00
tags:
  - init
  - worktree
  - git
  - store
---

## The report

Session hm (~/.config/home-manager) relayed this on 2026-11-18 at Ryan's request. Session tasks-f4 found it on 2026-11-18 while creating ~/projects/outins/tasket. Ryan has not ruled on the form of the fix.

`seeds init` creates `.seeds/config.yaml`, `.seeds/.mdformat.toml` and an EMPTY `.seeds/seeds/`. git does not track an empty directory. So a commit of `.seeds/` made before the first seed holds only the two config files. A worktree made from that commit has no `.seeds/seeds/`, and every command that needs the store fails:

```
Error: seeds not initialized. Run 'seeds init' first.
```

Ryan's rules put all seeds work in a worktree (`wt switch --create`), so the first seeds session of every new project meets this. The state ends when the first seed file is committed on main.

## Verified here (2026-11-18)

Reproduced in a scratch repo: init, commit `.seeds/`, `git worktree add`, then `seeds list` exits 1 with the error above. Log: `claude_stuff/init-gitkeep-repro-20261118-205031.log`.

The cause is `Store.is_initialized()` (`src/seeds/store.py:262`), which returns `self.files_dir.is_dir()`. The store is "initialized" only when `.seeds/seeds/` exists.

Following the error's advice is worse than the error. `seeds init` in that worktree exits 0 and rewrites the tracked `config.yaml` from `prefix: repo` to `prefix: wt`, the worktree directory's name. Log: `claude_stuff/init-gitkeep-repro-20261118-205053.log`. Filed as bead seeds-dn8a, which is needed whatever this seed decides, because projects initialized before any fix still reach this state.

hm tested a `.gitkeep` in a scratch repo: with an empty `.seeds/seeds/.gitkeep`, `seeds check` reports "0 files, no violations", `seeds list` and `seeds jot` exit 0, and `seeds check` still passes after a seed is added.

## Options (not ruled)

(a) `seeds init` writes `.seeds/seeds/.gitkeep`. Fixes new projects only. Projects already initialized and committed before their first seed stay broken until their first seed is committed. Adds a non-seed file to the seed directory, which `seeds check` already tolerates (hm's test).

(b) A store is initialized when `.seeds/config.yaml` exists, and a missing `.seeds/seeds/` reads as "initialized but empty". Fixes existing projects too. Reads need nothing more. Writes then need (c).

(c) Create `.seeds/seeds/` on the first write. Pairs with (b). Alone it does not fix reads such as `seeds list`.

Constraint on (b): the unconverted pre-0.7 state is also "`.seeds/` present, no `seeds/` tree" (`needs_conversion`, `src/seeds/store.py:153`). Pre-0.7 stores kept the prefix in SQLite, and the converter writes `config.yaml` only if absent (`src/seeds/convert.py:2279`), so most unconverted stores have no `config.yaml`. The `needs_conversion` test must still run first, so an unconverted store is never shown as an empty one.

The hm session stated no preference. It noted that (b)+(c) also fix projects initialized before the change, and (a) does not.

## Lean

(b)+(c), and (a) is optional on top of it. (b)+(c) puts the rule in the package, which matches the principle seeds-gi9k (guidance an agent needs ships IN the package), and it repairs every existing project with no file to add. Not ruled.

## Cross-references

- home-manager bead hm-sh8l tracks the local workaround in new-project-init.sh (touch `.seeds/seeds/.gitkeep` after `seeds init`). It can be dropped once this ships.
