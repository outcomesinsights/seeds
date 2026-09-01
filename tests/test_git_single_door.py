"""tests/githelpers.py must be the only place the suite invokes real git.

Bead seeds-3xs, following the 2026-08-26 incident in seed seeds-ngez. That
incident happened because ``_git``/``_git_init`` had been written twice, in
test_gitstage.py and test_cli.py, and only one copy was ever hardened. Two
different agents each wrote their own copy independently, so "we deduplicated
it" is not a durable state -- nothing stops a third appearing in the next
bead. This turns the convention into a checked invariant.

The check has to distinguish INVOKING git from MENTIONING it: a test may
legitimately build ``subprocess.CompletedProcess(args=["git"], ...)`` or
compare ``args[:2] == ["git", "diff"]`` inside a patched ``subprocess.run``,
and neither runs anything. So this walks the AST for real call nodes rather
than grepping for the string, and the detector is itself exercised against
hand-built samples below -- a detector that never fires is indistinguishable
from no detector.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
ALLOWED = {"githelpers.py"}

# The subprocess entry points that actually start a process.
_SUBPROCESS_CALLS = {"run", "Popen", "call", "check_call", "check_output"}


def _is_subprocess_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in _SUBPROCESS_CALLS:
        return isinstance(func.value, ast.Name) and func.value.id == "subprocess"
    return isinstance(func, ast.Name) and func.id in _SUBPROCESS_CALLS


def _looks_like_git_argv(node: ast.expr) -> bool:
    """True if this argument is a command that runs git."""
    if isinstance(node, (ast.List, ast.Tuple)):
        if not node.elts:
            return False
        first = node.elts[0]
        return (
            isinstance(first, ast.Constant)
            and isinstance(first.value, str)
            and (first.value == "git" or first.value.endswith("/git"))
        )
    # shell=True form: subprocess.run("git status", shell=True)
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and (node.value == "git" or node.value.startswith("git "))
    )


def git_invocations(source: str) -> list[int]:
    """Line numbers in ``source`` that invoke real git through subprocess."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and _is_subprocess_call(node)
            and node.args
            and _looks_like_git_argv(node.args[0])
        ):
            found.append(node.lineno)
    return sorted(found)


class TestTheDetectorItself:
    """Hand-built samples with hand-computed answers, both directions."""

    def test_flags_a_direct_subprocess_run(self):
        source = 'import subprocess\nsubprocess.run(["git", "init"])\n'
        assert git_invocations(source) == [2]

    def test_flags_every_process_starting_entry_point(self):
        source = (
            "import subprocess\n"
            'subprocess.Popen(["git", "log"])\n'
            'subprocess.check_output(["git", "status"])\n'
            'subprocess.check_call(["git", "add", "."])\n'
            'subprocess.call(["git", "diff"])\n'
        )
        assert git_invocations(source) == [2, 3, 4, 5]

    def test_flags_the_shell_string_form(self):
        source = 'import subprocess\nsubprocess.run("git status", shell=True)\n'
        assert git_invocations(source) == [2]

    def test_flags_an_absolute_git_path(self):
        source = 'import subprocess\nsubprocess.run(["/usr/bin/git", "init"])\n'
        assert git_invocations(source) == [2]

    def test_flags_the_splat_form_the_old_helpers_used(self):
        """The exact shape of the duplicated helper that caused the incident."""
        source = (
            "import subprocess\n"
            "def _git(cwd, *args):\n"
            '    return subprocess.run(["git", *args], cwd=cwd)\n'
        )
        assert git_invocations(source) == [3]

    def test_ignores_a_completed_process_literal(self):
        """A test may build one of these; it starts nothing."""
        source = (
            "import subprocess\n"
            'subprocess.CompletedProcess(args=["git"], returncode=128)\n'
        )
        assert git_invocations(source) == []

    def test_ignores_comparing_an_argv(self):
        """The fake inside a patched subprocess.run inspects args this way."""
        source = (
            'def fake(args, **kw):\n    if args[:2] == ["git", "diff"]:\n        pass\n'
        )
        assert git_invocations(source) == []

    def test_ignores_patching_subprocess(self):
        source = (
            "from unittest.mock import patch\n"
            'patch("subprocess.run", side_effect=OSError("git not found"))\n'
        )
        assert git_invocations(source) == []

    def test_ignores_running_something_that_is_not_git(self):
        source = 'import subprocess\nsubprocess.run(["uv", "run", "seeds"])\n'
        assert git_invocations(source) == []


class TestTheSuiteHasOneDoor:
    """The invariant itself, over the real test sources."""

    @pytest.mark.parametrize(
        "path",
        sorted(p for p in TESTS_DIR.glob("*.py") if p.name not in ALLOWED),
        ids=lambda p: p.name,
    )
    def test_no_test_file_invokes_git_directly(self, path):
        lines = git_invocations(path.read_text())
        assert not lines, (
            f"{path.name} invokes real git at line(s) {lines}. Every git call "
            f"must go through tests/githelpers.py, which sandboxes the "
            f"environment so a test cannot reach the real repository. "
            f"A second copy of that helper is what bricked this repo on "
            f"2026-08-26 (bead seeds-p0x)."
        )

    def test_githelpers_is_where_git_actually_runs(self):
        """Guards the allowlist: if the door moves, this fails loudly."""
        helper = TESTS_DIR / "githelpers.py"
        assert git_invocations(helper.read_text()), (
            "tests/githelpers.py no longer invokes git -- either the sandbox "
            "moved, in which case update ALLOWED, or it was gutted."
        )
