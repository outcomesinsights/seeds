"""The pre-0.7 store, read-only, kept alive for exactly one caller.

``.seeds/seeds.db`` and ``.seeds/seeds.jsonl`` stopped being the store when the
seed-file tree replaced them (``docs/storage-format.md``). The persistence layer
that wrote them is gone: no schema creation, no FTS, no writes of any kind.

What survives here is the narrow reader ``seeds convert`` needs, and it survives
because the converter is a **shipped verb for repos that have not converted
yet** — 13 repos on titan plus an external user who converts on his own
schedule. Deleting its ability to read a legacy SQLite store would make
conversion impossible for exactly the people it exists for.

So the contract of this module is deliberately narrow:

- **Read-only, and enforced.** The connection is opened ``mode=ro`` through a
  file URI, so a stray write raises rather than silently mutating a store the
  new code no longer understands. There is no ``init``, no ``CREATE TABLE``,
  and no migration.
- **Only what the converter asks for.** Seeds, relationship rows, and the
  ``config`` table's prefix. Not search, not blocking, not children — every one
  of those questions is answered off the tree now, by :mod:`seeds.store`.
- **Nothing else may import it.** A second caller would be a new dependency on
  a retired store, which is the shape this whole change removed.

:func:`db_extends_disk` and :func:`first_difference` come along for the same
reason. They compare a database body with a JSONL body, which is a question only
the two-store world can ask — and the converter is the last code that lives in
it.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from seeds.models import (
    DEFAULT_PREFIX,
    Relationship,
    RelationType,
    Seed,
    SeedStatus,
    is_valid_prefix,
    now_utc,
)

DB_FILE = "seeds.db"
"""The legacy SQLite store's filename inside ``.seeds/``."""

JSONL_FILE = "seeds.jsonl"
"""The legacy JSONL export's filename inside ``.seeds/``.

Retired on conversion day, and the *file* is then deleted -- ``seeds convert``
stages the removal wherever git can restore it. What is never deleted is its
**git history**, the only source for anything before a seed's ``converted_at``
(``docs/storage-format.md`` §11).
"""

PREFIX_CONFIG_KEY = "prefix"
"""The ``config`` table key the project prefix lived under before §9."""

REQUIRED_TABLES = frozenset({"seeds"})
"""Legacy tables without which there is nothing to convert.

``seeds`` alone, and the test is not "does the reader touch it" but "does it
carry deliberation". A store missing this table holds no seed bodies, no
titles and no ids, so there is no salvage to attempt and no honest way to
proceed — the reader refuses, naming the store and the table.

Everything else the reader touches is in :data:`OPTIONAL_TABLES`.
"""

OPTIONAL_TABLES = frozenset({"relationships", "questions", "config"})
"""Legacy tables whose absence means "empty", not "broken".

None of the three carries a seed. ``relationships`` carries edges *between*
seeds, ``questions`` is debris the converter drops wholesale anyway, and
``config`` carries one string the converter can derive from the ids when it is
missing. Absent, each reads as empty and the conversion continues.

This is the general rule, not a carve-out for ``relationships``. A pre-0.7
store is whatever schema it happened to stop at: ``mani`` and ``beads`` on
titan hold only ``seeds`` and ``questions``, a shape older than the
relationships table itself, and ``seeds convert`` used to meet it with a bare
``sqlite3.OperationalError``. Ruled 2026-09-01 (@aguynamedryan): a missing
``relationships`` table is "no relationships" — the 14 seeds in ``mani`` are
intact and readable, and stranding them over a table that carries nothing
would be the worse answer. Measured the same day, all 15 legacy stores on
titan agree: nowhere does an absent table hide an edge.

The JSONL reader has always behaved this way — a record with no
``relationships`` key reads as a record with no edges — so this brings the
SQLite reader to the same rule rather than inventing one for it.
"""

VESTIGIAL_REL_TYPES = frozenset({"answers"})
"""Legacy ``rel_type`` values that are dropped rather than translated.

``answers`` is the only one, and it is here because it was ruled vestigial
(``docs/storage-format.md`` §5.2) *after* real stores had already recorded a
handful of rows: ``seeds answer`` stores an answer as the question-seed's own
content and never made an edge, so the only route to one was a hand-run
``seeds link --type answers``. Removing ``RelationType.ANSWERS`` was right;
what it missed is that a pre-0.7 SQLite store can still hold the rows. Measured
2026-09-01 across the 13 unconverted repos on titan: 5 rows in three of them
(code_set_catalog 3, code_collector 1, habituate 1) against 2,384 edges total.

This set is *not* a general escape hatch. It names values already ruled dead,
one by one; anything else outside :class:`~seeds.models.RelationType` raises
:class:`LegacyRelationTypeError` so a future unknown cannot vanish into the
same bucket.
"""


class LegacyMissingTableError(LookupError):
    """A legacy store lacks a table the reader cannot do without.

    Carries the store and the missing names rather than a message alone, for
    the same reason :class:`LegacyRelationTypeError` does: the converter
    renders its own diagnostic naming which store and which table, instead of
    letting SQLite's ``no such table: …`` reach the operator as a traceback
    with no path in it.

    Only :data:`REQUIRED_TABLES` can raise this. An absent
    :data:`OPTIONAL_TABLES` member reads as empty and never gets here.
    """

    def __init__(self, path: Path, tables: tuple[str, ...]) -> None:
        self.path = path
        self.tables = tables
        super().__init__(f"{path}: missing legacy table(s): {', '.join(tables)}")


class LegacyRelationTypeError(ValueError):
    """A legacy ``relationships`` row names a ``rel_type`` nothing can read.

    Carries the row rather than a message alone, so the converter can render
    the same diagnostic it renders for the JSONL path — which store, which
    edge, which value — instead of the bare ``ValueError`` that constructing
    :class:`~seeds.models.RelationType` eagerly used to raise.
    """

    def __init__(
        self, path: Path, source_id: str, target_id: str, rel_type: str
    ) -> None:
        self.path = path
        self.source_id = source_id
        self.target_id = target_id
        self.rel_type = rel_type
        super().__init__(
            f"{path}: edge {source_id} -> {target_id}: rel_type {rel_type!r} "
            "is not readable"
        )


def _table_names(conn: sqlite3.Connection) -> set[str]:
    """Every table name in an open legacy store."""
    return {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def _str_to_datetime(value: str | None) -> datetime | None:
    """An ISO timestamp string as a datetime, or ``None``."""
    if value is None:
        return None
    return datetime.fromisoformat(value)


class LegacyDatabase:
    """A read-only window onto a pre-0.7 ``.seeds/seeds.db``.

    Opened through a ``file:…?mode=ro`` URI, so SQLite itself refuses a write.
    The file must already exist; ``mode=ro`` does not create one, and the
    converter checks for it before constructing this.

    The schema is checked once, when the connection opens: every
    :data:`REQUIRED_TABLES` member must be there or nothing is read at all.
    Checking at the door rather than inside each query means a store too old to
    convert says so before it has half-converted, and says it the same way
    whichever method the caller reached for first.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            conn = sqlite3.connect(f"file:{self.path.resolve()}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            missing = REQUIRED_TABLES - _table_names(conn)
            if missing:
                conn.close()
                raise LegacyMissingTableError(self.path, tuple(sorted(missing)))
            self._conn = conn
        return self._conn

    def close(self) -> None:
        """Close the connection, if one was opened."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _tables(self) -> set[str]:
        return _table_names(self._get_conn())

    def absent_tables(self) -> list[str]:
        """Which :data:`OPTIONAL_TABLES` this store does not have, sorted.

        Read as empty rather than refused — but reported, because an operator
        looking at a converted tree with no edges in it should be able to see
        that the store never had a place to keep one, rather than wonder what
        the converter threw away.
        """
        return sorted(OPTIONAL_TABLES - self._tables())

    def _row_to_seed(self, row: sqlite3.Row) -> Seed:
        return Seed(
            id=row["id"],
            title=row["title"],
            content=row["content"] or "",
            status=SeedStatus(row["status"]),
            seed_type=row["seed_type"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=_str_to_datetime(row["created_at"]) or now_utc(),
            updated_at=_str_to_datetime(row["updated_at"]) or now_utc(),
            resolved_at=_str_to_datetime(row["resolved_at"]),
            resolution=row["resolution"] if "resolution" in row.keys() else "",  # noqa: SIM118
        )

    def list_seeds(self) -> list[Seed]:
        """Every seed in the legacy store, terminal ones included.

        No filters: the converter reads the whole store or none of it, and a
        filtered migration is a silently short one.
        """
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM seeds ORDER BY id").fetchall()
        return [self._row_to_seed(row) for row in rows]

    def get_relationships(self, seed_id: str) -> list[Relationship]:
        """Every readable relationship row naming ``seed_id`` at either end.

        A row whose ``rel_type`` is in :data:`VESTIGIAL_REL_TYPES` is skipped —
        it names a relation already ruled dead, and translating it would invent
        a semantic nobody chose. It is skipped here rather than filtered by the
        caller so that ``convert``'s own verification, which re-reads through
        this same method, sees the same edges the conversion did.
        The dropped rows are still enumerated, by
        :meth:`vestigial_relationship_keys`, so a drop is reported and never
        silent.

        Any *other* unreadable value raises :class:`LegacyRelationTypeError`.

        A store with no ``relationships`` table at all has no edges, so this
        returns nothing — see :data:`OPTIONAL_TABLES`.
        """
        if "relationships" not in self._tables():
            return []
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM relationships WHERE source_id = ? OR target_id = ? "
            "ORDER BY created_at",
            (seed_id, seed_id),
        ).fetchall()
        relationships: list[Relationship] = []
        for row in rows:
            raw: str = row["rel_type"]
            if raw in VESTIGIAL_REL_TYPES:
                continue
            try:
                rel_type = RelationType(raw)
            except ValueError as exc:
                raise LegacyRelationTypeError(
                    self.path, row["source_id"], row["target_id"], raw
                ) from exc
            relationships.append(
                Relationship(
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    rel_type=rel_type,
                    created_at=_str_to_datetime(row["created_at"]) or now_utc(),
                )
            )
        return relationships

    def vestigial_relationship_keys(self) -> list[tuple[str, str, str]]:
        """Every dropped row as ``(source_id, target_id, rel_type)``.

        Identities rather than a count, because the same edge is usually
        recorded in *both* legacy stores — the SQLite and the JSONL export of
        it — and the converter reports how many edges it dropped, not how many
        rows across how many files said so. The caller unions these with the
        JSONL's and tallies once.

        Read table-wide rather than accumulated during
        :meth:`get_relationships`, which only ever visits rows naming a seed
        that exists: a dead edge pointing at a deleted seed would go uncounted,
        and an under-reported drop is the failure this exists to prevent.
        """
        if "relationships" not in self._tables():
            return []
        rows = self._get_conn().execute(
            "SELECT source_id, target_id, rel_type FROM relationships "
            f"WHERE rel_type IN ({','.join('?' * len(VESTIGIAL_REL_TYPES))}) "
            "ORDER BY source_id, target_id, rel_type",
            tuple(sorted(VESTIGIAL_REL_TYPES)),
        )
        return [(row[0], row[1], row[2]) for row in rows]

    def _get_config(self, key: str) -> str | None:
        if "config" not in self._tables():
            return None
        row = (
            self._get_conn()
            .execute("SELECT value FROM config WHERE key = ?", (key,))
            .fetchone()
        )
        if row is None:
            return None
        value: str = row["value"]
        return value

    def has_prefix_configured(self) -> bool:
        """Whether the legacy ``config`` table carries an explicit prefix."""
        return self._get_config(PREFIX_CONFIG_KEY) is not None

    def get_prefix(self) -> str:
        """The configured prefix, or :data:`DEFAULT_PREFIX` when unset.

        The converter is the last moment this value can be read: §9 moved it to
        a tracked ``.seeds/config.yaml``, and nothing after conversion opens
        this file again.
        """
        value = self._get_config(PREFIX_CONFIG_KEY)
        if value and is_valid_prefix(value):
            return value
        return DEFAULT_PREFIX


def db_extends_disk(db_content: str, disk_content: str) -> bool:
    """Does the database's content begin with the on-disk content?

    Divergence is decided on CONTENT, never on ``updated_at``. Timestamps only
    answer "which is newer", and they are the input already known to be
    untrustworthy (clock skew, hand edits, merge resolutions). The question
    that actually matters is "does the disk hold text the database has never
    seen", which is a content question.

    A flat "content differs -> diverged" would be unusable: the database is
    normally *ahead* of the file. The test that separates "ahead" from
    "diverged" leans on ``seeds update -a`` having been the normal editing verb
    for a seed body:

    - identical bodies -> nothing to lose.
    - the database's body **starts with** the file's -> the database is the
      file's version plus appends; taking it loses nothing.
    - anything else -> the file holds text the database never had. A fork.

    Validated against this project's own JSONL history: of 42 content-changing
    edits across 67 commits, 41 were literal appends. The single exception was
    an in-place rewrite that prepended a header to an existing body — precisely
    the kind of edit an operator should be told about.

    The stripped fallback exists because ``seeds update -a`` stripped the
    *combined* body, so appending to a body with leading whitespace yields a
    result that is not a literal prefix of it even though no text was lost.
    Whitespace is not deliberation. It cannot mask real loss: any actual
    character present on disk and absent from the database still fails.
    """
    if db_content.startswith(disk_content):
        return True
    return db_content.strip().startswith(disk_content.strip())


def first_difference(db_content: str, disk_content: str) -> int:
    """Index of the first character where the two bodies part ways.

    ``strict=False`` is deliberate: the two bodies routinely differ in length
    — one being a prefix of the other is the common, benign case — so zip must
    stop at the shorter. The fallback below reports that shared length as the
    divergence point.
    """
    for i, (a, b) in enumerate(zip(db_content, disk_content, strict=False)):
        if a != b:
            return i
    return min(len(db_content), len(disk_content))
