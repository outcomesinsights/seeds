"""Tests for seeds.gitstage — the git-side half of the mixed-stage guard.

seeds-ww8: `seeds sync` must not fold pending, unflushed seed-database changes
into a commit that is really about something else. staged_paths_outside is
the read-only "what's staged outside .seeds/, if anything" primitive that
guard is built on. Everything here is best-effort — None means "no commit
context", not an error — so the three states that matter are: not a git repo
at all, a git repo with nothing (relevant) staged, and a git repo with
something staged outside seeds_dir. See test_cli.py::TestSyncGuardsMixedStage
for the guard wired into the actual `sync` command.

staged_paths_outside shells out to plain `git` against the process cwd (no
`-C`/cwd argument of its own), matching how the rest of seeds always assumes
cwd is the project root. So every test here uses monkeypatch.chdir into the
directory under test, same as test_beads.py.
"""

import subprocess
from unittest.mock import patch

from seeds.gitstage import _subprocess_env, staged_paths_outside


def _git(cwd, *args):
    """Run a git subcommand in `cwd`; raises on failure so setup errors are loud.

    Strips the same GIT_DIR/GIT_INDEX_FILE/etc as staged_paths_outside itself
    before shelling out, for the same reason: running this suite as this very
    repo's own pre-commit `pytest` hook leaks those variables in from the real
    commit in progress, and every one of these "throwaway repo in tmp_path"
    setup calls would otherwise silently redirect into the real repo's index
    instead.
    """
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        env=_subprocess_env(),
    )


def _git_init(cwd):
    """Initialize a throwaway git repo at `cwd` with a usable local identity."""
    _git(cwd, "init", "-q")
    _git(cwd, "config", "user.email", "test@example.com")
    _git(cwd, "config", "user.name", "Test")
    _git(cwd, "config", "commit.gpgsign", "false")


class TestNoCommitContext:
    """None means "nothing to guard", covering every way that can happen."""

    def test_plain_directory_returns_none(self, tmp_path, monkeypatch):
        """Not a git repository at all -- the common no-guard case."""
        monkeypatch.chdir(tmp_path)
        assert staged_paths_outside(".seeds") is None

    def test_git_not_installed_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch("subprocess.run", side_effect=OSError("git not found")):
            assert staged_paths_outside(".seeds") is None

    def test_rev_parse_failure_returns_none(self, tmp_path, monkeypatch):
        """A git call that runs but fails (e.g. a corrupt repo) also degrades."""
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        bad_result = subprocess.CompletedProcess(
            args=["git"], returncode=128, stdout="", stderr="fatal: whatever"
        )
        with patch("subprocess.run", return_value=bad_result):
            assert staged_paths_outside(".seeds") is None

    def test_diff_call_raising_returns_none(self, tmp_path, monkeypatch):
        """rev-parse succeeds but the second (diff) call itself errors out."""
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        real_run = subprocess.run

        def flaky(args, **kwargs):
            if args[:2] == ["git", "diff"]:
                raise OSError("boom")
            return real_run(args, **kwargs)

        with patch("subprocess.run", side_effect=flaky):
            assert staged_paths_outside(".seeds") is None

    def test_diff_call_failing_returns_none(self, tmp_path, monkeypatch):
        """rev-parse succeeds but the diff call exits non-zero."""
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        real_run = subprocess.run

        def half_broken(args, **kwargs):
            if args[:2] == ["git", "diff"]:
                return subprocess.CompletedProcess(
                    args=args, returncode=129, stdout="", stderr="usage error"
                )
            return real_run(args, **kwargs)

        with patch("subprocess.run", side_effect=half_broken):
            assert staged_paths_outside(".seeds") is None


class TestIgnoresInheritedGitEnv:
    """Regression: a hook-inherited GIT_DIR must not point this at another repo.

    git sets GIT_DIR (and friends) in the environment when it invokes a hook,
    so a hook script keeps operating on the right repo/index regardless of
    what directory it changes to -- and that leaks to every child process the
    hook spawns. Reproduced by this very project's own test suite: running as
    seeds' own pre-commit `pytest` hook, this check reported a plain tmp dir
    with no git repo of its own as part of the seeds worktree whose
    `git commit` had spawned it, because GIT_DIR was still set in pytest's
    environment. Confirmed independently with plain git: `GIT_DIR=<real
    repo>/.git git -C <unrelated dir> rev-parse --is-inside-work-tree` prints
    "true".
    """

    def _decoy_repo(self, tmp_path):
        """A real repo with real staged work, standing in for the hook's repo.

        Deliberately built here rather than reusing seeds' own checkout. An
        earlier version pointed GIT_DIR at `Path(__file__).parent.parent/.git`,
        which works from a git clone and fails wherever the suite runs from an
        unpacked source tree with no `.git` -- caught by `nix flake check`,
        whose sandbox is exactly that (seeds-ww8, 2026-08-26). A test about
        environment leakage has no business depending on how its own source
        was obtained.

        It stages a file OUTSIDE .seeds/ on purpose: if the leak being guarded
        against were still present, staged_paths_outside would find that file
        and return a non-empty list, so the assertion below distinguishes
        "correctly ignored the inherited env" from "found nothing anywhere".
        """
        decoy = tmp_path / "decoy-repo"
        decoy.mkdir()
        _git_init(decoy)
        (decoy / "staged-elsewhere.txt").write_text("work in the other repo\n")
        _git(decoy, "add", "staged-elsewhere.txt")
        return decoy / ".git"

    def test_inherited_git_dir_does_not_leak_into_an_unrelated_directory(
        self, tmp_path, monkeypatch
    ):
        git_dir = self._decoy_repo(tmp_path)
        unrelated = tmp_path / "unrelated"
        unrelated.mkdir()

        monkeypatch.setenv("GIT_DIR", str(git_dir))
        monkeypatch.chdir(unrelated)

        assert staged_paths_outside(".seeds") is None

    def test_inherited_git_index_file_does_not_leak_either(self, tmp_path, monkeypatch):
        """Same leak, via the sibling variable that names the staged index."""
        git_dir = self._decoy_repo(tmp_path)
        unrelated = tmp_path / "unrelated"
        unrelated.mkdir()

        monkeypatch.setenv("GIT_DIR", str(git_dir))
        monkeypatch.setenv("GIT_INDEX_FILE", str(git_dir / "index"))
        monkeypatch.chdir(unrelated)

        assert staged_paths_outside(".seeds") is None


class TestCommitContextNoHead:
    """An unborn branch (no commits yet) is a normal, fully-supported case."""

    def test_nothing_staged_is_an_empty_list_not_none(self, tmp_path, monkeypatch):
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        assert staged_paths_outside(".seeds") == []

    def test_staged_file_outside_seeds_dir_is_reported(self, tmp_path, monkeypatch):
        _git_init(tmp_path)
        (tmp_path / "feature.txt").write_text("unrelated feature work\n")
        _git(tmp_path, "add", "feature.txt")
        monkeypatch.chdir(tmp_path)

        assert staged_paths_outside(".seeds") == ["feature.txt"]

    def test_staged_file_inside_seeds_dir_is_excluded(self, tmp_path, monkeypatch):
        _git_init(tmp_path)
        (tmp_path / ".seeds").mkdir()
        (tmp_path / ".seeds" / "seeds.jsonl").write_text('{"id": "seed-1"}\n')
        _git(tmp_path, "add", ".seeds/seeds.jsonl")
        monkeypatch.chdir(tmp_path)

        assert staged_paths_outside(".seeds") == []

    def test_mixed_stage_reports_only_the_outside_paths(self, tmp_path, monkeypatch):
        _git_init(tmp_path)
        (tmp_path / ".seeds").mkdir()
        (tmp_path / ".seeds" / "seeds.jsonl").write_text('{"id": "seed-1"}\n')
        (tmp_path / "feature.txt").write_text("unrelated feature work\n")
        _git(tmp_path, "add", ".seeds/seeds.jsonl", "feature.txt")
        monkeypatch.chdir(tmp_path)

        assert staged_paths_outside(".seeds") == ["feature.txt"]


class TestCommitContextWithHead:
    """The steady-state case: at least one commit already exists."""

    def test_nothing_staged_after_a_commit_is_empty(self, tmp_path, monkeypatch):
        _git_init(tmp_path)
        (tmp_path / "README.md").write_text("hello\n")
        _git(tmp_path, "add", "README.md")
        _git(tmp_path, "commit", "-q", "-m", "initial")
        monkeypatch.chdir(tmp_path)

        assert staged_paths_outside(".seeds") == []

    def test_newly_staged_file_outside_seeds_dir_is_reported(
        self, tmp_path, monkeypatch
    ):
        _git_init(tmp_path)
        (tmp_path / "README.md").write_text("hello\n")
        _git(tmp_path, "add", "README.md")
        _git(tmp_path, "commit", "-q", "-m", "initial")

        (tmp_path / "feature.txt").write_text("unrelated feature work\n")
        _git(tmp_path, "add", "feature.txt")
        monkeypatch.chdir(tmp_path)

        assert staged_paths_outside(".seeds") == ["feature.txt"]

    def test_custom_seeds_dir_name_is_respected(self, tmp_path, monkeypatch):
        """seeds_dir is a parameter, not hardcoded '.seeds' -- SEEDS_DIR can differ."""
        _git_init(tmp_path)
        (tmp_path / "custom-seeds").mkdir()
        (tmp_path / "custom-seeds" / "seeds.jsonl").write_text("{}\n")
        (tmp_path / "feature.txt").write_text("unrelated feature work\n")
        _git(tmp_path, "add", "custom-seeds/seeds.jsonl", "feature.txt")
        monkeypatch.chdir(tmp_path)

        assert staged_paths_outside("custom-seeds") == ["feature.txt"]
