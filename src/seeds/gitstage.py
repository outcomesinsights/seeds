"""git's hook contract, in one place: the repo-pinning environment variables.

This module used to hold ``staged_paths_outside``, the git-side half of ``seeds
sync``'s mixed-stage guard. That guard existed because the export rewrote
``.seeds/seeds.jsonl`` wholesale and, run inside a pre-commit hook, could fold
a not-yet-flushed database change into whatever commit fired next (seeds-ww8).
Both the export and the flush are gone: a seed IS its file, written before the
command returns, so there is no pending state for a commit to capture and
nothing left for the guard to protect.

What survives is :func:`_subprocess_env`, and it survives because it describes
something about git rather than about sync. A hook -- and anything the hook
spawns -- inherits ``GIT_DIR`` and friends pointing at the commit in progress,
so a subprocess that asks a question about some *other* directory gets an
answer about the wrong repository. Discovered by this project's own suite, run
as a pytest hook inside ``git commit``, reporting a "no git repo" tmp dir as
part of the seeds worktree whose pre-commit run spawned it.

:mod:`seeds.githistory` and tests/githelpers.py both need that, which is why it
lives here rather than in either of them.
"""

from __future__ import annotations

import os

# Git points a hook (and anything the hook itself spawns) at a specific repo
# and index via these variables, so a hook script that changes directories
# still operates on the commit in progress. Stripped so plain cwd-based
# discovery is always what decides the answer.
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
