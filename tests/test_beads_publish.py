"""Tests for scripts/beads-publish, the pre-push hook that publishes beads (seeds-tkk).

The publish decision is made on bd's WORDS, not its exit code: bd 1.3.0 exits 0
on paths that published nothing. So a gate that trusted the exit code would pass
while the beads stayed on the host, which is the failure it exists to catch.
Every case here runs the real script against a fake ``bd`` whose output and exit
code are hand-set, in a throwaway repo under tmp_path, and asserts the
hand-computed outcome, including how many times bd was called.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from tests.githelpers import git_env, git_init

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "beads-publish"

PUBLISHED = "Pushing to origin...\nPush complete."
# bd 1.3.0 prints this and exits 0 -- the case that makes the exit code useless.
INACCESSIBLE = "Error: push to origin/main: remote could not be accessed"
TRANSIENT = "Error: dial tcp: i/o timed out"

FAKE_BD = """#!/bin/sh
dir="$(dirname "$0")"
n=$(($(cat "$dir/count") + 1))
echo "$n" > "$dir/count"
{
  echo "call $n: $*"
  echo "GIT_DIR=${GIT_DIR-unset} GIT_INDEX_FILE=${GIT_INDEX_FILE-unset}"
} >> "$dir/calls"
if [ -f "$dir/out$n" ]; then cat "$dir/out$n"; else cat "$dir/out"; fi
exit 0
"""


def _tool_dir(tmp_path: Path) -> Path:
    """A PATH directory holding only what the script needs besides bd.

    bd and git often share a directory (a nix profile), so the host PATH cannot
    express "git present, bd absent". This one can.
    """
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("sh", "git", "grep", "sed", "cat", "dirname"):
        found = shutil.which(name)
        assert found, name
        (tools / name).symlink_to(found)
    return tools


def _fake_bd(tmp_path: Path, *outputs: str) -> Path:
    """Install a fake bd that prints ``outputs[i]`` on call i+1 (the last repeats)."""
    fake = tmp_path / "fakebd"
    fake.mkdir()
    (fake / "count").write_text("0\n")
    (fake / "calls").write_text("")
    for i, text in enumerate(outputs, start=1):
        (fake / f"out{i}").write_text(text + "\n")
    (fake / "out").write_text(outputs[-1] + "\n")
    bd = fake / "bd"
    bd.write_text(FAKE_BD)
    bd.chmod(bd.stat().st_mode | stat.S_IXUSR)
    return fake


def _repo(tmp_path: Path, config: str | None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git_init(repo)
    if config is not None:
        (repo / ".beads").mkdir()
        (repo / ".beads" / "config.yaml").write_text(config)
    return repo


def _run(repo: Path, path_dirs: list[Path], **extra_env: str):
    env = git_env(repo)
    env["PATH"] = os.pathsep.join(str(d) for d in path_dirs)
    env.update(extra_env)
    # Through `sh`, not the shebang: the nix build sandbox has no /usr/bin/env,
    # so exec-by-shebang fails there with ENOENT. `sh` resolves via the PATH
    # above. test_script_is_executable covers what prek relies on instead.
    return subprocess.run(
        ["sh", str(SCRIPT)], cwd=repo, env=env, capture_output=True, text=True
    )


def test_script_is_executable():
    """prek runs the entry directly, so a lost exec bit would fail every push."""
    assert os.access(SCRIPT, os.X_OK)


def _calls(fake: Path) -> list[str]:
    return [
        line
        for line in (fake / "calls").read_text().splitlines()
        if line.startswith("call")
    ]


SYNCED = 'sync.remote: "git+https://example.invalid/r.git"\n'


class TestAllowsWhenThereIsNothingToPublish:
    def test_no_bd_on_path_allows_silently(self, tmp_path):
        repo = _repo(tmp_path, SYNCED)
        result = _run(repo, [_tool_dir(tmp_path)])
        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")

    def test_no_beads_dir_allows_without_calling_bd(self, tmp_path):
        fake = _fake_bd(tmp_path, PUBLISHED)
        repo = _repo(tmp_path, None)
        result = _run(repo, [fake, _tool_dir(tmp_path)])
        assert result.returncode == 0
        assert _calls(fake) == []

    @pytest.mark.parametrize(
        "config",
        ["export.auto: false\n", "sync.remote:\n", "sync.remote:   \n"],
        ids=["absent", "empty", "blank"],
    )
    def test_no_sync_remote_allows_without_calling_bd(self, tmp_path, config):
        fake = _fake_bd(tmp_path, PUBLISHED)
        repo = _repo(tmp_path, config)
        result = _run(repo, [fake, _tool_dir(tmp_path)])
        assert result.returncode == 0
        assert _calls(fake) == []


class TestDecidesOnBdsWordsNotItsExitCode:
    def test_push_complete_allows(self, tmp_path):
        fake = _fake_bd(tmp_path, PUBLISHED)
        repo = _repo(tmp_path, SYNCED)
        result = _run(repo, [fake, _tool_dir(tmp_path)])
        assert result.returncode == 0
        assert "beads: published" in result.stdout
        assert _calls(fake) == ["call 1: dolt push --no-adopt"]

    def test_error_with_exit_zero_refuses(self, tmp_path):
        """bd exits 0 here; only its words show nothing was published."""
        fake = _fake_bd(tmp_path, INACCESSIBLE)
        repo = _repo(tmp_path, SYNCED)
        result = _run(repo, [fake, _tool_dir(tmp_path)])
        assert result.returncode == 1
        assert "BEADS DID NOT PUBLISH" in result.stderr
        assert INACCESSIBLE in result.stderr
        assert "SKIP=beads-publish" in result.stderr
        assert len(_calls(fake)) == 1  # not transient: no retry

    def test_silence_refuses(self, tmp_path):
        """No remote configured on bd's side prints guidance, not 'Push complete.'."""
        fake = _fake_bd(tmp_path, "No remote configured. Run: bd dolt remote add ...")
        repo = _repo(tmp_path, SYNCED)
        assert _run(repo, [fake, _tool_dir(tmp_path)]).returncode == 1


class TestRetriesATransientFailureOnce:
    def test_transient_then_published_allows(self, tmp_path):
        fake = _fake_bd(tmp_path, TRANSIENT, PUBLISHED)
        repo = _repo(tmp_path, SYNCED)
        result = _run(repo, [fake, _tool_dir(tmp_path)])
        assert result.returncode == 0
        assert len(_calls(fake)) == 2

    def test_transient_twice_refuses_after_exactly_two_calls(self, tmp_path):
        fake = _fake_bd(tmp_path, TRANSIENT, TRANSIENT, PUBLISHED)
        repo = _repo(tmp_path, SYNCED)
        result = _run(repo, [fake, _tool_dir(tmp_path)])
        assert result.returncode == 1
        assert len(_calls(fake)) == 2


def test_hook_environment_is_unset_before_bd_runs(tmp_path):
    """Git exports GIT_DIR/GIT_INDEX_FILE to hooks; bd must see the real repo."""
    fake = _fake_bd(tmp_path, PUBLISHED)
    repo = _repo(tmp_path, SYNCED)
    result = _run(
        repo,
        [fake, _tool_dir(tmp_path)],
        GIT_DIR=str(repo / ".git"),
        GIT_INDEX_FILE=str(repo / ".git" / "index"),
    )
    assert result.returncode == 0
    assert "GIT_DIR=unset GIT_INDEX_FILE=unset" in (fake / "calls").read_text()
