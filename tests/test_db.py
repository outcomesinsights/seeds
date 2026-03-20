"""Tests for seeds database layer."""

import os
import sqlite3
import tempfile

from seeds.db import SCHEMA, Database, find_seeds_dir
from seeds.models import (
    Relationship,
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
)

# Legacy v1 schema for migration tests — has questions table and related_to column
V1_SCHEMA = """
CREATE TABLE IF NOT EXISTS seeds (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'captured',
    seed_type TEXT NOT NULL DEFAULT 'idea',
    tags TEXT DEFAULT '[]',
    related_to TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    seed_id TEXT NOT NULL,
    text TEXT NOT NULL,
    answer TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    answered_at TEXT,
    FOREIGN KEY (seed_id) REFERENCES seeds(id)
);

CREATE INDEX IF NOT EXISTS idx_seeds_status ON seeds(status);
CREATE INDEX IF NOT EXISTS idx_seeds_type ON seeds(seed_type);
CREATE INDEX IF NOT EXISTS idx_questions_seed ON questions(seed_id);
CREATE INDEX IF NOT EXISTS idx_questions_status ON questions(status);
"""


class TestDatabaseInit:
    """Tests for database initialization."""

    def test_init_creates_directory(self, temp_dir):
        """Verify init creates .seeds directory if needed."""
        db_path = temp_dir / ".seeds" / "seeds.db"
        db = Database(path=db_path)
        assert not db_path.exists()
        db.init()
        assert db_path.exists()
        db.close()

    def test_is_initialized_false_before_init(self, temp_dir):
        """Verify is_initialized returns False before init."""
        db_path = temp_dir / ".seeds" / "seeds.db"
        db = Database(path=db_path)
        assert db.is_initialized() is False
        db.close()

    def test_is_initialized_true_after_init(self, db):
        """Verify is_initialized returns True after init."""
        assert db.is_initialized() is True


class TestSeedCRUD:
    """Tests for seed CRUD operations."""

    def test_create_and_get_seed(self, db, sample_seed):
        """Verify seed can be created and retrieved."""
        db.create_seed(sample_seed)
        retrieved = db.get_seed(sample_seed.id)

        assert retrieved is not None
        assert retrieved.id == sample_seed.id
        assert retrieved.title == sample_seed.title
        assert retrieved.content == sample_seed.content
        assert retrieved.status == sample_seed.status
        assert retrieved.seed_type == sample_seed.seed_type
        assert retrieved.tags == sample_seed.tags

    def test_get_nonexistent_seed_returns_none(self, db):
        """Verify get_seed returns None for missing ID."""
        result = db.get_seed("seed-nonexistent")
        assert result is None

    def test_update_seed(self, db, sample_seed):
        """Verify seed can be updated."""
        db.create_seed(sample_seed)

        sample_seed.title = "Updated Title"
        sample_seed.status = SeedStatus.EXPLORING
        sample_seed.tags = ["updated"]
        db.update_seed(sample_seed)

        retrieved = db.get_seed(sample_seed.id)
        assert retrieved.title == "Updated Title"
        assert retrieved.status == SeedStatus.EXPLORING
        assert retrieved.tags == ["updated"]

    def test_delete_seed(self, db, sample_seed):
        """Verify seed can be deleted."""
        db.create_seed(sample_seed)
        assert db.get_seed(sample_seed.id) is not None

        result = db.delete_seed(sample_seed.id)
        assert result is True
        assert db.get_seed(sample_seed.id) is None

    def test_delete_nonexistent_seed(self, db):
        """Verify deleting nonexistent seed returns False."""
        result = db.delete_seed("seed-nonexistent")
        assert result is False

    def test_delete_seed_deletes_relationships(self, db, sample_seed):
        """Verify deleting a seed also deletes its relationships."""
        db.create_seed(sample_seed)
        other = Seed(id="seed-other", title="Other")
        db.create_seed(other)
        db.create_relationship(sample_seed.id, other.id, RelationType.RELATES_TO)

        db.delete_seed(sample_seed.id)
        assert len(db.get_relationships(other.id)) == 0


class TestSeedListing:
    """Tests for seed listing and filtering."""

    def test_list_seeds_empty(self, db):
        """Verify list_seeds returns empty list when no seeds."""
        result = db.list_seeds()
        assert result == []

    def test_list_seeds_returns_all_non_terminal(self, db):
        """Verify list_seeds returns non-terminal seeds by default."""
        seeds = [
            Seed(id="seed-1", title="Captured", status=SeedStatus.CAPTURED),
            Seed(id="seed-2", title="Exploring", status=SeedStatus.EXPLORING),
            Seed(id="seed-3", title="Deferred", status=SeedStatus.DEFERRED),
            Seed(id="seed-4", title="Resolved", status=SeedStatus.RESOLVED),
            Seed(id="seed-5", title="Abandoned", status=SeedStatus.ABANDONED),
        ]
        for seed in seeds:
            db.create_seed(seed)

        result = db.list_seeds()
        ids = [s.id for s in result]
        assert "seed-1" in ids
        assert "seed-2" in ids
        assert "seed-3" in ids
        assert "seed-4" not in ids
        assert "seed-5" not in ids

    def test_list_seeds_include_terminal(self, db):
        """Verify include_terminal=True includes resolved/abandoned."""
        seeds = [
            Seed(id="seed-1", title="Captured", status=SeedStatus.CAPTURED),
            Seed(id="seed-2", title="Resolved", status=SeedStatus.RESOLVED),
        ]
        for seed in seeds:
            db.create_seed(seed)

        result = db.list_seeds(include_terminal=True)
        ids = [s.id for s in result]
        assert "seed-1" in ids
        assert "seed-2" in ids

    def test_list_seeds_filter_by_status(self, db):
        """Verify filtering by status works."""
        seeds = [
            Seed(id="seed-1", title="Captured", status=SeedStatus.CAPTURED),
            Seed(id="seed-2", title="Exploring", status=SeedStatus.EXPLORING),
        ]
        for seed in seeds:
            db.create_seed(seed)

        result = db.list_seeds(status=SeedStatus.CAPTURED)
        assert len(result) == 1
        assert result[0].id == "seed-1"

    def test_list_seeds_filter_by_type(self, db):
        """Verify filtering by type works."""
        seeds = [
            Seed(id="seed-1", title="Idea", seed_type=SeedType.IDEA),
            Seed(id="seed-2", title="Question", seed_type=SeedType.QUESTION),
        ]
        for seed in seeds:
            db.create_seed(seed)

        result = db.list_seeds(seed_type=SeedType.IDEA)
        assert len(result) == 1
        assert result[0].id == "seed-1"

    def test_list_seeds_filter_by_tag(self, db):
        """Verify filtering by tag works."""
        seeds = [
            Seed(id="seed-1", title="Tagged", tags=["important"]),
            Seed(id="seed-2", title="Not Tagged", tags=["other"]),
        ]
        for seed in seeds:
            db.create_seed(seed)

        result = db.list_seeds(tag="important")
        assert len(result) == 1
        assert result[0].id == "seed-1"


class TestSeedHierarchy:
    """Tests for parent-child hierarchy operations."""

    def test_get_children_empty(self, db, sample_seed):
        """Verify get_children returns empty list when no children."""
        db.create_seed(sample_seed)
        children = db.get_children(sample_seed.id)
        assert children == []

    def test_get_children_returns_direct_children(self, db):
        """Verify get_children returns only direct children, not grandchildren."""
        parent = Seed(id="seed-a1b2", title="Parent")
        child1 = Seed(id="seed-a1b2.1", title="Child 1")
        child2 = Seed(id="seed-a1b2.2", title="Child 2")
        grandchild = Seed(id="seed-a1b2.1.1", title="Grandchild")

        for seed in [parent, child1, child2, grandchild]:
            db.create_seed(seed)

        children = db.get_children("seed-a1b2")
        ids = [s.id for s in children]
        assert "seed-a1b2.1" in ids
        assert "seed-a1b2.2" in ids
        assert "seed-a1b2.1.1" not in ids

    def test_get_next_child_id_first_child(self, db):
        """Verify first child gets .1 suffix."""
        parent = Seed(id="seed-a1b2", title="Parent")
        db.create_seed(parent)

        next_id = db.get_next_child_id("seed-a1b2")
        assert next_id == "seed-a1b2.1"

    def test_get_next_child_id_subsequent_children(self, db):
        """Verify subsequent children get incrementing suffixes."""
        parent = Seed(id="seed-a1b2", title="Parent")
        child1 = Seed(id="seed-a1b2.1", title="Child 1")
        child2 = Seed(id="seed-a1b2.2", title="Child 2")

        for seed in [parent, child1, child2]:
            db.create_seed(seed)

        next_id = db.get_next_child_id("seed-a1b2")
        assert next_id == "seed-a1b2.3"

    def test_get_next_child_id_handles_gaps(self, db):
        """Verify next child ID handles gaps (deleted children)."""
        parent = Seed(id="seed-a1b2", title="Parent")
        child1 = Seed(id="seed-a1b2.1", title="Child 1")
        child3 = Seed(id="seed-a1b2.3", title="Child 3")  # Gap at .2

        for seed in [parent, child1, child3]:
            db.create_seed(seed)

        next_id = db.get_next_child_id("seed-a1b2")
        assert next_id == "seed-a1b2.4"  # Should be max + 1

    def test_get_next_child_id_non_numeric_suffix(self, db):
        """Verify next child ID handles non-numeric suffixes gracefully."""
        parent = Seed(id="seed-a1b2", title="Parent")
        # Child with a non-numeric suffix (edge case)
        child_weird = Seed(id="seed-a1b2.abc", title="Weird Child")
        child_normal = Seed(id="seed-a1b2.2", title="Normal Child")

        for seed in [parent, child_weird, child_normal]:
            db.create_seed(seed)

        next_id = db.get_next_child_id("seed-a1b2")
        assert next_id == "seed-a1b2.3"  # Should skip non-numeric, use max(2) + 1


class TestNextId:
    """Tests for sequential ID generation."""

    def test_next_id_empty_db(self, db):
        """Verify next_id returns 1 for empty database."""
        assert db.next_id() == "seeds-1"

    def test_next_id_increments(self, db):
        """Verify next_id increments from existing sequential IDs."""
        db.create_seed(Seed(id="seeds-1", title="First"))
        db.create_seed(Seed(id="seeds-2", title="Second"))
        assert db.next_id() == "seeds-3"

    def test_next_id_ignores_hex_ids(self, db):
        """Verify next_id ignores hex-hash IDs when computing max."""
        db.create_seed(Seed(id="seed-a1b2c3d4", title="Old hex"))
        db.create_seed(Seed(id="seeds-5", title="Sequential"))
        assert db.next_id() == "seeds-6"

    def test_next_id_ignores_children(self, db):
        """Verify next_id ignores child IDs (e.g., seeds-1.1)."""
        db.create_seed(Seed(id="seeds-1", title="Parent"))
        db.create_seed(Seed(id="seeds-1.1", title="Child"))
        assert db.next_id() == "seeds-2"

    def test_next_id_custom_prefix(self, db):
        """Verify next_id works with custom prefix."""
        db.create_seed(Seed(id="myproject-1", title="First"))
        assert db.next_id("myproject") == "myproject-2"


class TestMigrateToSequentialIds:
    """Tests for migrate_to_sequential_ids."""

    def test_migrate_basic(self, db):
        """Verify basic hex-to-sequential migration."""
        db.create_seed(Seed(id="seed-aaaa", title="First"))
        db.create_seed(Seed(id="seed-bbbb", title="Second"))

        id_map = db.migrate_to_sequential_ids()

        assert len(id_map) == 2
        # Both should now have sequential IDs
        assert db.get_seed("seeds-1") is not None
        assert db.get_seed("seeds-2") is not None
        # Old IDs should be gone
        assert db.get_seed("seed-aaaa") is None
        assert db.get_seed("seed-bbbb") is None

    def test_migrate_preserves_children(self, db):
        """Verify children keep parent relationship after migration."""
        db.create_seed(Seed(id="seed-aaaa", title="Parent"))
        db.create_seed(Seed(id="seed-aaaa.1", title="Child"))
        db.create_seed(Seed(id="seed-aaaa.2", title="Child 2"))

        id_map = db.migrate_to_sequential_ids()

        # Parent becomes seeds-1, children become seeds-1.1 and seeds-1.2
        assert db.get_seed("seeds-1") is not None
        assert db.get_seed("seeds-1.1") is not None
        assert db.get_seed("seeds-1.2") is not None
        assert id_map["seed-aaaa"] == "seeds-1"
        assert id_map["seed-aaaa.1"] == "seeds-1.1"

    def test_migrate_updates_relationships(self, db):
        """Verify relationships are updated with new IDs."""
        db.create_seed(Seed(id="seed-aaaa", title="A"))
        db.create_seed(Seed(id="seed-bbbb", title="B"))
        db.create_relationship("seed-aaaa", "seed-bbbb", RelationType.RELATES_TO)

        db.migrate_to_sequential_ids()

        # Relationship should reference new IDs
        rels = db.get_relationships("seeds-1", direction="outbound",
                                     rel_type=RelationType.RELATES_TO)
        assert len(rels) == 1
        assert rels[0].target_id == "seeds-2"

    def test_migrate_idempotent(self, db):
        """Verify migration is idempotent — skips if sequential IDs exist."""
        db.create_seed(Seed(id="seeds-1", title="Already sequential"))

        id_map = db.migrate_to_sequential_ids()
        assert id_map == {}  # No migration needed

    def test_migrate_preserves_data(self, db):
        """Verify migration preserves all seed fields."""
        db.create_seed(Seed(
            id="seed-aaaa",
            title="Important Decision",
            content="Detailed content",
            status=SeedStatus.EXPLORING,
            seed_type=SeedType.DECISION,
            tags=["important", "architecture"],
            resolution="",
        ))

        db.migrate_to_sequential_ids()

        seed = db.get_seed("seeds-1")
        assert seed.title == "Important Decision"
        assert seed.content == "Detailed content"
        assert seed.status == SeedStatus.EXPLORING
        assert seed.seed_type == SeedType.DECISION
        assert seed.tags == ["important", "architecture"]


class TestBlockedState:
    """Tests for blocked state derivation."""

    def test_is_blocked_false_with_no_children(self, db):
        """Verify seed without children is not blocked."""
        seed = Seed(id="seed-a1b2", title="No Children")
        db.create_seed(seed)

        assert db.is_blocked("seed-a1b2") is False

    def test_is_blocked_false_with_all_resolved_children(self, db):
        """Verify seed with all resolved children is not blocked."""
        parent = Seed(id="seed-a1b2", title="Parent")
        child1 = Seed(id="seed-a1b2.1", title="Child 1", status=SeedStatus.RESOLVED)
        child2 = Seed(id="seed-a1b2.2", title="Child 2", status=SeedStatus.ABANDONED)

        for seed in [parent, child1, child2]:
            db.create_seed(seed)

        assert db.is_blocked("seed-a1b2") is False

    def test_is_blocked_true_with_unresolved_children(self, db):
        """Verify seed with unresolved children is blocked."""
        parent = Seed(id="seed-a1b2", title="Parent")
        child1 = Seed(id="seed-a1b2.1", title="Child 1", status=SeedStatus.RESOLVED)
        child2 = Seed(id="seed-a1b2.2", title="Child 2", status=SeedStatus.EXPLORING)

        for seed in [parent, child1, child2]:
            db.create_seed(seed)

        assert db.is_blocked("seed-a1b2") is True

    def test_get_blocked_seeds(self, db):
        """Verify get_blocked_seeds returns only blocked seeds."""
        # Blocked parent with unresolved child
        blocked = Seed(id="seed-b1", title="Blocked")
        blocked_child = Seed(
            id="seed-b1.1", title="Unresolved", status=SeedStatus.EXPLORING
        )

        # Not blocked - no children
        not_blocked1 = Seed(id="seed-n1", title="No Children")

        # Not blocked - all children resolved
        not_blocked2 = Seed(id="seed-n2", title="All Resolved")
        resolved_child = Seed(
            id="seed-n2.1", title="Resolved", status=SeedStatus.RESOLVED
        )

        for seed in [
            blocked,
            blocked_child,
            not_blocked1,
            not_blocked2,
            resolved_child,
        ]:
            db.create_seed(seed)

        result = db.get_blocked_seeds()
        ids = [s.id for s in result]
        assert "seed-b1" in ids
        assert "seed-n1" not in ids
        assert "seed-n2" not in ids


class TestTags:
    """Tests for tag operations."""

    def test_get_all_tags_empty(self, db):
        """Verify get_all_tags returns empty list when no tags."""
        result = db.get_all_tags()
        assert result == []

    def test_get_all_tags_returns_unique_sorted(self, db):
        """Verify get_all_tags returns unique sorted tags."""
        seed1 = Seed(id="seed-1", title="S1", tags=["beta", "alpha"])
        seed2 = Seed(id="seed-2", title="S2", tags=["gamma", "alpha"])
        db.create_seed(seed1)
        db.create_seed(seed2)

        result = db.get_all_tags()
        assert result == ["alpha", "beta", "gamma"]  # Sorted, unique


class TestFindSeedsDir:
    """Tests for find_seeds_dir function."""

    def test_find_seeds_dir_in_current_directory(self):
        """Verify find_seeds_dir finds .seeds in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                # Create .seeds directory
                seeds_dir = os.path.join(tmpdir, ".seeds")
                os.makedirs(seeds_dir)

                result = find_seeds_dir()
                assert result is not None
                assert str(result) == seeds_dir
            finally:
                os.chdir(original_cwd)

    def test_find_seeds_dir_in_parent_directory(self):
        """Verify find_seeds_dir walks up to find .seeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                # Create .seeds in root of tmpdir
                seeds_dir = os.path.join(tmpdir, ".seeds")
                os.makedirs(seeds_dir)

                # Create a subdirectory and cd into it
                subdir = os.path.join(tmpdir, "subdir", "nested")
                os.makedirs(subdir)
                os.chdir(subdir)

                result = find_seeds_dir()
                assert result is not None
                assert str(result) == seeds_dir
            finally:
                os.chdir(original_cwd)

    def test_find_seeds_dir_returns_none_when_not_found(self):
        """Verify find_seeds_dir returns None when no .seeds exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = find_seeds_dir()
                assert result is None
            finally:
                os.chdir(original_cwd)


class TestSearch:
    """Tests for full-text search."""

    def test_search_by_title(self, db):
        """Verify search matches seed titles."""
        db.create_seed(Seed(id="seed-1", title="Deliberation workflow patterns"))
        db.create_seed(Seed(id="seed-2", title="Database optimization ideas"))

        results = db.search("deliberation")
        assert len(results) == 1
        assert results[0].id == "seed-1"

    def test_search_by_content(self, db):
        """Verify search matches seed content."""
        db.create_seed(
            Seed(id="seed-1", title="Some idea", content="We need better prototyping tools")
        )
        db.create_seed(
            Seed(id="seed-2", title="Other idea", content="The database layer is solid")
        )

        results = db.search("prototyping")
        assert len(results) == 1
        assert results[0].id == "seed-1"

    def test_search_by_tags(self, db):
        """Verify search matches tags stored as JSON."""
        db.create_seed(Seed(id="seed-1", title="Tagged seed", tags=["architecture", "mcp"]))
        db.create_seed(Seed(id="seed-2", title="Other seed", tags=["workflow"]))

        results = db.search("architecture")
        assert len(results) == 1
        assert results[0].id == "seed-1"

    def test_search_excludes_terminal_by_default(self, db):
        """Verify search excludes resolved/abandoned seeds."""
        db.create_seed(Seed(id="seed-1", title="Active deliberation"))
        db.create_seed(
            Seed(id="seed-2", title="Old deliberation", status=SeedStatus.RESOLVED)
        )

        results = db.search("deliberation")
        assert len(results) == 1
        assert results[0].id == "seed-1"

    def test_search_include_terminal(self, db):
        """Verify include_terminal=True returns resolved/abandoned seeds."""
        db.create_seed(Seed(id="seed-1", title="Active deliberation"))
        db.create_seed(
            Seed(id="seed-2", title="Old deliberation", status=SeedStatus.RESOLVED)
        )

        results = db.search("deliberation", include_terminal=True)
        assert len(results) == 2

    def test_search_no_results(self, db):
        """Verify search returns empty list for no matches."""
        db.create_seed(Seed(id="seed-1", title="Something completely different"))

        results = db.search("nonexistent")
        assert results == []

    def test_search_prefix_query(self, db):
        """Verify FTS5 prefix queries work."""
        db.create_seed(Seed(id="seed-1", title="Deliberation patterns"))
        db.create_seed(Seed(id="seed-2", title="Delivery pipeline"))

        results = db.search("delib*")
        assert len(results) == 1
        assert results[0].id == "seed-1"

    def test_search_multiple_terms(self, db):
        """Verify multi-word queries match."""
        db.create_seed(Seed(id="seed-1", title="Agent reasoning capture"))
        db.create_seed(Seed(id="seed-2", title="Agent workflow patterns"))
        db.create_seed(Seed(id="seed-3", title="Database optimization"))

        results = db.search("agent reasoning")
        assert len(results) >= 1
        ids = [s.id for s in results]
        assert "seed-1" in ids

    def test_search_updated_content(self, db):
        """Verify search reflects updated seed content."""
        seed = Seed(id="seed-1", title="Original title")
        db.create_seed(seed)

        # Should not match yet
        assert db.search("polymorphic") == []

        # Update content
        seed.content = "Explore polymorphic seed models"
        db.update_seed(seed)

        results = db.search("polymorphic")
        assert len(results) == 1
        assert results[0].id == "seed-1"

    def test_search_deleted_seed_removed(self, db):
        """Verify deleted seeds are removed from search index."""
        db.create_seed(Seed(id="seed-1", title="Ephemeral idea"))

        assert len(db.search("ephemeral")) == 1

        db.delete_seed("seed-1")
        assert db.search("ephemeral") == []

    def test_ensure_fts_migrates_existing_db(self, temp_dir):
        """Verify ensure_fts populates index for pre-FTS databases."""
        # Create a database with only the base schema (no FTS)
        db_path = temp_dir / ".seeds" / "seeds.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT INTO seeds (id, title, content, status, seed_type, tags, created_at, updated_at) "
            "VALUES ('seed-old', 'Legacy seed about prototyping', 'Old content', 'captured', 'idea', '[]', "
            "'2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
        )
        conn.commit()
        conn.close()

        # Open with Database class — ensure_fts should migrate
        db = Database(path=db_path)
        results = db.search("prototyping")
        assert len(results) == 1
        assert results[0].id == "seed-old"
        db.close()

    def test_rebuild_fts(self, db):
        """Verify rebuild_fts repopulates the entire index."""
        db.create_seed(Seed(id="seed-1", title="Deliberation patterns"))
        db.create_seed(Seed(id="seed-2", title="Workflow automation"))

        # Manually corrupt FTS by clearing it
        conn = db._get_conn()
        conn.execute("DELETE FROM seeds_fts")
        conn.commit()

        assert db.search("deliberation") == []

        db.rebuild_fts()
        assert len(db.search("deliberation")) == 1
        assert len(db.search("automation")) == 1


class TestRelationships:
    """Tests for relationship CRUD operations."""

    def test_create_relates_to_bidirectional(self, db):
        """Verify relates-to creates two rows (bidirectional)."""
        db.create_seed(Seed(id="seed-a", title="A"))
        db.create_seed(Seed(id="seed-b", title="B"))

        rel = db.create_relationship("seed-a", "seed-b", RelationType.RELATES_TO)
        assert rel.source_id == "seed-a"
        assert rel.target_id == "seed-b"
        assert rel.rel_type == RelationType.RELATES_TO

        # Both directions should exist
        outbound = db.get_relationships("seed-a", direction="outbound")
        assert len(outbound) == 1
        assert outbound[0].target_id == "seed-b"

        inbound = db.get_relationships("seed-a", direction="inbound")
        assert len(inbound) == 1
        assert inbound[0].source_id == "seed-b"

    def test_create_directed_relationship(self, db):
        """Verify questions/answers relationships are one-directional."""
        db.create_seed(Seed(id="seed-q", title="Why?", seed_type=SeedType.QUESTION))
        db.create_seed(Seed(id="seed-t", title="Target"))

        db.create_relationship("seed-q", "seed-t", RelationType.QUESTIONS)

        # Only outbound from question
        outbound = db.get_relationships("seed-q", direction="outbound")
        assert len(outbound) == 1
        assert outbound[0].rel_type == RelationType.QUESTIONS

        # No reverse edge created
        outbound_from_target = db.get_relationships(
            "seed-t", rel_type=RelationType.QUESTIONS, direction="outbound"
        )
        assert len(outbound_from_target) == 0

    def test_get_relationships_filter_by_type(self, db):
        """Verify filtering relationships by type."""
        db.create_seed(Seed(id="seed-a", title="A"))
        db.create_seed(Seed(id="seed-b", title="B"))
        db.create_seed(Seed(id="seed-q", title="Q?", seed_type=SeedType.QUESTION))

        db.create_relationship("seed-a", "seed-b", RelationType.RELATES_TO)
        db.create_relationship("seed-q", "seed-a", RelationType.QUESTIONS)

        relates = db.get_relationships("seed-a", rel_type=RelationType.RELATES_TO)
        assert len(relates) == 2  # Both directions of relates-to

        questions = db.get_relationships("seed-a", rel_type=RelationType.QUESTIONS)
        assert len(questions) == 1  # Only inbound question

    def test_get_relationships_both_direction(self, db):
        """Verify 'both' direction returns all relationships."""
        db.create_seed(Seed(id="seed-a", title="A"))
        db.create_seed(Seed(id="seed-b", title="B"))
        db.create_seed(Seed(id="seed-q", title="Q?", seed_type=SeedType.QUESTION))

        db.create_relationship("seed-a", "seed-b", RelationType.RELATES_TO)
        db.create_relationship("seed-q", "seed-a", RelationType.QUESTIONS)

        all_rels = db.get_relationships("seed-a")
        # relates-to: a→b and b→a, plus questions: q→a
        assert len(all_rels) == 3

    def test_delete_relationship_relates_to(self, db):
        """Verify deleting relates-to removes both directions."""
        db.create_seed(Seed(id="seed-a", title="A"))
        db.create_seed(Seed(id="seed-b", title="B"))

        db.create_relationship("seed-a", "seed-b", RelationType.RELATES_TO)
        assert len(db.get_relationships("seed-a")) == 2

        result = db.delete_relationship("seed-a", "seed-b", RelationType.RELATES_TO)
        assert result is True
        assert len(db.get_relationships("seed-a")) == 0
        assert len(db.get_relationships("seed-b")) == 0

    def test_delete_relationship_directed(self, db):
        """Verify deleting directed relationship removes only one row."""
        db.create_seed(Seed(id="seed-q", title="Q?", seed_type=SeedType.QUESTION))
        db.create_seed(Seed(id="seed-t", title="Target"))

        db.create_relationship("seed-q", "seed-t", RelationType.QUESTIONS)
        result = db.delete_relationship("seed-q", "seed-t", RelationType.QUESTIONS)
        assert result is True
        assert len(db.get_relationships("seed-q")) == 0

    def test_delete_nonexistent_relationship(self, db):
        """Verify deleting nonexistent relationship returns False."""
        result = db.delete_relationship("seed-x", "seed-y", RelationType.RELATES_TO)
        assert result is False

    def test_create_duplicate_relationship_ignored(self, db):
        """Verify creating duplicate relationship is silently ignored."""
        db.create_seed(Seed(id="seed-a", title="A"))
        db.create_seed(Seed(id="seed-b", title="B"))

        db.create_relationship("seed-a", "seed-b", RelationType.RELATES_TO)
        db.create_relationship("seed-a", "seed-b", RelationType.RELATES_TO)

        # Should still be just 2 rows (bidirectional), not 4
        all_rels = db.get_relationships("seed-a")
        assert len(all_rels) == 2

    def test_delete_seed_cascades_relationships(self, db):
        """Verify deleting a seed removes its relationships."""
        db.create_seed(Seed(id="seed-a", title="A"))
        db.create_seed(Seed(id="seed-b", title="B"))
        db.create_seed(Seed(id="seed-q", title="Q?", seed_type=SeedType.QUESTION))

        db.create_relationship("seed-a", "seed-b", RelationType.RELATES_TO)
        db.create_relationship("seed-q", "seed-a", RelationType.QUESTIONS)

        db.delete_seed("seed-a")

        # All relationships involving seed-a should be gone
        assert len(db.get_relationships("seed-b")) == 0
        assert len(db.get_relationships("seed-q")) == 0


class TestQuestionsForSeed:
    """Tests for get_questions_for_seed (relationship-based)."""

    def test_get_questions_for_seed_empty(self, db):
        """Verify returns empty list when no question relationships."""
        db.create_seed(Seed(id="seed-t", title="Target"))
        result = db.get_questions_for_seed("seed-t")
        assert result == []

    def test_get_questions_for_seed(self, db):
        """Verify returns question-seeds linked via 'questions' relationship."""
        db.create_seed(Seed(id="seed-t", title="Target"))
        db.create_seed(
            Seed(id="seed-q1", title="Question 1?", seed_type=SeedType.QUESTION)
        )
        db.create_seed(
            Seed(id="seed-q2", title="Question 2?", seed_type=SeedType.QUESTION)
        )

        db.create_relationship("seed-q1", "seed-t", RelationType.QUESTIONS)
        db.create_relationship("seed-q2", "seed-t", RelationType.QUESTIONS)

        questions = db.get_questions_for_seed("seed-t")
        assert len(questions) == 2
        ids = [q.id for q in questions]
        assert "seed-q1" in ids
        assert "seed-q2" in ids

    def test_get_questions_excludes_relates_to(self, db):
        """Verify get_questions_for_seed only returns 'questions' relationships."""
        db.create_seed(Seed(id="seed-t", title="Target"))
        db.create_seed(Seed(id="seed-r", title="Related"))
        db.create_seed(
            Seed(id="seed-q", title="Question?", seed_type=SeedType.QUESTION)
        )

        db.create_relationship("seed-r", "seed-t", RelationType.RELATES_TO)
        db.create_relationship("seed-q", "seed-t", RelationType.QUESTIONS)

        questions = db.get_questions_for_seed("seed-t")
        assert len(questions) == 1
        assert questions[0].id == "seed-q"


class TestBlockedWithQuestionSeeds:
    """Tests for is_blocked considering question-seed relationships."""

    def test_blocked_by_unresolved_question_seed(self, db):
        """Verify seed is blocked by unresolved question-seeds."""
        db.create_seed(Seed(id="seed-t", title="Target"))
        db.create_seed(
            Seed(
                id="seed-q",
                title="Unanswered?",
                seed_type=SeedType.QUESTION,
                status=SeedStatus.CAPTURED,
            )
        )
        db.create_relationship("seed-q", "seed-t", RelationType.QUESTIONS)

        assert db.is_blocked("seed-t") is True

    def test_not_blocked_when_question_resolved(self, db):
        """Verify seed is not blocked when question-seed is resolved."""
        db.create_seed(Seed(id="seed-t", title="Target"))
        db.create_seed(
            Seed(
                id="seed-q",
                title="Answered",
                seed_type=SeedType.QUESTION,
                status=SeedStatus.RESOLVED,
            )
        )
        db.create_relationship("seed-q", "seed-t", RelationType.QUESTIONS)

        assert db.is_blocked("seed-t") is False

    def test_blocked_by_either_children_or_questions(self, db):
        """Verify blocked considers both children and question-seeds."""
        db.create_seed(Seed(id="seed-p", title="Parent"))
        # Resolved child — not blocking
        db.create_seed(
            Seed(id="seed-p.1", title="Child", status=SeedStatus.RESOLVED)
        )
        # Unresolved question — blocking
        db.create_seed(
            Seed(
                id="seed-q",
                title="Blocking question?",
                seed_type=SeedType.QUESTION,
                status=SeedStatus.CAPTURED,
            )
        )
        db.create_relationship("seed-q", "seed-p", RelationType.QUESTIONS)

        assert db.is_blocked("seed-p") is True


class TestMigration:
    """Tests for migrate_to_relationships."""

    def test_migration_converts_related_to(self, temp_dir):
        """Verify migration creates relationships from related_to arrays."""
        db_path = temp_dir / ".seeds" / "seeds.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a v1 database with related_to
        conn = sqlite3.connect(db_path)
        conn.executescript(V1_SCHEMA)
        now = "2026-01-01T00:00:00+00:00"
        conn.execute(
            "INSERT INTO seeds (id, title, status, seed_type, tags, related_to, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("seed-a", "Seed A", "captured", "idea", "[]", '["seed-b"]', now, now),
        )
        conn.execute(
            "INSERT INTO seeds (id, title, status, seed_type, tags, related_to, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("seed-b", "Seed B", "captured", "idea", "[]", '["seed-a"]', now, now),
        )
        conn.commit()
        conn.close()

        db = Database(path=db_path)
        counts = db.migrate_to_relationships()

        assert counts["related_to"] == 2  # One from each seed
        rels = db.get_relationships("seed-a", rel_type=RelationType.RELATES_TO)
        assert len(rels) == 2  # Bidirectional (from migration + the stored reverse)
        db.close()

    def test_migration_converts_questions(self, temp_dir):
        """Verify migration creates question-seeds from questions table."""
        db_path = temp_dir / ".seeds" / "seeds.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path)
        conn.executescript(V1_SCHEMA)
        now = "2026-01-01T00:00:00+00:00"

        # Create a seed with questions
        conn.execute(
            "INSERT INTO seeds (id, title, status, seed_type, tags, related_to, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("seed-parent", "Parent", "exploring", "idea", "[]", "[]", now, now),
        )
        conn.execute(
            "INSERT INTO questions (id, seed_id, text, answer, status, created_at, answered_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("q-1", "seed-parent", "Open question?", None, "open", now, None),
        )
        conn.execute(
            "INSERT INTO questions (id, seed_id, text, answer, status, created_at, answered_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("q-2", "seed-parent", "Answered?", "Yes", "answered", now, now),
        )
        conn.execute(
            "INSERT INTO questions (id, seed_id, text, answer, status, created_at, answered_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("q-3", "seed-parent", "Deferred?", None, "deferred", now, None),
        )
        conn.commit()
        conn.close()

        db = Database(path=db_path)
        counts = db.migrate_to_relationships()

        assert counts["questions"] == 3

        # Question-seeds should exist
        question_seeds = db.get_questions_for_seed("seed-parent")
        assert len(question_seeds) == 3

        # Check status mapping
        statuses = {qs.title: qs.status for qs in question_seeds}
        assert statuses["Open question?"] == SeedStatus.CAPTURED
        assert statuses["Answered?"] == SeedStatus.RESOLVED
        assert statuses["Deferred?"] == SeedStatus.DEFERRED

        # Check answered question has content
        for qs in question_seeds:
            if qs.title == "Answered?":
                assert qs.content == "Yes"
                assert qs.seed_type == SeedType.QUESTION

        db.close()

    def test_migration_idempotent(self, temp_dir):
        """Verify running migration twice doesn't duplicate data."""
        db_path = temp_dir / ".seeds" / "seeds.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path)
        conn.executescript(V1_SCHEMA)
        now = "2026-01-01T00:00:00+00:00"
        conn.execute(
            "INSERT INTO seeds (id, title, status, seed_type, tags, related_to, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("seed-a", "A", "captured", "idea", "[]", '["seed-b"]', now, now),
        )
        conn.execute(
            "INSERT INTO seeds (id, title, status, seed_type, tags, related_to, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("seed-b", "B", "captured", "idea", "[]", "[]", now, now),
        )
        conn.commit()
        conn.close()

        db = Database(path=db_path)
        db.migrate_to_relationships()
        db.migrate_to_relationships()  # Second time

        # Should still be just the expected relationships
        rels = db.get_relationships("seed-a", rel_type=RelationType.RELATES_TO)
        assert len(rels) == 2  # Bidirectional, not duplicated
        db.close()
