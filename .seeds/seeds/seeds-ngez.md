---
id: seeds-ngez
title: "Test git fixtures can brick the main repo: agent worktrees share .git/config, and a bad write is silent until git stops working"
status: resolved
type: concern
created_at: 2026-08-26T21:07:57.117604+00:00
updated_at: 2026-08-31T21:35:01.590436+00:00
resolved_at: 2026-08-31T21:35:01.590429+00:00
resolution: "Closed out by the containment in 3919c00 plus the hardening in seeds-ngez.1. Three layers now stand between a test fixture and the main working tree: the sandboxed environment in tests/githelpers.py, the single-door test that enforces it, and scripts/check_git_config_sanity.py wired as a pre-commit hook ('git config sanity (not bare, no test identity)') so a bad core.bare or test identity is caught at commit rather than the next time git stops working. Efficacy: no tweaking, but the incident itself was an inherent unknown — nothing short of it happening would have surfaced that agent worktrees share .git/config."
tags:
  - testing
  - git
  - worktrees
  - isolation
  - ci
  - incident
  - 2026-08-26
converted_at: 2026-09-01T05:20:22.746832+00:00
---

INCIDENT (2026-08-26, titan). The main working tree of this repo became
unusable mid-session: `git status`, `git add` and `git commit` all failed with
`fatal: this operation must be run in a work tree`. Cause was four values that
appeared in .git/config at 13:44:24 -

    core.bare=true              <- this is what broke it
    user.email=test@example.com
    user.name=Test
    commit.gpgsign=false

@aguynamedryan ran the repair by hand (`git config --local core.bare false`, plus
--unset on the other three). No commit was ever authored with the bad
identity - it arrived after the 13:24 commit, and all commits check out as
@aguynamedryan <aguynamedryan@gmail.com>.

ROOT CAUSE, established from the timeline rather than guessed:
- 13:44 - worktree agent-a615c1063024add25, on branch
  seeds-ww8/guard-mixed-stage-flush, was developing the mixed-stage guard.
- 13:50 - that work merged as 00ed416, introducing src/seeds/gitstage.py and
  tests/test_gitstage.py.
- 13:54 - the worktree was removed, taking the direct evidence with it.

The three identity values are byte-identical to `_git_init()` at
tests/test_gitstage.py:47-49 and tests/test_cli.py:2495-2497, which shell out
to real git to build a throwaway repo. `core.bare=true` is the signature of
`git init` resolving to the main .git with no work tree attached. And the
mechanism that carried it into the main repo is that A LINKED WORKTREE SHARES
.git/config WITH THE MAIN REPO - a plain `git config <k> <v>` from inside a
worktree defaults to --local, which is the common config file.

THE IRONY, and the reason this is worth a seed rather than just a fix:
src/seeds/gitstage.py already carries `_subprocess_env()`, which strips six
repo-pinning GIT_* variables, and its own comment says it was written after
discovering exactly this class of bug ("run as a pytest hook inside `git
commit` ... would otherwise silently redirect into the real repo's index").
THE FIX LANDED SIX MINUTES AFTER THE DAMAGE. The guard was right; what was
missing was (a) anyone reverting the damage already done, and (b) any detector
that would have noticed. The repo sat bricked for ~20 minutes and was found
only because an unrelated `git add` failed.

WHY THIS IS A STANDING HAZARD, not a one-off. Agent worktrees under
.claude/worktrees/ are how every /bead-go run operates, and they all share one
.git/config. Any test in any future bead that shells out to git can do this
again. The blast radius is the developer's main working tree.

WHAT DOES *NOT* FIX IT - recorded so it is not re-proposed. Enabling
`extensions.worktreeConfig` was my first instinct and it is wrong twice over,
per git-worktree(1) on git 2.55.0:
- With the extension DISABLED (today's state), git already special-cases
  core.bare and core.worktree in the shared config so they "will be applied to
  the main worktree only". That is precisely why the four agent worktrees kept
  working while the main tree broke. Turning the extension ON removes that
  exception - the docs say you must then move core.bare into the main
  worktree's config.worktree by hand - so a stray core.bare=true would have
  propagated to EVERY worktree instead of one.
- It would not have prevented the write anyway. The extension only redirects
  `git config --worktree`. A test doing plain `git config user.email ...`
  defaults to --local and reaches the shared file either way.

PROPOSED REMEDIATION, in priority order:
1. DETECT. A pre-commit assertion that fails loudly if core.bare is true or
   user.email looks like a test fixture. The whole cost of this incident was
   that a config error surfaces as an unrelated, unexplained git failure. This
   converts a silent brick into a self-explaining one, and it must run inside
   worktrees too, not just the main tree.
2. CONTAIN POSITIVELY. `_subprocess_env()` is a deny-list of six variables -
   reactive, and it does not cover GIT_CONFIG, GIT_CONFIG_GLOBAL or
   GIT_CONFIG_SYSTEM. Better: set GIT_CEILING_DIRECTORIES to the tmpdir's
   parent so git physically cannot walk up to the real repo, and point
   GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM at /dev/null so no test can read or
   write host config.
3. DE-DUPLICATE. `_git` and `_git_init` exist twice, in test_gitstage.py and
   test_cli.py. Two copies of a safety-critical fixture will drift. They belong
   in tests/conftest.py.
4. ACCEPT the worktree sharing and rely on 1 to catch recurrences, since
   prevention at the git-config layer is not available (see above).

OPEN QUESTION worth deciding before implementing 2: whether the ceiling/config
redirection belongs in `_subprocess_env()` in src/, which is production code
whose purpose is different, or in a test-only fixture. Production `seeds sync`
has a legitimate reason to strip repo-pinning vars; it has no business
redirecting the user's global git config. Those are two different jobs that
currently share one function.


TRACKED AS: bead seeds-p0x (P1 bug) - carries the remediation plan, the
rejected extensions.worktreeConfig option, and acceptance criteria.


--- RESOLVED IN IMPLEMENTATION (2026-08-26, commit 3919c00) ---

THE OPEN QUESTION ABOVE IS ANSWERED: the sandboxing belongs in a TEST-ONLY
helper, not in `_subprocess_env()`. The two jobs really are different and the
split is now explicit in tests/githelpers.py:
- Shared with production: stripping the six repo-pinning GIT_* vars. That
  describes git's hook contract, and `seeds sync` needs it for its own reasons.
- Test-only, deliberately NOT in src/: GIT_CEILING_DIRECTORIES,
  GIT_CONFIG_GLOBAL/SYSTEM -> /dev/null, and the identity variables.
  Production sync must respect the user's real global config, and it never
  commits, so it has no business touching any of these.

A SEVENTH LEAK FOUND BY THE FIX'S OWN TEST, worth recording because it is the
same shape as the original and nearly shipped unnoticed: git exports
GIT_AUTHOR_NAME/EMAIL/DATE and GIT_COMMITTER_NAME/EMAIL/DATE into every hook,
and those OUTRANK config. So a throwaway repo built by the suite authored its
commits as the real user whenever the suite ran as this repo's pre-commit
pytest hook. The test passed standalone and failed only inside a commit -
exactly the split behaviour this whole effort exists to eliminate. Now
stripped, and the test sets those variables itself so the hook case runs every
time rather than only during a commit.

WHAT SHIPPED:
- tests/githelpers.py - the sandbox, and the single home for _git/_git_init
  (previously duplicated in test_gitstage.py and test_cli.py, which is how one
  copy came to poison a real repo).
- tests/conftest.py - session-scoped autouse guard that snapshots the ambient
  shared .git/config and fails the run if the suite changed it. Reads the file
  directly rather than shelling out, so it still works on a repo git can no
  longer open - which is why it is the PRIMARY alarm and the hook is secondary.
- scripts/check_git_config_sanity.py - first pre-commit hook; catches an
  already-poisoned config and prints the repair, the part that was not obvious
  in the moment.
- Both resolvers handle a worktree's `.git` FILE by resolving two levels up to
  the shared config, and TestTheTwoResolversAgree pins the duplicate walks
  together on hand-built trees.

642 passed, mypy strict and ruff clean, and - the acceptance criterion that
actually mattered - the suite passes when run as this repo's own pre-commit
pytest hook.
