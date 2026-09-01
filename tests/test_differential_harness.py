"""Tests for scripts/differential_harness.py (bead seeds-4co.17).

The thing under test is a **detector**, and this repo has now shipped several
gates that measured something adjacent to what they claimed. Two failure modes
matter here and both are silent:

* it reports zero differences because it compared nothing, and
* an allowlist entry is written broadly enough to swallow a real regression.

So nothing below lets the classifiers agree with whatever the tool currently
does on a real store: every case is a hand-built pair of outputs or records
with the verdict worked out by hand. The controls that matter most are the
*negative* ones — a search hit 0.6 found whose file contains the query as a
literal, a body that differs by more than a trailing newline, an added edge
that is not a materialized inverse. Each of those sits one character away from
an allowlisted case and must come back a regression.

``test_every_cited_rule_has_a_justification`` walks the harness's own AST and
fails if any ``Finding`` is constructed with a rule name that ``ALLOWLIST``
does not explain. An allowlist entry without a reason is the thing the bead
forbids, and a convention is not a gate.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "differential_harness.py"


def _load():
    spec = importlib.util.spec_from_file_location("differential_harness", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules[cls.__module__], so
    # a module loaded straight off a path has to be registered before exec.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dh = _load()

NONE = frozenset()


def rules(findings):
    """(rule-or-None, ...) for a list of findings, in order."""
    return tuple(f.rule for f in findings)


# --- Small pure helpers -------------------------------------------------------


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("○ vfm-v3k: Committed edge-case fixtures [a, b]", "vfm-v3k"),
        ("  ↔ epc-j9q.4: Code assignment", "epc-j9q.4"),
        ("● seeds-4co.17: Differential harness", "seeds-4co.17"),
        ("Current:", None),
        ("", None),
        ("Found 10 seed(s):", None),
        # A colon alone is not enough: the id has to carry a prefix and a body.
        ("○ notanid: nope", None),
    ],
)
def test_line_id(line, expected):
    assert dh.line_id(line) == expected


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ("body", "body\n", True),
        ("body\n", "body\n", False),  # identical is not a difference
        ("body", "body", False),
        ("body", "other\n", False),
        ("body\n", "body", False),  # the new side must be the one that gained it
        ("body\n\n", "body\n", True),
        ("body", "body \n", False),  # trailing space is not a trailing newline
    ],
)
def test_trailing_newline_only(old, new, expected):
    assert dh.trailing_newline_only(old, new) is expected


@pytest.mark.parametrize(
    ("seed_id", "expected"),
    [("vfm-064", None), ("epc-j9q.5", "epc-j9q"), ("seeds-71.1.1.1", "seeds-71.1.1")],
)
def test_derived_parent(seed_id, expected):
    assert dh.derived_parent(seed_id) == expected


def test_split_prime_splits_at_the_digest_heading():
    text = "static text\n\n## Current Seeds\n\n- one\n"
    head, digest = dh.split_prime(text)
    assert head == "static text\n\n"
    assert digest == "## Current Seeds\n\n- one\n"


def test_split_prime_refuses_rather_than_guessing():
    with pytest.raises(dh.Refusal):
        dh.split_prime("static text with no digest heading\n")


# --- classify_lines -----------------------------------------------------------

LIST_OLD = "○ p-a: Alpha\n○ p-b: Beta\n"


def test_identical_listings_produce_nothing():
    assert (
        dh.classify_lines(
            "list", LIST_OLD, LIST_OLD, dropped_fixtures=NONE, recovered=NONE
        )
        == []
    )


def test_dropped_fixture_is_allowlisted_but_any_other_loss_is_not():
    new = "○ p-b: Beta\n"
    assert rules(
        dh.classify_lines(
            "list", LIST_OLD, new, dropped_fixtures=frozenset({"p-a"}), recovered=NONE
        )
    ) == ("fixtures-dropped",)
    assert rules(
        dh.classify_lines("list", LIST_OLD, new, dropped_fixtures=NONE, recovered=NONE)
    ) == (None,)


def test_recovered_seed_is_allowlisted_but_any_other_arrival_is_not():
    new = LIST_OLD + "○ p-c: Gamma\n"
    assert rules(
        dh.classify_lines(
            "list", LIST_OLD, new, dropped_fixtures=NONE, recovered=frozenset({"p-c"})
        )
    ) == ("jsonl-only-recovered",)
    assert rules(
        dh.classify_lines("list", LIST_OLD, new, dropped_fixtures=NONE, recovered=NONE)
    ) == (None,)


def test_same_id_rendering_differently_is_a_regression():
    new = "○ p-a: Alpha CHANGED\n○ p-b: Beta\n"
    findings = dh.classify_lines(
        "list", LIST_OLD, new, dropped_fixtures=NONE, recovered=NONE
    )
    assert rules(findings) == (None,)
    assert "p-a" in findings[0].detail


def test_reordering_the_shared_seeds_is_a_regression_outside_search():
    new = "○ p-b: Beta\n○ p-a: Alpha\n"
    assert rules(
        dh.classify_lines("list", LIST_OLD, new, dropped_fixtures=NONE, recovered=NONE)
    ) == (None,)


def test_non_seed_lines_are_compared_too():
    old = "Found 2 seed(s):\n" + LIST_OLD
    new = "Found 3 seed(s):\n" + LIST_OLD
    assert rules(
        dh.classify_lines("list", old, new, dropped_fixtures=NONE, recovered=NONE)
    ) == (None,)


# --- classify_search ----------------------------------------------------------

FILES = {
    "p-a": "title: merge the stores\n",
    "p-b": "title: merging the stores\n",
    "p-c": "title: unrelated\n",
}


def test_search_same_set_same_order_is_silent():
    assert dh.classify_search("merge", ["p-a"], ["p-a"], FILES) == []


def test_search_reordering_is_allowlisted():
    assert rules(
        dh.classify_search("merge", ["p-b", "p-a"], ["p-a", "p-b"], FILES)
    ) == ("search-order",)


def test_a_stem_only_hit_lost_by_ripgrep_is_allowlisted():
    # 0.6 found p-b for "merge" through Porter stemming; p-b's file says
    # "merging", never the literal "merge"... except it does, as a substring.
    # Use a query where the stem genuinely differs from the literal.
    assert rules(dh.classify_search("merging", ["p-a", "p-b"], ["p-b"], FILES)) == (
        "search-stemming",
    )


def test_a_literal_hit_lost_by_ripgrep_is_a_regression():
    # p-b's file contains "merging" literally, so ripgrep had no excuse.
    findings = dh.classify_search("merging", ["p-a", "p-b"], ["p-a"], FILES)
    assert rules(findings) == (None,)
    assert "NOT found by ripgrep" in findings[0].detail


def test_a_hit_for_a_seed_with_no_file_is_a_regression():
    assert rules(dh.classify_search("merge", ["p-zz"], [], FILES)) == (None,)


def test_ripgrep_finding_more_is_allowlisted():
    assert rules(dh.classify_search("merge", ["p-a"], ["p-a", "p-b"], FILES)) == (
        "search-substring-broader",
    )


# --- classify_export ----------------------------------------------------------


def record(**overrides):
    base = {
        "id": "p-a",
        "title": "Alpha",
        "content": "body",
        "status": "captured",
        "seed_type": "idea",
        "tags": [],
        "relationships": [],
    }
    base.update(overrides)
    return base


def export(old, new, *, dropped=NONE, recovered=NONE, dropped_edges=NONE):
    return dh.classify_export(
        {r["id"]: r for r in old},
        {r["id"]: r for r in new},
        dropped_fixtures=dropped,
        recovered=recovered,
        dropped_edge_types=dropped_edges,
    )


def test_the_three_expected_field_changes_are_allowlisted():
    old = record(format_version=2)
    new = record(
        content="body\n", parent=None, converted_at="2026-09-01T00:00:00+00:00"
    )
    assert sorted(rules(export([old], [new]))) == [
        "body-trailing-newline",
        "export-field-set",
        "export-field-set",
        "export-field-set",
    ]


def test_a_parent_that_contradicts_the_id_is_a_regression():
    old = record(id="p-a.1")
    new = record(id="p-a.1", parent="p-WRONG")
    assert rules(export([old], [new])) == (None,)


def test_a_body_that_differs_by_more_than_a_newline_is_a_regression():
    findings = export([record()], [record(content="body truncat\n")])
    assert rules(findings) == (None,)
    assert "'content' differs" in findings[0].detail


def test_a_lost_seed_is_a_regression_unless_it_is_a_ruled_fixture():
    assert rules(export([record()], [])) == (None,)
    assert rules(export([record()], [], dropped=frozenset({"p-a"}))) == (
        "fixtures-dropped",
    )


def test_a_new_seed_is_a_regression_unless_the_union_recovered_it():
    assert rules(export([], [record()])) == (None,)
    assert rules(export([], [record()], recovered=frozenset({"p-a"}))) == (
        "jsonl-only-recovered",
    )


def edge(target, rel_type):
    return {
        "target_id": target,
        "rel_type": rel_type,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def test_a_materialized_questioned_by_half_is_allowlisted():
    old_q = record(id="p-q", relationships=[edge("p-a", "questions")])
    old_a = record(id="p-a")
    new_q = record(id="p-q", relationships=[edge("p-a", "questions")])
    new_a = record(id="p-a", relationships=[edge("p-q", "questioned-by")])
    assert rules(export([old_q, old_a], [new_q, new_a])) == ("questioned-by-inverse",)


def test_a_questioned_by_half_with_no_forward_edge_is_a_regression():
    old_a = record(id="p-a")
    new_a = record(id="p-a", relationships=[edge("p-q", "questioned-by")])
    assert rules(export([old_a], [new_a])) == (None,)


def test_an_added_relates_to_edge_is_a_regression():
    assert rules(
        export([record()], [record(relationships=[edge("p-b", "relates-to")])])
    ) == (None,)


def test_a_lost_edge_is_a_regression():
    findings = export([record(relationships=[edge("p-b", "relates-to")])], [record()])
    assert rules(findings) == (None,)
    assert "was lost" in findings[0].detail


def test_a_lost_edge_the_converter_reported_dropping_is_allowlisted():
    """The ruled `answers` drop is a declared difference, not a regression."""
    findings = export(
        [record(relationships=[edge("p-b", "answers")])],
        [record()],
        dropped_edges=frozenset({"answers"}),
    )
    assert rules(findings) == ("vestigial-answers-dropped",)


def test_a_lost_edge_the_converter_never_mentioned_is_still_a_regression():
    """The allowlist is the converter's own report, not the string 'answers'.

    An `answers` edge that vanished from a run whose report claimed no dropped
    edges is the silent loss this harness exists to catch.
    """
    assert rules(
        export([record(relationships=[edge("p-b", "answers")])], [record()])
    ) == (None,)
    assert rules(
        export(
            [record(relationships=[edge("p-b", "relates-to")])],
            [record()],
            dropped_edges=frozenset({"answers"}),
        )
    ) == (None,)


# --- classify_show ------------------------------------------------------------


def test_identical_show_is_silent():
    assert dh.classify_show("p-a", "same", "same", "same") == []


def test_show_full_reproducing_the_old_output_is_allowlisted():
    assert rules(dh.classify_show("p-a", "whole body", "trimmed", "whole body")) == (
        "show-full-supersede",
    )


def test_show_losing_text_that_full_does_not_restore_is_a_regression():
    assert rules(dh.classify_show("p-a", "whole body", "trimmed", "trimmed")) == (None,)


# --- Leading blank lines in a body --------------------------------------------


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ("\nbody\n", "body\n", True),
        ("\n\n\nbody", "body", True),
        ("body", "body", False),  # identical is not a difference
        ("body\n", "\nbody\n", False),  # 0.7 must not be the side that GAINED them
        ("\nbody\n", "\nbody\n", False),  # both sides have them: nothing normalized
        ("\nbody\n", "bodo\n", False),  # one character off is a regression
        ("\nbody text\n", "bodytext\n", False),  # whitespace inside is not an edge
        ("body\n\n", "body\n", False),  # trailing-only is the other rule
    ],
)
def test_leading_newline_only(old, new, expected):
    assert dh.leading_newline_only(old, new) is expected


SHOW_HEAD = "p-a: Alpha\n  Status: captured\n  Type: idea\n\nContent:\n"


def test_split_show_body_cuts_at_the_content_heading():
    assert dh.split_show_body(SHOW_HEAD + "line one\nline two\n") == (
        "p-a: Alpha\n  Status: captured\n  Type: idea\n\nContent:",
        "line one\nline two\n",
    )


def test_split_show_body_is_none_when_there_is_no_body_block():
    assert dh.split_show_body("p-a: Alpha\n  Status: captured\n") is None


@pytest.mark.parametrize(
    ("old_body", "new_body", "expected"),
    [
        ("\nbody\n", "body\n", "body-leading-newline"),
        ("body\n\n", "body\n", "body-trailing-newline"),
        ("\nbody\n\n", "body\n", "body-leading-newline"),
        ("body\n", "body\n", None),  # identical
        ("body one\n", "body two\n", None),  # different text
        ("a\n\nb\n", "a\nb\n", None),  # a blank line INSIDE the body is content
    ],
)
def test_show_body_blank_lines(old_body, new_body, expected):
    assert (
        dh.show_body_blank_lines(SHOW_HEAD + old_body, SHOW_HEAD + new_body) == expected
    )


def test_show_body_blank_lines_refuses_when_the_header_differs():
    other = SHOW_HEAD.replace("captured", "resolved")
    assert dh.show_body_blank_lines(SHOW_HEAD + "\nbody\n", other + "body\n") is None


# --- The multi-line legacy title split ----------------------------------------

OLD_TITLE = "The real question?\n\nElaboration one.\nElaboration two."
NEW_TITLE = "The real question?"
MOVED = "Elaboration one.\nElaboration two."


def test_a_faithful_title_split_is_recognised():
    assert dh.title_split_only(
        OLD_TITLE, "Resolved.\n", NEW_TITLE, f"{MOVED}\n\nResolved.\n"
    )


@pytest.mark.parametrize(
    ("old_title", "old_body", "new_title", "new_body"),
    [
        # 0.6's title was already one line: nothing was split.
        ("One line", "b\n", "One line", "b\n"),
        # 0.7's title is not a prefix of 0.6's -- the title was rewritten.
        (OLD_TITLE, "Resolved.\n", "A different title", f"{MOVED}\n\nResolved.\n"),
        # A word of the moved text went missing.
        (OLD_TITLE, "Resolved.\n", NEW_TITLE, "Elaboration two.\n\nResolved.\n"),
        # The original body went missing.
        (OLD_TITLE, "Resolved.\n", NEW_TITLE, f"{MOVED}\n"),
        # The moved text landed after the body instead of before it.
        (OLD_TITLE, "Resolved.\n", NEW_TITLE, f"Resolved.\n\n{MOVED}\n"),
        # A word was added that neither field held.
        (OLD_TITLE, "Resolved.\n", NEW_TITLE, f"{MOVED}\n\nResolved. Extra.\n"),
        # 0.7's title still spans lines, so nothing was fixed.
        (OLD_TITLE, "Resolved.\n", "The real\nquestion?", f"{MOVED}\n\nResolved.\n"),
    ],
)
def test_anything_other_than_a_faithful_split_is_refused(
    old_title, old_body, new_title, new_body
):
    assert not dh.title_split_only(old_title, old_body, new_title, new_body)


def split_pair():
    old = record(title=OLD_TITLE, content="Resolved.\n")
    new = record(title=NEW_TITLE, content=f"{MOVED}\n\nResolved.\n")
    return old, new


def test_title_splits_finds_only_verified_splits():
    old, new = split_pair()
    found = dh.title_splits({"p-a": old}, {"p-a": new})
    assert set(found) == {"p-a"}
    assert found["p-a"].new_title == NEW_TITLE
    assert found["p-a"].moved.strip() == MOVED
    # A title that merely changed is not a split.
    assert dh.title_splits({"p-a": old}, {"p-a": record(title="Rewritten")}) == {}


def test_export_allowlists_both_halves_of_a_split():
    old, new = split_pair()
    splits = dh.title_splits({"p-a": old}, {"p-a": new})
    findings = dh.classify_export(
        {"p-a": old},
        {"p-a": new},
        dropped_fixtures=NONE,
        recovered=NONE,
        splits=splits,
    )
    assert sorted(rules(findings)) == ["legacy-title-split", "legacy-title-split"]


def test_export_with_no_derived_split_reports_the_same_pair_as_a_regression():
    """The rule fires off the harness's own derivation, never off a claim.

    With `splits` empty -- which is what an unverifiable split produces -- the
    identical record pair must come back a regression.
    """
    old, new = split_pair()
    findings = dh.classify_export(
        {"p-a": old}, {"p-a": new}, dropped_fixtures=NONE, recovered=NONE
    )
    assert rules(findings) == (None, None)


def test_a_listing_allowlists_exactly_the_trailing_title_lines():
    old, new = split_pair()
    splits = dh.title_splits({"p-a": old}, {"p-a": new})
    old_out = f"○ p-a: The real question?\n\n{MOVED}\n"
    new_out = "○ p-a: The real question?\n"
    assert rules(
        dh.classify_lines(
            "list",
            old_out,
            new_out,
            dropped_fixtures=NONE,
            recovered=NONE,
            splits=splits,
        )
    ) == ("legacy-title-split",)


def test_a_listing_line_that_is_not_moved_title_text_is_still_a_regression():
    old, new = split_pair()
    splits = dh.title_splits({"p-a": old}, {"p-a": new})
    old_out = f"○ p-a: The real question?\n{MOVED}\nan unrelated line\n"
    new_out = "○ p-a: The real question?\n"
    assert rules(
        dh.classify_lines(
            "list",
            old_out,
            new_out,
            dropped_fixtures=NONE,
            recovered=NONE,
            splits=splits,
        )
    ) == (None,)


def test_a_listing_difference_that_is_only_blank_lines_is_not_a_split():
    old, new = split_pair()
    splits = dh.title_splits({"p-a": old}, {"p-a": new})
    assert rules(
        dh.classify_lines(
            "list",
            "○ p-a: The real question?\n\n",
            "○ p-a: The real question?\n",
            dropped_fixtures=NONE,
            recovered=NONE,
            splits=splits,
        )
    ) == (None,)


def show_output(title: str, body: str) -> str:
    return f"p-a: {title}\n  Status: captured\n  Type: idea\n\nContent:\n{body}"


def test_show_allowlists_a_reconstructible_title_split():
    old, new = split_pair()
    split = dh.title_splits({"p-a": old}, {"p-a": new})["p-a"]
    old_out = show_output(OLD_TITLE, "Resolved.\n")
    new_out = show_output(NEW_TITLE, f"{MOVED}\n\nResolved.\n")
    assert rules(dh.classify_show("p-a", old_out, new_out, new_out, split)) == (
        "legacy-title-split",
    )


def test_show_refuses_when_the_rest_of_the_output_also_moved():
    """The split explains the title and the body head, and nothing else."""
    old, new = split_pair()
    split = dh.title_splits({"p-a": old}, {"p-a": new})["p-a"]
    old_out = show_output(OLD_TITLE, "Resolved.\n")
    new_out = show_output(NEW_TITLE, f"{MOVED}\n\nResolved.\n").replace(
        "captured", "resolved"
    )
    assert rules(dh.classify_show("p-a", old_out, new_out, new_out, split)) == (None,)


def test_show_without_a_derived_split_is_a_regression():
    old_out = show_output(OLD_TITLE, "Resolved.\n")
    new_out = show_output(NEW_TITLE, f"{MOVED}\n\nResolved.\n")
    assert rules(dh.classify_show("p-a", old_out, new_out, new_out)) == (None,)


# --- Corpus-derived search terms ----------------------------------------------


def test_derive_queries_is_deterministic_and_safe_in_both_engines():
    corpus = [
        {"title": "Merging the stores into ONE tree"},
        {"title": "merging stores, again"},
        {"title": "ab cd"},
    ]
    first = dh.derive_queries(corpus, 5)
    assert first == dh.derive_queries(corpus, 5)
    assert all(word.isalpha() and word.islower() and len(word) >= 5 for word in first)
    assert "merging" in first
    assert "ab" not in first


# --- The invariant that keeps the allowlist honest ----------------------------


def cited_rule_names(source: str) -> set[str]:
    """Every literal rule name a ``Finding(...)`` call in the harness uses."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "Finding":
            continue
        candidates = list(node.args[2:3]) + [
            kw.value for kw in node.keywords if kw.arg == "rule"
        ]
        for candidate in candidates:
            if isinstance(candidate, ast.Constant) and isinstance(candidate.value, str):
                names.add(candidate.value)
        for candidate in candidates:
            if isinstance(candidate, ast.IfExp):
                names.update(_constants(candidate.body, candidate.orelse))
    # `rule = "x" if cond else None`, then `Finding(..., rule)` -- the name is a
    # constant one hop away, so follow the assignment rather than missing it.
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        target = node.targets[0]
        if not (isinstance(target, ast.Name) and target.id == "rule"):
            continue
        value = node.value
        branches = (
            (value.body, value.orelse) if isinstance(value, ast.IfExp) else (value,)
        )
        names.update(_constants(*branches))
    return names


def _constants(*nodes: ast.expr) -> set[str]:
    return {
        n.value
        for n in nodes
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }


def test_every_cited_rule_has_a_justification():
    source = SCRIPT.read_text(encoding="utf-8")
    cited = cited_rule_names(source)
    assert cited, "the AST walk found no rule names at all, so it proves nothing"
    assert cited <= set(dh.ALLOWLIST), (
        f"rule(s) with no written justification: {sorted(cited - set(dh.ALLOWLIST))}"
    )


def test_the_invariant_detector_actually_fires():
    # A detector that never fires is indistinguishable from no detector.
    sample = 'Finding("cmd", "detail", "invented-rule")\n'
    assert cited_rule_names(sample) == {"invented-rule"}
    assert not {"invented-rule"} <= set(dh.ALLOWLIST)
    # ...including through the one-hop `rule = ... if ... else None` form.
    hop = (
        'rule = "also-invented" if x else None\nfindings.append(Finding(c, d, rule))\n'
    )
    assert cited_rule_names(hop) == {"also-invented"}


def test_every_justification_is_a_real_argument():
    for name, why in dh.ALLOWLIST.items():
        assert len(why) > 120, f"{name}'s justification is too thin to be one"
