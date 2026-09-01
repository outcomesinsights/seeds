"""Tests for the seed-file store (:mod:`seeds.store`).

This is the surviving half of what tests/test_db.py covered. Every behaviour
here is one the CLI still depends on -- CRUD, listing and its filters,
hierarchy, id minting, blocking, tags, the project prefix, rename-prefix and
its body rewrites, relationships, and search. What went with test_db.py was the
machinery, not the behaviour: FTS5 index maintenance, ``suggest``'s scoring,
the relationships-table migration, and the JSONL bootstrap's prefix recovery
all describe a store that no longer exists.

The fixtures are the shared ``store`` and ``temp_dir`` from conftest.py -- an
isolated seed-file store in a temp directory, never the real project .seeds/.
"""

import os
import re
import tempfile
from datetime import timedelta
from pathlib import Path

import pytest

from seeds.models import RelationType, SeedStatus, SeedType, now_utc
from seeds.seedfile import SeedFileError, read_seed_file
from seeds.store import (
    Store,
    StoreError,
    find_seeds_dir,
    get_prefix,
    has_been_edited,
    has_prefix_configured,
    is_terminal,
    new_record,
    questions_asked_about,
    read_config,
    relates_to,
    write_prefix,
)


def add(store, seed_id, title="A title", **kwargs):
    """Write a seed straight into the store and hand the record back."""
    record = new_record(seed_id, title, **kwargs)
    if record.status in (SeedStatus.RESOLVED, SeedStatus.ABANDONED):
        record.resolved_at = record.updated_at
    store.create(record)
    return record


class TestLayout:
    def test_a_bare_directory_is_not_a_store(self, temp_dir):
        assert not Store(temp_dir / ".seeds").is_initialized()

    def test_the_seeds_subdir_is_what_makes_it_one(self, store):
        assert store.is_initialized()
        assert store.files_dir.name == "seeds"

    def test_the_path_is_the_id_verbatim_dots_included(self, store):
        """§1.1: the filename stem is the id, with no escaping and no nesting.

        `seeds show` is one path computation and one file read because of
        this, so a change that makes the path a search instead of a
        concatenation breaks the property the layout was chosen for.
        """
        assert store.path_for("seeds-lcfa.6.1").name == "seeds-lcfa.6.1.md"
        assert store.path_for("seeds-lcfa.6.1").parent == store.files_dir


class TestSeedCRUD:
    def test_create_and_get(self, store, sample_record):
        store.create(sample_record)

        read = store.get("seed-test")
        assert read.id == "seed-test"
        assert read.title == "Test Seed"
        assert read.body.rstrip("\n") == "This is test content"
        assert read.tags == ["test", "sample"]

    def test_create_writes_a_file(self, store, sample_record):
        store.create(sample_record)
        assert (store.files_dir / "seed-test.md").is_file()

    def test_get_nonexistent_returns_none(self, store):
        assert store.get("seed-nope") is None

    def test_get_a_malformed_id_returns_none_rather_than_raising(self, store):
        """A lookup of something that cannot be an id is a miss, not a crash.

        `seeds show ../etc/passwd` has to answer "not found"; path_for refuses
        the id outright, so get has to rule on the shape before computing it.
        """
        assert store.get("../etc/passwd") is None

    def test_create_refuses_to_overwrite(self, store, sample_record):
        store.create(sample_record)
        with pytest.raises(StoreError, match="already exists"):
            store.create(sample_record)

    def test_save_bumps_updated_at(self, store, sample_record):
        store.create(sample_record)
        record = store.get("seed-test")
        assert not has_been_edited(record)

        record.title = "Edited"
        store.save(record)

        assert has_been_edited(store.get("seed-test"))

    def test_save_without_touch_writes_the_timestamps_verbatim(
        self, store, sample_record
    ):
        store.create(sample_record)
        record = store.get("seed-test")
        record.title = "Edited"
        store.save(record, touch=False)

        assert not has_been_edited(store.get("seed-test"))

    def test_a_fresh_record_mirrors_created_at(self, store):
        """§3: updated_at == created_at means "never edited" and must be exact.

        Two now_utc() calls drift by microseconds, which would make every new
        seed read as already edited and arm the --content guard on capture.
        """
        record = new_record("seeds-a1", "New")
        assert record.updated_at == record.created_at

    def test_delete_removes_the_file(self, store, sample_record):
        store.create(sample_record)
        assert store.delete("seed-test")
        assert not (store.files_dir / "seed-test.md").exists()
        assert store.get("seed-test") is None

    def test_delete_nonexistent_returns_false(self, store):
        assert store.delete("seed-nope") is False

    def test_a_file_the_reader_refuses_fails_the_whole_corpus(self, store):
        """Strict in both directions, like `seeds check`.

        Skipping an unreadable file would drop a seed out of the answer to a
        query with nothing to say so -- the silent wrongness the format was
        changed to escape.
        """
        add(store, "seeds-a1")
        (store.files_dir / "seeds-b2.md").write_text("not a seed file\n")

        with pytest.raises(SeedFileError):
            store.all()

    def test_a_filename_that_is_not_an_id_fails_the_corpus(self, store):
        add(store, "seeds-a1")
        (store.files_dir / "NOTES.md").write_text("scratch\n")

        with pytest.raises(StoreError, match="not a valid seed id"):
            store.all()

    def test_reading_a_store_that_is_not_there_names_the_recovery(self, temp_dir):
        with pytest.raises(StoreError, match="seeds convert"):
            Store(temp_dir / ".seeds").all()


class TestListing:
    def test_empty(self, store):
        assert store.list_seeds() == []

    def test_terminal_seeds_are_excluded_by_default(self, store):
        add(store, "seeds-a1", status=SeedStatus.CAPTURED)
        add(store, "seeds-b2", status=SeedStatus.RESOLVED)
        add(store, "seeds-c3", status=SeedStatus.ABANDONED)

        assert [r.id for r in store.list_seeds()] == ["seeds-a1"]

    def test_include_terminal(self, store):
        add(store, "seeds-a1", status=SeedStatus.CAPTURED)
        add(store, "seeds-b2", status=SeedStatus.RESOLVED)

        assert len(store.list_seeds(include_terminal=True)) == 2

    def test_filter_by_status(self, store):
        add(store, "seeds-a1", status=SeedStatus.CAPTURED)
        add(store, "seeds-b2", status=SeedStatus.EXPLORING)

        got = store.list_seeds(status=SeedStatus.EXPLORING)
        assert [r.id for r in got] == ["seeds-b2"]

    def test_an_explicit_terminal_status_is_honoured(self, store):
        """--status resolved must return resolved seeds, not nothing."""
        add(store, "seeds-a1", status=SeedStatus.RESOLVED)

        got = store.list_seeds(status=SeedStatus.RESOLVED)
        assert [r.id for r in got] == ["seeds-a1"]

    def test_filter_by_type(self, store):
        add(store, "seeds-a1", seed_type="idea")
        add(store, "seeds-b2", seed_type="question")

        assert [r.id for r in store.list_seeds(seed_type="question")] == ["seeds-b2"]

    def test_filter_by_tag(self, store):
        add(store, "seeds-a1", tags=["storage", "format"])
        add(store, "seeds-b2", tags=["format"])
        add(store, "seeds-c3")

        got = store.list_seeds(tag="storage")
        assert [r.id for r in got] == ["seeds-a1"]

    def test_since_filters_on_updated_at(self, store):
        old = add(store, "seeds-a1")
        old.updated_at = now_utc() - timedelta(days=30)
        store.save(old, touch=False)
        add(store, "seeds-b2")

        cutoff = now_utc() - timedelta(days=1)
        assert [r.id for r in store.list_seeds(since=cutoff)] == ["seeds-b2"]

    def test_sort_by_updated(self, store):
        first = add(store, "seeds-a1")
        add(store, "seeds-b2")
        first.updated_at = now_utc() + timedelta(days=1)
        store.save(first, touch=False)

        got = store.list_seeds(sort_by="updated")
        assert [r.id for r in got] == ["seeds-a1", "seeds-b2"]

    def test_an_unknown_sort_is_refused(self, store):
        with pytest.raises(ValueError, match="sort_by"):
            store.list_seeds(sort_by="sideways")

    def test_ties_break_on_id_so_the_order_is_stable(self, store):
        """A converted corpus is full of identical timestamps.

        Without a tiebreak the list order would depend on directory order,
        which makes two runs of the same command disagree.
        """
        stamp = now_utc()
        for seed_id in ("seeds-c3", "seeds-a1", "seeds-b2"):
            record = new_record(seed_id, "T")
            record.created_at = record.updated_at = stamp
            store.create(record)

        assert [r.id for r in store.list_seeds()] == [
            "seeds-c3",
            "seeds-b2",
            "seeds-a1",
        ]


class TestHierarchy:
    def test_no_children(self, store):
        add(store, "seeds-a1")
        assert store.get_children("seeds-a1") == []

    def test_direct_children_only(self, store):
        """A grandchild is not a child, and the parent field says so.

        Globbing `seeds-a1.*` would match `seeds-a1.1.1` too, and excluding it
        means counting dots -- parsing structure back out of a name (§1.1).
        """
        add(store, "seeds-a1")
        add(store, "seeds-a1.1")
        add(store, "seeds-a1.2")
        add(store, "seeds-a1.1.1")

        assert [r.id for r in store.get_children("seeds-a1")] == [
            "seeds-a1.1",
            "seeds-a1.2",
        ]

    def test_next_child_id_first(self, store):
        add(store, "seeds-a1")
        assert store.next_child_id("seeds-a1") == "seeds-a1.1"

    def test_next_child_id_after_gaps(self, store):
        add(store, "seeds-a1")
        add(store, "seeds-a1.1")
        add(store, "seeds-a1.5")
        assert store.next_child_id("seeds-a1") == "seeds-a1.6"

    def test_a_child_carries_its_parent(self, store):
        record = add(store, "seeds-a1.1")
        assert store.get("seeds-a1.1").parent == "seeds-a1"
        assert record.parent == "seeds-a1"

    def test_a_top_level_seed_carries_no_parent(self, store):
        add(store, "seeds-a1")
        assert store.get("seeds-a1").parent is None


class TestNextId:
    HASH_ID_RE = re.compile(r"^seeds-[0-9a-z]{3,8}$")

    def test_mints_a_hash_id_on_an_empty_store(self, store):
        assert self.HASH_ID_RE.match(store.next_id(seed_text="a thought"))

    def test_never_reissues_an_existing_id(self, store):
        add(store, "seeds-5", "Grandfathered sequential")
        for _ in range(20):
            assert store.next_id(seed_text="probe") != "seeds-5"

    def test_children_do_not_count_toward_the_adaptive_length(self, store):
        add(store, "seeds-a1")
        for n in range(1, 30):
            add(store, f"seeds-a1.{n}")

        minted = store.next_id(seed_text="probe")
        assert len(minted.split("-", 1)[1]) == 3

    def test_a_custom_prefix_is_used(self, store):
        assert store.next_id("demo", seed_text="x").startswith("demo-")

    def test_the_configured_prefix_is_the_default(self, store):
        store.set_prefix("demo")
        assert store.next_id(seed_text="x").startswith("demo-")


class TestBlocking:
    def test_not_blocked_with_no_children(self, store):
        add(store, "seeds-a1")
        assert not store.is_blocked("seeds-a1")

    def test_not_blocked_when_every_child_is_terminal(self, store):
        add(store, "seeds-a1")
        add(store, "seeds-a1.1", status=SeedStatus.RESOLVED)
        add(store, "seeds-a1.2", status=SeedStatus.ABANDONED)
        assert not store.is_blocked("seeds-a1")

    def test_blocked_by_an_unresolved_child(self, store):
        add(store, "seeds-a1")
        add(store, "seeds-a1.1", status=SeedStatus.CAPTURED)
        assert store.is_blocked("seeds-a1")

    def test_blocked_by_an_unresolved_question_seed(self, store):
        add(store, "seeds-a1")
        add(store, "seeds-q1", seed_type=SeedType.QUESTION.value)
        store.link("seeds-q1", "seeds-a1", RelationType.QUESTIONS)

        assert store.is_blocked("seeds-a1")

    def test_not_blocked_once_the_question_resolves(self, store):
        add(store, "seeds-a1")
        add(store, "seeds-q1", seed_type=SeedType.QUESTION.value)
        store.link("seeds-q1", "seeds-a1", RelationType.QUESTIONS)

        question = store.get("seeds-q1")
        question.status = SeedStatus.RESOLVED
        question.resolved_at = now_utc()
        store.save(question)

        assert not store.is_blocked("seeds-a1")

    def test_blocked_lists_only_non_terminal_seeds(self, store):
        add(store, "seeds-a1")
        add(store, "seeds-a1.1")
        add(store, "seeds-b2", status=SeedStatus.RESOLVED)
        add(store, "seeds-b2.1")

        assert [r.id for r in store.blocked()] == ["seeds-a1"]


class TestRelationships:
    def test_relates_to_is_stored_at_both_ends_as_itself(self, store):
        """§5.1/§5.2: symmetric types store themselves at the far end."""
        add(store, "seeds-a1")
        add(store, "seeds-b2")

        store.link("seeds-a1", "seeds-b2", RelationType.RELATES_TO)

        near = store.get("seeds-a1").relationships
        far = store.get("seeds-b2").relationships
        assert [(e.target_id, e.rel_type) for e in near] == [
            ("seeds-b2", RelationType.RELATES_TO)
        ]
        assert [(e.target_id, e.rel_type) for e in far] == [
            ("seeds-a1", RelationType.RELATES_TO)
        ]

    def test_a_directional_type_stores_its_named_inverse(self, store):
        add(store, "seeds-q1")
        add(store, "seeds-a1")

        store.link("seeds-q1", "seeds-a1", RelationType.QUESTIONS)

        assert [
            (e.target_id, e.rel_type) for e in store.get("seeds-a1").relationships
        ] == [("seeds-q1", RelationType.QUESTIONED_BY)]

    def test_both_halves_share_one_created_at(self, store):
        """It is what lets `seeds check` pair the two ends of one edge."""
        add(store, "seeds-a1")
        add(store, "seeds-b2")

        store.link("seeds-a1", "seeds-b2", RelationType.RELATES_TO)

        near = store.get("seeds-a1").relationships[0]
        far = store.get("seeds-b2").relationships[0]
        assert near.created_at == far.created_at

    def test_linking_twice_does_not_duplicate_the_edge(self, store):
        add(store, "seeds-a1")
        add(store, "seeds-b2")

        store.link("seeds-a1", "seeds-b2", RelationType.RELATES_TO)
        store.link("seeds-a1", "seeds-b2", RelationType.RELATES_TO)

        assert len(store.get("seeds-a1").relationships) == 1

    def test_linking_a_missing_seed_is_refused(self, store):
        add(store, "seeds-a1")
        with pytest.raises(StoreError, match="seeds-b2 not found"):
            store.link("seeds-a1", "seeds-b2", RelationType.RELATES_TO)

    def test_relates_to_helper_reads_only_that_type(self, store):
        add(store, "seeds-a1")
        add(store, "seeds-b2")
        add(store, "seeds-q1")
        store.link("seeds-a1", "seeds-b2", RelationType.RELATES_TO)
        store.link("seeds-q1", "seeds-a1", RelationType.QUESTIONS)

        assert relates_to(store.get("seeds-a1")) == ["seeds-b2"]

    def test_questions_asked_about(self, store):
        add(store, "seeds-a1")
        add(store, "seeds-q1")
        store.link("seeds-q1", "seeds-a1", RelationType.QUESTIONS)

        assert questions_asked_about(store.get("seeds-q1")) == ["seeds-a1"]

    def test_questions_for_reads_the_far_end(self, store):
        add(store, "seeds-a1")
        add(store, "seeds-q1", "Why?")
        store.link("seeds-q1", "seeds-a1", RelationType.QUESTIONS)

        assert [r.id for r in store.questions_for("seeds-a1")] == ["seeds-q1"]

    def test_questions_for_ignores_relates_to(self, store):
        add(store, "seeds-a1")
        add(store, "seeds-b2")
        store.link("seeds-a1", "seeds-b2", RelationType.RELATES_TO)

        assert store.questions_for("seeds-a1") == []


class TestTags:
    def test_no_tags(self, store):
        assert store.all_tags() == []

    def test_unique_and_sorted(self, store):
        add(store, "seeds-a1", tags=["storage", "format"])
        add(store, "seeds-b2", tags=["format", "agents"])

        assert store.all_tags() == ["agents", "format", "storage"]


class TestRetype:
    def test_changes_every_matching_seed(self, store):
        add(store, "seeds-a1", seed_type="ideea")
        add(store, "seeds-b2", seed_type="ideea")
        add(store, "seeds-c3", seed_type="idea")

        assert store.retype("ideea", "idea") == ["seeds-a1", "seeds-b2"]
        assert store.get("seeds-a1").seed_type == "idea"
        assert store.get("seeds-c3").seed_type == "idea"

    def test_dry_run_writes_nothing(self, store):
        add(store, "seeds-a1", seed_type="ideea")

        assert store.retype("ideea", "idea", dry_run=True) == ["seeds-a1"]
        assert store.get("seeds-a1").seed_type == "ideea"

    def test_no_match_is_a_noop(self, store):
        add(store, "seeds-a1", seed_type="idea")
        assert store.retype("nonexistent", "idea") == []


class TestPrefixConfig:
    def test_default_when_unconfigured(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        seeds_dir.mkdir()
        assert get_prefix(seeds_dir) == "seeds"
        assert not has_prefix_configured(seeds_dir)

    def test_set_and_get(self, store):
        store.set_prefix("demo")
        assert store.get_prefix() == "demo"
        assert store.has_prefix_configured()

    def test_it_lands_in_config_yaml(self, store):
        """§9: the prefix is a property of the project, tracked beside the tree.

        Not frontmatter -- 312 copies of one value would only drift -- and not
        derived from filenames, since a repo with no seeds yet still has to
        know what to name its first one.
        """
        store.set_prefix("demo")
        assert (store.seeds_dir / "config.yaml").read_text() == "prefix: demo\n"

    def test_an_invalid_prefix_is_refused(self, store):
        with pytest.raises(StoreError, match="Invalid prefix"):
            store.set_prefix("123bad")

    def test_other_settings_survive_a_prefix_write(self, store):
        (store.seeds_dir / "config.yaml").write_text("prefix: old\nsomething: kept\n")

        write_prefix(store.seeds_dir, "new")

        assert read_config(store.seeds_dir) == {
            "prefix": "new",
            "something": "kept",
        }

    def test_comments_and_blank_lines_are_skipped(self, store):
        (store.seeds_dir / "config.yaml").write_text(
            "# the project prefix\n\nprefix: demo\n"
        )
        assert get_prefix(store.seeds_dir) == "demo"

    def test_a_quoted_value_reads_as_the_bare_string(self, store):
        (store.seeds_dir / "config.yaml").write_text('prefix: "demo"\n')
        assert get_prefix(store.seeds_dir) == "demo"


class TestFindSeedsDir:
    def test_in_the_current_directory(self, temp_dir):
        (temp_dir / ".seeds").mkdir()
        original = os.getcwd()
        os.chdir(temp_dir)
        try:
            assert find_seeds_dir() == Path.cwd() / ".seeds"
        finally:
            os.chdir(original)

    def test_in_a_parent_directory(self, temp_dir):
        (temp_dir / ".seeds").mkdir()
        nested = temp_dir / "a" / "b"
        nested.mkdir(parents=True)
        original = os.getcwd()
        os.chdir(nested)
        try:
            assert find_seeds_dir().name == ".seeds"
        finally:
            os.chdir(original)

    def test_none_when_there_is_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = os.getcwd()
            os.chdir(tmpdir)
            try:
                assert find_seeds_dir() is None
            finally:
                os.chdir(original)


class TestSearch:
    """`seeds search` over ripgrep (bead seeds-4co.10).

    What went with FTS5 is stemming and ranking, and only stemming is a
    behaviour a test can state. Recall did not go with it: on a real query grep
    returned 72 hits to FTS's 77 and found one FTS missed.
    """

    def test_matches_the_title(self, store):
        add(store, "seeds-a1", "Deliberation capture")
        add(store, "seeds-b2", "Something else")

        assert [r.id for r in store.search("Deliberation")] == ["seeds-a1"]

    def test_matches_the_body(self, store):
        add(store, "seeds-a1", "A title", body="the quick brown fox")
        add(store, "seeds-b2", "Another title")

        assert [r.id for r in store.search("brown fox")] == ["seeds-a1"]

    def test_matches_a_tag(self, store):
        add(store, "seeds-a1", tags=["storage"])
        add(store, "seeds-b2", tags=["agents"])

        assert [r.id for r in store.search("storage")] == ["seeds-a1"]

    def test_is_case_insensitive(self, store):
        add(store, "seeds-a1", "Deliberation capture")
        assert [r.id for r in store.search("DELIBERATION")] == ["seeds-a1"]

    def test_a_hyphenated_term_is_matched_literally(self, store):
        """The whole reason the FTS query had to be sanitized before.

        `seeds-to-beads` was parsed as FTS5 syntax and raised rather than
        searching. ripgrep has no such syntax to trip over.
        """
        add(store, "seeds-a1", "The seeds-to-beads workflow")
        assert [r.id for r in store.search("seeds-to-beads")] == ["seeds-a1"]

    def test_terminal_seeds_are_excluded_by_default(self, store):
        add(store, "seeds-a1", "Deliberation capture")
        add(store, "seeds-b2", "Deliberation elsewhere", status=SeedStatus.RESOLVED)
        add(store, "seeds-c3", "Deliberation dropped", status=SeedStatus.ABANDONED)

        assert [r.id for r in store.search("Deliberation")] == ["seeds-a1"]

    def test_include_terminal(self, store):
        add(store, "seeds-a1", "Deliberation capture")
        add(store, "seeds-b2", "Deliberation elsewhere", status=SeedStatus.RESOLVED)

        got = store.search("Deliberation", include_terminal=True)
        assert [r.id for r in got] == ["seeds-a1", "seeds-b2"]

    def test_the_status_filter_does_not_match_a_body_mentioning_it(self, store):
        """The filter is anchored to the frontmatter line, not to the word.

        A seed whose body discusses "status: resolved" is still open, and
        excluding it would be a silently short answer.
        """
        add(store, "seeds-a1", "Live", body="we write `status: resolved` on close")

        assert [r.id for r in store.search("close")] == ["seeds-a1"]

    def test_no_results(self, store):
        add(store, "seeds-a1", "Deliberation capture")
        assert store.search("nonexistent") == []

    def test_an_empty_store_returns_nothing_rather_than_searching_the_cwd(self, store):
        """ripgrep with no path arguments searches the working directory.

        With every seed filtered out there is nothing to hand it, and calling
        it anyway would answer a question nobody asked -- with matches from
        source files that are not seeds.
        """
        add(store, "seeds-a1", "Resolved", status=SeedStatus.RESOLVED)
        assert store.search("Resolved") == []

    def test_results_are_id_sorted(self, store):
        for seed_id in ("seeds-c3", "seeds-a1", "seeds-b2"):
            add(store, seed_id, "Deliberation capture")

        got = store.search("Deliberation")
        assert [r.id for r in got] == ["seeds-a1", "seeds-b2", "seeds-c3"]

    def test_a_malformed_regex_raises_rather_than_returning_nothing(self, store):
        """A search that silently finds nothing because the pattern was broken
        is the green-while-broken shape this project refuses everywhere."""
        add(store, "seeds-a1", "Deliberation capture")

        with pytest.raises(StoreError, match="ripgrep failed"):
            store.search("(unclosed")


class TestRenamePrefix:
    def test_renames_ids_and_files(self, store):
        add(store, "seeds-1", "first")
        add(store, "seeds-2", "second")

        id_map, _ = store.rename_prefix("demo")

        assert id_map == {"seeds-1": "demo-1", "seeds-2": "demo-2"}
        assert sorted(p.name for p in store.files_dir.glob("*.md")) == [
            "demo-1.md",
            "demo-2.md",
        ]
        assert store.get("demo-1").id == "demo-1"

    def test_children_and_their_parent_field_follow(self, store):
        add(store, "seeds-1")
        add(store, "seeds-1.1")

        store.rename_prefix("demo")

        assert store.get("demo-1.1").parent == "demo-1"

    def test_edges_are_rewritten_at_both_ends(self, store):
        add(store, "seeds-1")
        add(store, "seeds-2")
        store.link("seeds-1", "seeds-2", RelationType.RELATES_TO)

        store.rename_prefix("demo")

        assert relates_to(store.get("demo-1")) == ["demo-2"]
        assert relates_to(store.get("demo-2")) == ["demo-1"]

    def test_the_new_prefix_is_recorded(self, store):
        add(store, "seeds-1")
        store.rename_prefix("demo")
        assert store.get_prefix() == "demo"

    def test_a_non_matching_prefix_is_left_alone(self, store):
        add(store, "other-1")
        add(store, "seeds-1")

        id_map, _ = store.rename_prefix("demo")

        assert id_map == {"seeds-1": "demo-1"}
        assert store.get("other-1") is not None

    def test_a_word_shaped_suffix_is_not_an_id_to_rename(self, store):
        """`seeds-experiment` is prose-shaped, not a minted id."""
        add(store, "seeds-experiment")

        id_map, _ = store.rename_prefix("demo")

        assert id_map == {}
        assert store.get("seeds-experiment") is not None

    def test_renaming_to_the_same_prefix_is_a_noop(self, store):
        store.set_prefix("seeds")
        add(store, "seeds-1")

        assert store.rename_prefix("seeds") == ({}, [])

    def test_an_invalid_prefix_is_refused(self, store):
        with pytest.raises(StoreError, match="Invalid prefix"):
            store.rename_prefix("123bad")

    def test_a_collision_is_refused_before_anything_is_written(self, store):
        add(store, "seeds-1")
        add(store, "demo-1")

        with pytest.raises(StoreError, match="collide"):
            store.rename_prefix("demo")

        assert store.get("seeds-1") is not None

    def test_both_id_schemes_are_covered(self, store):
        """Hash ids and grandfathered sequential ones routinely coexist.

        Leaving either behind strands those seeds under the old prefix.
        """
        for seed_id in ("seeds-112", "seeds-060", "seeds-k3n7", "seeds-k3n7.1"):
            add(store, seed_id)

        id_map, _ = store.rename_prefix("demo")

        assert set(id_map) == {
            "seeds-112",
            "seeds-060",
            "seeds-k3n7",
            "seeds-k3n7.1",
        }

    def test_a_dry_run_writes_nothing(self, store):
        add(store, "seeds-1")

        id_map, _ = store.rename_prefix("demo", dry_run=True)

        assert id_map == {"seeds-1": "demo-1"}
        assert store.get("seeds-1") is not None
        assert store.get_prefix() == "seeds"

    def test_the_rename_does_not_count_as_an_edit(self, store):
        """updated_at == created_at is the "never edited" test (§3).

        Bumping it across the whole corpus at once would erase that signal for
        every seed, for a change that is not deliberation.
        """
        add(store, "seeds-1")

        store.rename_prefix("demo")

        assert not has_been_edited(store.get("demo-1"))


class TestRenamePrefixBodyRewrites:
    def test_rewrites_refs_in_the_body(self, store):
        add(store, "seeds-1")
        add(store, "seeds-2", body="see seeds-1 for the argument")

        _, changes = store.rename_prefix("demo")

        assert "see demo-1" in store.get("demo-2").body
        assert [c.field for c in changes] == ["body"]

    def test_rewrites_refs_in_the_title(self, store):
        add(store, "seeds-1")
        add(store, "seeds-2", "follows seeds-1")

        store.rename_prefix("demo")

        assert store.get("demo-2").title == "follows demo-1"

    def test_rewrites_refs_in_the_resolution(self, store):
        add(store, "seeds-1")
        record = add(store, "seeds-2", status=SeedStatus.RESOLVED)
        record.resolution = "settled by seeds-1"
        store.save(record)

        store.rename_prefix("demo")

        assert store.get("demo-2").resolution == "settled by demo-1"

    def test_rewrites_a_child_reference(self, store):
        add(store, "seeds-1")
        add(store, "seeds-1.2")
        add(store, "seeds-2", body="see seeds-1.2")

        store.rename_prefix("demo")

        assert "see demo-1.2" in store.get("demo-2").body

    def test_rewrites_a_markdown_link(self, store):
        add(store, "seeds-1")
        add(store, "seeds-2", body="[seeds-1](./seeds-1.md)")

        store.rename_prefix("demo")

        assert "[demo-1]" in store.get("demo-2").body

    def test_leaves_hash_shaped_prose_alone(self, store):
        """`seeds-native` is valid base36 and also ordinary English.

        Membership in the store is the only sound test, so a hash-shaped token
        is rewritten only when it names an id actually being renamed.
        """
        add(store, "seeds-1")
        add(store, "seeds-2", body="a seeds-native workflow")

        store.rename_prefix("demo")

        assert "seeds-native" in store.get("demo-2").body

    def test_no_rewrite_bodies_leaves_the_text_untouched(self, store):
        add(store, "seeds-1")
        add(store, "seeds-2", body="see seeds-1")

        store.rename_prefix("demo", rewrite_bodies=False)

        assert "see seeds-1" in store.get("demo-2").body


class TestTerminality:
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (SeedStatus.CAPTURED, False),
            (SeedStatus.EXPLORING, False),
            (SeedStatus.DEFERRED, False),
            (SeedStatus.RESOLVED, True),
            (SeedStatus.ABANDONED, True),
        ],
    )
    def test_is_terminal(self, status, expected):
        record = new_record("seeds-a1", "T", status=status)
        assert is_terminal(record) is expected


class TestAtomicWrites:
    def test_no_temp_file_is_left_behind(self, store, sample_record):
        """§7: write to a temp file in the same directory, then os.replace."""
        store.create(sample_record)
        assert [p.name for p in store.files_dir.iterdir()] == ["seed-test.md"]

    def test_a_rewrite_of_an_unchanged_record_is_byte_identical(
        self, store, sample_record
    ):
        """The field order the writer emits exists for exactly this.

        Re-writing an unchanged seed has to be a no-op at the byte level, so
        that a real edit shows as a small diff instead of a whole-file one.
        """
        store.create(sample_record)
        before = store.path_for("seed-test").read_bytes()

        record = read_seed_file(store.path_for("seed-test"))
        store.save(record, touch=False)

        assert store.path_for("seed-test").read_bytes() == before
