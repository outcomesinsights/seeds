"""`seeds doctor` reports the Claude Code plugin's state (bead seeds-p7ns).

A user who never ran the installer has no plugin, so no skills and no session
hooks; one who upgraded the CLI keeps a stale cached plugin. Doctor used to
check neither. These tests pin each state and its exact fix line.

Nothing here reaches the real `claude` or ~/.claude: the conftest stubs
`claude_path` to None for every test, and the tests that want `claude` present
stub it back together with `run_claude`, the only other way out.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from seeds import __version__, claude_plugin
from seeds.cli import main
from seeds.store import Store

PLUGIN = "seeds@seeds-marketplace"


def entry(scope="user", version=__version__, enabled=True, project_path=None):
    """One element of `claude plugin list --json`, as Claude Code 2.1 prints it."""
    record = {
        "id": PLUGIN,
        "version": version,
        "scope": scope,
        "enabled": enabled,
        "installPath": f"/cache/seeds-marketplace/seeds/{version}",
    }
    if project_path:
        record["projectPath"] = project_path
    return record


OTHER_PLUGIN = {"id": "beads@beads-marketplace", "version": "1", "scope": "user"}


@pytest.fixture
def fake_claude(monkeypatch):
    """Put a fake `claude` on PATH whose `plugin list --json` prints `listing`.

    Returns a setter; call it with the list (or a raw string, or a
    CompletedProcess) the fake should answer with.
    """
    state = {"reply": subprocess.CompletedProcess([], 0, stdout="[]", stderr="")}
    calls: list[tuple[str, ...]] = []

    def run_claude(*args):
        calls.append(args)
        assert args == ("plugin", "list", "--json"), args
        return state["reply"]

    monkeypatch.setattr(claude_plugin, "claude_path", lambda: "/usr/bin/claude")
    monkeypatch.setattr(claude_plugin, "run_claude", run_claude)

    def answer(listing):
        if isinstance(listing, subprocess.CompletedProcess):
            state["reply"] = listing
        else:
            text = listing if isinstance(listing, str) else json.dumps(listing)
            state["reply"] = subprocess.CompletedProcess([], 0, stdout=text, stderr="")

    answer.calls = calls
    return answer


@pytest.fixture
def project(tmp_path, monkeypatch):
    store = Store(tmp_path / ".seeds")
    store.files_dir.mkdir(parents=True)
    store.set_prefix("seeds")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def doctor():
    return CliRunner().invoke(main, ["doctor"])


class TestCheckPlugin:
    """The detector itself, one state at a time."""

    def test_claude_absent_checks_nothing(self):
        check = claude_plugin.check_plugin(__version__)

        assert not check.claude_found
        assert check.problems == ()

    def test_missing(self, fake_claude):
        fake_claude([OTHER_PLUGIN])

        check = claude_plugin.check_plugin(__version__)

        assert [(p.message, p.fix) for p in check.problems] == [
            ("not installed at user scope", "seeds setup claude")
        ]

    def test_a_project_scope_copy_does_not_count_as_installed(self, fake_claude):
        """The installer manages user scope; a copy another project installed
        does not load in this one."""
        fake_claude([entry(scope="project", project_path="/elsewhere")])

        check = claude_plugin.check_plugin(__version__)

        assert [p.fix for p in check.problems] == ["seeds setup claude"]

    def test_disabled(self, fake_claude):
        fake_claude([entry(enabled=False)])

        check = claude_plugin.check_plugin(__version__)

        assert [(p.message, p.fix) for p in check.problems] == [
            ("installed but disabled", "seeds setup claude")
        ]

    def test_stale(self, fake_claude):
        fake_claude([entry(version="0.5.0")])

        check = claude_plugin.check_plugin(__version__)

        assert [(p.message, p.fix) for p in check.problems] == [
            (
                f"stale: user scope has 0.5.0, this CLI is {__version__}",
                "seeds setup claude --reinstall",
            )
        ]

    def test_current_and_enabled_is_clean(self, fake_claude):
        fake_claude([OTHER_PLUGIN, entry()])

        check = claude_plugin.check_plugin(__version__)

        assert check.claude_found and check.error is None
        assert check.problems == ()

    def test_two_scopes_both_enabled_each_judged(self, fake_claude):
        """Titan, 2026-09-30: 0.5.0 at user scope AND 0.3.3 at project scope,
        both enabled. Each stale copy is its own finding with its own fix; the
        user-scope fix does not touch a project's copy."""
        fake_claude(
            [
                entry(
                    scope="project",
                    version="0.3.3",
                    project_path="/home/u/.config/home manager",
                ),
                entry(version="0.5.0"),
            ]
        )

        check = claude_plugin.check_plugin(__version__)

        assert [(p.message, p.fix) for p in check.problems] == [
            (
                "stale: project scope in /home/u/.config/home manager has 0.3.3, "
                f"this CLI is {__version__}",
                "cd '/home/u/.config/home manager' && "
                "claude plugin update seeds@seeds-marketplace --scope project",
            ),
            (
                f"stale: user scope has 0.5.0, this CLI is {__version__}",
                "seeds setup claude --reinstall",
            ),
        ]

    def test_a_project_that_disabled_seeds_is_left_alone(self, fake_claude):
        fake_claude([entry(), entry(scope="project", enabled=False, project_path="/p")])

        assert claude_plugin.check_plugin(__version__).problems == ()

    def test_listing_that_fails_is_an_error_not_a_verdict(self, fake_claude):
        fake_claude(subprocess.CompletedProcess([], 1, stdout="", stderr="boom"))

        check = claude_plugin.check_plugin(__version__)

        assert check.error and "boom" in check.error
        assert check.problems == ()

    def test_listing_that_is_not_json_is_an_error(self, fake_claude):
        fake_claude("seeds@seeds-marketplace\n")

        check = claude_plugin.check_plugin(__version__)

        assert check.error and "not JSON" in check.error


class TestDoctorReportsThePlugin:
    """What doctor prints for each state. All of it is warnings: exit 0."""

    def test_missing(self, project, fake_claude):
        fake_claude([])

        result = doctor()

        assert result.exit_code == 0, result.output
        assert "⚠ Claude Code plugin: not installed at user scope" in result.output
        assert "Fix: seeds setup claude\n" in result.output

    def test_disabled(self, project, fake_claude):
        fake_claude([entry(enabled=False)])

        result = doctor()

        assert result.exit_code == 0, result.output
        assert "⚠ Claude Code plugin: installed but disabled" in result.output
        assert "Fix: seeds setup claude\n" in result.output

    def test_stale(self, project, fake_claude):
        fake_claude([entry(version="0.5.0")])

        result = doctor()

        assert result.exit_code == 0, result.output
        assert "stale: user scope has 0.5.0" in result.output
        assert "Fix: seeds setup claude --reinstall" in result.output

    def test_current_is_one_ok_line(self, project, fake_claude):
        fake_claude([entry()])

        result = doctor()

        assert result.exit_code == 0, result.output
        assert f"✓ seeds plugin {__version__} installed and enabled" in result.output
        assert "Claude Code plugin:" not in result.output
        assert "Fix:" not in result.output

    def test_claude_absent_is_one_informational_line(self, project):
        result = doctor()

        assert result.exit_code == 0, result.output
        section = result.output.split("Claude Code:\n", 1)[1].split("\n\n", 1)[0]
        assert section.splitlines() == [
            "  → `claude` is not on PATH, so the Claude Code integration cannot "
            "be checked. seeds works without it."
        ]
        assert "Claude Code plugin" not in result.output

    def test_unreadable_listing_warns(self, project, fake_claude):
        fake_claude(subprocess.CompletedProcess([], 1, stdout="", stderr="boom"))

        result = doctor()

        assert result.exit_code == 0, result.output
        assert "⚠ Claude Code plugin: cannot be checked" in result.output


class TestInstallerSharesTheDetector:
    """`seeds skills install` decides install-vs-update from the same detector
    doctor reads, so the two cannot disagree about "installed"."""

    def test_a_project_scope_copy_alone_means_install_not_update(self):
        argvs: list[list[str]] = []
        listing = json.dumps([entry(scope="project", project_path="/elsewhere")])

        def run(argv, **_kwargs):
            argvs.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout=listing, stderr="")

        with (
            patch.object(claude_plugin, "claude_path", return_value="/usr/bin/claude"),
            patch.object(claude_plugin.subprocess, "run", side_effect=run),
            patch.object(
                claude_plugin,
                "plugin_installs",
                wraps=claude_plugin.plugin_installs,
            ) as detector,
        ):
            result = CliRunner().invoke(main, ["skills", "install"])

        assert result.exit_code == 0, result.output
        detector.assert_called_once()
        verbs = [a[2] for a in argvs if a[:2] == ["claude", "plugin"]]
        assert "install" in verbs and "update" not in verbs


def test_tests_never_see_the_real_claude():
    """The conftest guard is in force: `claude` looks absent unless stubbed."""
    assert claude_plugin.claude_path() is None
    assert Path.home()  # the guard does not need HOME redirected to hold
