"""Tests for ``seeds winnow`` (bead seeds-dqu).

A stale-check is itself code that can be silently wrong, and this one is worse
than most: everything it reports is a claim about somebody's *thinking*, so a
false positive spends credibility that the true findings need. Every corpus
here is hand-built and every expected verdict was computed by hand. Nothing
reads the real ``~/.claude`` or this project's own ``.seeds/``.

Two controls carry the suite.

``test_two_related_seeds_that_agree_are_not_flagged`` is the crying-wolf test
and the most important thing in this file. Both endpoints are resolved, both
are linked, and they say the same thing — the status gate alone would flag
them, so this is what proves the polarity half is doing real work.
``test_a_contrastive_not_is_not_a_denial`` is the same control in the form that
actually bit: "X, not Y" asserts X, and reading its "not" as a denial of the
whole sentence produced five false positives out of seven on the real corpus.

``test_an_old_resolved_seed_with_no_premise_is_not_stale`` is the other one.
Age is not evidence, and the cheapest way to build a staleness detector is to
let it become exactly that.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from seeds.cli import main
from seeds.models import RelationType, SeedStatus
from seeds.seedfile import SeedEdge, SeedRecord
from seeds.store import SEEDS_DIR, Store
from seeds.winnow import (
    FLAVORS,
    edges,
    format_report,
    report_as_dict,
    winnow,
)
from tests.beadshelpers import make_beads_workspace

NOW = datetime(2026, 9, 2, tzinfo=UTC)


def ago(days: int) -> datetime:
    return NOW - timedelta(days=days)


def seed(
    seed_id: str,
    title: str,
    *,
    body: str = "",
    status: SeedStatus = SeedStatus.CAPTURED,
    created: int = 400,
    updated: int = 400,
    resolved: int | None = None,
    resolution: str = "",
    parent: str | None = None,
) -> SeedRecord:
    """A seed with every timestamp stated in days-ago, so ages are hand-computed."""
    return SeedRecord(
        id=seed_id,
        title=title,
        status=status,
        seed_type="idea",
        created_at=ago(created),
        updated_at=ago(updated),
        parent=parent,
        resolved_at=ago(resolved) if resolved is not None else None,
        resolution=resolution,
        body=body,
    )


def relate(left: SeedRecord, right: SeedRecord, days: int = 300) -> None:
    """Write a ``relates-to`` edge at both ends, the way the store does."""
    stamp = ago(days)
    left.relationships.append(SeedEdge(right.id, RelationType.RELATES_TO, stamp))
    right.relationships.append(SeedEdge(left.id, RelationType.RELATES_TO, stamp))


def codes(findings) -> list[str]:
    return [finding.code for finding in findings]


def ids_for(findings, code: str) -> list[tuple[str, ...]]:
    return [f.seed_ids for f in findings if f.code == code]


# --- The graph ---------------------------------------------------------------


def test_the_candidate_set_is_the_edge_set_not_the_cross_product():
    """Four seeds is six pairs; this corpus has three edges and finds three.

    The rule the whole design rests on: contradiction needs two seeds to be
    about the same thing, and the edges already say which those are. Measured
    on the real corpus, 314 seeds is 49,141 pairs and 427 deduplicated edges.
    """
    a = seed("seeds-a", "A")
    b = seed("seeds-b", "B", parent="seeds-a")
    c = seed("seeds-c", "C")
    d = seed("seeds-d", "D")
    relate(a, c)
    b.relationships.append(SeedEdge("seeds-c", RelationType.RELATES_TO, ago(10)))
    c.relationships.append(SeedEdge("seeds-b", RelationType.RELATES_TO, ago(10)))
    found = edges([a, b, c, d])
    assert {(e.a, e.b, e.kind) for e in found} == {
        ("seeds-a", "seeds-b", "parent"),
        ("seeds-a", "seeds-c", "relates-to"),
        ("seeds-b", "seeds-c", "relates-to"),
    }
    assert "seeds-d" not in {e.a for e in found} | {e.b for e in found}


def test_a_both_ended_edge_is_counted_once():
    a = seed("seeds-a", "A")
    b = seed("seeds-b", "B")
    relate(a, b)
    assert len(edges([a, b])) == 1


def test_an_edge_to_a_missing_seed_is_dropped():
    """A dangling edge is `seeds doctor`'s finding, not this module's."""
    a = seed("seeds-a", "A")
    a.relationships.append(SeedEdge("seeds-gone", RelationType.RELATES_TO, ago(5)))
    assert edges([a]) == []


# --- Contradiction: the crying-wolf controls ---------------------------------

STORE_IN_CONFIG = "We will store the project prefix in config.yaml."
STORE_NOT_IN_CONFIG = "We will not store the project prefix in config.yaml."


def _pair(left_body: str, right_body: str) -> list[SeedRecord]:
    left = seed(
        "seeds-lft",
        "Where the prefix lives",
        body=left_body,
        status=SeedStatus.RESOLVED,
        resolved=300,
    )
    right = seed(
        "seeds-rgt",
        "Where the prefix lives, revisited",
        body=right_body,
        status=SeedStatus.RESOLVED,
        resolved=100,
    )
    relate(left, right)
    return [left, right]


def test_a_true_intra_cluster_contradiction_is_detected():
    report = winnow(_pair(STORE_IN_CONFIG, STORE_NOT_IN_CONFIG), now=NOW)
    assert ids_for(report.candidates, "contradiction-candidate") == [
        ("seeds-lft", "seeds-rgt")
    ]
    finding = next(f for f in report.candidates if f.code == "contradiction-candidate")
    assert finding.tier == "candidate"
    assert any(STORE_IN_CONFIG in item for item in finding.evidence)
    assert any(STORE_NOT_IN_CONFIG in item for item in finding.evidence)


def test_two_related_seeds_that_agree_are_not_flagged():
    """THE crying-wolf test.

    Both resolved, both linked — the status gate on its own flags this pair.
    Nothing but the polarity test stops it, and a detector that fires on
    agreement is worse than no detector at all.
    """
    agreeing = _pair(
        STORE_IN_CONFIG,
        "The project prefix will be stored in config.yaml, as decided.",
    )
    report = winnow(agreeing, now=NOW)
    assert "contradiction-candidate" not in codes(report.candidates)


def test_a_contrastive_not_is_not_a_denial():
    """ "X, not Y" asserts X. It does not deny the sentence it appears in.

    This is the false positive that actually happened: on the real corpus,
    reading every "not" as flipping its whole sentence made five of seven
    candidates wrong, including two seeds that plainly agreed.
    """
    report = winnow(
        _pair(
            "The prefix will live in config.yaml, not in the frontmatter.",
            "We will store the project prefix in config.yaml.",
        ),
        now=NOW,
    )
    assert "contradiction-candidate" not in codes(report.candidates)


def test_opposite_claims_with_no_edge_between_them_are_not_compared():
    """No edge, no comparison — the search never leaves the graph."""
    left = seed(
        "seeds-lft",
        "Where the prefix lives",
        body=STORE_IN_CONFIG,
        status=SeedStatus.RESOLVED,
        resolved=300,
    )
    right = seed(
        "seeds-rgt",
        "Where the prefix lives, revisited",
        body=STORE_NOT_IN_CONFIG,
        status=SeedStatus.RESOLVED,
        resolved=100,
    )
    report = winnow([left, right], now=NOW)
    assert report.edges == 0
    assert report.candidates == []


def test_an_open_pair_does_not_pass_the_status_gate():
    """Two seeds still being worked out are not a contradiction yet."""
    pair = _pair(STORE_IN_CONFIG, STORE_NOT_IN_CONFIG)
    for record in pair:
        record.status = SeedStatus.EXPLORING
        record.resolved_at = None
    report = winnow(pair, now=NOW)
    assert "contradiction-candidate" not in codes(report.candidates)


def test_a_resolved_seed_and_a_later_capture_do_pass_the_gate():
    """One settled, then somebody wrote the opposite afterwards."""
    left = seed(
        "seeds-lft",
        "Where the prefix lives",
        body=STORE_IN_CONFIG,
        status=SeedStatus.RESOLVED,
        created=400,
        resolved=300,
    )
    right = seed(
        "seeds-rgt",
        "Second thoughts on the prefix",
        body=STORE_NOT_IN_CONFIG,
        status=SeedStatus.CAPTURED,
        created=50,
        updated=50,
    )
    relate(left, right, days=40)
    report = winnow([left, right], flavors=["contradiction"], now=NOW)
    assert ids_for(report.candidates, "contradiction-candidate") == [
        ("seeds-lft", "seeds-rgt")
    ]


def test_two_linked_seeds_about_different_things_are_not_compared():
    """A shared subject is required; a shared link is not enough."""
    report = winnow(
        _pair(
            STORE_IN_CONFIG,
            "We will not ship the web view in this release.",
        ),
        now=NOW,
    )
    assert "contradiction-candidate" not in codes(report.candidates)


# --- Neglected deferrals -----------------------------------------------------


def test_a_quiet_deferral_is_flagged_and_a_recent_one_is_not():
    quiet = seed(
        "seeds-old", "Deferred and forgotten", status=SeedStatus.DEFERRED, updated=200
    )
    recent = seed(
        "seeds-new", "Deferred last week", status=SeedStatus.DEFERRED, updated=7
    )
    report = winnow([quiet, recent], flavors=["neglect"], now=NOW)
    assert ids_for(report.facts, "neglected-deferral") == [("seeds-old",)]
    assert report.facts[0].tier == "fact"
    assert "200 days" in report.facts[0].message


def test_since_moves_the_neglect_cutoff():
    recent = seed(
        "seeds-new", "Deferred last week", status=SeedStatus.DEFERRED, updated=7
    )
    report = winnow([recent], flavors=["neglect"], since=ago(3), now=NOW)
    assert ids_for(report.facts, "neglected-deferral") == [("seeds-new",)]


# --- Blocked but unblocked ---------------------------------------------------


def test_a_seed_whose_blockers_all_closed_is_flagged():
    parent = seed("seeds-p", "The parent", status=SeedStatus.EXPLORING, updated=10)
    child = seed(
        "seeds-p.1",
        "The child",
        parent="seeds-p",
        status=SeedStatus.RESOLVED,
        resolved=30,
    )
    question = seed(
        "seeds-q",
        "The open question",
        status=SeedStatus.RESOLVED,
        resolved=20,
    )
    question.relationships.append(SeedEdge("seeds-p", RelationType.QUESTIONS, ago(40)))
    parent.relationships.append(
        SeedEdge("seeds-q", RelationType.QUESTIONED_BY, ago(40))
    )
    report = winnow([parent, child, question], flavors=["unblocked"], now=NOW)
    assert ids_for(report.facts, "unblocked-and-open") == [("seeds-p",)]
    finding = report.facts[0]
    assert "2 blocker(s)" in finding.message
    # Freed when the LAST blocker closed, not the first.
    assert ago(20).date().isoformat() in finding.message


def test_a_seed_with_one_blocker_still_open_is_not_flagged():
    parent = seed("seeds-p", "The parent", status=SeedStatus.EXPLORING, updated=10)
    done = seed(
        "seeds-p.1",
        "Finished child",
        parent="seeds-p",
        status=SeedStatus.RESOLVED,
        resolved=30,
    )
    live = seed(
        "seeds-p.2", "Live child", parent="seeds-p", status=SeedStatus.EXPLORING
    )
    report = winnow([parent, done, live], flavors=["unblocked"], now=NOW)
    assert report.facts == []


def test_a_resolved_parent_is_not_flagged_as_unblocked():
    parent = seed("seeds-p", "Done", status=SeedStatus.RESOLVED, resolved=5)
    child = seed(
        "seeds-p.1",
        "Also done",
        parent="seeds-p",
        status=SeedStatus.RESOLVED,
        resolved=10,
    )
    report = winnow([parent, child], flavors=["unblocked"], now=NOW)
    assert report.facts == []


# --- Long unresolved ---------------------------------------------------------


def test_long_unresolved_reports_graph_position():
    stalled = seed(
        "seeds-a", "Still exploring", status=SeedStatus.EXPLORING, updated=300
    )
    child = seed(
        "seeds-a.1", "A child", parent="seeds-a", status=SeedStatus.EXPLORING, updated=1
    )
    fresh = seed("seeds-b", "Touched yesterday", status=SeedStatus.CAPTURED, updated=1)
    relate(stalled, fresh)
    report = winnow([stalled, child, fresh], flavors=["unresolved"], now=NOW)
    assert ids_for(report.facts, "long-unresolved") == [("seeds-a",)]
    assert "2 edge(s)" in report.facts[0].message
    assert "1 child(ren)" in report.facts[0].message


def test_a_resolved_seed_is_never_long_unresolved():
    old = seed("seeds-a", "Settled long ago", status=SeedStatus.RESOLVED, resolved=900)
    report = winnow([old], flavors=["unresolved"], now=NOW)
    assert report.facts == []


# --- Staleness ---------------------------------------------------------------


def test_an_old_resolved_seed_with_no_premise_is_not_stale():
    """Age is not evidence and must never be allowed to become it."""
    old = seed(
        "seeds-a",
        "We decided to keep the vocabulary open",
        body=(
            "An open vocabulary costs nothing and a closed one broke on the "
            "first unrecognised value it met."
        ),
        status=SeedStatus.RESOLVED,
        created=900,
        resolved=900,
    )
    report = winnow([old], flavors=["staleness"], now=NOW)
    assert report.candidates == []


@pytest.mark.parametrize(
    ("body", "kind"),
    [
        ("This rests on click v8.1.8 accepting the flag.", "version"),
        ("The scan takes 35ms across 306 files, so the cost is nil.", "measurement"),
        ("Measured on titan 2026-01-04: the export was complete.", "as-of"),
    ],
)
def test_a_resolved_seed_citing_a_checkable_premise_is_a_candidate(body, kind):
    old = seed(
        "seeds-a",
        "A conclusion resting on something checkable",
        body=body,
        status=SeedStatus.RESOLVED,
        created=900,
        resolved=900,
    )
    report = winnow([old], flavors=["staleness"], now=NOW)
    assert ids_for(report.candidates, "staleness-candidate") == [("seeds-a",)]
    assert report.candidates[0].evidence[0].startswith(kind)


def test_a_numbered_list_marker_is_not_a_measurement():
    """ "1. Seed content is prose" is a list item, not a count of seeds."""
    old = seed(
        "seeds-a",
        "A list of considerations",
        body="1. Seed content is prose.\n2. Files are what git tracks.",
        status=SeedStatus.RESOLVED,
        created=900,
        resolved=900,
    )
    report = winnow([old], flavors=["staleness"], now=NOW)
    assert report.candidates == []


def test_a_recently_resolved_premise_is_not_offered():
    """The cutoff narrows what to re-check first; it never raises a candidate."""
    fresh = seed(
        "seeds-a",
        "Settled last week on a measurement",
        body="The scan takes 35ms across 306 files.",
        status=SeedStatus.RESOLVED,
        created=10,
        resolved=7,
    )
    report = winnow([fresh], flavors=["staleness"], now=NOW)
    assert report.candidates == []


# --- Outcomes ----------------------------------------------------------------


def test_outcome_candidates_need_a_beads_workspace(tmp_path):
    seeds_dir = tmp_path / ".seeds"
    (seeds_dir / "seeds").mkdir(parents=True)
    resolved = seed(
        "seeds-a",
        "Shipped through seeds-999",
        body="Implemented by seeds-999.",
        status=SeedStatus.RESOLVED,
        resolved=10,
    )
    # No .beads/ at all: the flavor is silent rather than guessing.
    assert (
        winnow([resolved], flavors=["outcome"], seeds_dir=seeds_dir, now=NOW).candidates
        == []
    )

    make_beads_workspace(seeds_dir)
    (seeds_dir.parent / ".beads" / "issues.jsonl").write_text(
        json.dumps({"id": "seeds-999", "title": "Do the thing"}) + "\n",
        encoding="utf-8",
    )
    report = winnow([resolved], flavors=["outcome"], seeds_dir=seeds_dir, now=NOW)
    assert ids_for(report.candidates, "outcome-candidate") == [("seeds-a",)]
    assert report.candidates[0].evidence == ("seeds-999",)


def test_a_reference_to_another_seed_is_not_a_downstream_bead(tmp_path):
    seeds_dir = tmp_path / ".seeds"
    (seeds_dir / "seeds").mkdir(parents=True)
    make_beads_workspace(seeds_dir)
    (seeds_dir.parent / ".beads" / "issues.jsonl").write_text(
        json.dumps({"id": "seeds-b", "title": "Same id as a seed"}) + "\n",
        encoding="utf-8",
    )
    a = seed(
        "seeds-a",
        "Refers to a sibling seed",
        body="See seeds-b for the other half.",
        status=SeedStatus.RESOLVED,
        resolved=10,
    )
    b = seed("seeds-b", "The sibling", status=SeedStatus.RESOLVED, resolved=10)
    report = winnow([a, b], flavors=["outcome"], seeds_dir=seeds_dir, now=NOW)
    assert report.candidates == []


# --- Report shape ------------------------------------------------------------


def _mixed_corpus() -> list[SeedRecord]:
    pair = _pair(STORE_IN_CONFIG, STORE_NOT_IN_CONFIG)
    quiet = seed(
        "seeds-def", "Deferred and quiet", status=SeedStatus.DEFERRED, updated=250
    )
    return [*pair, quiet]


def test_facts_and_candidates_never_share_a_section():
    report = winnow(_mixed_corpus(), now=NOW)
    rendered = format_report(report)
    assert "FACTS (1)" in rendered
    assert "CANDIDATES (1)" in rendered
    assert rendered.index("FACTS") < rendered.index("CANDIDATES")
    assert "neglected-deferral" in rendered.split("CANDIDATES")[0]
    assert "contradiction-candidate" in rendered.split("CANDIDATES")[1]


def test_every_finding_names_what_to_do_next():
    report = winnow(_mixed_corpus(), now=NOW)
    for finding in [*report.facts, *report.candidates]:
        assert finding.action.strip()


def test_report_as_dict_keeps_the_tiers_apart():
    payload = report_as_dict(winnow(_mixed_corpus(), now=NOW))
    assert payload["corpus"] == {"seeds": 3, "edges": 1}
    assert [f["code"] for f in payload["facts"]] == ["neglected-deferral"]
    assert [f["code"] for f in payload["candidates"]] == ["contradiction-candidate"]
    json.dumps(payload)


def test_flavors_can_be_selected():
    report = winnow(_mixed_corpus(), flavors=["neglect"], now=NOW)
    assert report.flavors == ("neglect",)
    assert report.candidates == []
    assert codes(report.facts) == ["neglected-deferral"]


def test_an_empty_corpus_reports_nothing_and_says_so():
    rendered = format_report(winnow([], now=NOW))
    assert "0 seed(s), 0 edge(s)" in rendered
    assert rendered.count("(none)") == 2


# --- The CLI -----------------------------------------------------------------


@pytest.fixture
def winnow_project():
    """A chdir'd project holding the mixed corpus."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        store = Store(root / SEEDS_DIR)
        store.files_dir.mkdir(parents=True)
        store.set_prefix("seeds")
        for record in _mixed_corpus():
            store.create(record)
        original = os.getcwd()
        os.chdir(root)
        try:
            yield root
        finally:
            os.chdir(original)


def test_winnow_cli_prints_both_sections(winnow_project):
    result = CliRunner().invoke(main, ["winnow"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "FACTS" in result.output
    assert "CANDIDATES" in result.output
    assert "neglected-deferral" in result.output


def test_winnow_cli_is_read_only(winnow_project):
    store = Store(winnow_project / SEEDS_DIR)
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(store.files_dir.iterdir())
    }
    listing_before = sorted(p.name for p in (winnow_project / SEEDS_DIR).iterdir())

    result = CliRunner().invoke(main, ["winnow"], catch_exceptions=False)
    assert result.exit_code == 0

    after = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(store.files_dir.iterdir())
    }
    assert after == before
    assert sorted(p.name for p in (winnow_project / SEEDS_DIR).iterdir()) == (
        listing_before
    )


def test_winnow_cli_json(winnow_project):
    result = CliRunner().invoke(main, ["winnow", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert set(payload) == {"corpus", "flavors", "facts", "candidates"}
    assert payload["corpus"]["seeds"] == 3
    assert payload["flavors"] == list(FLAVORS)


def test_winnow_cli_flavor_filter(winnow_project):
    result = CliRunner().invoke(
        main, ["winnow", "--flavor", "neglect", "--json"], catch_exceptions=False
    )
    payload = json.loads(result.output)
    assert payload["flavors"] == ["neglect"]
    assert payload["candidates"] == []


def test_winnow_cli_rejects_an_unknown_flavor(winnow_project):
    result = CliRunner().invoke(main, ["winnow", "--flavor", "vibes"])
    assert result.exit_code != 0
    assert "vibes" in result.output


def test_winnow_cli_rejects_a_bad_since(winnow_project):
    result = CliRunner().invoke(main, ["winnow", "--since", "whenever"])
    assert result.exit_code == 1
    assert "Unrecognized --since" in result.output


def test_winnow_is_in_the_help():
    result = CliRunner().invoke(main, ["--help"])
    assert "winnow" in result.output
