"""Tests for seeds data models."""

import pytest
from seeds.models import (
    Relationship,
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
    generate_id,
    get_parent_id,
    is_valid_prefix,
    parse_sequential_id,
    sanitize_prefix,
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


class TestParseSequentialId:
    """Tests for parse_sequential_id."""

    def test_parse_simple_sequential(self):
        """Verify parsing sequential IDs."""
        assert parse_sequential_id("seeds-1") == 1
        assert parse_sequential_id("seeds-42") == 42
        assert parse_sequential_id("seeds-999") == 999

    def test_parse_hex_returns_none(self):
        """Verify hex IDs return None."""
        assert parse_sequential_id("seed-a1b2c3d4") is None
        assert parse_sequential_id("seeds-086a609d") is None

    def test_parse_child_returns_none(self):
        """Verify child IDs return None (not top-level)."""
        assert parse_sequential_id("seeds-42.1") is None

    def test_parse_no_dash(self):
        """Verify IDs without dashes return None."""
        assert parse_sequential_id("seeds") is None


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
        )
        assert seed.id == "seed-full"
        assert seed.status == SeedStatus.EXPLORING
        assert seed.seed_type == SeedType.DECISION
        assert seed.tags == ["important", "urgent"]

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


class TestSanitizePrefix:
    """Tests for sanitize_prefix."""

    def test_simple_lowercase(self):
        assert sanitize_prefix("myproj") == "myproj"

    def test_already_kebab(self):
        assert sanitize_prefix("my-project") == "my-project"

    def test_uppercase_lowered(self):
        assert sanitize_prefix("MyProject") == "myproject"

    def test_space_to_hyphen(self):
        assert sanitize_prefix("My Project") == "my-project"

    def test_underscore_to_hyphen(self):
        assert sanitize_prefix("foo_bar") == "foo-bar"

    def test_dots_to_hyphen(self):
        assert sanitize_prefix("foo_bar.v2") == "foo-bar-v2"

    def test_collapses_runs(self):
        assert sanitize_prefix("foo  bar___baz") == "foo-bar-baz"

    def test_strips_leading_trailing(self):
        assert sanitize_prefix("-foo-") == "foo"
        assert sanitize_prefix("__bar__") == "bar"

    def test_empty_input(self):
        assert sanitize_prefix("") == ""

    def test_only_punctuation(self):
        assert sanitize_prefix("!!!") == ""

    def test_leading_digit_invalid(self):
        assert sanitize_prefix("123proj") == ""

    def test_seeds_unchanged(self):
        assert sanitize_prefix("seeds") == "seeds"


class TestIsValidPrefix:
    """Tests for is_valid_prefix."""

    def test_valid(self):
        assert is_valid_prefix("seeds") is True
        assert is_valid_prefix("my-project") is True
        assert is_valid_prefix("p1") is True

    def test_invalid_uppercase(self):
        assert is_valid_prefix("Seeds") is False

    def test_invalid_starts_with_digit(self):
        assert is_valid_prefix("1abc") is False

    def test_invalid_empty(self):
        assert is_valid_prefix("") is False

    def test_invalid_chars(self):
        assert is_valid_prefix("foo_bar") is False
        assert is_valid_prefix("foo.bar") is False
        assert is_valid_prefix("foo bar") is False


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
