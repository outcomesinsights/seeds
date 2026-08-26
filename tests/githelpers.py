"""Shared helpers for tests that shell out to real git.

Every test that builds a throwaway repository goes through here, and the
reason is an incident on 2026-08-26 (seed seeds-ngez, bead seeds-p0x): a
fixture running inside an agent worktree wrote ``core.bare=true`` and a test
identity into this repo's own ``.git/config``, leaving the main working tree
unable to run ``git status`` at all. A linked worktree shares ``.git/config``
with the main repo, so a plain ``git config <k> <v>`` from inside one lands in
the shared file. That was the third time this class of leak bit the suite, so
the containment here is deliberately belt-and-braces:

* ``_subprocess_env()`` (from ``seeds.gitstage``) strips the six repo-pinning
  ``GIT_*`` variables git exports into hooks. That is production behaviour
  ``seeds sync`` genuinely needs, and it is right here for the same reason:
  running this suite as this repo's own pre-commit ``pytest`` hook otherwise
  leaks them in from the real commit in progress.
* Everything layered on top is TEST-ONLY, and deliberately not in ``src/``.
  ``GIT_CEILING_DIRECTORIES`` stops git walking up out of the directory under
  test to find a real repository, and ``GIT_CONFIG_GLOBAL`` /
  ``GIT_CONFIG_SYSTEM`` point at ``os.devnull`` so no test can read or write
  the host's git config. Production ``seeds sync`` must respect the user's
  real global config; only a test has any business redirecting it.

The split matters: the deny-list half is shared with production because it
describes git's hook contract, and the redirection half is not, because it
describes a sandbox only tests should ever be in.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from seeds.gitstage import _subprocess_env

# The identity every throwaway repo gets. Named constants rather than inline
# literals so the session guard in conftest.py can recognise these exact
# values if they ever escape into a real repo's config again.
TEST_EMAIL = "test@example.com"
TEST_NAME = "Test"

# git exports these into every hook, and they take precedence over config --
# so a suite run as this repo's own pre-commit `pytest` hook would otherwise
# author its throwaway commits as the real user rather than the fixture
# identity. Caught by test_init_commit_and_identity_round_trip, which passes
# standalone and fails under the hook: the exact split-behaviour this module
# exists to eliminate. Stripped test-side only -- production `seeds sync`
# never commits, so seeds.gitstage has no business touching identity.
_IDENTITY_ENV_VARS = (
    "GIT_AUTHOR_NAME",
    "GIT_AUTHOR_EMAIL",
    "GIT_AUTHOR_DATE",
    "GIT_COMMITTER_NAME",
    "GIT_COMMITTER_EMAIL",
    "GIT_COMMITTER_DATE",
)


def git_env(cwd: Path) -> dict[str, str]:
    """Environment for a git call in ``cwd`` that cannot escape ``cwd``.

    The ceiling is ``cwd``'s parent, which means git searches ``cwd`` and then
    refuses to chdir up any further -- so discovery can only ever find a
    repository at ``cwd`` itself, never an ancestor. That is the containment
    that would have stopped the 2026-08-26 incident: the leak worked by git
    resolving upward to the real repo and writing its config.
    """
    sandbox = Path(cwd).resolve().parent
    env = _subprocess_env()
    for name in _IDENTITY_ENV_VARS:
        env.pop(name, None)
    env["GIT_CEILING_DIRECTORIES"] = str(sandbox)
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    # GIT_CONFIG_GLOBAL covers ~/.gitconfig, but git still reads HOME for
    # include.path chains, init.templateDir and credential helpers -- so point
    # HOME at the sandbox too, closing the category rather than the one path.
    # Neither knob is set globally on titan today; the lesson of seeds-p0x is
    # that the instance is never the last one.
    env["HOME"] = str(sandbox)
    env["XDG_CONFIG_HOME"] = str(sandbox)
    return env


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git subcommand in ``cwd``; raises on failure so setup errors are loud."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        env=git_env(cwd),
    )


def git_init(cwd: Path) -> None:
    """Initialize a throwaway git repo at ``cwd`` with a usable local identity.

    ``commit.gpgsign`` is forced off locally (not globally) so a signing key
    configured on the host can never turn a test into a hang waiting on a
    passphrase prompt.
    """
    git(cwd, "init", "-q")
    git(cwd, "config", "user.email", TEST_EMAIL)
    git(cwd, "config", "user.name", TEST_NAME)
    git(cwd, "config", "commit.gpgsign", "false")
