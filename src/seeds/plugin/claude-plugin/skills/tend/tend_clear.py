"""Clear a Claude Code session through herdr, then start the next tend topic.

The seeds:tend skill runs this helper after the user picks "Clear and
continue" (bead seeds-z03u, rulings in seed seeds-x6m0). Claude Code gives a
model, a skill or a hook no way to run /clear. herdr can type into the pane, so
this helper types the commands for the user.

Two modes:

    python3 tend_clear.py [--wait-timeout S] [--confirm-timeout S]
        Detach from the Claude Code process tree, and then, in order:
        1. wait until the pane is idle,
        2. send /clear,
        3. confirm that the /clear took effect,
        4. wait until the pane is idle again,
        5. send /seeds:tend next.
        The parent prints the log path and exits 0 at once. The detached child
        does the work and writes every step to the log.

    python3 tend_clear.py mark-cleared
        The plugin's SessionStart hook runs this after a /clear. It writes the
        marker that step 3 waits for. It prints nothing, because the stdout of
        a SessionStart hook becomes session context.

herdr's agent status can report idle while a turn still runs. A /clear sent
during a turn is lost. So idle alone does not prove that the /clear happened.
The marker proves it: only Claude Code's SessionStart hook writes it, and Claude
Code runs that hook only after a /clear. Without the marker, the helper sends
nothing more.

Outside herdr (no HERDR_PANE_ID, or no herdr on PATH) the helper sends nothing
and exits 2 with a message. The skill then tells the user to type the commands.

This file runs under any python3 from 3.9 on, with the standard library only,
because the plugin cannot know which interpreter a host has.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import TextIO

CLEAR_COMMAND = "/clear"
NEXT_COMMAND = "/seeds:tend next"

EXIT_NOT_IN_HERDR = 2

MANUAL_FALLBACK = "Type these two commands yourself: /clear, and then /seeds:tend next."


def state_dir() -> Path:
    """Where the markers and the logs live: outside every repo, per user."""
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "seeds" / "tend"


def pane_key(pane: str) -> str:
    """A pane ID such as w1:p2, made safe for a file name."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", pane)


def pending_path(pane: str) -> Path:
    """Exists while the helper waits for a /clear in this pane."""
    return state_dir() / f"pending-{pane_key(pane)}"


def marker_path(pane: str) -> Path:
    """Written by the SessionStart hook when a /clear happened in this pane."""
    return state_dir() / f"cleared-{pane_key(pane)}"


class Log:
    """Timestamped lines in the log file."""

    def __init__(self, stream: TextIO) -> None:
        self.stream = stream

    def line(self, text: str) -> None:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.stream.write(f"{stamp} {text}\n")
        self.stream.flush()


def herdr(log: Log, *args: str) -> bool:
    """Run one herdr command. Log it and its result. True when it succeeded."""
    log.line("run: herdr " + " ".join(args))
    proc = subprocess.run(["herdr", *args], capture_output=True, text=True, check=False)
    if proc.stdout.strip():
        log.line("stdout: " + proc.stdout.strip())
    if proc.stderr.strip():
        log.line("stderr: " + proc.stderr.strip())
    log.line(f"exit: {proc.returncode}")
    return proc.returncode == 0


def wait_idle(log: Log, pane: str, timeout_s: float) -> bool:
    return herdr(
        log,
        "agent",
        "wait",
        pane,
        "--until",
        "idle",
        "--until",
        "done",
        "--timeout",
        str(int(timeout_s * 1000)),
    )


def wait_for_marker(marker: Path, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if marker.exists():
            return True
        time.sleep(0.2)
    return marker.exists()


def clear_and_continue(
    log: Log, pane: str, wait_timeout_s: float, confirm_timeout_s: float
) -> bool:
    """The five steps. Each send happens only after the step before it worked."""
    pending = pending_path(pane)
    marker = marker_path(pane)

    log.line(f"step 1: wait until pane {pane} is idle")
    if not wait_idle(log, pane, wait_timeout_s):
        log.line("FAILED: the pane did not become idle. Nothing was sent.")
        return False

    # Arm the hook only now. A marker can then come only from a /clear that
    # happened after this point.
    marker.unlink(missing_ok=True)
    pending.write_text(f"{os.getpid()}\n")
    try:
        log.line(f"step 2: send {CLEAR_COMMAND}")
        if not herdr(log, "agent", "prompt", pane, CLEAR_COMMAND):
            log.line(f"FAILED: herdr did not send {CLEAR_COMMAND}.")
            return False

        log.line(f"step 3: wait up to {confirm_timeout_s:g}s for {marker}")
        if not wait_for_marker(marker, confirm_timeout_s):
            log.line(
                f"FAILED: no SessionStart hook confirmed the {CLEAR_COMMAND}. "
                f"{NEXT_COMMAND} was NOT sent. " + MANUAL_FALLBACK
            )
            return False
        log.line(f"confirmed: {CLEAR_COMMAND} took effect")
    finally:
        pending.unlink(missing_ok=True)
        marker.unlink(missing_ok=True)

    log.line(f"step 4: wait until pane {pane} is idle again")
    if not wait_idle(log, pane, wait_timeout_s):
        log.line(f"FAILED: the pane did not become idle. {NEXT_COMMAND} not sent.")
        return False

    log.line(f"step 5: send {NEXT_COMMAND}")
    if not herdr(log, "agent", "prompt", pane, NEXT_COMMAND):
        log.line(f"FAILED: herdr did not send {NEXT_COMMAND}.")
        return False
    return True


def detach(log_file: Path) -> bool:
    """Double fork into a new session. True in the detached child.

    The new session takes the child out of the process group of Claude Code's
    Bash tool. The second fork makes init its parent. So the child survives
    when Claude Code ends the tool's process group, or the whole session.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    if os.fork() > 0:
        os.wait()
        return False
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    devnull = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull, 0)
    out = os.open(log_file, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    os.dup2(out, 1)
    os.dup2(out, 2)
    return True


def run(args: argparse.Namespace) -> int:
    pane = os.environ.get("HERDR_PANE_ID", "")
    if not pane:
        print(
            "tend_clear: HERDR_PANE_ID is not set, so this session is not in a "
            "herdr pane. Nothing was sent. " + MANUAL_FALLBACK,
            file=sys.stderr,
        )
        return EXIT_NOT_IN_HERDR
    if shutil.which("herdr") is None:
        print(
            "tend_clear: herdr is not on PATH. Nothing was sent. " + MANUAL_FALLBACK,
            file=sys.stderr,
        )
        return EXIT_NOT_IN_HERDR

    logs = state_dir() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_file = logs / f"clear-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}.log"

    if not detach(log_file):
        print(f"tend_clear: started for pane {pane}. Log: {log_file}")
        return 0

    log = Log(sys.stdout)
    log.line(f"helper pid {os.getpid()}, session {os.getsid(0)}, pane {pane}")
    ok = clear_and_continue(log, pane, args.wait_timeout, args.confirm_timeout)
    log.line("result: ok" if ok else "result: FAILED")
    sys.stdout.flush()
    os._exit(0 if ok else 1)


def mark_cleared() -> int:
    """The SessionStart hook. Writes the marker only when a helper waits."""
    pane = os.environ.get("HERDR_PANE_ID", "")
    if pane and pending_path(pane).exists():
        marker_path(pane).write_text(time.strftime("%Y-%m-%d %H:%M:%S\n"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tend_clear.py",
        description="Clear this Claude Code session through herdr, "
        "then send /seeds:tend next.",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="run",
        choices=["run", "mark-cleared"],
        help="run (the default) clears and continues. mark-cleared is for "
        "the SessionStart hook.",
    )
    parser.add_argument(
        "--wait-timeout",
        type=float,
        default=900.0,
        help="Seconds to wait for the pane to become idle (default 900).",
    )
    parser.add_argument(
        "--confirm-timeout",
        type=float,
        default=60.0,
        help="Seconds to wait for the hook to confirm the /clear (default 60).",
    )
    args = parser.parse_args(argv)
    if args.mode == "mark-cleared":
        return mark_cleared()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
