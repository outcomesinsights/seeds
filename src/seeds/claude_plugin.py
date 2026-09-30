"""The seeds Claude Code plugin, as seen through Claude Code's own CLI.

One detector, shared: the installer asks it whether the plugin is already
there, and ``seeds doctor`` and ``seeds setup claude --check`` ask it whether
the plugin is missing, disabled or stale (beads seeds-p7ns, seeds-fuiz). A
second copy of the parsing would be free to disagree
with the first about what "installed" means, which is the drift this module
exists to prevent.

Everything goes through ``claude plugin list --json`` -- never by reading
``~/.claude`` directly -- so the answer is Claude Code's own, and
``CLAUDE_CONFIG_DIR`` redirects it along with every other ``claude`` call.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from dataclasses import dataclass

PLUGIN = "seeds@seeds-marketplace"
MARKETPLACE = "seeds-marketplace"

# The commands a finding tells the user to run. `install` always ends by
# enabling, so it is the fix for both "missing" and "disabled"; `--reinstall`
# replaces a cached copy whose version no longer matches the CLI.
INSTALL_FIX = "seeds setup claude"
REINSTALL_FIX = "seeds setup claude --reinstall"


class ClaudeListError(Exception):
    """`claude plugin list --json` failed or printed something unparseable."""


def claude_path() -> str | None:
    """Where `claude` is on PATH, or None. The one seam tests stub."""
    return shutil.which("claude")


def run_claude(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a `claude` subcommand and return it, whatever its exit status."""
    return subprocess.run(
        ["claude", *args],
        capture_output=True,
        text=True,
        check=False,
    )


@dataclass(frozen=True)
class PluginInstall:
    """One install of the seeds plugin. Claude Code keeps one per scope."""

    scope: str
    version: str
    enabled: bool
    project_path: str | None = None

    def where(self) -> str:
        if self.project_path:
            return f"{self.scope} scope in {self.project_path}"
        return f"{self.scope} scope"


def plugin_installs() -> list[PluginInstall]:
    """Every install of the seeds plugin that Claude Code knows about.

    Raises ClaudeListError when the listing cannot be had or read.
    """
    proc = run_claude("plugin", "list", "--json")
    if proc.returncode != 0:
        raise ClaudeListError(
            f"`claude plugin list --json` failed: {proc.stderr.strip()}"
        )
    try:
        entries = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ClaudeListError(
            f"`claude plugin list --json` printed something that is not JSON: {exc}"
        ) from exc
    if not isinstance(entries, list):
        raise ClaudeListError("`claude plugin list --json` did not print a list")
    return [
        PluginInstall(
            scope=str(entry.get("scope", "")),
            version=str(entry.get("version", "")),
            enabled=bool(entry.get("enabled", False)),
            project_path=entry.get("projectPath"),
        )
        for entry in entries
        if isinstance(entry, dict) and entry.get("id") == PLUGIN
    ]


def user_install(installs: list[PluginInstall]) -> PluginInstall | None:
    """The user-scope install -- the one `seeds setup claude` manages."""
    return next((i for i in installs if i.scope == "user"), None)


@dataclass(frozen=True)
class PluginProblem:
    message: str
    fix: str


@dataclass(frozen=True)
class PluginCheck:
    """What the detector found.

    ``claude_found`` False: `claude` is not on PATH, nothing was checked.
    ``error`` set: `claude` is there but its listing could not be read.
    Otherwise ``problems`` is the whole verdict, and empty means healthy.
    """

    claude_found: bool
    installs: tuple[PluginInstall, ...] = ()
    problems: tuple[PluginProblem, ...] = ()
    error: str | None = None


def check_plugin(expected_version: str) -> PluginCheck:
    """Is the seeds plugin installed, enabled and current for this CLI?

    The user-scope install is the one the installer manages, so it alone can
    be missing or disabled. Any install, at any scope, can be stale: a project
    pinned to an old copy is drift. A project that DISABLED seeds is not
    reported -- that is a choice the project made, not something to undo.
    """
    if claude_path() is None:
        return PluginCheck(claude_found=False)
    try:
        installs = plugin_installs()
    except ClaudeListError as exc:
        return PluginCheck(claude_found=True, error=str(exc))

    problems: list[PluginProblem] = []
    user = user_install(installs)
    if user is None:
        problems.append(PluginProblem("not installed at user scope", INSTALL_FIX))
    elif not user.enabled:
        problems.append(PluginProblem("installed but disabled", INSTALL_FIX))

    for install in installs:
        if install.version == expected_version:
            continue
        message = (
            f"stale: {install.where()} has {install.version}, "
            f"this CLI is {expected_version}"
        )
        if install.scope == "user":
            fix = REINSTALL_FIX
        else:
            # `seeds setup claude` touches user scope only. Updating in place
            # is the least that fixes this copy: it leaves the project's own
            # settings, and its choice to install seeds there, alone.
            fix = f"claude plugin update {PLUGIN} --scope {install.scope}"
            if install.project_path:
                fix = f"cd {shlex.quote(install.project_path)} && {fix}"
        problems.append(PluginProblem(message, fix))

    return PluginCheck(
        claude_found=True, installs=tuple(installs), problems=tuple(problems)
    )
