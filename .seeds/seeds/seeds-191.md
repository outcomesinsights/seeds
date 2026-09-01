---
id: seeds-191
title: "Worktree-aware .seeds resolution: match beads (a worktree falls back to main repo's DB)"
status: captured
type: idea
created_at: 2026-07-10T02:53:57.848293+00:00
updated_at: 2026-08-31T20:02:45.821327+00:00
tags:
  - worktree
  - git
  - db-resolution
  - beads-parity
  - dogfood
relationships:
  - target_id: seeds-lcfa.2
    rel_type: relates-to
    created_at: 2026-08-26T03:40:53.696841+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

DECISION (@aguynamedryan, 2026-07-09): seeds should resolve its store across git worktrees the way beads does, so agents stop cp-ing seeds.db between worktrees. Surfaced by the finding-memo deliberation repo (constellation-CLI research; its memo-2 CLI-bypass audit + memo-3.5 worktree audit). Today seeds has ZERO git/worktree awareness; beads handles it deliberately.

CURRENT (src/seeds/db.py):
- find_seeds_dir() walks up the directory tree from cwd looking for a .seeds/; Database() default path is cwd/.seeds/seeds.db. No git, no main-repo concept.
- Because seeds.jsonl is git-TRACKED but seeds.db is gitignored, every worktree checkout has a .seeds/seeds.jsonl (branch snapshot) but no live seeds.db -> seeds bootstraps an empty/stale db in the worktree -> divergence -> the manual `cp seeds.db` + `seeds sync` workaround seen in the wild.

TARGET — port beads' FindBeadsDir resolution order into find_seeds_dir():
  1. SEEDS_DIR env override (already respected).
  2. If inside a git worktree:
     a. use the worktree's OWN .seeds/ ONLY IF it has a real DB/config (separate-DB / isolated mode);
     b. else FALL BACK to the main repo's .seeds/ (shared-DB mode).
  3. Else walk up the tree (today's behavior).

CRITICAL TRAP — the one thing a naive port gets wrong: beads decides "this worktree has its own DB" via hasBeadsProjectFiles(), which keys off config.yaml / metadata.json / *.db — NEVER the tracked issues.jsonl. Seeds tracks seeds.jsonl, so if the seeds detector keys off "does .seeds/ or seeds.jsonl exist" it will ALWAYS pick separate-DB mode and NEVER fall back to main — silently defeating the fix. The seeds detector MUST key off seeds.db (or a seeds config file). seeds.db is gitignored, so a fresh worktree correctly lacks it -> falls back to main.

MAIN-REPO ROOT = dirname(`git rev-parse --git-common-dir`). Exactly what beads GetMainRepoRoot does for a worktree — one subprocess call, no libgit2. Detect "am I in a worktree" by comparing `git rev-parse --git-dir` vs `--git-common-dir` (they differ in a worktree).

TESTS (mirror beads integrations/beads-mcp/tests/test_worktree_separate_dbs.py):
  - shared-fallback: seeds init in main, `git worktree add` a branch; from the worktree (only the tracked seeds.jsonl present) assert seeds resolves to MAIN's seeds.db and sees main's seeds.
  - separate-DB: after an explicit `seeds init` inside the worktree, assert it stays isolated with its own db.
  - (optional) detached-commit / megarepo worktree layout: beads prefers a stable-branch worktree there — decide whether seeds needs the same.

INTERIM (no release needed): callers/wrappers can export SEEDS_DIR=<main>/.seeds when invoking seeds inside a worktree to force shared-DB behavior today.

Scope: one function + a git helper + two integration tests. Reference implementation to copy: beads internal/beads/beads.go (FindBeadsDir, hasBeadsProjectFiles) and internal/git/gitdir.go (GetMainRepoRoot).

DECISION (@aguynamedryan, 2026-07-10): Resolve to the MAIN repo's .seeds/ from ANY git worktree — always. Separate-DB mode is dropped entirely: seeds does NOT try to detect whether a worktree has its own store. This RETIRES the CRITICAL TRAP above — with nothing to detect, the seeds.db-vs-seeds.jsonl keying problem disappears. SEEDS_DIR stays as the sole escape hatch for a deliberately isolated store.

Reads AND writes both resolve to main (answers the read/write-asymmetry concern raised in review): sync/export from inside a worktree updates MAIN's .seeds/ (main's db and main's seeds.jsonl), never the worktree's branch snapshot.

RESOLUTION ORDER (final):
  1. SEEDS_DIR env override -> use it (unchanged).
  2. Inside any git repo (main OR worktree) -> use <main-repo-root>/.seeds/ for BOTH read and write. main-repo-root = dirname of `git rev-parse --git-common-dir`, resolved to an ABSOLUTE path before taking dirname.
  3. Not a git repo, or git unavailable/errors -> walk up the directory tree (today's behavior). Any git failure MUST degrade to this, never crash: find_seeds_dir() is on every command's hot path.

SCOPE (revised: three call sites, not one). The worktree-aware resolver must back all three currently-cwd-based defaults, or the read/write split reappears:
  - Database() default (db.py): Path.cwd()/.seeds/seeds.db
  - export_to_jsonl() default output (export.py): Path.cwd()/.seeds/seeds.jsonl
  - import default input (export.py): Path.cwd()/.seeds/seeds.jsonl
Plus a graceful git-failure fallback, and a shared-fallback integration test: a worktree carrying only the tracked seeds.jsonl + .gitignore (no seeds.db) resolves to MAIN for read AND write, and `seeds sync` from that worktree does NOT overwrite the branch's tracked seeds.jsonl with main's contents.

CONSEQUENCE (accepted, not a bug): a branch's tracked seeds.jsonl goes inert inside a worktree (seeds uses main's instead), and saving from a worktree edits the MAIN checkout's seeds.jsonl on disk. Consistent with "one shared deliberation store" and with how beads already behaves. Open future question, out of scope here: should non-main branches track seeds.jsonl at all?


--- STILL UNBUILT, AND NOW CONFIRMED INDEPENDENT OF THE STORAGE QUESTION (2026-08-25) ---

Raised during the Dolt deliberation: would a different storage engine make worktrees more reliable? No — and the reasoning is worth recording here so this seed does not get parked behind a storage decision it has nothing to do with (full write-up in seeds-lcfa.2).

Re-verified today, unchanged since this seed was written: `find_seeds_dir()` at src/seeds/db.py:110 still just walks up the directory tree with no git awareness; `.seeds/.gitignore` still ignores `*.db` while seeds.jsonl stays tracked. So a fresh worktree still gets a branch-snapshot JSONL and no live DB.

Why no engine fixes it: beads' `.beads/embeddeddolt/` is gitignored exactly like our seeds.db — confirmed with `git ls-files .beads`, which lists only issues.jsonl, metadata.json, config.yaml, export-state.json and the hooks. A worktree gets no Dolt data either. Beads solved worktrees with resolution logic (FindBeadsDir + GetMainRepoRoot), not with Dolt. Any engine we pick inherits the identical hole until this seed's fix lands.

The one storage-flavoured alternative — worktree as a Dolt branch, merged at integration — is the isolated-per-worktree model this seed EXPLICITLY dropped on 2026-07-10 in favour of "everyone resolves to main." Proposing it means reopening that decision, not implementing this one.

Status unchanged: decision made 2026-07-10, scope is one function plus a git helper plus two integration tests, nothing blocks it, and parallel-worktree bead workflows are hitting the problem now. This is the cheapest ready thing in this whole area and it should not wait.
