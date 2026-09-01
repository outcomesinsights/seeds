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
from datetime import UTC, datetime
from pathlib import Path

import pytest

from seeds.cli import main
from seeds.prime import PRIME_OUTPUT
from seeds.store import needs_conversion

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
    """The one command that must inform WITHOUT aborting."""

    def test_it_still_exits_zero_and_still_teaches_the_verbs(
        self, unconverted, cli_runner
    ):
        result = cli_runner.invoke(main, ["prime"])

        assert result.exit_code == 0
        assert "seeds jot" in result.output
        assert "## Essential Commands" in result.output

    def test_the_notice_is_at_the_top_where_a_truncated_read_still_sees_it(
        self, unconverted, cli_runner
    ):
        result = cli_runner.invoke(main, ["prime"])

        head = result.output.splitlines()[:6]
        assert any("seeds convert" in line for line in head), head
        assert any("OUT OF DATE" in line for line in head), head

    def test_the_notice_is_also_where_the_state_block_would_have_been(
        self, unconverted, cli_runner
    ):
        """Placement, not merely presence: absence explained at the absence."""
        result = cli_runner.invoke(main, ["prime"])

        assert "## Current Seeds" in result.output
        _, _, after = result.output.partition("## Current Seeds")
        assert "Unavailable" in after
        assert "seeds convert" in after
        assert "NOT been converted" in after or "not been converted" in after

    def test_it_says_the_existing_seeds_are_not_lost(self, unconverted, cli_runner):
        result = cli_runner.invoke(main, ["prime"])

        assert "NOT lost" in result.output
        assert 'Do not read that absence as "this project has no seeds."' in (
            result.output
        )

    def test_it_reports_no_count_because_it_never_opens_the_legacy_store(
        self, unconverted, cli_runner
    ):
        """Reading the pre-0.7 store to count seeds was asked for and declined."""
        result = cli_runner.invoke(main, ["prime"])

        assert "**Counts:**" not in result.output
        assert "1 total" not in result.output

    def test_prime_imports_no_legacy_reader(self):
        """The legacy reader stays confined to the converter."""
        source = (
            Path(__file__).resolve().parent.parent / "src" / "seeds" / "prime.py"
        ).read_text(encoding="utf-8")
        assert "import sqlite3" not in source
        assert "from seeds.legacy import" not in source

    def test_a_converted_store_gets_no_notice_at_all(self, unconverted, cli_runner):
        (unconverted / "seeds").mkdir()

        result = cli_runner.invoke(main, ["prime"])

        assert result.exit_code == 0
        assert "OUT OF DATE" not in result.output
        assert result.output.strip().startswith(PRIME_OUTPUT.strip()[:40])


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
