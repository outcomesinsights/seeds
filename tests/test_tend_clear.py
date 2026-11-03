"""The tend helper that clears a session through herdr (bead seeds-z03u).

Rulings are in seed seeds-x6m0 (2026-11-03). The helper waits for idle, sends
/clear, confirms the /clear through the SessionStart hook's marker, waits for
idle again, and then sends /seeds:tend next.

SAFETY. The developer who runs this suite is often inside a real herdr pane,
with HERDR_PANE_ID set and the real herdr on PATH. A test that inherited either
one would type /clear into that live session. So every test builds its
environment from scratch: no HERDR_* variable is inherited, PATH holds a stub
herdr and system directories only, and the ``env`` fixture asserts that
``herdr`` on that PATH resolves to the stub before any test runs the helper.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEND_DIR = REPO_ROOT / "src/seeds/plugin/claude-plugin/skills/tend"
HELPER = TEND_DIR / "tend_clear.py"
PLUGIN_JSON = REPO_ROOT / "src/seeds/plugin/claude-plugin/.claude-plugin/plugin.json"

FAKE_PANE = "wtest:pfake"

WAIT = [
    "agent",
    "wait",
    FAKE_PANE,
    "--until",
    "idle",
    "--until",
    "done",
    "--timeout",
    "5000",
]
CLEAR = ["agent", "prompt", FAKE_PANE, "/clear"]
NEXT = ["agent", "prompt", FAKE_PANE, "/seeds:tend next"]

# The stub records each call as one JSON line. It blocks `agent wait` until a
# gate file exists, when STUB_HERDR_GATE names one. It fails `agent wait` when
# STUB_HERDR_WAIT_FAIL is set. When STUB_HERDR_CLEARS is set, a `/clear` prompt
# runs the plugin's real SessionStart hook command, as Claude Code would.
STUB_HERDR = textwrap.dedent(
    """\
    #!{python}
    import json, os, subprocess, sys, time
    args = sys.argv[1:]
    with open(os.environ["STUB_HERDR_CALLS"], "a") as f:
        f.write(json.dumps(args) + "\\n")
    if args[:2] == ["agent", "wait"]:
        if os.environ.get("STUB_HERDR_WAIT_FAIL"):
            sys.stderr.write('{{"error": "timeout"}}\\n')
            sys.exit(1)
        gate = os.environ.get("STUB_HERDR_GATE")
        deadline = time.monotonic() + 30
        while gate and not os.path.exists(gate) and time.monotonic() < deadline:
            time.sleep(0.05)
    if args[:2] == ["agent", "prompt"] and args[3] == "/clear":
        if os.environ.get("STUB_HERDR_CLEARS"):
            subprocess.run(["sh", "-c", os.environ["STUB_CLEAR_HOOK"]], check=True)
    """
)


def clear_hook_command() -> str:
    """The command the plugin's SessionStart `clear` hook runs."""
    entries = json.loads(PLUGIN_JSON.read_text())["hooks"]["SessionStart"]
    [entry] = [e for e in entries if e["matcher"] == "clear"]
    [hook] = entry["hooks"]
    return str(hook["command"])


@pytest.fixture
def env(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "herdr"
    stub.write_text(STUB_HERDR.format(python=sys.executable))
    stub.chmod(0o755)
    # python3 must be on PATH for the hook command, and the real herdr must not.
    py_dir = tmp_path / "py"
    py_dir.mkdir()
    (py_dir / "python3").symlink_to(sys.executable)

    built = {k: v for k, v in os.environ.items() if not k.startswith("HERDR_")}
    built.update(
        PATH=f"{bin_dir}:{py_dir}:/usr/bin:/bin",
        HERDR_PANE_ID=FAKE_PANE,
        XDG_STATE_HOME=str(tmp_path / "state"),
        STUB_HERDR_CALLS=str(tmp_path / "calls.jsonl"),
        CLAUDE_PLUGIN_ROOT=str(REPO_ROOT / "src/seeds/plugin/claude-plugin"),
        STUB_CLEAR_HOOK=clear_hook_command(),
    )
    assert shutil.which("herdr", path=built["PATH"]) == str(stub), (
        "the test PATH must resolve herdr to the stub, never the real herdr"
    )
    return built


def calls(env) -> list[list[str]]:
    path = Path(env["STUB_HERDR_CALLS"])
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def start(env, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(HELPER),
            "--wait-timeout",
            "5",
            "--confirm-timeout",
            "1",
            *extra,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def log_path(proc: subprocess.CompletedProcess[str]) -> Path:
    assert proc.returncode == 0, proc.stderr
    return Path(proc.stdout.split("Log: ", 1)[1].strip())


def wait_for_result(log: Path, timeout: float = 20) -> str:
    """The detached child's log, once it has written its result line."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if log.exists() and "result:" in log.read_text():
            return log.read_text()
        time.sleep(0.05)
    raise AssertionError(f"the helper wrote no result within {timeout}s: {log}")


def pending_files(env) -> list[Path]:
    state = Path(env["XDG_STATE_HOME"]) / "seeds" / "tend"
    return sorted(state.glob("pending-*")) + sorted(state.glob("cleared-*"))


def test_order_is_wait_clear_confirm_wait_next(env):
    env["STUB_HERDR_CLEARS"] = "1"

    text = wait_for_result(log_path(start(env)))

    assert "result: ok" in text
    assert "confirmed: /clear took effect" in text
    assert calls(env) == [WAIT, CLEAR, WAIT, NEXT]
    assert pending_files(env) == []


def test_nothing_more_is_sent_when_the_clear_is_not_confirmed(env):
    # No STUB_HERDR_CLEARS: the /clear "was lost", so no hook wrote the marker.
    text = wait_for_result(log_path(start(env)))

    assert "result: FAILED" in text
    assert "/seeds:tend next was NOT sent" in text
    assert calls(env) == [WAIT, CLEAR]
    assert pending_files(env) == []


def test_nothing_is_sent_when_the_pane_never_becomes_idle(env):
    env["STUB_HERDR_WAIT_FAIL"] = "1"

    text = wait_for_result(log_path(start(env)))

    assert "result: FAILED" in text
    assert calls(env) == [WAIT]


def test_the_helper_survives_the_exit_of_the_process_that_started_it(env, tmp_path):
    """Claude Code can end the tool's whole process group, or the session.

    The parent runs in its own process group here. The test lets it exit, kills
    that group, and then proves that the helper still runs and finishes.
    """
    gate = tmp_path / "gate"
    env["STUB_HERDR_GATE"] = str(gate)
    env["STUB_HERDR_CLEARS"] = "1"
    parent = subprocess.Popen(
        [sys.executable, str(HELPER), "--wait-timeout", "30"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    out, err = parent.communicate(timeout=20)
    assert parent.returncode == 0, err
    log = Path(out.split("Log: ", 1)[1].strip())

    # The helper is blocked in its first `herdr agent wait`.
    deadline = time.monotonic() + 20
    while not (log.exists() and "helper pid" in log.read_text()):
        assert time.monotonic() < deadline, "the helper never started"
        time.sleep(0.05)
    helper_pid = int(log.read_text().split("helper pid ", 1)[1].split(",")[0])
    assert helper_pid != parent.pid
    assert os.getsid(helper_pid) != parent.pid, "the helper kept the parent session"

    with contextlib.suppress(ProcessLookupError):
        os.killpg(parent.pid, signal.SIGKILL)
    os.kill(helper_pid, 0)  # raises if the helper died with the parent

    gate.touch()
    text = wait_for_result(log)
    assert "result: ok" in text
    assert calls(env) == [
        [*WAIT[:-1], "30000"],
        CLEAR,
        [*WAIT[:-1], "30000"],
        NEXT,
    ]


def test_without_herdr_pane_id_nothing_is_sent(env):
    del env["HERDR_PANE_ID"]

    proc = start(env)

    assert proc.returncode == 2
    assert "HERDR_PANE_ID is not set" in proc.stderr
    assert "/clear, and then /seeds:tend next" in proc.stderr
    assert calls(env) == []


def test_without_herdr_on_path_nothing_is_sent(env, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    env["PATH"] = str(empty)
    assert shutil.which("herdr", path=env["PATH"]) is None

    proc = start(env)

    assert proc.returncode == 2
    assert "herdr is not on PATH" in proc.stderr
    assert calls(env) == []


def run_hook(env) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", "-c", clear_hook_command()],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_the_hook_marks_a_clear_only_while_a_helper_waits(env):
    state = Path(env["XDG_STATE_HOME"]) / "seeds" / "tend"
    marker = state / "cleared-wtest_pfake"

    proc = run_hook(env)
    assert proc.returncode == 0
    assert not marker.exists()

    state.mkdir(parents=True)
    (state / "pending-wtest_pfake").write_text("1\n")
    proc = run_hook(env)
    assert proc.returncode == 0
    assert marker.exists()
    # A SessionStart hook's stdout becomes session context.
    assert proc.stdout == ""


def test_the_hook_does_nothing_outside_herdr(env):
    del env["HERDR_PANE_ID"]

    proc = run_hook(env)

    assert proc.returncode == 0
    assert proc.stdout == ""
    assert not (Path(env["XDG_STATE_HOME"]) / "seeds").exists()


def test_the_skill_runs_this_helper_and_takes_the_command_it_sends():
    """The skill (bead seeds-stwi) and the helper must agree on two strings:
    the path the skill runs, and the command the helper types."""
    skill = (TEND_DIR / "SKILL.md").read_text()

    assert 'python3 "${CLAUDE_SKILL_DIR}/tend_clear.py"' in skill
    assert "/seeds:tend next" in skill
    assert "If the argument is exactly `next`" in skill
    assert "/seeds:tend next" in HELPER.read_text()
