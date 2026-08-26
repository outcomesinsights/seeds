"""Tests for scripts/check_git_config_sanity.py (bead seeds-p0x).

The detector is itself code that can be silently wrong, and a detector that
returns 0 on a poisoned config is worse than no detector -- it reads as
"checked and clean". So every case here is a hand-built config file with a
hand-computed expected exit status, and the poisoned fixtures are written into
tmp_path, never against this repository.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent / "scripts" / "check_git_config_sanity.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("check_git_config_sanity", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load()


def _write(tmp_path: Path, body: str) -> Path:
    config = tmp_path / "config"
    config.write_text(body)
    return config


CLEAN = """\
[core]
\trepositoryformatversion = 0
\tfilemode = true
\tbare = false
"""


class TestAcceptsHealthyConfigs:
    def test_ordinary_checkout_passes(self, tmp_path):
        assert checker.main([str(_write(tmp_path, CLEAN))]) == 0

    def test_real_identity_passes(self, tmp_path):
        body = CLEAN + "[user]\n\temail = someone@example.org\n\tname = Someone Real\n"
        assert checker.main([str(_write(tmp_path, body))]) == 0

    def test_missing_file_is_not_a_failure(self, tmp_path):
        """No config to check is not the same as a poisoned one."""
        assert checker.main([str(tmp_path / "does-not-exist")]) == 0


class TestCatchesEachPoisonedValue:
    """One test per value that actually appeared on 2026-08-26."""

    def test_core_bare_true_is_caught(self, tmp_path):
        body = "[core]\n\trepositoryformatversion = 0\n\tbare = true\n"
        assert checker.main([str(_write(tmp_path, body))]) == 1

    def test_fixture_email_is_caught(self, tmp_path):
        body = CLEAN + f"[user]\n\temail = {checker.TEST_EMAIL}\n"
        assert checker.main([str(_write(tmp_path, body))]) == 1

    def test_fixture_name_is_caught(self, tmp_path):
        body = CLEAN + f"[user]\n\tname = {checker.TEST_NAME}\n"
        assert checker.main([str(_write(tmp_path, body))]) == 1

    def test_the_exact_2026_08_26_config_is_caught(self, tmp_path):
        """The real thing, reproduced verbatim from the incident."""
        body = (
            "[core]\n"
            "\trepositoryformatversion = 0\n"
            "\tfilemode = true\n"
            "\tbare = true\n"
            "\tlogallrefupdates = true\n"
            "[user]\n"
            f"\temail = {checker.TEST_EMAIL}\n"
            f"\tname = {checker.TEST_NAME}\n"
            "[commit]\n"
            "\tgpgsign = false\n"
        )
        assert checker.main([str(_write(tmp_path, body))]) == 1

    def test_failure_names_every_problem_and_prints_the_repair(self, tmp_path, capsys):
        """A detector that fails without saying how to fix it wastes the catch."""
        body = (
            "[core]\n\tbare = true\n"
            f"[user]\n\temail = {checker.TEST_EMAIL}\n\tname = {checker.TEST_NAME}\n"
        )
        assert checker.main([str(_write(tmp_path, body))]) == 1
        err = capsys.readouterr().err
        assert "core.bare=true" in err
        assert checker.TEST_EMAIL in err
        assert "git config --local core.bare false" in err
        assert "seeds-p0x" in err


class TestBareIsMatchedCaseInsensitively:
    """git accepts these spellings for true; so must the check."""

    @pytest.mark.parametrize("value", ["true", "True", "TRUE"])
    def test_true_spellings_are_caught(self, tmp_path, value):
        body = f"[core]\n\tbare = {value}\n"
        assert checker.main([str(_write(tmp_path, body))]) == 1


class TestFindsTheSharedConfig:
    """Resolution has to work from the main repo AND from a linked worktree."""

    def test_main_repo_finds_its_own_config(self, tmp_path):
        repo = tmp_path / "main"
        (repo / ".git").mkdir(parents=True)
        (repo / ".git" / "config").write_text(CLEAN)
        (repo / "scripts").mkdir()

        found = checker.shared_config(repo / "scripts" / "check.py")
        assert found == repo / ".git" / "config"

    def test_worktree_resolves_to_the_shared_main_config(self, tmp_path):
        """The case that matters: a worktree must NOT report its own gitdir."""
        main_git = tmp_path / "main" / ".git"
        gitdir = main_git / "worktrees" / "agent-x"
        gitdir.mkdir(parents=True)
        (main_git / "config").write_text(CLEAN)

        worktree = tmp_path / "wt"
        (worktree / "scripts").mkdir(parents=True)
        (worktree / ".git").write_text(f"gitdir: {gitdir}\n")

        found = checker.shared_config(worktree / "scripts" / "check.py")
        assert found == main_git / "config"
        assert found != gitdir / "config"

    def test_no_repo_anywhere_returns_none(self, tmp_path):
        """nix flake check unpacks a source tree with no .git at all."""
        plain = tmp_path / "unpacked" / "scripts"
        plain.mkdir(parents=True)
        assert checker.shared_config(plain / "check.py") is None

    def test_a_poisoned_worktree_config_is_caught_end_to_end(self, tmp_path):
        """Resolution plus detection together, which is how the hook runs."""
        main_git = tmp_path / "main" / ".git"
        gitdir = main_git / "worktrees" / "agent-x"
        gitdir.mkdir(parents=True)
        (main_git / "config").write_text("[core]\n\tbare = true\n")

        worktree = tmp_path / "wt"
        (worktree / "scripts").mkdir(parents=True)
        (worktree / ".git").write_text(f"gitdir: {gitdir}\n")

        found = checker.shared_config(worktree / "scripts" / "check.py")
        assert checker.main([str(found)]) == 1


class TestTheTwoResolversAgree:
    """conftest and the script each walk up to the shared config, separately.

    The duplication is deliberate -- the script runs as a git hook, outside
    this project's virtualenv, so it cannot import from the test package. But
    two copies of the same walk is exactly the drift that put ``_git_init`` in
    two files and let one of them poison a real repo. These pin them together.
    """

    def _trees(self, tmp_path):
        """A main-repo layout and a worktree layout, both hand-built."""
        main_git = tmp_path / "main" / ".git"
        gitdir = main_git / "worktrees" / "agent-x"
        gitdir.mkdir(parents=True)
        (main_git / "config").write_text(CLEAN)
        (tmp_path / "main" / "tests").mkdir()

        worktree = tmp_path / "wt"
        (worktree / "tests").mkdir(parents=True)
        (worktree / ".git").write_text(f"gitdir: {gitdir}\n")
        return main_git / "config", worktree / "tests" / "conftest.py"

    def test_worktree_resolution_matches(self, tmp_path):
        from tests.conftest import _ambient_shared_git_config

        expected, start = self._trees(tmp_path)
        assert checker.shared_config(start) == expected
        assert _ambient_shared_git_config(start) == expected

    def test_main_repo_resolution_matches(self, tmp_path):
        from tests.conftest import _ambient_shared_git_config

        expected, _ = self._trees(tmp_path)
        start = tmp_path / "main" / "tests" / "conftest.py"
        assert checker.shared_config(start) == expected
        assert _ambient_shared_git_config(start) == expected

    def test_no_repo_resolution_matches(self, tmp_path):
        from tests.conftest import _ambient_shared_git_config

        start = tmp_path / "unpacked" / "tests"
        start.mkdir(parents=True)
        assert checker.shared_config(start / "conftest.py") is None
        assert _ambient_shared_git_config(start / "conftest.py") is None


class TestTheSessionGuardActuallyFires:
    """Drive conftest's session fixture by hand, both directions.

    An alarm nobody has ever seen go off is indistinguishable from no alarm,
    and this one is the primary defence: it catches the write at the moment it
    happens, on a repo git may already have stopped being able to open.
    """

    def _drive(self, monkeypatch, config):
        import tests.conftest as conftest_module

        monkeypatch.setattr(
            conftest_module,
            "_ambient_shared_git_config",
            lambda start=None: config,
        )
        return conftest_module._guard_ambient_git_config.__wrapped__()

    def test_unchanged_config_passes_silently(self, tmp_path, monkeypatch):
        config = _write(tmp_path, CLEAN)
        generator = self._drive(monkeypatch, config)
        next(generator)
        with pytest.raises(StopIteration):
            next(generator)

    def test_a_poisoned_config_fails_the_session(self, tmp_path, monkeypatch):
        """The 2026-08-26 write, replayed against the guard."""
        config = _write(tmp_path, CLEAN)
        generator = self._drive(monkeypatch, config)
        next(generator)

        config.write_text(
            "[core]\n\tbare = true\n"
            f"[user]\n\temail = {checker.TEST_EMAIL}\n\tname = {checker.TEST_NAME}\n"
        )

        with pytest.raises(AssertionError) as caught:
            next(generator)
        message = str(caught.value)
        assert "modified" in message
        assert "githelpers" in message
        assert "git config --local core.bare false" in message

    def test_a_deleted_config_also_fails(self, tmp_path, monkeypatch):
        config = _write(tmp_path, CLEAN)
        generator = self._drive(monkeypatch, config)
        next(generator)
        config.unlink()
        with pytest.raises(AssertionError):
            next(generator)

    def test_absent_config_is_not_guarded(self, tmp_path, monkeypatch):
        """No repo (the nix sandbox) must not turn into a false alarm."""
        generator = self._drive(monkeypatch, None)
        next(generator)
        with pytest.raises(StopIteration):
            next(generator)
