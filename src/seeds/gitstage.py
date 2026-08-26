"""Best-effort read of what's staged for commit, for the mixed-stage guard.

``seeds sync``'s export half rewrites ``.seeds/seeds.jsonl`` wholesale. Run as
part of a pre-commit hook, the pre-commit framework re-stages whatever the
export just wrote, so any not-yet-flushed database change gets folded into
whatever commit fires next -- regardless of topic (seeds-ww8). Telling that
apart from an ordinary, on-topic flush requires asking git what else is
staged.

Everything here is best-effort, matching ``seeds.beads``: ``sync`` is also
invoked outside any commit context at all -- a manual flush before
``git add``, a project with no git repo. None of those are errors. git being
absent, the cwd not being inside a git working tree, or the git call
otherwise failing all degrade to "no commit context" (``None``) so ``sync``
keeps working. This module must never be the reason ``sync`` crashes.
"""

from __future__ import annotations

import os
import subprocess

# Git points a hook (and anything the hook itself spawns) at a specific repo
# and index via these variables, so a hook script that changes directories
# still operates on the commit in progress. That is exactly backwards for
# this module: seeds sync is meant to run AS such a hook, but this function
# has to answer for the directory it is actually asked about, not for
# whatever repo the calling process happens to be mid-operation on. Discovered
# via this project's own test suite -- run as a pytest hook inside `git
# commit` -- reporting a "no git repo" tmp dir as part of the seeds worktree
# whose pre-commit run spawned it. Stripped so plain cwd-based discovery is
# always what decides the answer.
_GIT_REPO_ENV_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
)


def _subprocess_env() -> dict[str, str]:
    """The current environment with repo-pinning GIT_* variables removed."""
    return {k: v for k, v in os.environ.items() if k not in _GIT_REPO_ENV_VARS}


def staged_paths_outside(seeds_dir: str) -> list[str] | None:
    """Paths staged for commit outside ``seeds_dir``, or ``None`` if unknown.

    ``None`` means there is no commit context to guard: git isn't installed,
    the current directory isn't inside a git working tree, or the git
    invocation otherwise failed. An initial commit (no ``HEAD`` yet) is NOT
    one of these cases -- ``git diff --cached`` handles an unborn branch by
    diffing against the empty tree, so it still returns a real (possibly
    empty) list there.

    An empty list is a different, meaningful answer from ``None``: there IS a
    commit context, it's simply clean outside ``seeds_dir``.
    """
    env = _subprocess_env()
    try:
        inside = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except OSError:
        return None
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return None

    exclude_pathspec = f":!{seeds_dir.rstrip('/')}/"
    try:
        diff = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--", exclude_pathspec],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except OSError:
        return None
    if diff.returncode != 0:
        return None

    return [line for line in diff.stdout.splitlines() if line.strip()]
