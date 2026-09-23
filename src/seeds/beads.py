"""Optional, read-only lookup of bead IDs from a sibling ``.beads/`` workspace.

seeds and beads (https://github.com/gastownhall/beads) often share a project
prefix, so a body citing a real bead — ``see seeds-230`` — is indistinguishable
from a hallucinated seed reference by shape alone. Asking ``bd`` lets the
reference validator tell the two apart.

Everything here is best-effort. Beads is **not** a dependency: most projects
have no ``.beads/`` at all, and that is the normal case, not an error.

**``bd`` is the only source.** Until 2026-09-23 a sibling ``.beads/issues.jsonl``
was read first, as a cheap export that lagged ``bd`` by about a minute. JSONL was
retired on 2026-09-13 and nothing maintains the file, so where it survived it
was frozen: measured here, 175 ids against ``bd``'s 183, and untracked, so a
fresh clone had none. It failed both ways. A bead created since the freeze was
missed (harmless, ``bd`` caught it). A bead DELETED since was still vouched for,
never reached ``bd``, and a dangling reference passed as valid. And
``winnow``'s outcome flavor read it with no fallback at all, so it silently
found nothing on any clone without the file (bead seeds-dlq).

Two queries, chosen by how many ids are in hand. Measured on this project:
``bd show`` costs about a third of a second PER id (1 id 0.6s, 10 ids 3.6s,
60 ids 19.9s), while ``bd list --all`` returned all 185 beads in 0.5s.

* :func:`query_bead_ids` -- ``bd show`` on the handful of unknown references in
  one body. Exact: ``show`` applies no status or type filter.
* :func:`all_bead_ids` -- ``bd list --all`` once, for callers that need the
  whole set (``winnow``). ``list`` may hide gate, infra and template beads;
  nothing resolves a seed into one of those, so for that use it does not matter.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

from seeds.gitstage import subprocess_env

BEADS_DIR = ".beads"

#: Written by ``bd init``. Its presence is what "beads is in use" means here;
#: without it there is no tracker to ask, and ``bd`` is never run.
BEADS_CONFIG_FILE = "config.yaml"

BEADS_CLI = "bd"

#: Cap on the ``bd`` lookup. Generous -- the embedded Dolt engine takes a
#: moment to open -- but bounded, because a wedged tracker must not hang
#: ``seeds create``. A timeout degrades to "could not consult beads".
BEADS_CLI_TIMEOUT = 15.0


def beads_dir(seeds_dir: Path) -> Path:
    """Return the sibling ``.beads`` directory for ``seeds_dir``."""
    return seeds_dir.parent / BEADS_DIR


def beads_in_use(seeds_dir: Path) -> bool:
    """Return True when a real beads workspace sits beside ``seeds_dir``.

    Gates every ``bd`` invocation, so that projects without beads -- the
    normal case -- never spawn a subprocess.
    """
    return (beads_dir(seeds_dir) / BEADS_CONFIG_FILE).is_file()


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
            # `bd` shells out to git itself, and an inherited GIT_DIR outranks
            # both cwd and an explicit `git -C` -- so without this, a `bd show`
            # from inside a hook reads whichever repo the hook is committing
            # in, not this one. Same seam as gitstage's, for the same reason.
            env=subprocess_env(),
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


def all_bead_ids(seeds_dir: Path) -> set[str] | None:
    """Every bead id ``bd list --all`` reports, or ``None`` if beads is unreachable.

    One call for the whole set -- for callers that need it all rather than a
    few named references. ``None`` means "could not ask", never "no beads":
    a caller that treated the two alike would report a clean result for a
    check that never ran.
    """
    if not beads_in_use(seeds_dir):
        return None
    executable = shutil.which(BEADS_CLI)
    if executable is None:
        return None
    try:
        completed = subprocess.run(
            [executable, "list", "--all", "--json"],
            cwd=seeds_dir.parent,
            env=subprocess_env(),
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
    if not isinstance(payload, list):
        return None
    return {
        record["id"]
        for record in payload
        if isinstance(record, dict)
        and isinstance(record.get("id"), str)
        and record["id"]
    }
