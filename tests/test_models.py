"""Tests for seeds data models."""

from datetime import datetime, timezone

import pytest

from seeds.models import (
    Relationship,
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
    find_id_refs,
    generate_id,
    get_parent_id,
    is_valid_prefix,
    iter_id_ref_snippets,
    parse_sequential_id,
    parse_since,
    rewrite_id_refs,
    sanitize_prefix,
    tokenize_for_suggest,
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


class TestRewriteIdRefs:
    """Tests for rewrite_id_refs."""

    def test_simple_reference(self):
        text, count = rewrite_id_refs("see seeds-7", "seeds", "myproj")
        assert text == "see myproj-7"
        assert count == 1

    def test_multiple_references(self):
        text, count = rewrite_id_refs(
            "seeds-1 and seeds-2 and seeds-3", "seeds", "myproj"
        )
        assert text == "myproj-1 and myproj-2 and myproj-3"
        assert count == 3

    def test_child_id_reference(self):
        text, count = rewrite_id_refs("see seeds-7.1.2", "seeds", "myproj")
        assert text == "see myproj-7.1.2"
        assert count == 1

    def test_markdown_link(self):
        text, count = rewrite_id_refs("See [seeds-7](url)", "seeds", "myproj")
        assert text == "See [myproj-7](url)"
        assert count == 1

    def test_does_not_touch_compound_token(self):
        text, count = rewrite_id_refs("the seeds-related code", "seeds", "myproj")
        assert text == "the seeds-related code"
        assert count == 0

    def test_does_not_touch_inside_word(self):
        text, count = rewrite_id_refs("see myseeds-7 here", "seeds", "myproj")
        # Preceded by 's' (alphanumeric) → no match.
        assert text == "see myseeds-7 here"
        assert count == 0

    def test_does_not_touch_trailing_word(self):
        text, count = rewrite_id_refs("see seeds-7-banana", "seeds", "myproj")
        # Followed by '-' (in our exclusion class) → no match.
        assert text == "see seeds-7-banana"
        assert count == 0

    def test_empty_text(self):
        text, count = rewrite_id_refs("", "seeds", "myproj")
        assert text == ""
        assert count == 0

    def test_idempotent(self):
        once, _ = rewrite_id_refs("see seeds-7", "seeds", "myproj")
        twice, _ = rewrite_id_refs(once, "seeds", "myproj")
        assert once == twice

    def test_hyphenated_prefix(self):
        text, count = rewrite_id_refs("see my-proj-7 here", "my-proj", "different")
        assert text == "see different-7 here"
        assert count == 1

    def test_hash_ref_needs_known_ids(self):
        """Without known_ids a hash-shaped token is indistinguishable from prose."""
        text, count = rewrite_id_refs("see seeds-k3n7", "seeds", "myproj")
        assert text == "see seeds-k3n7"
        assert count == 0

    def test_hash_ref_rewritten_when_known(self):
        text, count = rewrite_id_refs(
            "see seeds-k3n7", "seeds", "myproj", {"seeds-k3n7"}
        )
        assert text == "see myproj-k3n7"
        assert count == 1

    def test_known_ids_does_not_widen_prose(self):
        """Only the listed IDs are rewritten; other base36 words stay put."""
        text, count = rewrite_id_refs(
            "the seeds-related seeds-k3n7 work", "seeds", "myproj", {"seeds-k3n7"}
        )
        assert text == "the seeds-related myproj-k3n7 work"
        assert count == 1

    def test_hash_child_ref_judged_by_parent(self):
        text, count = rewrite_id_refs(
            "see seeds-k3n7.1", "seeds", "myproj", {"seeds-k3n7"}
        )
        assert text == "see myproj-k3n7.1"
        assert count == 1

    def test_numeric_ref_does_not_need_known_ids(self):
        """Sequential refs are rewritten even for since-deleted seeds."""
        text, count = rewrite_id_refs("see seeds-7", "seeds", "myproj", {"seeds-k3n7"})
        assert text == "see myproj-7"
        assert count == 1

    def test_all_digit_hash_ref_is_rewritten(self):
        """'seeds-060' parses as a number, so it rewrites either way."""
        text, count = rewrite_id_refs("see seeds-060", "seeds", "myproj")
        assert text == "see myproj-060"
        assert count == 1


class TestIterIdRefSnippets:
    """Tests for iter_id_ref_snippets."""

    def test_basic_snippet(self):
        pairs = iter_id_ref_snippets("see seeds-7 now", "seeds", "myproj")
        assert pairs == [("see seeds-7 now", "see myproj-7 now")]

    def test_no_matches_returns_empty(self):
        pairs = iter_id_ref_snippets("no refs here", "seeds", "myproj")
        assert pairs == []

    def test_multiple_pairs(self):
        pairs = iter_id_ref_snippets("first seeds-1 then seeds-2", "seeds", "myproj")
        assert len(pairs) == 2
        assert "seeds-1" in pairs[0][0]
        assert "myproj-1" in pairs[0][1]
        assert "seeds-2" in pairs[1][0]
        assert "myproj-2" in pairs[1][1]

    def test_ellipsis_marker_for_long_context(self):
        text = "x" * 200 + " seeds-7 " + "y" * 200
        pairs = iter_id_ref_snippets(text, "seeds", "myproj", ctx=10)
        assert pairs[0][0].startswith("…")
        assert pairs[0][0].endswith("…")

    def test_collapses_newlines(self):
        pairs = iter_id_ref_snippets(
            "line one\nline two seeds-7 line three\nlast",
            "seeds",
            "myproj",
        )
        assert "\n" not in pairs[0][0]
        assert "\n" not in pairs[0][1]

    def test_hash_refs_need_known_ids(self):
        assert iter_id_ref_snippets("see seeds-k3n7 now", "seeds", "myproj") == []
        assert iter_id_ref_snippets(
            "see seeds-k3n7 now", "seeds", "myproj", known_ids={"seeds-k3n7"}
        ) == [("see seeds-k3n7 now", "see myproj-k3n7 now")]


class TestFindIdRefs:
    """Tests for find_id_refs helper."""

    def test_empty_text(self):
        assert find_id_refs("", "seeds") == []

    def test_single_ref(self):
        assert find_id_refs("see seeds-7", "seeds") == ["seeds-7"]

    def test_multiple_unique_refs(self):
        assert find_id_refs("seeds-7 and seeds-12 also seeds-3", "seeds") == [
            "seeds-12",
            "seeds-3",
            "seeds-7",
        ]

    def test_dedupes_repeated(self):
        assert find_id_refs("seeds-7 seeds-7 seeds-7", "seeds") == ["seeds-7"]

    def test_child_ids(self):
        assert find_id_refs("see seeds-7.1 and seeds-12.3.4", "seeds") == [
            "seeds-12.3.4",
            "seeds-7.1",
        ]

    def test_ignores_compound_words(self):
        assert find_id_refs("the seeds-related work", "seeds") == []
        assert find_id_refs("foo-seeds-7-bar", "seeds") == []

    def test_wrong_prefix_not_matched(self):
        assert find_id_refs("see csc-7", "seeds") == []

    def test_hash_refs_need_known_ids(self):
        assert find_id_refs("see seeds-k3n7", "seeds") == []
        assert find_id_refs("see seeds-k3n7", "seeds", {"seeds-k3n7"}) == ["seeds-k3n7"]


class TestParseSince:
    """Tests for parse_since helper."""

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_since("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            parse_since("   ")

    def test_iso_date(self):
        result = parse_since("2026-05-08")
        assert result.year == 2026
        assert result.month == 5
        assert result.day == 8
        assert result.tzinfo is not None  # naive interpreted as UTC

    def test_iso_datetime_with_tz(self):
        result = parse_since("2026-05-08T12:00:00+00:00")
        assert result.year == 2026
        assert result.hour == 12

    def test_relative_days(self):
        now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
        result = parse_since("7d", now=now)
        assert result == datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc)

    def test_relative_weeks(self):
        now = datetime(2026, 5, 18, tzinfo=timezone.utc)
        result = parse_since("2w", now=now)
        assert result == datetime(2026, 5, 4, tzinfo=timezone.utc)

    def test_relative_months(self):
        now = datetime(2026, 5, 18, tzinfo=timezone.utc)
        result = parse_since("1m", now=now)
        # 30-day month convention
        assert result == datetime(2026, 4, 18, tzinfo=timezone.utc)

    def test_relative_years(self):
        now = datetime(2026, 5, 18, tzinfo=timezone.utc)
        result = parse_since("1y", now=now)
        # 365-day year convention
        assert result == datetime(2025, 5, 18, tzinfo=timezone.utc)

    def test_today_keyword(self):
        now = datetime(2026, 5, 18, 15, 30, 22, tzinfo=timezone.utc)
        result = parse_since("today", now=now)
        assert result == datetime(2026, 5, 18, 0, 0, 0, tzinfo=timezone.utc)

    def test_yesterday_keyword(self):
        now = datetime(2026, 5, 18, 15, 30, tzinfo=timezone.utc)
        result = parse_since("yesterday", now=now)
        assert result == datetime(2026, 5, 17, 0, 0, 0, tzinfo=timezone.utc)

    def test_case_insensitive_keyword(self):
        now = datetime(2026, 5, 18, 15, tzinfo=timezone.utc)
        assert parse_since("TODAY", now=now) == parse_since("today", now=now)

    def test_invalid_value(self):
        with pytest.raises(ValueError, match="Unrecognized"):
            parse_since("not-a-date")

    def test_invalid_unit(self):
        with pytest.raises(ValueError):
            parse_since("7x")


class TestTokenizeForSuggest:
    """Tests for the natural-language tokenizer used by suggest."""

    def test_empty(self):
        assert tokenize_for_suggest("") == []

    def test_drops_stopwords(self):
        result = tokenize_for_suggest("the quick brown fox")
        assert "the" not in result
        assert "quick" in result
        assert "brown" in result
        assert "fox" in result

    def test_lowercases(self):
        result = tokenize_for_suggest("VENN Diagram")
        assert result == ["venn", "diagram"]

    def test_strips_punctuation(self):
        result = tokenize_for_suggest("compare, diff: overlap!")
        assert result == ["compare", "diff", "overlap"]

    def test_keeps_hyphenated(self):
        result = tokenize_for_suggest("opinionated post-alpha mark")
        assert "post-alpha" in result

    def test_drops_short_tokens(self):
        result = tokenize_for_suggest("a x ok venn")
        # 'ok' is a stopword? Actually no — it's just len-2, kept.
        # 'x' is len-1, dropped. 'a' is stopword.
        assert "x" not in result
        assert "a" not in result
        assert "venn" in result

    def test_all_stopwords(self):
        assert tokenize_for_suggest("the of and to with") == []


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
