"""What seeds says on a repo that has not been converted (bead seeds-4co.18).

Rollout is on-demand: repos are converted the first time someone uses seeds in
them. There is no migration guide and no batch tool, so **the refusal message
IS the migration experience** — which makes it a shipped surface with tests,
not incidental error text.

Measured before this bead, 19 of 22 data-touching commands already refused
correctly and three did not. The one that mattered was ``seeds prime``: it
exited 0 and emitted normal-looking workflow context, because the static half
of that document renders without a store and the live-state block was silently
absent. An agent has no reason to suspect a block is missing and concludes the
project has no seeds; the measured example had 29.

@aguynamedryan ruled that prime must NOT abort — aborting loses the agent the
verbs as well as the information — so :class:`TestPrime` asserts the shape that
ruling produces: exit 0, the notice at the top *and* where the state block
would have been, and no seed count anywhere (reading the legacy store to
produce one was asked for and declined).

:class:`TestEveryDataTouchingCommand` is the sweep. It is parametrized over the
real command list rather than spot-checking, because "19 of 22" is exactly the
kind of gap that reappears the next time a verb is added.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from seeds.cli import main
from seeds.convert import convert
from seeds.models import Seed, SeedStatus
from seeds.prime import PRIME_OUTPUT, PRIME_SHORT_OUTPUT
from seeds.store import needs_conversion
from tests.githelpers import git, git_init
from tests.legacyhelpers import LegacyWriter, build_legacy_db

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

#: Every verb that reads, adds or updates seed data, with arguments that get
#: past click's own parsing so the store guard is what answers.
DATA_TOUCHING = [
    ("list",),
    ("ready",),
    ("show", "seeds-a1"),
    ("tree", "seeds-a1"),
    ("search", "anything"),
    ("questions",),
    ("blocked",),
    ("deferred",),
    ("recent",),
    ("jot", "a thought"),
    ("create", "--title", "A title"),
    ("update", "seeds-a1", "--append", "more"),
    ("resolve", "seeds-a1"),
    ("explore", "seeds-a1"),
    ("defer", "seeds-a1"),
    ("abandon", "seeds-a1"),
    ("link", "seeds-a1", "--relates-to", "seeds-b2"),
    ("ask", "A question?", "--seed", "seeds-a1"),
    ("retype", "--from", "idea", "--to", "concern"),
    ("history", "seeds-a1"),
    ("prefix",),
    ("doctor",),
    ("check",),
    ("export", "--json"),
]


@pytest.fixture
def unconverted(temp_dir, monkeypatch):
    """A pre-0.7 store: the JSONL is here, ``.seeds/seeds/`` is not."""
    seeds_dir = temp_dir / ".seeds"
    seeds_dir.mkdir(parents=True)
    (seeds_dir / "seeds.jsonl").write_text(
        json.dumps(
            {
                "format_version": 2,
                "id": "seeds-a1",
                "title": "A seed that predates the conversion",
                "content": "Deliberation.",
                "status": "captured",
                "seed_type": "idea",
                "tags": [],
                "created_at": T0.isoformat(),
                "updated_at": T0.isoformat(),
                "resolved_at": None,
                "resolution": "",
                "relationships": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(temp_dir)
    return seeds_dir


class TestTheStateItself:
    def test_needs_conversion_is_the_jsonl_without_the_tree(self, unconverted):
        assert needs_conversion(unconverted) is True

    def test_an_initialized_store_does_not_need_conversion(self, unconverted):
        (unconverted / "seeds").mkdir()
        assert needs_conversion(unconverted) is False

    def test_an_empty_seeds_dir_is_uninitialized_not_unconverted(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        seeds_dir.mkdir()
        assert needs_conversion(seeds_dir) is False


class TestEveryDataTouchingCommand:
    """Refuse, name the recovery that works, and exit non-zero. All of them."""

    @pytest.mark.parametrize("argv", DATA_TOUCHING, ids=lambda a: a[0])
    def test_it_names_seeds_convert_and_exits_non_zero(
        self, argv, unconverted, cli_runner
    ):
        result = cli_runner.invoke(main, list(argv))

        assert result.exit_code != 0, result.output
        assert "seeds convert" in result.output, result.output

    @pytest.mark.parametrize("argv", DATA_TOUCHING, ids=lambda a: a[0])
    def test_it_does_not_send_the_operator_to_seeds_init(
        self, argv, unconverted, cli_runner
    ):
        """``seeds init`` refuses on this state, so naming it is a closed loop."""
        result = cli_runner.invoke(main, list(argv))

        assert "seeds init" not in result.output, result.output


class TestPrime:
    """The one command that must inform WITHOUT aborting -- in either form.

    The short form is what the plugin hooks inject at every session start, so
    it is the form an agent meets first; it carries both notices too (bead
    seeds-oiy).
    """

    @pytest.fixture(params=[["prime"], ["prime", "--full"]], ids=["short", "full"])
    def argv(self, request):
        return request.param

    def test_it_still_exits_zero_and_still_teaches_the_verbs(
        self, argv, unconverted, cli_runner
    ):
        result = cli_runner.invoke(main, argv)

        assert result.exit_code == 0
        assert "seeds jot" in result.output
        assert "## Essential Commands" in result.output

    def test_the_notice_is_at_the_top_where_a_truncated_read_still_sees_it(
        self, argv, unconverted, cli_runner
    ):
        result = cli_runner.invoke(main, argv)

        head = result.output.splitlines()[:6]
        assert any("seeds convert" in line for line in head), head
        assert any("OUT OF DATE" in line for line in head), head

    def test_the_notice_is_also_where_the_state_block_would_have_been(
        self, argv, unconverted, cli_runner
    ):
        """Placement, not merely presence: absence explained at the absence."""
        result = cli_runner.invoke(main, argv)

        assert "## Current Seeds" in result.output
        _, _, after = result.output.partition("## Current Seeds")
        assert "Unavailable" in after
        assert "seeds convert" in after
        assert "NOT been converted" in after or "not been converted" in after

    def test_it_says_the_existing_seeds_are_not_lost(
        self, argv, unconverted, cli_runner
    ):
        result = cli_runner.invoke(main, argv)

        assert "NOT lost" in result.output
        assert 'Do not read that absence as "this project has no seeds."' in (
            result.output
        )

    def test_it_reports_no_count_because_it_never_opens_the_legacy_store(
        self, argv, unconverted, cli_runner
    ):
        """Reading the pre-0.7 store to count seeds was asked for and declined."""
        result = cli_runner.invoke(main, argv)

        assert "**Counts:**" not in result.output
        assert "1 total" not in result.output

    def test_prime_imports_no_legacy_reader(self):
        """The legacy reader stays confined to the converter."""
        source = (
            Path(__file__).resolve().parent.parent / "src" / "seeds" / "prime.py"
        ).read_text(encoding="utf-8")
        assert "import sqlite3" not in source
        assert "from seeds.legacy import" not in source

    def test_a_converted_store_gets_no_notice_at_all(
        self, argv, unconverted, cli_runner
    ):
        (unconverted / "seeds").mkdir()

        result = cli_runner.invoke(main, argv)

        assert result.exit_code == 0
        assert "OUT OF DATE" not in result.output
        expected = PRIME_OUTPUT if "--full" in argv else PRIME_SHORT_OUTPUT
        # stdout, because the seeds.jsonl left beside the tree earns the
        # one-line stderr warning every command gives that state (seeds-mlc7);
        # what prime itself emits is unchanged.
        assert result.stdout.strip().startswith(expected.strip())


class TestJotDoesNotEatTheThought:
    """Refusing is right. Losing the text with it is not."""

    THOUGHT = "the union is the input, not the database reconciled against it"

    def test_the_text_comes_back_verbatim(self, unconverted, cli_runner):
        result = cli_runner.invoke(main, ["jot", self.THOUGHT])

        assert result.exit_code == 1
        assert self.THOUGHT in result.output

    def test_it_prints_a_command_that_can_be_pasted_back(self, unconverted, cli_runner):
        result = cli_runner.invoke(main, ["jot", self.THOUGHT])

        assert f"seeds jot '{self.THOUGHT}'" in result.output

    def test_a_thought_with_quotes_in_it_is_still_pasteable(
        self, unconverted, cli_runner
    ):
        thought = "he said 'just fucking make sure' — so: shell-safe quoting"

        result = cli_runner.invoke(main, ["jot", thought])

        assert thought in result.output
        # shlex.quote's form for a string containing single quotes.
        assert "'\"'\"'" in result.output

    def test_it_says_nothing_was_written(self, unconverted, cli_runner):
        result = cli_runner.invoke(main, ["jot", self.THOUGHT])

        assert "Nothing was written" in result.output
        assert not (unconverted / "seeds").exists()


class TestTheTwoCommandsThatReportedABarePath:
    def test_export_json_names_the_recovery_not_just_the_missing_directory(
        self, unconverted, cli_runner
    ):
        result = cli_runner.invoke(main, ["export", "--json"])

        assert result.exit_code == 1
        assert "seeds convert" in result.output
        assert "not the database" not in result.output

    def test_check_names_the_recovery_not_just_the_missing_directory(
        self, unconverted, cli_runner
    ):
        result = cli_runner.invoke(main, ["check"])

        assert result.exit_code == 1
        assert "seeds convert" in result.output
        assert "store-missing" not in result.output


# --- A legacy store still being written beside the tree (seeds-mlc7) ---------


def _legacy_seed(seed_id: str, *, content: str = "Deliberation.") -> Seed:
    return Seed(
        id=seed_id,
        title=f"Seed {seed_id}",
        content=content,
        status=SeedStatus.CAPTURED,
        seed_type="idea",
        tags=[],
        created_at=T0,
        updated_at=T0,
    )


#: When ``converted_repo`` was converted.
CONVERTED = datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def converted_repo(temp_dir, monkeypatch):
    """A converted, committed repo whose only legacy file left is seeds.db.

    The state every converted host is in: convert staged seeds.jsonl's
    deletion and it was committed, while the gitignored seeds.db stays.
    """
    repo = temp_dir / "repo"
    seeds_dir = repo / ".seeds"
    build_legacy_db(seeds_dir, [_legacy_seed("seeds-a1")]).close()
    (seeds_dir / ".gitignore").write_text("*.db\n", encoding="utf-8")
    report = convert(seeds_dir, now=CONVERTED)
    assert report.clean
    git_init(repo)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "converted")
    monkeypatch.chdir(repo)
    return seeds_dir


#: A spread of commands: reading, writing, and the two that read the legacy
#: store themselves.
SOME_COMMANDS = [
    ("list",),
    ("show", "seeds-a1"),
    ("ready",),
    ("export", "--json"),
    ("prime",),
    ("check",),
    ("doctor",),
]


class TestALegacyStoreBesideTheTree:
    @pytest.mark.parametrize("argv", SOME_COMMANDS, ids=lambda a: a[0])
    def test_seeds_jsonl_beside_the_tree_warns_and_changes_no_exit_code(
        self, argv, converted_repo, cli_runner
    ):
        without = cli_runner.invoke(main, list(argv))
        assert "Warning" not in without.stderr
        (converted_repo / "seeds.jsonl").write_text("", encoding="utf-8")

        result = cli_runner.invoke(main, list(argv))

        assert result.exit_code == without.exit_code, result.output
        warnings = [line for line in result.stderr.splitlines() if "Warning" in line]
        assert len(warnings) == 1, result.stderr
        assert ".seeds/seeds.jsonl" in warnings[0]
        assert "seeds convert" in warnings[0]
        assert "seeds doctor" in warnings[0]

    @pytest.mark.parametrize("argv", SOME_COMMANDS, ids=lambda a: a[0])
    def test_only_the_leftover_seeds_db_with_nothing_newer_says_nothing(
        self, argv, converted_repo, cli_runner
    ):
        assert (converted_repo / "seeds.db").exists()

        result = cli_runner.invoke(main, list(argv))

        assert result.exit_code == 0, result.output
        assert "Warning" not in result.stderr
        assert "legacy-" not in result.output
        assert "✗ Legacy store" not in result.output

    def test_doctor_passes_the_leftover_seeds_db(self, converted_repo, cli_runner):
        result = cli_runner.invoke(main, ["doctor"])

        assert result.exit_code == 0, result.output
        assert "✓ seeds.db holds nothing the tree lacks" in result.output

    def test_a_seed_only_the_legacy_db_holds_fails_doctor_check_and_the_gate(
        self, converted_repo, cli_runner
    ):
        assert cli_runner.invoke(main, ["check", "--gate"]).exit_code == 0
        # A 0.6 client, still running in the converted checkout, adds a seed.
        writer = LegacyWriter(converted_repo / "seeds.db")
        writer.create_seed(_legacy_seed("seeds-z9"))
        writer.close()

        doctor = cli_runner.invoke(main, ["doctor"])
        check = cli_runner.invoke(main, ["check"])
        gate = cli_runner.invoke(main, ["check", "--gate"])

        assert doctor.exit_code == 1, doctor.output
        assert "✗ Legacy store: 1 seed(s)" in doctor.output
        assert "seeds-z9" in doctor.output
        assert "seeds convert" in doctor.output
        assert check.exit_code == 1, check.output
        assert "legacy-seed-not-in-tree" in check.output
        assert "seeds-z9" in check.output
        assert gate.exit_code == 1, gate.output
        assert "legacy-seed-not-in-tree" in gate.output

    def test_convert_then_clears_it(self, converted_repo, cli_runner):
        writer = LegacyWriter(converted_repo / "seeds.db")
        writer.create_seed(_legacy_seed("seeds-z9"))
        writer.close()

        assert cli_runner.invoke(main, ["convert"]).exit_code == 0

        assert (converted_repo / "seeds" / "seeds-z9.md").exists()
        assert cli_runner.invoke(main, ["check"]).exit_code == 0
        assert cli_runner.invoke(main, ["doctor"]).exit_code == 0

    def test_a_legacy_edit_after_conversion_is_a_violation(
        self, converted_repo, cli_runner
    ):
        conn = sqlite3.connect(converted_repo / "seeds.db")
        conn.execute(
            "UPDATE seeds SET content = ?, updated_at = ? WHERE id = ?",
            (
                "Deliberation. And more from 0.6.",
                "2026-03-01T00:00:00+00:00",
                "seeds-a1",
            ),
        )
        conn.commit()
        conn.close()

        check = cli_runner.invoke(main, ["check"])
        doctor = cli_runner.invoke(main, ["doctor"])

        assert check.exit_code == 1, check.output
        assert "legacy-edited-after-conversion" in check.output
        assert doctor.exit_code == 1, doctor.output
        assert "edited in the pre-0.7 store after conversion" in doctor.output

    def test_a_stale_but_harmless_jsonl_is_a_warning_and_a_smell(
        self, converted_repo, cli_runner
    ):
        # Convert could not retire it, or `seeds sync` recreated it from the
        # same old database: it holds exactly what the tree already has.
        record = {
            "format_version": 2,
            "id": "seeds-a1",
            "title": "Seed seeds-a1",
            "content": "Deliberation.",
            "status": "captured",
            "seed_type": "idea",
            "tags": [],
            "created_at": T0.isoformat(),
            "updated_at": T0.isoformat(),
            "resolved_at": None,
            "resolution": "",
            "relationships": [],
        }
        (converted_repo / "seeds.jsonl").write_text(
            json.dumps(record) + "\n", encoding="utf-8"
        )

        doctor = cli_runner.invoke(main, ["doctor"])
        check = cli_runner.invoke(main, ["check"])
        smells = cli_runner.invoke(main, ["check", "--smells"])

        assert doctor.exit_code == 0, doctor.output
        assert "⚠ Legacy store: seeds.jsonl is still beside the tree" in (doctor.output)
        assert check.exit_code == 0, check.output
        assert "legacy-jsonl-beside-tree" not in check.stdout
        assert smells.exit_code == 0, smells.output
        assert "legacy-jsonl-beside-tree" in smells.stdout

    def test_the_ruled_fixtures_convert_dropped_are_not_missing(
        self, converted_repo, cli_runner
    ):
        """This repo's own seeds.db still holds the six ruled fixtures."""
        writer = LegacyWriter(converted_repo / "seeds.db")
        writer.create_seed(_legacy_seed("seeds-71", content=""))
        writer.close()

        assert cli_runner.invoke(main, ["check"]).exit_code == 0
        assert cli_runner.invoke(main, ["doctor"]).exit_code == 0
