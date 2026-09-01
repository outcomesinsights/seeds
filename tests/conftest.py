"""Pytest fixtures for seeds tests."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from seeds.models import SeedStatus, SeedType
from seeds.store import Store, new_record


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def store(temp_dir):
    """An initialized, empty seed-file store in a temp directory."""
    seeds_dir = temp_dir / ".seeds"
    store = Store(seeds_dir)
    store.files_dir.mkdir(parents=True, exist_ok=True)
    store.set_prefix("seeds")
    return store


@pytest.fixture
def sample_record():
    """A sample seed record for testing."""
    return new_record(
        "seed-test",
        "Test Seed",
        body="This is test content",
        status=SeedStatus.CAPTURED,
        seed_type=SeedType.IDEA.value,
        tags=["test", "sample"],
    )


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture
def cli_env(temp_dir):
    """Create environment for CLI testing with isolated .seeds directory."""
    seeds_dir = temp_dir / ".seeds"
    seeds_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def _ambient_shared_git_config(start: Path | None = None) -> Path | None:
    """The ``.git/config`` of whatever real repo this suite is running inside.

    Returns ``None`` when there is no such repo -- ``nix flake check`` unpacks
    a source tree with no ``.git`` at all, and the suite must stay green there
    (859aacd). For a linked worktree, ``.git`` is a *file* pointing at
    ``<main>/.git/worktrees/<name>``, and the config that matters is the
    SHARED one two levels up: that sharing is the whole mechanism behind the
    incident this guard exists for.
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


@pytest.fixture(scope="session", autouse=True)
def _guard_ambient_git_config():
    """Fail the session if the suite mutated the real repo's git config.

    On 2026-08-26 a test fixture wrote ``core.bare=true`` plus a test identity
    into this repo's own ``.git/config``, which left the main working tree
    unable to run ``git status``, ``git add`` or ``git commit`` at all -- for
    about twenty minutes, until an unrelated command happened to fail. The
    write itself was silent (seed seeds-ngez, bead seeds-p0x).

    Detection lives here rather than only in a git hook because once
    ``core.bare=true`` is set, git is broken and a hook can no longer run to
    report it. Reading the file is plain I/O, so this still works on a repo
    that git itself has stopped being able to open.

    tests/githelpers.py is the containment; this is the alarm that says the
    containment failed.
    """
    config = _ambient_shared_git_config()
    before = config.read_bytes() if config and config.exists() else None
    yield
    if before is None:
        return
    after = config.read_bytes() if config.exists() else None
    if after != before:
        raise AssertionError(
            f"The test suite modified {config} -- this breaks the real "
            f"repository. Every git call in a test must go through "
            f"tests/githelpers.py, which sandboxes it. See bead seeds-p0x.\n"
            f"Repair with:\n"
            f"  git config --local core.bare false\n"
            f"  git config --local --unset user.email\n"
            f"  git config --local --unset user.name\n"
            f"  git config --local --unset commit.gpgsign"
        )
