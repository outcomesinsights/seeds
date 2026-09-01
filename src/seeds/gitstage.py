"""The one door to git: how it is invoked, and the one write seeds performs.

Everything in ``src/`` that starts a ``git`` process comes through here. That
is the same rule tests/githelpers.py enforces on the suite (see
tests/test_git_single_door.py), and for the same reason: the hardening below is
easy to write once and easy to forget the second time, and a second copy is how
the 2026-08-26 incident happened.

**The hook contract.** :func:`_subprocess_env` strips the repo-pinning ``GIT_*``
variables. A hook -- and anything the hook spawns -- inherits ``GIT_DIR`` and
friends pointing at the commit in progress, so a subprocess that asks a question
about some *other* directory gets an answer about the wrong repository.
Discovered by this project's own suite, run as a pytest hook inside ``git
commit``, reporting a "no git repo" tmp dir as part of the seeds worktree whose
pre-commit run spawned it.

**Reads, and exactly one write.** :mod:`seeds.githistory` and :mod:`seeds.check`
only ever ask git questions. The single exception is
:func:`stage_tracked_deletion`, which stages the removal of the retired
``.seeds/seeds.jsonl`` during ``seeds convert``. It is a write, so it is fenced
by :func:`plan_tracked_deletion`: three conditions, all required, each of whose
failures means git could not restore the file afterwards.

This module used to hold ``staged_paths_outside``, the git-side half of ``seeds
sync``'s mixed-stage guard. That guard existed because the export rewrote
``.seeds/seeds.jsonl`` wholesale and, run inside a pre-commit hook, could fold
a not-yet-flushed database change into whatever commit fired next (seeds-ww8).
Both the export and the flush are gone: a seed IS its file, written before the
command returns, so there is no pending state for a commit to capture and
nothing left for the guard to protect.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "DeletionPlan",
    "GitUnavailable",
    "git_bytes",
    "git_text",
    "plan_tracked_deletion",
    "repo_root",
    "stage_tracked_deletion",
]

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


class GitUnavailable(Exception):
    """git could not answer at all: not installed, or not in a work tree."""


def git_text(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git subcommand in ``cwd`` and capture its output as text."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env=_subprocess_env(),
        )
    except OSError as exc:  # git not installed, cwd gone
        raise GitUnavailable(f"could not run git: {exc}") from exc


def git_bytes(
    cwd: Path, *args: str, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    """As :func:`git_text`, but for output that is blob content, not text.

    Seed files are UTF-8 by the format, but a corrupted one in history is
    exactly the sort of thing a checker is asked about, so the bytes are
    decoded with replacement at the point of use rather than here.
    """
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            check=False,
            input=stdin,
            env=_subprocess_env(),
        )
    except OSError as exc:
        raise GitUnavailable(f"could not run git: {exc}") from exc


def repo_root(path: Path) -> Path:
    """The work tree containing ``path``, or raise :class:`GitUnavailable`."""
    path = Path(path)
    if not path.is_dir():
        raise GitUnavailable(f"{path} is not a directory")
    proc = git_text(path, "rev-parse", "--show-toplevel")
    if proc.returncode != 0 or not proc.stdout.strip():
        raise GitUnavailable(
            f"{path} is not inside a git work tree, so there is no history "
            f"to compare against"
        )
    return Path(proc.stdout.strip()).resolve()


# --- Staging a deletion git can undo ------------------------------------------


@dataclass(frozen=True)
class DeletionPlan:
    """Whether git holds a restorable copy of ``path``, and if not, why not.

    ``blocker`` is the whole product. Deleting a file git cannot restore is
    unrecoverable, so each of the three conditions below is checked in turn and
    the first failure is reported *as a sentence naming the condition* rather
    than as a bare false.
    """

    path: Path
    root: Path | None = None
    relpath: str | None = None
    blocker: str | None = None

    @property
    def deletable(self) -> bool:
        """Whether all three conditions hold, so git can restore the file."""
        return self.blocker is None


def plan_tracked_deletion(path: Path) -> DeletionPlan:
    """Decide whether ``path`` can be deleted with git holding the only copy.

    Three conditions, **all required**, because failing any one of them means
    the bytes about to be removed exist nowhere else:

    1. ``path`` is inside a git work tree.
    2. ``path`` is **tracked**. An untracked file has never been committed, so
       there is nothing to check out afterwards.
    3. ``path`` has **no uncommitted changes** — staged or unstaged. An
       uncommitted delta is, by definition, in the working file and nowhere
       else, and the last commit's version is not it.

    Returns a plan either way; the caller reports the blocker rather than
    treating it as an error, because "leave the file alone and say why" is the
    correct outcome, not a failure.
    """
    path = Path(path)
    parent = path.parent
    try:
        root = repo_root(parent)
    except GitUnavailable:
        return DeletionPlan(
            path=path,
            blocker=(
                f"{parent} is not inside a git work tree, so nothing holds a "
                f"copy of the file to restore from"
            ),
        )

    try:
        relpath = path.resolve().relative_to(root).as_posix()
    except ValueError:  # a symlinked path that resolves outside the work tree
        return DeletionPlan(
            path=path,
            root=root,
            blocker=f"{path} resolves outside the work tree at {root}",
        )

    tracked = git_text(root, "ls-files", "--error-unmatch", "--", relpath)
    if tracked.returncode != 0:
        return DeletionPlan(
            path=path,
            root=root,
            relpath=relpath,
            blocker=(
                f"{relpath} is not tracked by git, so git holds no copy of it "
                f"to restore from"
            ),
        )

    status = git_text(root, "status", "--porcelain", "--", relpath)
    if status.returncode != 0:
        return DeletionPlan(
            path=path,
            root=root,
            relpath=relpath,
            blocker=f"git could not report the status of {relpath}",
        )
    if status.stdout.strip():
        return DeletionPlan(
            path=path,
            root=root,
            relpath=relpath,
            blocker=(
                f"{relpath} has uncommitted changes, and an uncommitted change "
                f"exists nowhere but that file"
            ),
        )

    return DeletionPlan(path=path, root=root, relpath=relpath)


def stage_tracked_deletion(plan: DeletionPlan) -> None:
    """Remove the file and stage the removal, so it lands in the next commit.

    ``git rm`` rather than a bare ``rm``: the index entry has to go too, or the
    next commit does not carry the removal and the operator is left with a
    deletion that git reports as unstaged work. And rather than ``git rm
    --cached``, which would leave the retired file sitting on disk — the whole
    hazard being removed is a file that goes on *looking* authoritative while
    nothing updates it.

    Refuses a plan that is not :attr:`~DeletionPlan.deletable`; the fence is
    :func:`plan_tracked_deletion` and calling this around it is a bug.
    """
    assert plan.deletable, f"refusing to stage an unsafe deletion: {plan.blocker}"
    assert plan.root is not None and plan.relpath is not None
    proc = git_text(plan.root, "rm", "--quiet", "--", plan.relpath)
    if proc.returncode != 0:
        raise GitUnavailable(
            f"could not stage the deletion of {plan.relpath}: "
            f"{proc.stderr.strip() or proc.returncode}"
        )
