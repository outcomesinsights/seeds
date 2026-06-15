"""seeds SQLite database layer."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from seeds.models import (
    DEFAULT_PREFIX,
    Relationship,
    RelationType,
    ScoredSeed,
    Seed,
    SeedStatus,
    SeedType,
    is_valid_prefix,
    iter_id_ref_snippets,
    now_utc,
    parse_sequential_id,
    rewrite_id_refs,
)


def recover_prefix_from_id(seed_id: str) -> str | None:
    """Recover the project prefix from a seed ID like 'seeds-155' -> 'seeds'.

    Strips any child suffix first (``seeds-155.1`` is the child of top-level
    ``seeds-155``), then takes everything before the final ``-<number>``
    segment. Returns ``None`` when ``seed_id`` is not a recoverable
    ``<prefix>-<number>`` shape (e.g. a legacy hex hash like ``seed-a1b2`` or
    a malformed ID), or when the recovered prefix is not a valid prefix.

    Used by fresh-clone import bootstrap to set the project prefix from the
    first JSONL record when the gitignored DB (which holds the prefix config)
    is absent.
    """
    if not seed_id:
        return None
    # Drop any child suffix: 'seeds-155.1' -> 'seeds-155'.
    top_level = seed_id.split(".", 1)[0]
    # The trailing '-'-delimited segment must be the sequence number.
    if parse_sequential_id(top_level) is None:
        return None
    prefix = top_level.rsplit("-", 1)[0]
    if not is_valid_prefix(prefix):
        return None
    return prefix


@dataclass(frozen=True)
class BodyRefChange:
    """A single ID reference change inside a seed's body field."""

    seed_id: str
    field: str  # "title" | "content" | "resolution"
    old_snippet: str
    new_snippet: str


# Allow override via environment variable for testing/development
SEEDS_DIR = os.environ.get("SEEDS_DIR", ".seeds")
DB_FILE = "seeds.db"

# Gitignore template for .seeds/ directory (following beads' pattern).
# Ignores SQLite DB and runtime files; JSONL is tracked by git by default.
SEEDS_GITIGNORE = """\
# SQLite databases
*.db
*.db-journal
*.db-wal
*.db-shm
"""


def find_seeds_dir() -> Path | None:
    """Find the .seeds directory by walking up the directory tree.

    Returns the path to the .seeds directory if found, None otherwise.
    Searches from current directory up to filesystem root.
    """
    current = Path.cwd()
    while True:
        seeds_dir = current / SEEDS_DIR
        if seeds_dir.is_dir():
            return seeds_dir
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            return None
        current = parent


SCHEMA = """
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

CREATE INDEX IF NOT EXISTS idx_seeds_status ON seeds(status);
CREATE INDEX IF NOT EXISTS idx_seeds_type ON seeds(seed_type);
CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(rel_type);

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

PREFIX_CONFIG_KEY = "prefix"

# FTS5 virtual table for full-text search across seeds.
FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS seeds_fts USING fts5(
    id UNINDEXED,
    title,
    content,
    tags,
    resolution,
    tokenize='porter unicode61'
);
"""

# Triggers to keep FTS index in sync with seed changes.
FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS seeds_fts_insert AFTER INSERT ON seeds
BEGIN
    INSERT INTO seeds_fts(id, title, content, tags, resolution)
    VALUES (
        NEW.id, NEW.title,
        COALESCE(NEW.content, ''), COALESCE(NEW.tags, ''), COALESCE(NEW.resolution, '')
    );
END;

CREATE TRIGGER IF NOT EXISTS seeds_fts_update AFTER UPDATE ON seeds
BEGIN
    DELETE FROM seeds_fts WHERE id = OLD.id;
    INSERT INTO seeds_fts(id, title, content, tags, resolution)
    VALUES (
        NEW.id, NEW.title,
        COALESCE(NEW.content, ''), COALESCE(NEW.tags, ''), COALESCE(NEW.resolution, '')
    );
END;

CREATE TRIGGER IF NOT EXISTS seeds_fts_delete AFTER DELETE ON seeds
BEGIN
    DELETE FROM seeds_fts WHERE id = OLD.id;
END;
"""


def _datetime_to_str(dt: datetime | None) -> str | None:
    """Convert datetime to ISO format string."""
    if dt is None:
        return None
    return dt.isoformat()


def _str_to_datetime(s: str | None) -> datetime | None:
    """Convert ISO format string to datetime."""
    if s is None:
        return None
    return datetime.fromisoformat(s)


class Database:
    """SQLite database for seeds."""

    def __init__(self, path: Path | None = None):
        """Initialize database connection.

        Args:
            path: Path to database file. If None, uses .seeds/seeds.db in cwd.
        """
        if path is None:
            path = Path.cwd() / SEEDS_DIR / DB_FILE
        self.path = path
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.path)
            self._conn.row_factory = sqlite3.Row
            self._migrate_add_resolution(self._conn)
            self._migrate_add_config(self._conn)
        return self._conn

    def init(self, prefix: str | None = None) -> None:
        """Initialize database schema and .seeds/.gitignore.

        Args:
            prefix: Optional project prefix to store in the config table.
                If None, the prefix stays unset and callers fall back to
                DEFAULT_PREFIX until rename-prefix or auto-derive sets it.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        conn.executescript(SCHEMA)
        conn.executescript(FTS_SCHEMA)
        conn.executescript(FTS_TRIGGERS)
        conn.commit()
        self._migrate_add_resolution(conn)
        self._migrate_add_config(conn)

        if prefix is not None:
            self.set_prefix(prefix)

        # Create .gitignore inside .seeds/ (like beads' .beads/.gitignore)
        # Ignores SQLite DB and runtime files; JSONL is tracked by default.
        gitignore_path = self.path.parent / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(SEEDS_GITIGNORE)

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _migrate_add_resolution(self, conn: sqlite3.Connection) -> None:
        """Add resolution column if missing (migration for existing DBs)."""
        # Check if seeds table exists (won't on fresh init before schema creation)
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='seeds'"
        ).fetchone()
        if table_exists is None:
            return
        columns = [
            row[1] for row in conn.execute("PRAGMA table_info(seeds)").fetchall()
        ]
        if "resolution" not in columns:
            conn.execute("ALTER TABLE seeds ADD COLUMN resolution TEXT DEFAULT ''")
            conn.commit()

    def _migrate_add_config(self, conn: sqlite3.Connection) -> None:
        """Add the config key/value table if missing (migration for older DBs)."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.commit()

    # --- Config / prefix ---

    def get_config(self, key: str, default: str | None = None) -> str | None:
        """Read a config value by key, returning ``default`` if not set."""
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        value: str = row["value"]
        return value

    def set_config(self, key: str, value: str) -> None:
        """Set or replace a config value."""
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()

    def get_prefix(self) -> str:
        """Return the configured project prefix, or DEFAULT_PREFIX if unset."""
        value = self.get_config(PREFIX_CONFIG_KEY)
        if value and is_valid_prefix(value):
            return value
        return DEFAULT_PREFIX

    def has_prefix_configured(self) -> bool:
        """Return True if the prefix has been explicitly set in config."""
        return self.get_config(PREFIX_CONFIG_KEY) is not None

    def set_prefix(self, prefix: str) -> None:
        """Validate and store the project prefix in config.

        Does not rewrite existing IDs — use :meth:`rename_prefix` for that.
        """
        if not is_valid_prefix(prefix):
            raise ValueError(
                f"Invalid prefix {prefix!r}: must start with a lowercase letter "
                "and contain only lowercase letters, digits, and hyphens."
            )
        self.set_config(PREFIX_CONFIG_KEY, prefix)

    def is_initialized(self) -> bool:
        """Check if database exists and is initialized."""
        return self.path.exists()

    def next_id(self, prefix: str | None = None) -> str:
        """Generate the next sequential ID like 'myproj-1', 'myproj-2', etc.

        Scans all existing IDs to find the current max sequential number.
        If ``prefix`` is None, the configured project prefix is used
        (falling back to DEFAULT_PREFIX when no config entry exists).
        """
        if prefix is None:
            prefix = self.get_prefix()
        conn = self._get_conn()
        rows = conn.execute("SELECT id FROM seeds").fetchall()

        max_num = 0
        for row in rows:
            num = parse_sequential_id(row["id"])
            if num is not None and num > max_num:
                max_num = num

        return f"{prefix}-{max_num + 1}"

    # --- Seed operations ---

    def _row_to_seed(self, row: sqlite3.Row) -> Seed:
        """Convert database row to Seed object."""
        return Seed(
            id=row["id"],
            title=row["title"],
            content=row["content"] or "",
            status=SeedStatus(row["status"]),
            seed_type=SeedType(row["seed_type"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=_str_to_datetime(row["created_at"]) or now_utc(),
            updated_at=_str_to_datetime(row["updated_at"]) or now_utc(),
            resolved_at=_str_to_datetime(row["resolved_at"]),
            resolution=row["resolution"] if "resolution" in row.keys() else "",  # noqa: SIM118
        )

    def create_seed(self, seed: Seed) -> Seed:
        """Insert a new seed into the database."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO seeds (
                id, title, content, status, seed_type,
                tags, created_at, updated_at, resolved_at, resolution
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                seed.id,
                seed.title,
                seed.content,
                seed.status.value,
                seed.seed_type.value,
                json.dumps(seed.tags),
                _datetime_to_str(seed.created_at),
                _datetime_to_str(seed.updated_at),
                _datetime_to_str(seed.resolved_at),
                seed.resolution,
            ),
        )
        conn.commit()
        return seed

    def get_seed(self, seed_id: str) -> Seed | None:
        """Get a seed by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM seeds WHERE id = ?", (seed_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_seed(row)

    def update_seed(self, seed: Seed, touch: bool = True) -> Seed:
        """Update an existing seed.

        By default (``touch=True``) the seed's ``updated_at`` is force-bumped
        to the current time, matching every interactive edit path. Pass
        ``touch=False`` to write the seed's existing ``updated_at`` verbatim —
        used by JSONL import, which must preserve the source timestamp so that
        last-write-wins comparisons stay meaningful across round-trips.
        """
        if touch:
            seed.updated_at = now_utc()
        conn = self._get_conn()
        conn.execute(
            """
            UPDATE seeds SET
                title = ?, content = ?, status = ?, seed_type = ?,
                tags = ?, updated_at = ?, resolved_at = ?, resolution = ?
            WHERE id = ?
            """,
            (
                seed.title,
                seed.content,
                seed.status.value,
                seed.seed_type.value,
                json.dumps(seed.tags),
                _datetime_to_str(seed.updated_at),
                _datetime_to_str(seed.resolved_at),
                seed.resolution,
                seed.id,
            ),
        )
        conn.commit()
        return seed

    def delete_seed(self, seed_id: str) -> bool:
        """Delete a seed by ID. Returns True if deleted.

        Also cascade-deletes relationships involving this seed.
        """
        conn = self._get_conn()
        # Cascade-delete relationships where this seed is source or target
        conn.execute(
            "DELETE FROM relationships WHERE source_id = ? OR target_id = ?",
            (seed_id, seed_id),
        )
        result = conn.execute("DELETE FROM seeds WHERE id = ?", (seed_id,))
        conn.commit()
        return result.rowcount > 0

    def list_seeds(
        self,
        status: SeedStatus | None = None,
        seed_type: SeedType | None = None,
        tag: str | None = None,
        include_terminal: bool = False,
        since: datetime | None = None,
        sort_by: str = "created",
    ) -> list[Seed]:
        """List seeds with optional filters.

        ``since`` filters to seeds whose ``updated_at`` is on or after the
        given datetime. ``sort_by`` is ``'created'`` (default, mirrors prior
        behavior) or ``'updated'``; both sort descending.
        """
        conn = self._get_conn()
        query = "SELECT * FROM seeds WHERE 1=1"
        params: list[str] = []

        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        elif not include_terminal:
            # Exclude resolved and abandoned by default
            query += " AND status NOT IN (?, ?)"
            params.extend([SeedStatus.RESOLVED.value, SeedStatus.ABANDONED.value])

        if seed_type is not None:
            query += " AND seed_type = ?"
            params.append(seed_type.value)

        if tag is not None:
            # Search in JSON array
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')

        if since is not None:
            query += " AND updated_at >= ?"
            params.append(_datetime_to_str(since) or "")

        if sort_by == "updated":
            query += " ORDER BY updated_at DESC"
        elif sort_by == "created":
            query += " ORDER BY created_at DESC"
        else:
            raise ValueError(f"sort_by must be 'created' or 'updated', got {sort_by!r}")

        rows = conn.execute(query, params).fetchall()
        return [self._row_to_seed(row) for row in rows]

    def get_children(self, parent_id: str) -> list[Seed]:
        """Get direct children of a seed."""
        conn = self._get_conn()
        # Children have IDs like 'parent_id.N'
        pattern = f"{parent_id}.%"
        rows = conn.execute(
            """
            SELECT * FROM seeds
            WHERE id LIKE ? AND id NOT LIKE ?
            ORDER BY id
            """,
            (pattern, f"{parent_id}.%.%"),  # Exclude grandchildren
        ).fetchall()
        return [self._row_to_seed(row) for row in rows]

    def get_next_child_id(self, parent_id: str) -> str:
        """Generate the next child ID for a parent."""
        children = self.get_children(parent_id)
        if not children:
            return f"{parent_id}.1"

        # Find highest child number
        max_num = 0
        for child in children:
            suffix = child.id.split(".")[-1]
            try:
                num = int(suffix)
                max_num = max(max_num, num)
            except ValueError:
                pass

        return f"{parent_id}.{max_num + 1}"

    def is_blocked(self, seed_id: str) -> bool:
        """Check if a seed is blocked.

        A seed is blocked if it has unresolved children OR unresolved
        question-seeds (seeds linked via a 'questions' relationship).
        """
        children = self.get_children(seed_id)
        if any(not child.is_terminal() for child in children):
            return True

        # Check for unresolved question-seeds via relationships
        question_seeds = self.get_questions_for_seed(seed_id)
        return any(not qs.is_terminal() for qs in question_seeds)

    def get_blocked_seeds(self) -> list[Seed]:
        """Get all seeds that are blocked by unresolved children or questions."""
        all_seeds = self.list_seeds(include_terminal=False)
        blocked = []
        for seed in all_seeds:
            if self.is_blocked(seed.id):
                blocked.append(seed)
        return blocked

    # --- Relationship operations ---

    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationType = RelationType.RELATES_TO,
        created_at: datetime | None = None,
    ) -> Relationship:
        """Create a relationship between two seeds.

        For RELATES_TO (bidirectional), creates two rows (A→B and B→A).
        For directed types (QUESTIONS, ANSWERS), creates one row.

        Returns the relationship (source→target direction).
        """
        if created_at is None:
            created_at = now_utc()
        conn = self._get_conn()

        conn.execute(
            """
            INSERT OR IGNORE INTO relationships
                (source_id, target_id, rel_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (source_id, target_id, rel_type.value, _datetime_to_str(created_at)),
        )

        if rel_type == RelationType.RELATES_TO:
            # Bidirectional: also create reverse edge
            conn.execute(
                """
                INSERT OR IGNORE INTO relationships
                    (source_id, target_id, rel_type, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (target_id, source_id, rel_type.value, _datetime_to_str(created_at)),
            )

        conn.commit()
        return Relationship(
            source_id=source_id,
            target_id=target_id,
            rel_type=rel_type,
            created_at=created_at,
        )

    def get_relationships(
        self,
        seed_id: str,
        rel_type: RelationType | None = None,
        direction: str = "both",
    ) -> list[Relationship]:
        """Get relationships for a seed.

        Args:
            seed_id: The seed to query relationships for.
            rel_type: Filter by relationship type (None = all types).
            direction: 'outbound' (source=seed), 'inbound' (target=seed), or 'both'.

        Returns:
            List of Relationship objects.
        """
        conn = self._get_conn()
        conditions = []
        params: list[str] = []

        if direction == "outbound":
            conditions.append("source_id = ?")
            params.append(seed_id)
        elif direction == "inbound":
            conditions.append("target_id = ?")
            params.append(seed_id)
        else:  # both
            conditions.append("(source_id = ? OR target_id = ?)")
            params.extend([seed_id, seed_id])

        if rel_type is not None:
            conditions.append("rel_type = ?")
            params.append(rel_type.value)

        where_clause = " AND ".join(conditions)
        query = f"SELECT * FROM relationships WHERE {where_clause} ORDER BY created_at"
        rows = conn.execute(query, params).fetchall()

        return [
            Relationship(
                source_id=row["source_id"],
                target_id=row["target_id"],
                rel_type=RelationType(row["rel_type"]),
                created_at=_str_to_datetime(row["created_at"]) or now_utc(),
            )
            for row in rows
        ]

    def delete_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationType = RelationType.RELATES_TO,
    ) -> bool:
        """Delete a relationship between two seeds.

        For RELATES_TO (bidirectional), deletes both directions.
        Returns True if any rows were deleted.
        """
        conn = self._get_conn()
        delete_sql = (
            "DELETE FROM relationships"
            " WHERE source_id = ? AND target_id = ? AND rel_type = ?"
        )
        result = conn.execute(
            delete_sql,
            (source_id, target_id, rel_type.value),
        )
        deleted = result.rowcount > 0

        if rel_type == RelationType.RELATES_TO:
            result2 = conn.execute(
                delete_sql,
                (target_id, source_id, rel_type.value),
            )
            deleted = deleted or result2.rowcount > 0

        conn.commit()
        return deleted

    def get_questions_for_seed(self, seed_id: str) -> list[Seed]:
        """Get question-seeds linked to a seed via 'questions' relationships.

        Returns Seed objects (of type=question) that question the given seed.
        """
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT s.* FROM seeds s
            JOIN relationships r ON s.id = r.source_id
            WHERE r.target_id = ? AND r.rel_type = ?
            ORDER BY s.created_at
            """,
            (seed_id, RelationType.QUESTIONS.value),
        ).fetchall()
        return [self._row_to_seed(row) for row in rows]

    # --- Migration ---

    def migrate_to_relationships(self) -> dict[str, int]:
        """Migrate from legacy questions table and related_to to relationships.

        This migration:
        1. Creates relationships table if needed
        2. Converts related_to JSON arrays to bidirectional relates-to relationships
        3. Converts questions to question-type seeds with 'questions' relationships

        Returns dict with counts: {'related_to': N, 'questions': N}
        """
        conn = self._get_conn()
        counts = {"related_to": 0, "questions": 0}

        # Ensure relationships table exists
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                rel_type TEXT NOT NULL DEFAULT 'relates-to',
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES seeds(id),
                FOREIGN KEY (target_id) REFERENCES seeds(id),
                UNIQUE(source_id, target_id, rel_type)
            )
            """
        )

        # Step 1: Migrate related_to arrays to relationships
        # Check if related_to column exists
        columns = [
            row[1] for row in conn.execute("PRAGMA table_info(seeds)").fetchall()
        ]
        if "related_to" in columns:
            rows = conn.execute(
                "SELECT id, related_to, created_at FROM seeds"
                " WHERE related_to != '[]' AND related_to IS NOT NULL"
            ).fetchall()
            for row in rows:
                related_ids = json.loads(row["related_to"]) if row["related_to"] else []
                for related_id in related_ids:
                    # Create bidirectional relates-to edges
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO relationships
                            (source_id, target_id, rel_type, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            row["id"],
                            related_id,
                            RelationType.RELATES_TO.value,
                            row["created_at"],
                        ),
                    )
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO relationships
                            (source_id, target_id, rel_type, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            related_id,
                            row["id"],
                            RelationType.RELATES_TO.value,
                            row["created_at"],
                        ),
                    )
                    counts["related_to"] += 1

        # Step 2: Migrate questions to seeds + relationships
        # Check if questions table exists
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='questions'"
        ).fetchone()
        if table_exists:
            q_rows = conn.execute("SELECT * FROM questions").fetchall()
            for q in q_rows:
                # Map question status to seed status
                q_status = q["status"]
                if q_status == "open":
                    seed_status = SeedStatus.CAPTURED.value
                elif q_status == "answered":
                    seed_status = SeedStatus.RESOLVED.value
                elif q_status == "deferred":
                    seed_status = SeedStatus.DEFERRED.value
                else:
                    seed_status = SeedStatus.CAPTURED.value

                # Generate a new seed-prefixed ID for the migrated question
                new_id = self.next_id()

                resolved_at = q["answered_at"] if q_status == "answered" else None

                # Create question as a seed
                conn.execute(
                    """
                    INSERT OR IGNORE INTO seeds (
                        id, title, content, status, seed_type,
                        tags, created_at, updated_at, resolved_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id,
                        q["text"],
                        q["answer"] or "",
                        seed_status,
                        SeedType.QUESTION.value,
                        "[]",
                        q["created_at"],
                        q["created_at"],
                        resolved_at,
                    ),
                )

                # Create 'questions' relationship: question-seed → parent seed
                conn.execute(
                    """
                    INSERT OR IGNORE INTO relationships
                        (source_id, target_id, rel_type, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        new_id,
                        q["seed_id"],
                        RelationType.QUESTIONS.value,
                        q["created_at"],
                    ),
                )
                counts["questions"] += 1

        conn.commit()
        return counts

    def migrate_to_sequential_ids(self, prefix: str | None = None) -> dict[str, str]:
        """Migrate all hex-hash IDs to sequential IDs.

        Assigns sequential IDs in creation order. Children keep their
        parent relationship (seed-81a4.1 becomes <prefix>-N.M).

        If ``prefix`` is None, uses the configured project prefix.

        Returns the old-to-new ID mapping.
        """
        if prefix is None:
            prefix = self.get_prefix()
        conn = self._get_conn()

        # Check if already migrated: if there are no hex-style top-level IDs, skip
        rows = conn.execute("SELECT id FROM seeds").fetchall()
        has_hex_ids = False
        for row in rows:
            sid = row["id"]
            if "." in sid:
                continue  # Skip children
            if parse_sequential_id(sid) is None:
                has_hex_ids = True
                break
        if not has_hex_ids and len(rows) > 0:
            return {}  # All top-level IDs are already sequential

        # Get all seeds ordered by created_at
        all_seeds = conn.execute(
            "SELECT id, created_at FROM seeds ORDER BY created_at"
        ).fetchall()

        # Separate top-level seeds from children
        top_level = []
        children = []  # (id, parent_old_id, child_suffix)
        for row in all_seeds:
            sid = row["id"]
            if "." in sid:
                # It's a child — store full dotted suffix path after top-level parent
                top_parent = sid.split(".")[0]
                dot_suffix = sid[len(top_parent) :]  # e.g., ".1" or ".1.1"
                children.append((sid, top_parent, dot_suffix))
            else:
                top_level.append(sid)

        # Build old -> new mapping for top-level seeds
        id_map: dict[str, str] = {}
        for i, old_id in enumerate(top_level, start=1):
            new_id = f"{prefix}-{i}"
            id_map[old_id] = new_id

        # Map children based on their parent's new ID
        for old_id, top_parent, dot_suffix in children:
            if top_parent in id_map:
                new_id = f"{id_map[top_parent]}{dot_suffix}"
                id_map[old_id] = new_id

        # Apply the mapping in a transaction
        # Disable foreign keys temporarily to allow ID updates
        conn.execute("PRAGMA foreign_keys = OFF")

        # Use a temp suffix to avoid primary key collisions during rename
        temp_map = {}
        for old_id, new_id in id_map.items():
            temp_id = f"__temp__{new_id}"
            temp_map[temp_id] = new_id
            conn.execute("UPDATE seeds SET id = ? WHERE id = ?", (temp_id, old_id))
            conn.execute(
                "UPDATE relationships SET source_id = ? WHERE source_id = ?",
                (temp_id, old_id),
            )
            conn.execute(
                "UPDATE relationships SET target_id = ? WHERE target_id = ?",
                (temp_id, old_id),
            )

        # Now rename from temp to final
        for temp_id, new_id in temp_map.items():
            conn.execute("UPDATE seeds SET id = ? WHERE id = ?", (new_id, temp_id))
            conn.execute(
                "UPDATE relationships SET source_id = ? WHERE source_id = ?",
                (new_id, temp_id),
            )
            conn.execute(
                "UPDATE relationships SET target_id = ? WHERE target_id = ?",
                (new_id, temp_id),
            )

        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()

        # Rebuild FTS index with new IDs
        self.ensure_fts()
        self.rebuild_fts()

        return id_map

    def rename_prefix(
        self,
        new_prefix: str,
        old_prefix: str | None = None,
        rewrite_bodies: bool = True,
        dry_run: bool = False,
    ) -> tuple[dict[str, str], list[BodyRefChange]]:
        """Rewrite all IDs that use ``old_prefix`` to use ``new_prefix``.

        Updates seeds.id, relationships.source_id, relationships.target_id,
        and (when ``rewrite_bodies`` is True) ID references inside each
        seed's title/content/resolution. Stores ``new_prefix`` in config.

        If ``old_prefix`` is None, uses the currently configured prefix
        (falling back to DEFAULT_PREFIX). IDs whose top-level segment does
        not match ``old_prefix`` are left untouched, so this is safe to run
        on databases containing legacy hex IDs alongside prefixed ones.

        When ``dry_run`` is True, no writes happen — the return value
        reports what *would* change, including snippet previews for every
        body reference. Useful for ``seeds rename-prefix --dry-run``.

        Returns ``(id_map, body_changes)``:
            ``id_map``: dict mapping each old top-level/child ID to its new
                form. Empty when no IDs matched.
            ``body_changes``: list of :class:`BodyRefChange` rows, one per
                in-text reference (always populated, even on dry-run).
        """
        if not is_valid_prefix(new_prefix):
            raise ValueError(
                f"Invalid prefix {new_prefix!r}: must start with a lowercase "
                "letter and contain only lowercase letters, digits, and hyphens."
            )
        if old_prefix is None:
            old_prefix = self.get_prefix()

        # Renaming to the current prefix is a no-op (config still gets touched).
        if old_prefix == new_prefix:
            if not dry_run:
                self.set_config(PREFIX_CONFIG_KEY, new_prefix)
            return {}, []

        conn = self._get_conn()
        rows = conn.execute("SELECT id FROM seeds").fetchall()

        old_lead = f"{old_prefix}-"
        id_map: dict[str, str] = {}
        for row in rows:
            sid = row["id"]
            # Top-level prefix segment is everything before the first '.'
            top = sid.split(".", 1)[0]
            if not top.startswith(old_lead):
                continue
            # Confirm the segment after the prefix is purely numeric so we
            # don't accidentally rename something like 'seeds-experiment'.
            try:
                int(top[len(old_lead) :])
            except ValueError:
                continue
            new_id = f"{new_prefix}{sid[len(old_prefix) :]}"
            id_map[sid] = new_id

        # Body rewriting can fire even when no IDs match (text references to
        # deleted seeds), and we always *compute* the changes so callers can
        # preview on dry-run. ``_apply_body_id_rewrites`` does the writes
        # itself unless ``dry_run`` is True.
        body_changes: list[BodyRefChange] = []
        if rewrite_bodies:
            body_changes = self._apply_body_id_rewrites(
                old_prefix, new_prefix, dry_run=dry_run
            )

        if not id_map:
            if not dry_run:
                self.set_config(PREFIX_CONFIG_KEY, new_prefix)
                if body_changes:
                    self.ensure_fts()
                    self.rebuild_fts()
            return {}, body_changes

        # Guard against collisions: if any new_id already exists in the DB and
        # is NOT being renamed away, the rewrite would create a duplicate PK.
        existing_ids = {row["id"] for row in rows}
        renamed_sources = set(id_map.keys())
        for new_id in id_map.values():
            if new_id in existing_ids and new_id not in renamed_sources:
                raise ValueError(
                    f"Renaming '{old_prefix}' to '{new_prefix}' would collide "
                    f"with existing ID {new_id!r}. Database has mixed prefixes; "
                    "resolve manually before retrying."
                )

        if dry_run:
            return id_map, body_changes

        # Two-phase rewrite via temp IDs to avoid PK collisions.
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            temp_map: dict[str, str] = {}
            for old_id, new_id in id_map.items():
                temp_id = f"__rename__{new_id}"
                temp_map[temp_id] = new_id
                conn.execute("UPDATE seeds SET id = ? WHERE id = ?", (temp_id, old_id))
                conn.execute(
                    "UPDATE relationships SET source_id = ? WHERE source_id = ?",
                    (temp_id, old_id),
                )
                conn.execute(
                    "UPDATE relationships SET target_id = ? WHERE target_id = ?",
                    (temp_id, old_id),
                )

            for temp_id, new_id in temp_map.items():
                conn.execute("UPDATE seeds SET id = ? WHERE id = ?", (new_id, temp_id))
                conn.execute(
                    "UPDATE relationships SET source_id = ? WHERE source_id = ?",
                    (new_id, temp_id),
                )
                conn.execute(
                    "UPDATE relationships SET target_id = ? WHERE target_id = ?",
                    (new_id, temp_id),
                )
        finally:
            conn.execute("PRAGMA foreign_keys = ON")

        self.set_config(PREFIX_CONFIG_KEY, new_prefix)
        conn.commit()

        self.ensure_fts()
        self.rebuild_fts()

        return id_map, body_changes

    def _apply_body_id_rewrites(
        self, old_prefix: str, new_prefix: str, dry_run: bool = False
    ) -> list[BodyRefChange]:
        """Rewrite ID references in seed text fields (title/content/resolution).

        Always computes the list of changes (with snippet previews) so callers
        can preview the result. Performs the writes unless ``dry_run`` is True.
        """
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, title, content, resolution FROM seeds"
        ).fetchall()

        changes: list[BodyRefChange] = []
        for row in rows:
            title = row["title"] or ""
            content = row["content"] or ""
            resolution = row["resolution"] or ""

            new_title, c1 = rewrite_id_refs(title, old_prefix, new_prefix)
            new_content, c2 = rewrite_id_refs(content, old_prefix, new_prefix)
            new_resolution, c3 = rewrite_id_refs(resolution, old_prefix, new_prefix)

            if c1 == 0 and c2 == 0 and c3 == 0:
                continue

            for field_name, original in (
                ("title", title),
                ("content", content),
                ("resolution", resolution),
            ):
                for old_snip, new_snip in iter_id_ref_snippets(
                    original, old_prefix, new_prefix
                ):
                    changes.append(
                        BodyRefChange(
                            seed_id=row["id"],
                            field=field_name,
                            old_snippet=old_snip,
                            new_snippet=new_snip,
                        )
                    )

            if not dry_run:
                conn.execute(
                    "UPDATE seeds SET title = ?, content = ?, "
                    "resolution = ? WHERE id = ?",
                    (new_title, new_content, new_resolution, row["id"]),
                )

        return changes

    # --- Search operations ---

    def ensure_fts(self) -> None:
        """Ensure FTS tables and triggers exist, creating and populating if needed.

        Safe to call on existing databases — migrates them to FTS support.
        Rebuilds FTS if schema has changed (e.g., new columns added).
        """
        conn = self._get_conn()
        # Check if FTS table exists
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='seeds_fts'"
        ).fetchone()
        if row is None:
            conn.executescript(FTS_SCHEMA)
            conn.executescript(FTS_TRIGGERS)
            self.rebuild_fts()
        else:
            # Check if FTS schema has the resolution column; rebuild if not
            fts_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='seeds_fts'"
            ).fetchone()
            if fts_sql and "resolution" not in fts_sql["sql"]:
                # Drop old FTS table and triggers, recreate with new schema
                conn.executescript("DROP TABLE IF EXISTS seeds_fts;")
                conn.executescript("DROP TRIGGER IF EXISTS seeds_fts_insert;")
                conn.executescript("DROP TRIGGER IF EXISTS seeds_fts_update;")
                conn.executescript("DROP TRIGGER IF EXISTS seeds_fts_delete;")
                conn.executescript(FTS_SCHEMA)
                conn.executescript(FTS_TRIGGERS)
                self.rebuild_fts()

    def rebuild_fts(self) -> None:
        """Rebuild FTS index from current seed data."""
        conn = self._get_conn()
        conn.execute("DELETE FROM seeds_fts")
        conn.execute(
            """
            INSERT INTO seeds_fts(id, title, content, tags, resolution)
            SELECT
                s.id, s.title,
                COALESCE(s.content, ''), COALESCE(s.tags, ''),
                COALESCE(s.resolution, '')
            FROM seeds s
            """
        )
        conn.commit()

    def suggest(
        self,
        text: str,
        *,
        limit: int = 5,
        open_only: bool = False,
    ) -> list[ScoredSeed]:
        """Rank existing seeds by relevance to natural-language ``text``.

        Combines three signals:
          - FTS5 BM25 score over title/content/tags/resolution
          - Tag-overlap boost (project tags mentioned in ``text``)
          - Small recency boost (seeds touched within 30 days)

        Returns top ``limit`` results, sorted by combined score descending.
        Drops any result below half the top score (dynamic noise floor).

        By default includes resolved/abandoned seeds — the question is
        'does this idea exist in our deliberation history?', not 'what could
        I update?'. Set ``open_only=True`` to restrict to actionable seeds.
        """
        from seeds.models import tokenize_for_suggest

        tokens = tokenize_for_suggest(text)
        if not tokens:
            return []

        self.ensure_fts()
        conn = self._get_conn()

        # OR the tokens together — BM25 ranks; we'll post-filter.
        fts_query = " OR ".join(tokens)

        sql = """
            SELECT s.*,
                   bm25(seeds_fts) AS bm25_score,
                   snippet(seeds_fts, 2, '«', '»', '…', 12) AS snip
            FROM seeds s
            JOIN seeds_fts fts ON s.id = fts.id
            WHERE seeds_fts MATCH ?
        """
        params: list[str] = [fts_query]
        if open_only:
            sql += " AND s.status NOT IN (?, ?)"
            params.extend([SeedStatus.RESOLVED.value, SeedStatus.ABANDONED.value])
        sql += " ORDER BY bm25_score LIMIT 200"  # cap candidate pool

        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            # FTS5 can reject malformed queries (e.g. only punctuation tokens).
            return []
        if not rows:
            return []

        # Project tags mentioned in input → tag-overlap boost
        project_tags = set(self.get_all_tags())
        token_set = set(tokens)
        candidate_tags = project_tags & token_set

        now = now_utc()
        candidates: list[ScoredSeed] = []
        for row in rows:
            seed = self._row_to_seed(row)
            # BM25 returns negative numbers (lower = better). Flip sign.
            base = -float(row["bm25_score"])
            # Multiplicative boosts so they scale with FTS strength and don't
            # punch holes through the dynamic noise floor on small matches.
            overlap = len(set(seed.tags) & candidate_tags)
            tag_mult = 1.0 + 0.25 * overlap
            days_old = (now - seed.updated_at).days if seed.updated_at else 9999
            recency_mult = 1.1 if days_old < 30 else 1.0
            score = base * tag_mult * recency_mult
            candidates.append(
                ScoredSeed(seed=seed, score=score, snippet=row["snip"] or "")
            )

        candidates.sort(key=lambda c: c.score, reverse=True)

        # Dynamic noise floor: drop hits below half the top score.
        top = candidates[0].score
        floor = top / 2 if top > 0 else 0.0
        kept = [c for c in candidates if c.score >= floor]
        return kept[:limit]

    def search(self, query: str, include_terminal: bool = False) -> list[Seed]:
        """Full-text search across seed titles, content, and tags.

        Args:
            query: FTS5 query string (supports AND, OR, NOT, prefix*, "phrases").
            include_terminal: If True, include resolved/abandoned seeds.

        Returns:
            Seeds matching the query, ordered by relevance.
        """
        self.ensure_fts()
        conn = self._get_conn()

        sql = """
            SELECT s.* FROM seeds s
            JOIN seeds_fts fts ON s.id = fts.id
            WHERE seeds_fts MATCH ?
        """
        params: list[str] = [query]

        if not include_terminal:
            sql += " AND s.status NOT IN (?, ?)"
            params.extend([SeedStatus.RESOLVED.value, SeedStatus.ABANDONED.value])

        sql += " ORDER BY rank"

        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_seed(row) for row in rows]

    # --- Tag operations ---

    def get_all_tags(self) -> list[str]:
        """Get all unique tags used across seeds."""
        conn = self._get_conn()
        rows = conn.execute("SELECT tags FROM seeds").fetchall()
        all_tags: set[str] = set()
        for row in rows:
            if row["tags"]:
                tags = json.loads(row["tags"])
                all_tags.update(tags)
        return sorted(all_tags)
