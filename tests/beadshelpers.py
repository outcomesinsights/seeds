"""Shared helper for tests that exercise the ``bd`` lookup in seeds.beads.

``query_bead_ids`` shells out to whatever ``bd`` is on PATH. Letting the
suite reach the real one would make results depend on the developer's own
beads database -- and, worse, run a tracker against a throwaway directory.
Every test therefore installs a stub instead: a tiny script that echoes a
canned payload and records how it was called.
"""

from __future__ import annotations

import sys
from pathlib import Path

BD_CALL_LOG = "bd-calls.log"


def install_fake_bd(
    tmp_path: Path,
    monkeypatch,
    stdout: str = "[]",
    exit_code: int = 0,
) -> Path:
    """Put a stub ``bd`` on PATH and return the file it logs its calls to.

    Each invocation appends one line: the working directory it was run from,
    then its arguments, tab-separated. PATH is replaced outright rather than
    prepended to, so a real ``bd`` cannot be found behind the stub.
    """
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    payload = bin_dir / "bd-stdout"
    payload.write_text(stdout, encoding="utf-8")
    log = bin_dir / BD_CALL_LOG
    script = bin_dir / "bd"
    # Python rather than /bin/sh: PATH is emptied of everything but this
    # directory, so a shell stub could not find `cat`, and the shebang here is
    # an absolute interpreter path that PATH cannot affect.
    script.write_text(
        f"#!{sys.executable}\n"
        "import pathlib, sys\n"
        f"log = pathlib.Path({str(log)!r})\n"
        "with log.open('a', encoding='utf-8') as fh:\n"
        "    fh.write(pathlib.Path.cwd().as_posix() + '\\t'"
        " + ' '.join(sys.argv[1:]) + '\\n')\n"
        f"sys.stdout.write(pathlib.Path({str(payload)!r}).read_text('utf-8'))\n"
        f"sys.exit({exit_code})\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))
    return log


def hide_bd(monkeypatch, tmp_path: Path) -> None:
    """Make PATH hold no ``bd`` at all."""
    empty = tmp_path / "empty-bin"
    empty.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PATH", str(empty))


def make_beads_workspace(seeds_dir: Path) -> Path:
    """Create the sibling ``.beads/config.yaml`` that marks beads as in use."""
    beads = seeds_dir.parent / ".beads"
    beads.mkdir(parents=True, exist_ok=True)
    config = beads / "config.yaml"
    config.write_text("prefix: seeds\n", encoding="utf-8")
    return beads


def call_lines(log: Path) -> list[str]:
    """Return the stub's recorded invocations, newest last."""
    if not log.exists():
        return []
    return [line for line in log.read_text(encoding="utf-8").splitlines() if line]
