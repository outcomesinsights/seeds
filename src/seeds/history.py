"""One seed's evolution, read out of git and joined across the conversion.

``seeds history <id>`` answers "how did this seed get to be what it is?" from
the only store that holds the answer. It **structures and labels; it never
summarises.**

That cut is the whole design. Walking git and naming which fields a commit
changed is deterministic: two runs agree, and every line is checkable against
``git show``. Deciding what a change *meant* is judgment, and a rolling summary
of a deliberation is a decision log -- the artifact seeds exists not to be. It
would also be non-deterministic and unauditable, so two runs could disagree
about what the journey was and neither could be checked. Labelling is a verb;
interpretation belongs to the caller.

**Both sides of the conversion, joined into one list.** Conversion writes every
seed file in a single commit, so a seed's own file history begins on conversion
day and, read alone, would claim that a seed deliberated over seven months was
born that morning -- orphaning the ~113 commits of real history on precisely the
day the format is supposed to make history *better*. So the walk is: the seed
file's own commits, and before them the commits of ``.seeds/seeds.jsonl``, whose
history is load-bearing forever and must never be filtered out of the repository
as cleanup (``docs/storage-format.md`` §11). ``converted_at`` -- stamped once, by
the converter -- is what says where to switch.

The rejected alternative was replaying the JSONL history as synthetic per-file
commits. That is ~113 fabricated commits appended to main in every repo that
converts, and there is no honest way to do it that does not either rewrite
history or lie about dates.

**The join is a single diff chain, not two lists stapled together.** Each
revision is diffed against the one before it *regardless of which store it came
from*, so the conversion commit reports only what conversion actually changed
(``converted_at``, and ``parent`` for a child seed) rather than re-announcing
every field as new. Both sides are projected through the same key names --
:func:`seeds.jsonexport.record_to_dict` deliberately kept the retired JSONL's
names -- which is what makes that one chain possible.

The pre-conversion technique is to materialize the whole JSONL at each commit
that touched it and pull the record out by id. Per-seed history is cleanly
extractable that way; it is only the raw *diffs* that are interleaved across 300
records and unreadable.

Deliberately not here: per-section attribution via ``git blame``. Per-commit is
enough to ship, and the finer granularity is a separate question.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from seeds.githistory import Commit, path_commits, repo_root, show_file
from seeds.jsonexport import record_to_dict
from seeds.legacy import JSONL_FILE
from seeds.seedfile import SeedFileError, SeedRecord, parse_seed_file, path_for_id

__all__ = [
    "FILE_SOURCE",
    "JSONL_SOURCE",
    "History",
    "Revision",
    "format_history",
    "seed_history",
]

FILE_SOURCE = "file"
"""A revision read from the seed's own ``.seeds/seeds/<id>.md``."""

JSONL_SOURCE = "jsonl"
"""A revision read from ``.seeds/seeds.jsonl``, before conversion."""

REMOVED = "<removed>"
"""Stands where a field list would go when the seed left the store."""

UNREADABLE = "<unreadable>"
"""Stands where a field list would go when a revision will not parse.

History is not editable, so a revision the strict reader refuses is reported as
what it is rather than raised. Losing the whole history over one bad commit
would be the larger failure.
"""

# The JSONL's own bookkeeping, not a field of the seed. Comparing it would
# report a format bump as a change to every seed at once.
_IGNORED_KEYS = frozenset({"format_version"})

# Renderings of "this field carries nothing". Used only for the first revision,
# where there is no previous state and listing every empty field as newly set
# would bury the ones that were.
_EMPTY = frozenset({"null", '""', "[]", "{}"})


@dataclass(frozen=True)
class _Snapshot:
    """What one commit held for one seed: nothing, something, or garbage."""

    present: bool
    readable: bool
    fields: dict[str, str]


_ABSENT = _Snapshot(present=False, readable=True, fields={})


@dataclass(frozen=True)
class Revision:
    """One commit in which this seed actually changed.

    A commit that touched the store without touching *this* seed never becomes
    a Revision -- 120 commits touch the JSONL and four of them touch any given
    seed, so reporting the rest would be reporting the store's history under the
    seed's name.
    """

    commit: Commit
    source: str
    fields: tuple[str, ...]


@dataclass(frozen=True)
class History:
    """Every revision of one seed, oldest first, across both stores."""

    seed_id: str
    title: str
    converted_at: datetime | None
    file_path: str
    jsonl_path: str
    revisions: tuple[Revision, ...]

    @property
    def before_conversion(self) -> int:
        """How many revisions came from the JSONL."""
        return sum(1 for rev in self.revisions if rev.source == JSONL_SOURCE)

    @property
    def after_conversion(self) -> int:
        """How many revisions came from the seed's own file."""
        return sum(1 for rev in self.revisions if rev.source == FILE_SOURCE)


def _relpath(root: Path, path: Path) -> str:
    """``path`` as a repo-relative POSIX path, which is how git names things.

    Resolved rather than probed: the seed file for an id is a computable path
    (§1.1) whether or not it exists, and a path that has been *deleted* still
    has a history worth reading.
    """
    return path.resolve().relative_to(root).as_posix()


def _normalize(payload: dict[str, Any]) -> dict[str, str]:
    """One record as ``{field: stable rendering}``, ready to compare.

    JSON with sorted keys so a relationship list reordered by a rewrite of the
    store does not read as a change to the seed, and ``default=str`` so a
    datetime that reached here undecoded still renders rather than raising.
    """
    return {
        key: json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
        for key, value in payload.items()
        if key not in _IGNORED_KEYS
    }


def _changed(prev: _Snapshot, cur: _Snapshot) -> tuple[str, ...]:
    """The fields this revision changed, sorted; empty when it changed nothing.

    A key missing on one side reads as ``null``, which is what makes the
    conversion boundary honest: the pre-0.7 records carry no ``parent`` and no
    ``converted_at``, so a top-level seed reports neither as changed while a
    child seed correctly reports that conversion is where its ``parent`` was
    first written down.
    """
    if not cur.readable:
        return (UNREADABLE,)
    if not cur.present:
        return (REMOVED,) if prev.present else ()
    if not prev.present or not prev.readable:
        return tuple(
            sorted(key for key, value in cur.fields.items() if value not in _EMPTY)
        )
    keys = set(prev.fields) | set(cur.fields)
    return tuple(
        sorted(
            key
            for key in keys
            if prev.fields.get(key, "null") != cur.fields.get(key, "null")
        )
    )


def _file_snapshot(root: Path, rev: str, relpath: str) -> _Snapshot:
    """The seed as its own file held it at ``rev``."""
    text = show_file(root, rev, relpath)
    if text is None:
        return _ABSENT
    try:
        record = parse_seed_file(root / relpath, text)
    except SeedFileError:
        return _Snapshot(present=True, readable=False, fields={})
    return _Snapshot(
        present=True, readable=True, fields=_normalize(record_to_dict(record))
    )


def _jsonl_snapshot(root: Path, rev: str, relpath: str, seed_id: str) -> _Snapshot:
    """The seed as ``.seeds/seeds.jsonl`` held it at ``rev``.

    The whole file is materialized and the record pulled out by id. Lines that
    do not mention the id at all are skipped before parsing -- a substring test,
    never a substitute for the real check, because another seed's body or
    relationship list can name this one and only ``record["id"]`` decides.
    """
    text = show_file(root, rev, relpath)
    if text is None:
        return _ABSENT
    needle = f'"{seed_id}"'
    for line in text.splitlines():
        if needle not in line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("id") == seed_id:
            return _Snapshot(present=True, readable=True, fields=_normalize(record))
    return _ABSENT


def seed_history(seeds_dir: Path, record: SeedRecord) -> History:
    """``record``'s evolution, oldest first, joined across the conversion.

    Raises :class:`~seeds.githistory.GitUnavailable` when there is no git to
    ask, and :class:`ValueError` when the store is not inside the work tree git
    reports. Both are loud on purpose: a history that silently came back short
    is indistinguishable from a seed with a short history, which is the "green
    while broken" shape this subsystem exists to prevent.
    """
    seeds_dir = Path(seeds_dir)
    root = repo_root(seeds_dir)
    file_rel = _relpath(root, path_for_id(seeds_dir, record.id))
    jsonl_rel = _relpath(root, seeds_dir / JSONL_FILE)

    steps: list[tuple[Commit, str, _Snapshot]] = []
    if record.converted_at is not None:
        cutoff = record.converted_at.timestamp()
        for commit in path_commits(root, jsonl_rel):
            if commit.timestamp > cutoff:
                continue
            steps.append(
                (
                    commit,
                    JSONL_SOURCE,
                    _jsonl_snapshot(root, commit.sha, jsonl_rel, record.id),
                )
            )
    for commit in path_commits(root, file_rel):
        steps.append((commit, FILE_SOURCE, _file_snapshot(root, commit.sha, file_rel)))

    revisions: list[Revision] = []
    previous = _ABSENT
    for commit, source, snapshot in steps:
        fields = _changed(previous, snapshot)
        if fields:
            revisions.append(Revision(commit=commit, source=source, fields=fields))
        previous = snapshot

    return History(
        seed_id=record.id,
        title=record.title,
        converted_at=record.converted_at,
        file_path=file_rel,
        jsonl_path=jsonl_rel,
        revisions=tuple(revisions),
    )


def format_history(history: History) -> str:
    """``history`` as the reader's view: a table, a boundary, and no prose.

    The boundary line is the one piece of narrative allowed, and it is a fact
    with a timestamp behind it rather than a reading of what changed.
    """
    lines = [f"{history.seed_id}  {history.title}"]

    if not history.revisions:
        lines.append("")
        lines.append(
            f"No committed revisions. Nothing in this repository's history "
            f"touches {history.file_path}"
            + (
                f" or names it in {history.jsonl_path}."
                if history.converted_at is not None
                else "."
            )
        )
        return "\n".join(lines)

    before, after = history.before_conversion, history.after_conversion
    if history.converted_at is not None and before:
        summary = (
            f"{len(history.revisions)} revisions: {before} in "
            f"{history.jsonl_path} before conversion, {after} in "
            f"{history.file_path} after."
        )
    else:
        summary = f"{len(history.revisions)} revisions in {history.file_path}."
    lines.append(summary)
    lines.append("")

    rows = [
        (rev.commit.date, rev.commit.author, ",".join(rev.fields), rev.commit.subject)
        for rev in history.revisions
    ]
    date_w = max(len(row[0]) for row in rows)
    author_w = max(len(row[1]) for row in rows)
    fields_w = max(len(row[2]) for row in rows)

    emitted_boundary = False
    for rev, row in zip(history.revisions, rows, strict=True):
        if rev.source == FILE_SOURCE and before and not emitted_boundary:
            lines.append(f"--- converted {_stamp(history.converted_at)} ---")
            emitted_boundary = True
        date, author, fields, subject = row
        lines.append(
            f"{date:<{date_w}}  {author:<{author_w}}  {fields:<{fields_w}}  {subject}"
        )
    return "\n".join(lines)


def _stamp(value: datetime | None) -> str:
    """A conversion timestamp for the boundary line."""
    return "unknown" if value is None else value.isoformat()
