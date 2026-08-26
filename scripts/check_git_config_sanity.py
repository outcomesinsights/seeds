#!/usr/bin/env python3
"""Fail loudly if this repo's own git config has been poisoned (bead seeds-p0x).

On 2026-08-26 a test fixture running inside an agent worktree wrote
``core.bare=true`` plus a test identity into this repository's ``.git/config``.
A linked worktree shares that file with the main repo, so a plain ``git config
<k> <v>`` from inside one lands in the shared config. The main working tree
then could not run ``git status``, ``git add`` or ``git commit`` at all, and
because the symptom is the unhelpful ``fatal: this operation must be run in a
work tree``, nothing connected it to the config for about twenty minutes.

This is the cheap second alarm. The first is the session guard in
tests/conftest.py, which catches the write as it happens; this catches a
poisoned config that arrived some other way, and — more importantly — prints
the repair, which is the part that was not obvious in the moment.

The config file is read via ``git config --file``, which does no repository
discovery, so this keeps working on a repo git has otherwise stopped opening.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Matches tests/githelpers.py. Duplicated rather than imported because this
# runs as a git hook, outside the project's virtualenv.
TEST_EMAIL = "test@example.com"
TEST_NAME = "Test"

REPAIR = """\
Repair with:
  git config --local core.bare false
  git config --local --unset user.email
  git config --local --unset user.name
  git config --local --unset commit.gpgsign"""


def shared_config(start: Path | None = None) -> Path | None:
    """The shared ``.git/config`` at or above ``start`` (default: this script).

    A linked worktree's ``.git`` is a FILE pointing at
    ``<main>/.git/worktrees/<name>``, and the config that matters is the
    SHARED one two levels up -- that sharing is the entire mechanism behind
    the incident this script guards against, so it must resolve to the main
    repo's config, not the worktree's private directory.

    ``start`` is a parameter so the suite can exercise both layouts against
    hand-built trees.
    """
    origin = Path(__file__) if start is None else Path(start)
    for parent in origin.resolve().parents:
        dot_git = parent / ".git"
        if dot_git.is_dir():
            return dot_git / "config"
        if dot_git.is_file():
            text = dot_git.read_text().strip()
            if text.startswith("gitdir:"):
                gitdir = Path(text.split(":", 1)[1].strip())
                if gitdir.parent.name == "worktrees":
                    return gitdir.parent.parent / "config"
                return gitdir / "config"
    return None


def get(config: Path, key: str) -> str | None:
    result = subprocess.run(
        ["git", "config", "--file", str(config), "--get", key],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def main(argv: list[str] | None = None) -> int:
    """Check ``argv[0]`` if given, else this repo's own shared config.

    The optional argument exists so the suite can point this at hand-built
    poisoned configs; the hook always calls it with no arguments.
    """
    argv = sys.argv[1:] if argv is None else argv
    config = Path(argv[0]) if argv else shared_config()
    if config is None or not config.exists():
        return 0

    problems = []
    if (get(config, "core.bare") or "").lower() == "true":
        problems.append(
            "core.bare=true — the main working tree cannot run git at all "
            "while this is set. This repo is a normal checkout, never bare."
        )
    if get(config, "user.email") == TEST_EMAIL:
        problems.append(f"user.email={TEST_EMAIL} — a test fixture identity.")
    if get(config, "user.name") == TEST_NAME:
        problems.append(f"user.name={TEST_NAME} — a test fixture identity.")

    if not problems:
        return 0

    print(f"\n{config} has been poisoned by a test fixture:\n", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    print(
        f"\nA linked worktree shares this file with the main repo, so a test "
        f"that shells out to git without the tests/githelpers.py sandbox can "
        f"write it. See bead seeds-p0x.\n\n{REPAIR}\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
