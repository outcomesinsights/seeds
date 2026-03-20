"""Tests for seeds CLI commands."""

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner
from seeds.cli import main
from seeds.db import SEEDS_DIR, Database
from seeds.models import (
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
)


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture
def initialized_env():
    """Create a temp directory with initialized seeds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            # Initialize seeds
            db = Database()
            db.init()
            db.close()
            yield Path(tmpdir)
        finally:
            os.chdir(original_cwd)


@pytest.fixture
def env_with_seeds(initialized_env):
    """Create env with some test seeds."""
    db = Database()

    # Create some test seeds
    seeds = [
        Seed(id="seed-test1", title="Test Seed 1", status=SeedStatus.CAPTURED),
        Seed(id="seed-test2", title="Test Seed 2", status=SeedStatus.EXPLORING),
        Seed(id="seed-test3", title="Test Seed 3", status=SeedStatus.DEFERRED),
        Seed(id="seed-test1.1", title="Child Seed", status=SeedStatus.CAPTURED),
    ]
    for seed in seeds:
        db.create_seed(seed)

    db.close()
    yield initialized_env


class TestInitCommand:
    """Tests for 'seeds init' command."""

    def test_init_creates_seeds_directory(self, cli_runner):
        """Verify init creates .seeds directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = cli_runner.invoke(main, ["init"])
                assert result.exit_code == 0
                assert "Initialized seeds" in result.output
                assert (Path(tmpdir) / SEEDS_DIR).exists()
            finally:
                os.chdir(original_cwd)

    def test_init_already_initialized(self, cli_runner, initialized_env):
        """Verify init handles already initialized directory."""
        result = cli_runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "already initialized" in result.output


class TestJotCommand:
    """Tests for 'seeds jot' command."""

    def test_jot_creates_seed(self, cli_runner, initialized_env):
        """Verify jot creates a captured seed."""
        result = cli_runner.invoke(main, ["jot", "My quick thought"])
        assert result.exit_code == 0
        assert "seed-" in result.output
        assert "My quick thought" in result.output

        # Verify seed was created
        db = Database()
        seeds = db.list_seeds()
        assert len(seeds) == 1
        assert seeds[0].title == "My quick thought"
        assert seeds[0].status == SeedStatus.CAPTURED
        db.close()

    def test_jot_requires_init(self, cli_runner):
        """Verify jot fails if not initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = cli_runner.invoke(main, ["jot", "Test"])
                assert result.exit_code != 0
                assert "not initialized" in result.output
            finally:
                os.chdir(original_cwd)


class TestCreateCommand:
    """Tests for 'seeds create' command."""

    def test_create_with_title_only(self, cli_runner, initialized_env):
        """Verify create with just title works."""
        result = cli_runner.invoke(main, ["create", "--title", "New Idea"])
        assert result.exit_code == 0
        assert "Created seed" in result.output
        assert "New Idea" in result.output

    def test_create_with_type_and_tags(self, cli_runner, initialized_env):
        """Verify create with type and tags works."""
        result = cli_runner.invoke(
            main,
            [
                "create",
                "--title",
                "Decision",
                "--type",
                "decision",
                "--tags",
                "important,urgent",
            ],
        )
        assert result.exit_code == 0

        db = Database()
        seeds = db.list_seeds()
        assert len(seeds) == 1
        assert seeds[0].seed_type == SeedType.DECISION
        assert seeds[0].tags == ["important", "urgent"]
        db.close()

    def test_create_with_parent(self, cli_runner, env_with_seeds):
        """Verify create with parent creates child seed."""
        result = cli_runner.invoke(
            main,
            ["create", "--title", "New Child", "--parent", "seed-test1"],
        )
        assert result.exit_code == 0
        assert "seed-test1." in result.output
        assert "Parent: seed-test1" in result.output

    def test_create_with_invalid_parent(self, cli_runner, initialized_env):
        """Verify create with invalid parent fails."""
        result = cli_runner.invoke(
            main,
            ["create", "--title", "Child", "--parent", "nonexistent"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output


class TestListCommand:
    """Tests for 'seeds list' command."""

    def test_list_empty(self, cli_runner, initialized_env):
        """Verify list shows no seeds message when empty."""
        result = cli_runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "No seeds found" in result.output

    def test_list_shows_seeds(self, cli_runner, env_with_seeds):
        """Verify list shows all non-terminal seeds."""
        result = cli_runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output
        assert "seed-test2" in result.output
        assert "seed-test3" in result.output

    def test_list_filter_by_status(self, cli_runner, env_with_seeds):
        """Verify list can filter by status."""
        result = cli_runner.invoke(main, ["list", "--status", "captured"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output
        assert "seed-test2" not in result.output


class TestShowCommand:
    """Tests for 'seeds show' command."""

    def test_show_displays_seed(self, cli_runner, env_with_seeds):
        """Verify show displays seed details."""
        result = cli_runner.invoke(main, ["show", "seed-test1"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output
        assert "Test Seed 1" in result.output
        assert "Status: captured" in result.output

    def test_show_not_found(self, cli_runner, initialized_env):
        """Verify show handles nonexistent seed."""
        result = cli_runner.invoke(main, ["show", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_show_displays_resolution(self, cli_runner, env_with_seeds):
        """Verify show displays resolution for resolved seeds."""
        # Resolve with resolution text
        cli_runner.invoke(
            main,
            ["resolve", "seed-test2", "--resolution", "Decided to use approach B"],
        )

        result = cli_runner.invoke(main, ["show", "seed-test2"])
        assert result.exit_code == 0
        assert "Resolution: Decided to use approach B" in result.output

    def test_show_with_children(self, cli_runner, env_with_seeds):
        """Verify show displays children."""
        result = cli_runner.invoke(main, ["show", "seed-test1"])
        assert result.exit_code == 0
        assert "Children:" in result.output
        assert "seed-test1.1" in result.output


class TestStatusCommands:
    """Tests for status change commands (explore, defer, resolve, abandon)."""

    def test_explore_changes_status(self, cli_runner, env_with_seeds):
        """Verify explore changes status to exploring."""
        result = cli_runner.invoke(main, ["explore", "seed-test1"])
        assert result.exit_code == 0
        assert "Now exploring" in result.output

        db = Database()
        seed = db.get_seed("seed-test1")
        assert seed.status == SeedStatus.EXPLORING
        db.close()

    def test_defer_changes_status(self, cli_runner, env_with_seeds):
        """Verify defer changes status to deferred."""
        result = cli_runner.invoke(main, ["defer", "seed-test1"])
        assert result.exit_code == 0
        assert "Deferred" in result.output

        db = Database()
        seed = db.get_seed("seed-test1")
        assert seed.status == SeedStatus.DEFERRED
        db.close()

    def test_resolve_changes_status(self, cli_runner, env_with_seeds):
        """Verify resolve changes status to resolved."""
        result = cli_runner.invoke(main, ["resolve", "seed-test2"])
        assert result.exit_code == 0
        assert "Resolved" in result.output

        db = Database()
        seed = db.get_seed("seed-test2")
        assert seed.status == SeedStatus.RESOLVED
        assert seed.resolved_at is not None
        assert seed.resolution == ""
        db.close()

    def test_resolve_with_resolution(self, cli_runner, env_with_seeds):
        """Verify resolve captures resolution text."""
        result = cli_runner.invoke(
            main,
            ["resolve", "seed-test2", "--resolution", "Shipped in PR #42"],
        )
        assert result.exit_code == 0
        assert "Resolved" in result.output
        assert "Shipped in PR #42" in result.output

        db = Database()
        seed = db.get_seed("seed-test2")
        assert seed.status == SeedStatus.RESOLVED
        assert seed.resolution == "Shipped in PR #42"
        db.close()

    def test_abandon_changes_status(self, cli_runner, env_with_seeds):
        """Verify abandon changes status to abandoned."""
        result = cli_runner.invoke(main, ["abandon", "seed-test2"])
        assert result.exit_code == 0
        assert "Abandoned" in result.output

        db = Database()
        seed = db.get_seed("seed-test2")
        assert seed.status == SeedStatus.ABANDONED
        db.close()

    def test_abandon_with_reason(self, cli_runner, env_with_seeds):
        """Verify abandon captures reason in resolution field."""
        result = cli_runner.invoke(
            main,
            ["abandon", "seed-test2", "--reason", "Not feasible"],
        )
        assert result.exit_code == 0
        assert "Not feasible" in result.output

        db = Database()
        seed = db.get_seed("seed-test2")
        assert seed.resolution == "Not feasible"
        db.close()


class TestUpdateCommand:
    """Tests for 'seeds update' command."""

    def test_update_title(self, cli_runner, env_with_seeds):
        """Verify update can change title."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--title", "New Title"],
        )
        assert result.exit_code == 0
        assert "Updated" in result.output

        db = Database()
        seed = db.get_seed("seed-test1")
        assert seed.title == "New Title"
        db.close()

    def test_update_append_content(self, cli_runner, env_with_seeds):
        """Verify update --append adds to content."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--append", "Additional thoughts"],
        )
        assert result.exit_code == 0

        db = Database()
        seed = db.get_seed("seed-test1")
        assert "Additional thoughts" in seed.content
        db.close()

    def test_update_no_changes(self, cli_runner, env_with_seeds):
        """Verify update without changes shows message."""
        result = cli_runner.invoke(main, ["update", "seed-test1"])
        assert result.exit_code == 0
        assert "No changes specified" in result.output


class TestQuestionCommands:
    """Tests for question-related commands (question-seeds + relationships)."""

    def test_ask_creates_question_seed(self, cli_runner, env_with_seeds):
        """Verify ask creates a question-type seed with relationship."""
        result = cli_runner.invoke(
            main,
            ["ask", "What is the answer?", "--seed", "seed-test1"],
        )
        assert result.exit_code == 0
        assert "seeds-" in result.output
        assert "What is the answer?" in result.output
        assert "Attached to: seed-test1" in result.output

        db = Database()
        question_seeds = db.get_questions_for_seed("seed-test1")
        assert len(question_seeds) == 1
        assert question_seeds[0].title == "What is the answer?"
        assert question_seeds[0].seed_type == SeedType.QUESTION
        db.close()

    def test_ask_invalid_seed(self, cli_runner, initialized_env):
        """Verify ask fails with invalid seed."""
        result = cli_runner.invoke(
            main,
            ["ask", "Question?", "--seed", "nonexistent"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_answer_resolves_question_seed(self, cli_runner, env_with_seeds):
        """Verify answer sets content and resolves question-seed."""
        # Create a question-seed via ask
        result = cli_runner.invoke(
            main,
            ["ask", "What is the answer?", "--seed", "seed-test1"],
        )
        assert result.exit_code == 0
        # Extract question-seed ID from output
        q_id = result.output.split(":")[0].split()[-1]

        result = cli_runner.invoke(main, ["answer", q_id, "42"])
        assert result.exit_code == 0
        assert "42" in result.output

        db = Database()
        q_seed = db.get_seed(q_id)
        assert q_seed.content == "42"
        assert q_seed.status == SeedStatus.RESOLVED
        db.close()

    def test_questions_lists_open(self, cli_runner, env_with_seeds):
        """Verify questions shows open question-seeds."""
        # Create a question via ask
        result = cli_runner.invoke(
            main,
            ["ask", "Open question?", "--seed", "seed-test1"],
        )
        assert result.exit_code == 0

        result = cli_runner.invoke(main, ["questions"])
        assert result.exit_code == 0
        assert "Open question?" in result.output


class TestLinkCommand:
    """Tests for 'seeds link' command."""

    def test_link_creates_bidirectional_relationship(self, cli_runner, env_with_seeds):
        """Verify link creates bidirectional relates-to relationship."""
        result = cli_runner.invoke(
            main,
            ["link", "seed-test1", "--relates-to", "seed-test2"],
        )
        assert result.exit_code == 0
        assert "Linked" in result.output

        db = Database()
        rels = db.get_relationships(
            "seed-test1", rel_type=RelationType.RELATES_TO, direction="outbound"
        )
        assert len(rels) == 1
        assert rels[0].target_id == "seed-test2"
        # Reverse direction too
        rels2 = db.get_relationships(
            "seed-test2", rel_type=RelationType.RELATES_TO, direction="outbound"
        )
        assert len(rels2) == 1
        assert rels2[0].target_id == "seed-test1"
        db.close()

    def test_link_already_linked(self, cli_runner, env_with_seeds):
        """Verify link handles already linked seeds."""
        # Link first
        cli_runner.invoke(
            main,
            ["link", "seed-test1", "--relates-to", "seed-test2"],
        )

        # Try to link again
        result = cli_runner.invoke(
            main,
            ["link", "seed-test1", "--relates-to", "seed-test2"],
        )
        assert result.exit_code == 0
        assert "Already linked" in result.output

    def test_link_with_type(self, cli_runner, env_with_seeds):
        """Verify link with --type creates typed relationship."""
        result = cli_runner.invoke(
            main,
            ["link", "seed-test1", "--relates-to", "seed-test2", "--type", "questions"],
        )
        assert result.exit_code == 0
        assert "questions" in result.output

        db = Database()
        rels = db.get_relationships(
            "seed-test1", rel_type=RelationType.QUESTIONS, direction="outbound"
        )
        assert len(rels) == 1
        db.close()


class TestReadyDeferredBlocked:
    """Tests for ready, deferred, and blocked commands."""

    def test_ready_shows_captured_seeds(self, cli_runner, env_with_seeds):
        """Verify ready shows only captured seeds."""
        result = cli_runner.invoke(main, ["ready"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output
        assert "seed-test2" not in result.output  # exploring, not captured

    def test_deferred_shows_deferred_seeds(self, cli_runner, env_with_seeds):
        """Verify deferred shows only deferred seeds."""
        result = cli_runner.invoke(main, ["deferred"])
        assert result.exit_code == 0
        assert "seed-test3" in result.output
        assert "seed-test1" not in result.output

    def test_blocked_shows_blocked_seeds(self, cli_runner, env_with_seeds):
        """Verify blocked shows seeds with unresolved children."""
        result = cli_runner.invoke(main, ["blocked"])
        assert result.exit_code == 0
        # seed-test1 has child seed-test1.1 which is captured (unresolved)
        assert "seed-test1" in result.output


class TestTreeCommand:
    """Tests for 'seeds tree' command."""

    def test_tree_shows_hierarchy(self, cli_runner, env_with_seeds):
        """Verify tree shows parent-child hierarchy."""
        result = cli_runner.invoke(main, ["tree", "seed-test1"])
        assert result.exit_code == 0
        assert "Current:" in result.output
        assert "seed-test1" in result.output
        assert "Children:" in result.output
        assert "seed-test1.1" in result.output


class TestSyncCommand:
    """Tests for 'seeds sync' command."""

    def test_sync_exports_jsonl(self, cli_runner, env_with_seeds):
        """Verify sync exports to JSONL."""
        result = cli_runner.invoke(main, ["sync", "--flush-only"])
        assert result.exit_code == 0
        assert "Exported" in result.output
        assert "seeds.jsonl" in result.output

        jsonl_path = env_with_seeds / SEEDS_DIR / "seeds.jsonl"
        assert jsonl_path.exists()


class TestPrimeCommand:
    """Tests for 'seeds prime' command."""

    def test_prime_outputs_context_in_seeds_project(self, cli_runner, initialized_env):
        """Verify prime outputs workflow context when in a seeds project."""
        result = cli_runner.invoke(main, ["prime"])
        assert result.exit_code == 0
        assert "seeds Workflow Context" in result.output
        assert "seeds jot" in result.output

    def test_prime_silent_exit_outside_seeds_project(self, cli_runner):
        """Verify prime silently exits when not in a seeds project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = cli_runner.invoke(main, ["prime"])
                assert result.exit_code == 0
                assert result.output == ""  # Silent exit - no output
            finally:
                os.chdir(original_cwd)


class TestShowOutputFile:
    """Tests for 'seeds show --output-file' flag."""

    def test_show_output_file_creates_temp_file(self, cli_runner, env_with_seeds):
        """Verify show --output-file writes to temp file and prints path."""
        result = cli_runner.invoke(main, ["show", "seed-test1", "--output-file"])
        assert result.exit_code == 0
        # Output should be a file path
        output_path = result.output.strip()
        assert "seeds-seed-test1-" in output_path

        # File should contain seed details
        content = Path(output_path).read_text()
        assert "seed-test1" in content
        assert "Test Seed 1" in content

        # Cleanup
        Path(output_path).unlink(missing_ok=True)


class TestShowDetailFormatting:
    """Tests for format_seed_detail covering various fields."""

    def test_show_with_tags(self, cli_runner, initialized_env):
        """Verify show displays tags."""
        db = Database()
        seed = Seed(id="seed-tagged", title="Tagged Seed", tags=["important", "urgent"])
        db.create_seed(seed)
        db.close()

        result = cli_runner.invoke(main, ["show", "seed-tagged"])
        assert result.exit_code == 0
        assert "Tags:" in result.output
        assert "important" in result.output

    def test_show_with_content(self, cli_runner, initialized_env):
        """Verify show displays content."""
        db = Database()
        seed = Seed(
            id="seed-content", title="Content Seed", content="Detailed content here"
        )
        db.create_seed(seed)
        db.close()

        result = cli_runner.invoke(main, ["show", "seed-content"])
        assert result.exit_code == 0
        assert "Content:" in result.output
        assert "Detailed content here" in result.output

    def test_show_with_related(self, cli_runner, initialized_env):
        """Verify show displays related seeds via relationships."""
        db = Database()
        seed1 = Seed(id="seed-r1", title="Seed 1")
        seed2 = Seed(id="seed-r2", title="Seed 2")
        db.create_seed(seed1)
        db.create_seed(seed2)
        db.create_relationship("seed-r1", "seed-r2", RelationType.RELATES_TO)
        db.close()

        result = cli_runner.invoke(main, ["show", "seed-r1"])
        assert result.exit_code == 0
        assert "Related to:" in result.output
        assert "seed-r2" in result.output

    def test_show_child_displays_parent(self, cli_runner, env_with_seeds):
        """Verify show of child displays parent ID."""
        result = cli_runner.invoke(main, ["show", "seed-test1.1"])
        assert result.exit_code == 0
        assert "Parent: seed-test1" in result.output

    def test_show_with_questions_flag(self, cli_runner, env_with_seeds):
        """Verify show --questions displays question-seeds via relationships."""
        db = Database()
        q_seed = Seed(id="seeds-qshow", title="Show this?", seed_type=SeedType.QUESTION)
        db.create_seed(q_seed)
        db.create_relationship("seeds-qshow", "seed-test1", RelationType.QUESTIONS)
        db.close()

        result = cli_runner.invoke(main, ["show", "seed-test1", "--questions"])
        assert result.exit_code == 0
        assert "Questions:" in result.output
        assert "seeds-qshow" in result.output
        assert "Show this?" in result.output

    def test_show_with_answered_question(self, cli_runner, env_with_seeds):
        """Verify show displays answered question-seeds with content."""
        db = Database()
        q_seed = Seed(
            id="seeds-qanswered",
            title="Answered?",
            content="Yes it is",
            seed_type=SeedType.QUESTION,
            status=SeedStatus.RESOLVED,
        )
        db.create_seed(q_seed)
        db.create_relationship("seeds-qanswered", "seed-test1", RelationType.QUESTIONS)
        db.close()

        result = cli_runner.invoke(main, ["show", "seed-test1", "--questions"])
        assert result.exit_code == 0
        assert "Yes it is" in result.output


class TestEmptyStateLists:
    """Tests for empty state messages in ready/deferred/blocked."""

    def test_ready_no_seeds(self, cli_runner, initialized_env):
        """Verify ready shows message when no captured seeds."""
        result = cli_runner.invoke(main, ["ready"])
        assert result.exit_code == 0
        assert "No captured seeds" in result.output

    def test_deferred_no_seeds(self, cli_runner, initialized_env):
        """Verify deferred shows message when no deferred seeds."""
        result = cli_runner.invoke(main, ["deferred"])
        assert result.exit_code == 0
        assert "No deferred seeds" in result.output

    def test_blocked_no_seeds(self, cli_runner, initialized_env):
        """Verify blocked shows message when no blocked seeds."""
        result = cli_runner.invoke(main, ["blocked"])
        assert result.exit_code == 0
        assert "No blocked seeds" in result.output


class TestExploreWarning:
    """Tests for explore warning when seed is not captured."""

    def test_explore_non_captured_shows_warning(self, cli_runner, env_with_seeds):
        """Verify explore warns when seed is not in captured state."""
        result = cli_runner.invoke(main, ["explore", "seed-test2"])
        assert result.exit_code == 0
        assert "Warning" in result.output
        assert "not captured" in result.output


class TestUpdateContentAndTags:
    """Tests for update --content and --tags flags."""

    def test_update_content(self, cli_runner, env_with_seeds):
        """Verify update --content replaces content."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--content", "New content"],
        )
        assert result.exit_code == 0

        db = Database()
        seed = db.get_seed("seed-test1")
        assert seed.content == "New content"
        db.close()

    def test_update_tags(self, cli_runner, env_with_seeds):
        """Verify update --tags replaces tags."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--tags", "new,tags"],
        )
        assert result.exit_code == 0

        db = Database()
        seed = db.get_seed("seed-test1")
        assert seed.tags == ["new", "tags"]
        db.close()

    def test_update_clear_tags(self, cli_runner, env_with_seeds):
        """Verify update --tags '' clears tags."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--tags", ""],
        )
        assert result.exit_code == 0

        db = Database()
        seed = db.get_seed("seed-test1")
        assert seed.tags == []
        db.close()


class TestAnswerNotFound:
    """Test for answering nonexistent question-seed."""

    def test_answer_nonexistent_question(self, cli_runner, initialized_env):
        """Verify answer fails for nonexistent question-seed."""
        result = cli_runner.invoke(main, ["answer", "seeds-nonexistent", "The answer"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestQuestionsFiltering:
    """Tests for questions command filtering and empty state."""

    def test_questions_no_open(self, cli_runner, initialized_env):
        """Verify questions shows message when no open questions."""
        result = cli_runner.invoke(main, ["questions"])
        assert result.exit_code == 0
        assert "No open questions" in result.output

    def test_questions_filter_by_seed(self, cli_runner, env_with_seeds):
        """Verify questions --seed filters by seed."""
        db = Database()
        q1 = Seed(id="seeds-qs1", title="Q for seed1?", seed_type=SeedType.QUESTION)
        q2 = Seed(id="seeds-qs2", title="Q for seed2?", seed_type=SeedType.QUESTION)
        db.create_seed(q1)
        db.create_seed(q2)
        db.create_relationship("seeds-qs1", "seed-test1", RelationType.QUESTIONS)
        db.create_relationship("seeds-qs2", "seed-test2", RelationType.QUESTIONS)
        db.close()

        result = cli_runner.invoke(main, ["questions", "--seed", "seed-test1"])
        assert result.exit_code == 0
        assert "seeds-qs1" in result.output
        assert "seeds-qs2" not in result.output


class TestLinkNotFound:
    """Test for linking to nonexistent seed."""

    def test_link_nonexistent_related(self, cli_runner, env_with_seeds):
        """Verify link fails when related seed doesn't exist."""
        result = cli_runner.invoke(
            main,
            ["link", "seed-test1", "--relates-to", "nonexistent"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_link_nonexistent_source(self, cli_runner, initialized_env):
        """Verify link fails when source seed doesn't exist."""
        result = cli_runner.invoke(
            main,
            ["link", "nonexistent", "--relates-to", "also-nonexistent"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output


class TestTreeAdvanced:
    """Tests for tree with parent chains, grandchildren, and related seeds."""

    def test_tree_shows_parent_chain(self, cli_runner, env_with_seeds):
        """Verify tree shows ancestor chain for child seeds."""
        result = cli_runner.invoke(main, ["tree", "seed-test1.1"])
        assert result.exit_code == 0
        assert "Ancestors:" in result.output
        assert "seed-test1" in result.output

    def test_tree_shows_grandchildren(self, cli_runner, initialized_env):
        """Verify tree shows grandchildren."""
        db = Database()
        db.create_seed(Seed(id="seed-p", title="Parent"))
        db.create_seed(Seed(id="seed-p.1", title="Child"))
        db.create_seed(Seed(id="seed-p.1.1", title="Grandchild"))
        db.close()

        result = cli_runner.invoke(main, ["tree", "seed-p"])
        assert result.exit_code == 0
        assert "Children:" in result.output
        assert "seed-p.1" in result.output
        assert "seed-p.1.1" in result.output

    def test_tree_shows_related(self, cli_runner, initialized_env):
        """Verify tree shows related seeds via relationships."""
        db = Database()
        db.create_seed(Seed(id="seed-x", title="Main"))
        db.create_seed(Seed(id="seed-y", title="Related"))
        db.create_relationship("seed-x", "seed-y", RelationType.RELATES_TO)
        db.close()

        result = cli_runner.invoke(main, ["tree", "seed-x"])
        assert result.exit_code == 0
        assert "Related:" in result.output
        assert "seed-y" in result.output

    def test_tree_shows_missing_related(self, cli_runner, initialized_env):
        """Verify tree handles missing related seeds gracefully."""
        db = Database()
        db.create_seed(Seed(id="seed-x", title="Main"))
        db.create_seed(Seed(id="seed-gone", title="Will be deleted"))
        db.create_relationship("seed-x", "seed-gone", RelationType.RELATES_TO)
        # Delete the target but leave the relationship orphaned
        conn = db._get_conn()
        conn.execute("DELETE FROM seeds WHERE id = 'seed-gone'")
        conn.commit()
        db.close()

        result = cli_runner.invoke(main, ["tree", "seed-x"])
        assert result.exit_code == 0
        assert "seed-gone" in result.output
        assert "(not found)" in result.output


class TestDoctorCommand:
    """Tests for 'seeds doctor' command."""

    def test_doctor_passes_on_healthy_install(self, cli_runner, env_with_seeds):
        """Verify doctor passes on healthy installation."""
        # First sync to create JSONL
        cli_runner.invoke(main, ["sync", "--flush-only"])

        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "Database exists" in result.output
        assert "passed" in result.output

    def test_doctor_warns_no_jsonl(self, cli_runner, env_with_seeds):
        """Verify doctor warns when JSONL file doesn't exist."""
        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "No JSONL file" in result.output or "JSONL" in result.output

    def test_doctor_shows_warnings_count(self, cli_runner, initialized_env):
        """Verify doctor shows warning count when there are issues."""
        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        # No open seeds = warning, no JSONL = warning
        assert "warning" in result.output

    def test_doctor_shows_open_questions(self, cli_runner, env_with_seeds):
        """Verify doctor reports open question-seeds."""
        db = Database()
        q_seed = Seed(
            id="seeds-qdoc", title="Doctor question?", seed_type=SeedType.QUESTION
        )
        db.create_seed(q_seed)
        db.create_relationship("seeds-qdoc", "seed-test1", RelationType.QUESTIONS)
        db.close()

        # Create JSONL to avoid stale warning noise
        cli_runner.invoke(main, ["sync", "--flush-only"])

        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "open question" in result.output
