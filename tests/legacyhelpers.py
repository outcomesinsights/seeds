"""Building a pre-0.7 SQLite store, for the converter's tests only.

``seeds.legacy`` is read-only on purpose — nothing shipped may write the retired
store — so the fixtures that give ``seeds convert`` something to convert have to
create one themselves. That is exactly the right place for the write path to
live: a test helper, where using it is a deliberate act, rather than a method on
the shipped reader that a future caller could reach for.

The schema below is the pre-0.7 one verbatim, minus the FTS5 virtual table and
its triggers. The converter never reads those, and re-creating a search index
for a store that is being deleted would only invite someone to keep it.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from seeds.models import Relationship, RelationType, Seed

LEGACY_SCHEMA = """
CREATE TABLE IF NOT EXISTS seeds (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'captured',
    seed_type TEXT NOT NULL DEFAULT 'idea',
    tags TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    resolution TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    rel_type TEXT NOT NULL DEFAULT 'relates-to',
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES seeds(id),
    FOREIGN KEY (target_id) REFERENCES seeds(id),
    UNIQUE(source_id, target_id, rel_type)
);

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _stamp(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


class LegacyWriter:
    """A writable handle on a legacy store. Tests only."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(LEGACY_SCHEMA)
        self.conn.commit()

    def set_prefix(self, prefix: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES ('prefix', ?)",
            (prefix,),
        )
        self.conn.commit()

    def create_seed(self, seed: Seed) -> Seed:
        self.conn.execute(
            "INSERT INTO seeds (id, title, content, status, seed_type, tags, "
            "created_at, updated_at, resolved_at, resolution) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                seed.id,
                seed.title,
                seed.content,
                seed.status.value,
                seed.seed_type,
                json.dumps(seed.tags),
                _stamp(seed.created_at),
                _stamp(seed.updated_at),
                _stamp(seed.resolved_at),
                seed.resolution,
            ),
        )
        self.conn.commit()
        return seed

    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationType = RelationType.RELATES_TO,
        created_at: datetime | None = None,
    ) -> Relationship:
        """Insert an edge, mirroring the pre-0.7 write path.

        ``relates-to`` was stored as two rows there, one per direction;
        directed types as one. The converter has to cope with both shapes, so
        the helper reproduces them rather than normalizing.
        """
        assert created_at is not None, "legacy fixtures stamp their edges"
        self.conn.execute(
            "INSERT OR IGNORE INTO relationships "
            "(source_id, target_id, rel_type, created_at) VALUES (?, ?, ?, ?)",
            (source_id, target_id, rel_type.value, _stamp(created_at)),
        )
        if rel_type is RelationType.RELATES_TO:
            self.conn.execute(
                "INSERT OR IGNORE INTO relationships "
                "(source_id, target_id, rel_type, created_at) "
                "VALUES (?, ?, ?, ?)",
                (target_id, source_id, rel_type.value, _stamp(created_at)),
            )
        self.conn.commit()
        return Relationship(
            source_id=source_id,
            target_id=target_id,
            rel_type=rel_type,
            created_at=created_at,
        )

    def close(self) -> None:
        self.conn.close()


def build_legacy_db(
    seeds_dir: Path, seeds: list[Seed], *, prefix: str = "seeds"
) -> LegacyWriter:
    """A legacy store holding exactly ``seeds``, left open for the caller."""
    writer = LegacyWriter(Path(seeds_dir) / "seeds.db")
    writer.set_prefix(prefix)
    for seed in seeds:
        writer.create_seed(seed)
    return writer
