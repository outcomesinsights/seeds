"""`seeds setup claude`, the installer's honest name (bead seeds-fuiz).

`seeds skills install` installs more than skills: the plugin also carries the
SessionStart and PreCompact hooks that run `seeds prime`. `seeds setup claude`
says so, and `seeds skills install` stays as an alias. One implementation
behind both, and `--check` reads the same detector `seeds doctor` does.

Nothing here reaches the real `claude`: the conftest stubs `claude_path` to
None, and the tests that want `claude` present stub `subprocess.run` too.
"""

import json
import subprocess
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from seeds import __version__, claude_plugin
from seeds.cli import main


def invoke(*args: str):
    return CliRunner().invoke(main, list(args))


class TestOneImplementation:
    @pytest.mark.parametrize(
        ("flags", "reinstall"),
        [((), False), (("--reinstall",), True), (("--upgrade",), True)],
    )
    def test_both_names_call_the_same_installer(self, flags, reinstall):
        with patch("seeds.cli.install_claude_integration") as installer:
            setup = invoke("setup", "claude", *flags)
            alias = invoke("skills", "install", *flags)

        assert setup.exit_code == 0, setup.output
        assert alias.exit_code == 0, alias.output
        assert installer.call_args_list == [((reinstall,),), ((reinstall,),)]

    @pytest.mark.parametrize("flags", [(), ("--reinstall",)])
    def test_both_names_run_the_same_claude_commands(self, flags):
        """End to end through a fake `claude`: identical argv, identical output."""
        listing = json.dumps(
            [{"id": claude_plugin.PLUGIN, "scope": "user", "version": "0"}]
        )

        def run(names):
            argvs: list[list[str]] = []

            def fake(argv, **_kwargs):
                argvs.append(argv)
                return subprocess.CompletedProcess(argv, 0, stdout=listing, stderr="")

            with (
                patch.object(claude_plugin, "claude_path", return_value="/bin/claude"),
                patch.object(claude_plugin.subprocess, "run", side_effect=fake),
            ):
                result = invoke(*names, *flags)
            assert result.exit_code == 0, result.output
            return argvs, result.output

        assert run(("setup", "claude")) == run(("skills", "install"))

    def test_setup_claude_aborts_without_claude(self):
        result = invoke("setup", "claude")

        assert result.exit_code != 0
        assert "`claude` CLI not found" in result.output


class TestFindable:
    def test_top_level_help_lists_setup(self):
        result = invoke("--help")

        assert result.exit_code == 0
        assert any(
            line.split()[:1] == ["setup"] for line in result.output.splitlines()
        ), result.output

    def test_help_says_it_installs_the_session_hooks(self):
        for args in (("setup", "claude", "--help"), ("skills", "install", "--help")):
            result = invoke(*args)
            assert "SessionStart" in result.output, args
            assert "PreCompact" in result.output, args
            assert "seeds prime" in result.output, args

    def test_alias_help_names_the_new_command(self):
        assert "seeds setup claude" in invoke("skills", "install", "--help").output


class TestCheck:
    """`--check` installs nothing and shares doctor's detector."""

    def test_check_reads_the_detector_doctor_reads(self):
        verdict = claude_plugin.PluginCheck(claude_found=True)
        with (
            patch.object(claude_plugin, "check_plugin", return_value=verdict) as check,
            patch("seeds.cli.install_claude_integration") as installer,
        ):
            result = invoke("setup", "claude", "--check")

        assert result.exit_code == 0, result.output
        check.assert_called_once_with(__version__)
        installer.assert_not_called()
        assert f"✓ seeds plugin {__version__} installed and enabled" in result.output

    def test_a_problem_exits_1_with_its_fix(self):
        verdict = claude_plugin.PluginCheck(
            claude_found=True,
            problems=(
                claude_plugin.PluginProblem(
                    "installed but disabled", claude_plugin.INSTALL_FIX
                ),
            ),
        )
        with patch.object(claude_plugin, "check_plugin", return_value=verdict):
            result = invoke("setup", "claude", "--check")

        assert result.exit_code == 1
        assert "⚠ Claude Code plugin: installed but disabled" in result.output
        assert "Fix: seeds setup claude\n" in result.output

    def test_no_claude_exits_1(self):
        result = invoke("setup", "claude", "--check")

        assert result.exit_code == 1
        assert "not on PATH" in result.output

    def test_check_refuses_reinstall(self):
        result = invoke("setup", "claude", "--check", "--reinstall")

        assert result.exit_code == 2
        assert "--check installs nothing" in result.output


def test_readme_install_step_leads_with_setup_claude():
    """The first command README's Claude Code install step shows is the new name."""
    from pathlib import Path

    readme = (Path(__file__).resolve().parent.parent / "README.md").read_text()
    step = readme.split("**2. Install the Claude Code integration**", 1)[1]
    first_block = step.split("```bash\n", 1)[1].split("```", 1)[0]

    assert first_block.strip() == "seeds setup claude"
