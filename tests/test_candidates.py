"""Tests for ``seeds candidates`` — the discovery half of resolve-seeds-from-beads.

This module is a DETECTOR, so it is tested the way winnow is: hand-built inputs
with hand-computed answers, and a false-positive control for every rule that can
produce one. The rules that matter most are the ones that WITHHOLD — a
``Context:``-cited seed, a seed already resolved, a prose token that names a
bead. A detector that over-offers gets deliberation closed with nothing behind
it, which is the failure this whole loop exists to prevent.

No test here goes near ``bd``. The verb takes dicts; the fixtures are dicts.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from seeds.candidates import (
    EVIDENCE_PROSE,
    EVIDENCE_SOURCE,
    CandidatesError,
    find_candidates,
    format_report,
    load_bead_records,
    parse_lineage,
    report_as_dict,
)
from seeds.models import SeedStatus, SeedType
from seeds.store import new_record

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
SINCE = NOW - timedelta(days=30)


def bead(bead_id, *, notes="", description="", status="closed", days_ago=5, title="t"):
    """One bead record in the shape ``bd list --json`` emits."""
    return {
        "id": bead_id,
        "title": title,
        "description": description,
        "notes": notes,
        "status": status,
        "closed_at": (NOW - timedelta(days=days_ago)).isoformat()
        if status == "closed"
        else None,
    }


def seed(seed_id, *, status=SeedStatus.CAPTURED, title="a seed"):
    return new_record(
        seed_id, title, status=status, seed_type=SeedType.IDEA.value, body=""
    )


def run(records, seeds, *, since=SINCE):
    return find_candidates(records, seeds, prefix="seeds", since=since, now=NOW)


# --------------------------------------------------------------------------
# parse_lineage: the Source:/Context: grammar
# --------------------------------------------------------------------------


def test_parse_lineage_reads_both_labels():
    src, ctx = parse_lineage("Source: seeds-aaa, seeds-bbb\nContext: seeds-ccc")
    assert src == ["seeds-aaa", "seeds-bbb"]
    assert ctx == ["seeds-ccc"]


def test_parse_lineage_source_none_is_empty():
    """``Source: none`` is a deliberate 'no seed', not an ID named none."""
    assert parse_lineage("Source: none") == ([], [])


def test_parse_lineage_absent_field_is_empty():
    assert parse_lineage("just some notes about the work") == ([], [])
    assert parse_lineage("") == ([], [])


def test_parse_lineage_ignores_midline_label():
    """A sentence mentioning the word must not masquerade as the field."""
    assert parse_lineage("we discussed Source: seeds-aaa in passing") == ([], [])


def test_parse_lineage_unions_repeated_labels():
    src, _ = parse_lineage("Source: seeds-aaa\nSource: seeds-bbb")
    assert src == ["seeds-aaa", "seeds-bbb"]


def test_parse_lineage_survives_trailing_notes():
    src, ctx = parse_lineage(
        "Source: seeds-aaa\nContext: seeds-bbb\n\nAssumed: we picked JSON.\n"
    )
    assert (src, ctx) == (["seeds-aaa"], ["seeds-bbb"])


# --------------------------------------------------------------------------
# Evidence classes
# --------------------------------------------------------------------------


def test_source_field_beats_prose():
    records = [bead("seeds-b1", notes="Source: seeds-aaa", description="see seeds-zzz")]
    report = run(records, [seed("seeds-aaa"), seed("seeds-zzz")])
    assert [c.seed_id for c in report.candidates] == ["seeds-aaa"]
    assert report.candidates[0].evidence == EVIDENCE_SOURCE


def test_prose_is_the_fallback_when_no_source_field():
    records = [bead("seeds-b1", description="implements seeds-aaa at last")]
    report = run(records, [seed("seeds-aaa")])
    assert [c.seed_id for c in report.candidates] == ["seeds-aaa"]
    assert report.candidates[0].evidence == EVIDENCE_PROSE


def test_stronger_evidence_wins_when_two_beads_cite_one_seed():
    records = [
        bead("seeds-b1", description="mentions seeds-aaa"),
        bead("seeds-b2", notes="Source: seeds-aaa"),
    ]
    report = run(records, [seed("seeds-aaa")])
    assert len(report.candidates) == 1
    assert report.candidates[0].evidence == EVIDENCE_SOURCE
    assert {b.bead_id for b in report.candidates[0].beads} == {"seeds-b1", "seeds-b2"}


def test_source_candidates_sort_ahead_of_prose():
    records = [
        bead("seeds-b1", description="see seeds-aaa", days_ago=1),
        bead("seeds-b2", notes="Source: seeds-bbb", days_ago=20),
    ]
    report = run(records, [seed("seeds-aaa"), seed("seeds-bbb")])
    assert [c.seed_id for c in report.candidates] == ["seeds-bbb", "seeds-aaa"]


# --------------------------------------------------------------------------
# The withholding rules — false-positive controls
# --------------------------------------------------------------------------


def test_context_only_seed_is_never_a_candidate():
    """The whole point of splitting Context: from Source:.

    A cited seed must not come back as something to resolve; resolving it would
    close deliberation that this bead never discharged.
    """
    records = [bead("seeds-b1", notes="Source: seeds-aaa\nContext: seeds-ccc")]
    report = run(records, [seed("seeds-aaa"), seed("seeds-ccc")])
    assert [c.seed_id for c in report.candidates] == ["seeds-aaa"]
    assert report.cited_only == ["seeds-ccc"]


def test_context_seed_in_prose_is_still_withheld():
    """A bead with no Source: falls back to prose, which would otherwise
    re-admit the very seed the Context: line said was only cited."""
    records = [
        bead("seeds-b1", notes="Context: seeds-ccc", description="builds on seeds-ccc")
    ]
    report = run(records, [seed("seeds-ccc")])
    assert report.candidates == []
    assert report.cited_only == ["seeds-ccc"]


def test_a_seed_cited_by_one_bead_and_sourced_by_another_is_a_candidate():
    """Withholding is per-seed, not per-mention: a real Source: elsewhere wins."""
    records = [
        bead("seeds-b1", notes="Context: seeds-aaa"),
        bead("seeds-b2", notes="Source: seeds-aaa"),
    ]
    report = run(records, [seed("seeds-aaa")])
    assert [c.seed_id for c in report.candidates] == ["seeds-aaa"]
    assert report.cited_only == []


def test_prose_token_naming_a_bead_is_dropped():
    """Bead and seed IDs are shaped identically; existence decides."""
    records = [
        bead("seeds-b1", description="follows on from seeds-b2"),
        bead("seeds-b2"),
    ]
    report = run(records, [seed("seeds-b2")])  # a SEED also exists with that id
    assert report.candidates == []


def test_terminal_seeds_are_excluded_but_reported():
    records = [bead("seeds-b1", notes="Source: seeds-aaa, seeds-bbb")]
    seeds = [seed("seeds-aaa", status=SeedStatus.RESOLVED), seed("seeds-bbb")]
    report = run(records, seeds)
    assert [c.seed_id for c in report.candidates] == ["seeds-bbb"]
    assert report.already_terminal == ["seeds-aaa"]


def test_abandoned_seeds_are_terminal_too():
    records = [bead("seeds-b1", notes="Source: seeds-aaa")]
    report = run(records, [seed("seeds-aaa", status=SeedStatus.ABANDONED)])
    assert report.candidates == []
    assert report.already_terminal == ["seeds-aaa"]


def test_unknown_ref_is_quarantined_not_offered():
    """A seed from another project's store, quoted in prose."""
    records = [bead("seeds-b1", description="like seeds-zzz over in the blog store")]
    report = run(records, [])
    assert report.candidates == []
    assert report.unresolved_refs == ["seeds-zzz"]


def test_open_beads_contribute_ids_but_never_lineage():
    """An open bead cannot have discharged anything, but its ID still helps
    tell a bead reference apart from a seed reference."""
    records = [
        bead("seeds-b1", notes="Source: seeds-aaa", status="open"),
        bead("seeds-b2", description="unrelated to seeds-b1", status="closed"),
    ]
    report = run(records, [seed("seeds-aaa"), seed("seeds-b1")])
    assert report.candidates == []
    assert report.beads_in_window == 1
    assert report.beads_in == 2


# --------------------------------------------------------------------------
# The window
# --------------------------------------------------------------------------


def test_beads_closed_before_the_window_are_skipped():
    records = [
        bead("seeds-b1", notes="Source: seeds-aaa", days_ago=5),
        bead("seeds-b2", notes="Source: seeds-bbb", days_ago=90),
    ]
    report = run(records, [seed("seeds-aaa"), seed("seeds-bbb")])
    assert [c.seed_id for c in report.candidates] == ["seeds-aaa"]
    assert report.beads_in_window == 1


def test_undated_closed_bead_is_kept_not_silently_dropped():
    """Discarding a closed-but-undated bead would narrow the sweep invisibly."""
    record = bead("seeds-b1", notes="Source: seeds-aaa")
    record["closed_at"] = None
    report = run([record], [seed("seeds-aaa")])
    assert [c.seed_id for c in report.candidates] == ["seeds-aaa"]
    assert report.candidates[0].beads[0].closed_at is None


def test_unparseable_close_timestamp_does_not_drop_the_bead():
    record = bead("seeds-b1", notes="Source: seeds-aaa")
    record["closed_at"] = "not a date"
    report = run([record], [seed("seeds-aaa")])
    assert [c.seed_id for c in report.candidates] == ["seeds-aaa"]


def test_window_line_is_printed_even_with_no_candidates():
    """'nothing found' and 'nothing looked at' are different answers."""
    out = format_report(run([], []))
    assert "window: beads closed since 2026-08-14" in out
    assert "No candidate seeds" in out


# --------------------------------------------------------------------------
# Input handling
# --------------------------------------------------------------------------


def test_load_bead_records_accepts_a_bare_array():
    assert load_bead_records('[{"id": "seeds-b1"}]') == [{"id": "seeds-b1"}]


def test_load_bead_records_accepts_an_issues_object():
    assert load_bead_records('{"issues": [{"id": "seeds-b1"}]}') == [{"id": "seeds-b1"}]


def test_load_bead_records_accepts_jsonl():
    text = '{"id": "seeds-b1"}\n{"id": "seeds-b2"}\n'
    assert [r["id"] for r in load_bead_records(text)] == ["seeds-b1", "seeds-b2"]


def test_load_bead_records_empty_input_is_not_an_error():
    assert load_bead_records("   \n  ") == []


def test_load_bead_records_rejects_garbage():
    with pytest.raises(CandidatesError):
        load_bead_records("this is not json at all")


def test_load_bead_records_rejects_a_json_scalar():
    with pytest.raises(CandidatesError):
        load_bead_records("42")


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def test_report_as_dict_round_trips_through_json():
    records = [bead("seeds-b1", notes="Source: seeds-aaa")]
    payload = report_as_dict(run(records, [seed("seeds-aaa", title="the title")]))
    assert json.loads(json.dumps(payload))["candidates"][0] == {
        "seed_id": "seeds-aaa",
        "title": "the title",
        "status": "captured",
        "evidence": EVIDENCE_SOURCE,
        "beads": [
            {
                "id": "seeds-b1",
                "title": "t",
                "closed_at": (NOW - timedelta(days=5)).isoformat(),
            }
        ],
    }


def test_prose_candidates_carry_a_warning_in_the_text_report():
    """The over-claim this loop's worked example is about (seeds-lcfa.1.1)
    looks exactly like a prose candidate, so the caveat ships with the output
    rather than living only in the skill."""
    out = format_report(
        run([bead("seeds-b1", description="see seeds-aaa")], [seed("seeds-aaa")])
    )
    assert "not evidence it implemented one" in out


def test_source_only_report_omits_the_prose_warning():
    out = format_report(
        run([bead("seeds-b1", notes="Source: seeds-aaa")], [seed("seeds-aaa")])
    )
    assert "not evidence it implemented one" not in out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_cli_reads_stdin_and_reports(cli_runner, store, monkeypatch):
    from seeds.cli import main

    store.create(seed("seeds-aaa", title="a real seed"))
    monkeypatch.chdir(store.seeds_dir.parent)
    payload = json.dumps([bead("seeds-b1", notes="Source: seeds-aaa")])
    result = cli_runner.invoke(main, ["candidates", "-"], input=payload)
    assert result.exit_code == 0, result.output
    assert "seeds-aaa" in result.output
    assert "[source]" in result.output


def test_cli_json_flag_emits_parseable_json(cli_runner, store, monkeypatch):
    from seeds.cli import main

    store.create(seed("seeds-aaa"))
    monkeypatch.chdir(store.seeds_dir.parent)
    payload = json.dumps([bead("seeds-b1", notes="Source: seeds-aaa")])
    result = cli_runner.invoke(main, ["candidates", "-", "--json"], input=payload)
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["candidates"][0]["seed_id"] == "seeds-aaa"


def test_cli_rejects_a_bad_since_value(cli_runner, store, monkeypatch):
    from seeds.cli import main

    monkeypatch.chdir(store.seeds_dir.parent)
    result = cli_runner.invoke(
        main, ["candidates", "-", "--since", "whenever"], input="[]"
    )
    assert result.exit_code == 1
    assert "Unrecognized --since" in result.output


def test_cli_rejects_garbage_input_with_a_hint(cli_runner, store, monkeypatch):
    from seeds.cli import main

    monkeypatch.chdir(store.seeds_dir.parent)
    result = cli_runner.invoke(main, ["candidates", "-"], input="nonsense")
    assert result.exit_code == 1
    assert "bd list" in result.output
