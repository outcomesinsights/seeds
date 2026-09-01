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


def export(old, new, *, dropped=NONE, recovered=NONE):
    return dh.classify_export(
        {r["id"]: r for r in old},
        {r["id"]: r for r in new},
        dropped_fixtures=dropped,
        recovered=recovered,
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


# --- classify_show ------------------------------------------------------------


def test_identical_show_is_silent():
    assert dh.classify_show("p-a", "same", "same", "same") == []


def test_show_full_reproducing_the_old_output_is_allowlisted():
    assert rules(dh.classify_show("p-a", "whole body", "trimmed", "whole body")) == (
        "show-full-supersede",
    )


def test_show_losing_text_that_full_does_not_restore_is_a_regression():
    assert rules(dh.classify_show("p-a", "whole body", "trimmed", "trimmed")) == (None,)


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
