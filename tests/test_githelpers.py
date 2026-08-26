"""Tests for the git test sandbox itself (bead seeds-p0x).

These exist because the thing being guarded has already failed three times,
and the last failure (2026-08-26, seed seeds-ngez) left the main working tree
unable to run ``git status`` at all. A sandbox nobody tests is a sandbox that
quietly stops sandboxing, so each test here builds the leak by hand and states
the expected outcome explicitly rather than asserting "no exception raised".
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.githelpers import TEST_EMAIL, TEST_NAME, git, git_env, git_init


class TestSandboxEnvironment:
    """The env itself, asserted directly rather than through git's behaviour."""

    def test_repo_pinning_vars_are_stripped(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GIT_DIR", "/somewhere/else/.git")
        monkeypatch.setenv("GIT_INDEX_FILE", "/somewhere/else/.git/index")
        monkeypatch.setenv("GIT_WORK_TREE", "/somewhere/else")
        env = git_env(tmp_path)
        assert "GIT_DIR" not in env
        assert "GIT_INDEX_FILE" not in env
        assert "GIT_WORK_TREE" not in env

    def test_hook_identity_vars_are_stripped(self, tmp_path, monkeypatch):
        """git exports these into hooks and they outrank config."""
        monkeypatch.setenv("GIT_AUTHOR_NAME", "Real Person")
        monkeypatch.setenv("GIT_AUTHOR_EMAIL", "real@example.org")
        monkeypatch.setenv("GIT_COMMITTER_NAME", "Real Person")
        monkeypatch.setenv("GIT_COMMITTER_EMAIL", "real@example.org")
        env = git_env(tmp_path)
        assert "GIT_AUTHOR_NAME" not in env
        assert "GIT_AUTHOR_EMAIL" not in env
        assert "GIT_COMMITTER_NAME" not in env
        assert "GIT_COMMITTER_EMAIL" not in env

    def test_host_config_is_redirected_to_devnull(self, tmp_path):
        env = git_env(tmp_path)
        assert env["GIT_CONFIG_GLOBAL"] == os.devnull
        assert env["GIT_CONFIG_SYSTEM"] == os.devnull

    def test_home_is_redirected_into_the_sandbox(self, tmp_path):
        """GIT_CONFIG_GLOBAL misses include.path, templateDir and helpers."""
        env = git_env(tmp_path)
        sandbox = str(tmp_path.resolve().parent)
        assert env["HOME"] == sandbox
        assert env["XDG_CONFIG_HOME"] == sandbox
        assert env["HOME"] != os.path.expanduser("~")

    def test_ceiling_is_the_parent_so_only_cwd_is_searched(self, tmp_path):
        """Parent, not cwd: git searches cwd, then refuses to chdir above it."""
        env = git_env(tmp_path)
        assert env["GIT_CEILING_DIRECTORIES"] == str(tmp_path.resolve().parent)


class TestCannotReachAnAncestorRepo:
    """The containment that would have prevented the 2026-08-26 incident."""

    def test_config_write_from_a_subdir_cannot_reach_the_repo_above_it(self, tmp_path):
        """The incident in miniature: a git config write one level down.

        Without the ceiling, git walks up from ``sub``, finds ``outer``'s
        repository, and writes ``outer/.git/config`` -- which is exactly how a
        test fixture reached the real seeds repo. With it, discovery stops at
        ``sub``, git reports it is not in a repository, and the call fails
        loudly instead of succeeding somewhere it should never have looked.
        """
        outer = tmp_path / "outer"
        outer.mkdir()
        git_init(outer)
        before = (outer / ".git" / "config").read_bytes()

        sub = outer / "sub"
        sub.mkdir()
        with pytest.raises(subprocess.CalledProcessError):
            git(sub, "config", "user.email", "leak@example.com")

        assert (outer / ".git" / "config").read_bytes() == before

    def test_leaked_git_dir_does_not_redirect_init_into_the_outer_repo(
        self, tmp_path, monkeypatch
    ):
        """A hook's GIT_DIR must not capture a throwaway repo's setup.

        This is the shape that produced ``core.bare=true``: ``git init`` with
        GIT_DIR pointed at a real repository and no work tree re-initializes
        THAT repository as bare. The inner repo must be built at ``inner``,
        and ``outer`` must come through byte-identical.
        """
        outer = tmp_path / "outer"
        outer.mkdir()
        git_init(outer)
        before = (outer / ".git" / "config").read_bytes()

        inner = tmp_path / "inner"
        inner.mkdir()
        monkeypatch.setenv("GIT_DIR", str(outer / ".git"))
        monkeypatch.setenv("GIT_INDEX_FILE", str(outer / ".git" / "index"))
        git_init(inner)

        assert (inner / ".git").is_dir()
        assert (outer / ".git" / "config").read_bytes() == before

    def test_host_global_config_is_not_readable(self, tmp_path):
        """``--global`` resolves to /dev/null, so the host's identity is invisible.

        Skipped when the host has no global identity to leak, so the assertion
        never passes vacuously. The host config is located by reading the file
        rather than asking git, because every git call in this suite must go
        through the sandbox (bead seeds-3xs) and asking git unsandboxed is
        exactly what that forbids.
        """
        candidates = [
            Path.home() / ".gitconfig",
            Path.home() / ".config" / "git" / "config",
        ]
        if not any(c.exists() and "name" in c.read_text() for c in candidates):
            pytest.skip("host has no global git identity to leak")

        repo = tmp_path / "repo"
        repo.mkdir()
        git_init(repo)
        with pytest.raises(subprocess.CalledProcessError):
            git(repo, "config", "--global", "--get", "user.name")


class TestSandboxStillProducesAUsableRepo:
    """Containment that broke the fixture would just get reverted, so prove it works."""

    def test_init_commit_and_identity_round_trip(self, tmp_path, monkeypatch):
        """Also pins the hook case: an inherited identity must not win.

        This test failed exactly once -- under this repo's own pre-commit
        `pytest` hook, where git had exported GIT_AUTHOR_* -- and authored the
        commit as the real user instead of the fixture. Setting them here
        makes that case run every time, not only inside a commit.
        """
        monkeypatch.setenv("GIT_AUTHOR_NAME", "Real Person")
        monkeypatch.setenv("GIT_AUTHOR_EMAIL", "real@example.org")
        monkeypatch.setenv("GIT_COMMITTER_NAME", "Real Person")
        monkeypatch.setenv("GIT_COMMITTER_EMAIL", "real@example.org")

        repo = tmp_path / "repo"
        repo.mkdir()
        git_init(repo)
        (repo / "file.txt").write_text("contents\n")
        git(repo, "add", "file.txt")
        git(repo, "commit", "-q", "-m", "test commit")

        author = git(repo, "log", "--format=%an <%ae>", "-1").stdout.strip()
        assert author == f"{TEST_NAME} <{TEST_EMAIL}>"

        staged = git(repo, "log", "--format=", "--name-only", "-1").stdout.split()
        assert staged == ["file.txt"]
