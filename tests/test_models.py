"""Tests for seeds data models."""

import pytest
from seeds.models import (
    Question,
    QuestionStatus,
    Relationship,
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
    generate_child_id,
    generate_id,
    get_parent_id,
)


class TestSeedStatus:
    """Tests for SeedStatus enum."""

    def test_all_statuses_exist(self):
        """Verify all expected statuses are defined."""
        assert SeedStatus.CAPTURED.value == "captured"
        assert SeedStatus.EXPLORING.value == "exploring"
        assert SeedStatus.DEFERRED.value == "deferred"
        assert SeedStatus.RESOLVED.value == "resolved"
        assert SeedStatus.ABANDONED.value == "abandoned"

    def test_status_from_value(self):
        """Verify statuses can be created from string values."""
        assert SeedStatus("captured") == SeedStatus.CAPTURED
        assert SeedStatus("exploring") == SeedStatus.EXPLORING
        assert SeedStatus("deferred") == SeedStatus.DEFERRED
        assert SeedStatus("resolved") == SeedStatus.RESOLVED
        assert SeedStatus("abandoned") == SeedStatus.ABANDONED

    def test_invalid_status_raises(self):
        """Verify invalid status values raise ValueError."""
        with pytest.raises(ValueError):
            SeedStatus("invalid")


class TestSeedType:
    """Tests for SeedType enum."""

    def test_all_types_exist(self):
        """Verify all expected types are defined."""
        assert SeedType.IDEA.value == "idea"
        assert SeedType.QUESTION.value == "question"
        assert SeedType.DECISION.value == "decision"
        assert SeedType.EXPLORATION.value == "exploration"
        assert SeedType.CONCERN.value == "concern"

    def test_type_from_value(self):
        """Verify types can be created from string values."""
        assert SeedType("idea") == SeedType.IDEA
        assert SeedType("question") == SeedType.QUESTION
        assert SeedType("exploration") == SeedType.EXPLORATION


class TestQuestionStatus:
    """Tests for QuestionStatus enum."""

    def test_all_statuses_exist(self):
        """Verify all expected question statuses are defined."""
        assert QuestionStatus.OPEN.value == "open"
        assert QuestionStatus.ANSWERED.value == "answered"
        assert QuestionStatus.DEFERRED.value == "deferred"


class TestGenerateId:
    """Tests for ID generation functions."""

    def test_generate_id_default_prefix(self):
        """Verify default prefix is 'seed'."""
        id1 = generate_id()
        assert id1.startswith("seed-")
        assert len(id1) == 13  # "seed-" + 8 chars

    def test_generate_id_custom_prefix(self):
        """Verify custom prefix works."""
        id1 = generate_id("q")
        assert id1.startswith("q-")
        assert len(id1) == 10  # "q-" + 8 chars

    def test_generate_id_unique(self):
        """Verify generated IDs are unique."""
        ids = [generate_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique

    def test_generate_child_id(self):
        """Verify child ID generation."""
        child_id = generate_child_id("seed-a1b2")
        assert child_id == "seed-a1b2.1"


class TestGetParentId:
    """Tests for parent ID extraction."""

    def test_root_seed_has_no_parent(self):
        """Verify root seeds return None."""
        assert get_parent_id("seed-a1b2") is None

    def test_child_returns_parent(self):
        """Verify child IDs return correct parent."""
        assert get_parent_id("seed-a1b2.1") == "seed-a1b2"

    def test_grandchild_returns_parent(self):
        """Verify grandchild IDs return correct parent (not grandparent)."""
        assert get_parent_id("seed-a1b2.1.3") == "seed-a1b2.1"

    def test_deeply_nested(self):
        """Verify deeply nested IDs work correctly."""
        assert get_parent_id("seed-a1b2.1.2.3.4") == "seed-a1b2.1.2.3"


class TestSeed:
    """Tests for Seed dataclass."""

    def test_create_minimal_seed(self):
        """Verify seed can be created with minimal args."""
        seed = Seed(id="seed-test", title="Test")
        assert seed.id == "seed-test"
        assert seed.title == "Test"
        assert seed.content == ""
        assert seed.status == SeedStatus.CAPTURED
        assert seed.seed_type == SeedType.IDEA
        assert seed.tags == []
        assert seed.related_to == []
        assert seed.resolved_at is None

    def test_create_full_seed(self):
        """Verify seed can be created with all args."""
        seed = Seed(
            id="seed-full",
            title="Full Seed",
            content="Detailed content",
            status=SeedStatus.EXPLORING,
            seed_type=SeedType.DECISION,
            tags=["important", "urgent"],
            related_to=["seed-other"],
        )
        assert seed.id == "seed-full"
        assert seed.status == SeedStatus.EXPLORING
        assert seed.seed_type == SeedType.DECISION
        assert seed.tags == ["important", "urgent"]
        assert seed.related_to == ["seed-other"]

    def test_parent_id_property(self):
        """Verify parent_id property works correctly."""
        root = Seed(id="seed-a1b2", title="Root")
        child = Seed(id="seed-a1b2.1", title="Child")
        grandchild = Seed(id="seed-a1b2.1.2", title="Grandchild")

        assert root.parent_id is None
        assert child.parent_id == "seed-a1b2"
        assert grandchild.parent_id == "seed-a1b2.1"

    def test_is_terminal_resolved(self):
        """Verify resolved status is terminal."""
        seed = Seed(id="seed-test", title="Test", status=SeedStatus.RESOLVED)
        assert seed.is_terminal() is True

    def test_is_terminal_abandoned(self):
        """Verify abandoned status is terminal."""
        seed = Seed(id="seed-test", title="Test", status=SeedStatus.ABANDONED)
        assert seed.is_terminal() is True

    def test_is_terminal_false_for_active_states(self):
        """Verify active states are not terminal."""
        for status in [SeedStatus.CAPTURED, SeedStatus.EXPLORING, SeedStatus.DEFERRED]:
            seed = Seed(id="seed-test", title="Test", status=status)
            assert seed.is_terminal() is False, f"{status} should not be terminal"


class TestRelationType:
    """Tests for RelationType enum."""

    def test_all_types_exist(self):
        """Verify all expected relationship types are defined."""
        assert RelationType.RELATES_TO.value == "relates-to"
        assert RelationType.QUESTIONS.value == "questions"
        assert RelationType.ANSWERS.value == "answers"

    def test_type_from_value(self):
        """Verify types can be created from string values."""
        assert RelationType("relates-to") == RelationType.RELATES_TO
        assert RelationType("questions") == RelationType.QUESTIONS
        assert RelationType("answers") == RelationType.ANSWERS

    def test_invalid_type_raises(self):
        """Verify invalid relationship type raises ValueError."""
        with pytest.raises(ValueError):
            RelationType("invalid")


class TestRelationship:
    """Tests for Relationship dataclass."""

    def test_create_minimal_relationship(self):
        """Verify relationship can be created with minimal args."""
        rel = Relationship(source_id="seed-a", target_id="seed-b")
        assert rel.source_id == "seed-a"
        assert rel.target_id == "seed-b"
        assert rel.rel_type == RelationType.RELATES_TO
        assert rel.created_at is not None

    def test_create_typed_relationship(self):
        """Verify relationship with explicit type."""
        rel = Relationship(
            source_id="seed-q",
            target_id="seed-t",
            rel_type=RelationType.QUESTIONS,
        )
        assert rel.rel_type == RelationType.QUESTIONS


class TestQuestion:
    """Tests for Question dataclass."""

    def test_create_minimal_question(self):
        """Verify question can be created with minimal args."""
        question = Question(
            id="q-test",
            seed_id="seed-test",
            text="What is the answer?",
        )
        assert question.id == "q-test"
        assert question.seed_id == "seed-test"
        assert question.text == "What is the answer?"
        assert question.answer is None
        assert question.status == QuestionStatus.OPEN
        assert question.answered_at is None

    def test_create_answered_question(self):
        """Verify answered question has all fields."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        question = Question(
            id="q-test",
            seed_id="seed-test",
            text="What is the answer?",
            answer="42",
            status=QuestionStatus.ANSWERED,
            answered_at=now,
        )
        assert question.answer == "42"
        assert question.status == QuestionStatus.ANSWERED
        assert question.answered_at == now
