"""Tests for seeds database layer."""

import os
import tempfile

import pytest

from seeds.db import Database, find_seeds_dir
from seeds.models import (
    Question,
    QuestionStatus,
    Seed,
    SeedStatus,
    SeedType,
)


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

    def test_delete_seed_deletes_questions(self, db, sample_seed, sample_question):
        """Verify deleting a seed also deletes its questions."""
        db.create_seed(sample_seed)
        db.create_question(sample_question)

        db.delete_seed(sample_seed.id)
        assert db.get_question(sample_question.id) is None


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
        blocked_child = Seed(id="seed-b1.1", title="Unresolved", status=SeedStatus.EXPLORING)

        # Not blocked - no children
        not_blocked1 = Seed(id="seed-n1", title="No Children")

        # Not blocked - all children resolved
        not_blocked2 = Seed(id="seed-n2", title="All Resolved")
        resolved_child = Seed(id="seed-n2.1", title="Resolved", status=SeedStatus.RESOLVED)

        for seed in [blocked, blocked_child, not_blocked1, not_blocked2, resolved_child]:
            db.create_seed(seed)

        result = db.get_blocked_seeds()
        ids = [s.id for s in result]
        assert "seed-b1" in ids
        assert "seed-n1" not in ids
        assert "seed-n2" not in ids


class TestQuestionCRUD:
    """Tests for question CRUD operations."""

    def test_create_and_get_question(self, db, sample_seed, sample_question):
        """Verify question can be created and retrieved."""
        db.create_seed(sample_seed)
        db.create_question(sample_question)

        retrieved = db.get_question(sample_question.id)
        assert retrieved is not None
        assert retrieved.id == sample_question.id
        assert retrieved.seed_id == sample_question.seed_id
        assert retrieved.text == sample_question.text
        assert retrieved.status == sample_question.status

    def test_get_nonexistent_question_returns_none(self, db):
        """Verify get_question returns None for missing ID."""
        result = db.get_question("q-nonexistent")
        assert result is None

    def test_update_question(self, db, sample_seed, sample_question):
        """Verify question can be updated."""
        db.create_seed(sample_seed)
        db.create_question(sample_question)

        sample_question.answer = "42"
        sample_question.status = QuestionStatus.ANSWERED
        db.update_question(sample_question)

        retrieved = db.get_question(sample_question.id)
        assert retrieved.answer == "42"
        assert retrieved.status == QuestionStatus.ANSWERED

    def test_delete_question(self, db, sample_seed, sample_question):
        """Verify question can be deleted."""
        db.create_seed(sample_seed)
        db.create_question(sample_question)

        result = db.delete_question(sample_question.id)
        assert result is True
        assert db.get_question(sample_question.id) is None


class TestQuestionListing:
    """Tests for question listing and filtering."""

    def test_list_questions_empty(self, db):
        """Verify list_questions returns empty list when no questions."""
        result = db.list_questions()
        assert result == []

    def test_list_questions_filter_by_seed(self, db, sample_seed):
        """Verify filtering questions by seed_id works."""
        other_seed = Seed(id="seed-other", title="Other Seed")
        db.create_seed(sample_seed)
        db.create_seed(other_seed)

        q1 = Question(id="q-1", seed_id=sample_seed.id, text="Q1")
        q2 = Question(id="q-2", seed_id="seed-other", text="Q2")
        db.create_question(q1)
        db.create_question(q2)

        result = db.list_questions(seed_id=sample_seed.id)
        assert len(result) == 1
        assert result[0].id == "q-1"

    def test_list_questions_filter_by_status(self, db, sample_seed):
        """Verify filtering questions by status works."""
        db.create_seed(sample_seed)

        q1 = Question(id="q-1", seed_id=sample_seed.id, text="Q1", status=QuestionStatus.OPEN)
        q2 = Question(id="q-2", seed_id=sample_seed.id, text="Q2", status=QuestionStatus.ANSWERED)
        db.create_question(q1)
        db.create_question(q2)

        result = db.list_questions(status=QuestionStatus.OPEN)
        assert len(result) == 1
        assert result[0].id == "q-1"

    def test_get_open_questions(self, db, sample_seed):
        """Verify get_open_questions returns only open questions."""
        db.create_seed(sample_seed)

        q1 = Question(id="q-1", seed_id=sample_seed.id, text="Open", status=QuestionStatus.OPEN)
        q2 = Question(id="q-2", seed_id=sample_seed.id, text="Answered", status=QuestionStatus.ANSWERED)
        q3 = Question(id="q-3", seed_id=sample_seed.id, text="Deferred", status=QuestionStatus.DEFERRED)
        for q in [q1, q2, q3]:
            db.create_question(q)

        result = db.get_open_questions()
        assert len(result) == 1
        assert result[0].id == "q-1"


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
