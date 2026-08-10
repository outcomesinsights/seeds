"""Optional, read-only lookup of bead IDs from a sibling ``.beads/`` directory.

seeds and beads (https://github.com/gastownhall/beads) often share a project
prefix, so a body citing a real bead — ``see seeds-230`` — is indistinguishable
from a hallucinated seed reference by shape alone. Reading the beads export
lets the reference validator tell the two apart.

Everything here is best-effort. Beads is **not** a dependency: most projects
have no ``.beads/`` at all, and that is the normal case, not an error. A
missing, unreadable, or malformed export degrades to "no bead IDs known" so
that seed creation never fails because of the neighbouring tracker. The
git-tracked ``.beads/issues.jsonl`` is read directly rather than shelling out
to the ``bd`` CLI, which may not be installed.
"""

from __future__ import annotations

import json
from pathlib import Path

BEADS_DIR = ".beads"
BEADS_ISSUES_FILE = "issues.jsonl"


def beads_issues_path(seeds_dir: Path) -> Path:
    """Return where the beads export lives relative to ``seeds_dir``.

    ``.seeds/`` and ``.beads/`` are siblings at the project root, so the
    location is derived from the seeds directory's parent — never from the
    current working directory, which may be anywhere beneath it.
    """
    return seeds_dir.parent / BEADS_DIR / BEADS_ISSUES_FILE


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
