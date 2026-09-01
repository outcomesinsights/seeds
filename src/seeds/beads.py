"""Optional, read-only lookup of bead IDs from a sibling ``.beads/`` directory.

seeds and beads (https://github.com/gastownhall/beads) often share a project
prefix, so a body citing a real bead — ``see seeds-230`` — is indistinguishable
from a hallucinated seed reference by shape alone. Reading the beads export
lets the reference validator tell the two apart.

Everything here is best-effort. Beads is **not** a dependency: most projects
have no ``.beads/`` at all, and that is the normal case, not an error. A
missing, unreadable, or malformed export degrades to "no bead IDs known" so
that seed creation never fails because of the neighbouring tracker.

Two sources, in cost order. ``.beads/issues.jsonl`` is read directly and
answers almost every lookup, but it is a **derived, throttled export**: ``bd
create`` writes to Dolt and the export catches up later (beads' own
``export.interval``, 60s by default), so a bead created seconds ago is real
and absent from the file. Treating that miss as authoritative is what made
seeds reject a live bead ID and demand ``--allow-unknown-refs`` (bead
seeds-4co.23). :func:`query_bead_ids` closes that gap by asking ``bd`` itself,
and is called only for IDs the export did not already vouch for -- so the
subprocess is paid on the would-be-rejection path, never on the happy one.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

BEADS_DIR = ".beads"
BEADS_ISSUES_FILE = "issues.jsonl"

#: Written by ``bd init``. Its presence is what "beads is in use" means here:
#: a lone ``issues.jsonl`` someone copied into place is an export, not a live
#: workspace, and running ``bd`` against it would be asking a tracker that is
#: not there.
BEADS_CONFIG_FILE = "config.yaml"

BEADS_CLI = "bd"

#: Cap on the ``bd`` lookup. Generous -- the embedded Dolt engine takes a
#: moment to open -- but bounded, because a wedged tracker must not hang
#: ``seeds create``. A timeout degrades to "could not consult beads".
BEADS_CLI_TIMEOUT = 15.0


def beads_issues_path(seeds_dir: Path) -> Path:
    """Return where the beads export lives relative to ``seeds_dir``.

    ``.seeds/`` and ``.beads/`` are siblings at the project root, so the
    location is derived from the seeds directory's parent — never from the
    current working directory, which may be anywhere beneath it.
    """
    return seeds_dir.parent / BEADS_DIR / BEADS_ISSUES_FILE


def beads_dir(seeds_dir: Path) -> Path:
    """Return the sibling ``.beads`` directory for ``seeds_dir``."""
    return seeds_dir.parent / BEADS_DIR


def beads_in_use(seeds_dir: Path) -> bool:
    """Return True when a real beads workspace sits beside ``seeds_dir``.

    Gates every ``bd`` invocation, so that projects without beads -- the
    normal case -- never spawn a subprocess.
    """
    return (beads_dir(seeds_dir) / BEADS_CONFIG_FILE).is_file()


def load_bead_ids(seeds_dir: Path) -> set[str]:
    """Return the bead IDs exported alongside ``seeds_dir``, if any.

    Returns an empty set when there is no beads export, when it cannot be
    read, or when its contents are unusable. Individual unparseable lines are
    skipped rather than aborting the whole read, so a partially corrupt export
    still contributes the IDs it does have.
    """
    path = beads_issues_path(seeds_dir)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()

    ids: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        bead_id = record.get("id")
        if isinstance(bead_id, str) and bead_id:
            ids.add(bead_id)
    return ids


def query_bead_ids(seeds_dir: Path, refs: Sequence[str]) -> set[str] | None:
    """Ask ``bd`` which of ``refs`` name real beads.

    Returns the subset that exists, or ``None`` when beads could not be
    consulted at all -- no workspace, no ``bd`` on PATH, a crash, a timeout,
    or output this function cannot read. ``None`` is not "none of them
    exist": callers must keep the two apart, because the first means the
    answer is still coming from the possibly stale export and should be
    reported that way.

    ``bd show`` is used rather than ``bd list --id`` deliberately: ``list``
    applies the default status filter and hides gate, infra and template
    beads, so a closed or infrastructure bead would come back "missing".
    ``show`` fetches by ID with no filtering.
    """
    if not refs or not beads_in_use(seeds_dir):
        return None
    executable = shutil.which(BEADS_CLI)
    if executable is None:
        return None
    try:
        completed = subprocess.run(
            [executable, "show", *refs, "--json"],
            cwd=seeds_dir.parent,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=BEADS_CLI_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    try:
        payload = json.loads(completed.stdout)
    except ValueError:
        return None

    if isinstance(payload, list):
        return {
            record["id"]
            for record in payload
            if isinstance(record, dict)
            and isinstance(record.get("id"), str)
            and record["id"]
        }
    # When none of the IDs exist, bd answers with an error object rather than
    # an empty array. That is still an authoritative "no such bead", so it
    # must not be confused with a failure to reach beads.
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, str) and "no issues found" in error.lower():
            return set()
    return None
