#!/usr/bin/env python3
"""Differential harness: prove the 0.7 storage change costs nothing behaviourally.

Run via ``just differential REPO [REPO...]``; bead ``seeds-4co.17``.

@aguynamedryan set the requirement on 2026-09-01, before the storage change
ships to the other repos: *"we probably want to think of ways of
comparing/checking on seeds behavior under the new storage to ensure no
degradation."*

The shape
---------
For each repo named on the command line:

1. Its ``.seeds/`` is **copied twice**, into ``old/`` and ``new/``. Neither the
   source store nor this repo's own ``.seeds/`` is ever written. A repo that
   has already been converted is refused rather than half-compared.
2. The ``old/`` copy is driven by a real **seeds 0.6** built from the ``v0.6.0``
   tag (``git archive``, so nothing is written into ``.git``), reading SQLite.
3. The ``new/`` copy is converted with :func:`seeds.convert.convert` and driven
   by the seeds in *this* checkout, reading the seed-file tree.
4. The same command set runs against both and the outputs are diffed.

Every difference is then classified against :data:`ALLOWLIST`. Anything that
does not match a rule **by that rule's own reason** is reported as a
regression and the run exits 1.

Why an allowlist needs reasons
------------------------------
An allowlist without justifications degrades into "ignore the failures", so
each entry in :data:`ALLOWLIST` carries the argument for why that difference is
the intended consequence of the ruling rather than a defect — and each is
matched **narrowly**. "Body differs" is not allowlisted; "body differs by
exactly a trailing newline and by nothing else" is. "Search output differs" is
not allowlisted; "the two runs found the same id set in a different order" is,
and separately "0.6 found an id whose seed file does not contain the query as a
literal substring", which is a Porter-stemming hit and could not survive the
move to ripgrep. A search hit 0.6 found, whose file *does* contain the literal,
is a regression and is reported as one.

The two traps this harness is built to avoid
--------------------------------------------
**Reporting zero diffs because it compared nothing.** ``seeds check`` exits 0
on an empty store, and the same shape has already been caught once in this
epic. So: the corpus is asserted non-empty on *both* sides before anything is
concluded; every comparison records whether it was VACUOUS (empty output on
both sides); the mandatory set — ``list --all``, per-seed ``show``, ``export``
— must be non-vacuous or the run refuses with exit 2; and the report prints
what it compared next to the verdict, so a green cannot be read without seeing
its denominator.

**An allowlist that swallows a real regression.** ``--inject`` is the control:
it makes a deliberate behavioural change to the converted copy and *requires*
the harness to report it. ``--inject`` inverts the exit code — 0 only if the
injected difference was caught — so it can run as a gate rather than being
eyeballed. ``tests/test_differential_harness.py`` exercises the classifiers on
hand-built inputs with hand-computed verdicts, so they never merely agree with
whatever the tool currently does.

Refusing is an outcome, and it says which kind
----------------------------------------------
Exit 2 means "no comparison was made here", and the operator's next move
depends entirely on *why*. ``convert-crashed`` is a defect in this checkout.
``empty-corpus`` is a store that never held anything. ``no-0.6-baseline`` is
neither: seeds 0.6 cannot read the store either, because its SQLite predates a
table 0.6 requires and 0.6 ships no migration that runs to create it. ``mani``
is that case — its store has no ``relationships`` table, 0.6's
``migrate_to_relationships`` is defined and never called, and 0.6 dies inside
its own ``db.py``. The repo was orphaned under 0.6 before 0.7 existed, so 0.7
is the first version that can read it at all; printing 0.6's traceback in that
slot invited the exact opposite reading. Every :class:`Refusal` therefore
declares one of :data:`REFUSAL_REASONS`, the summary groups by cause and
prints the argument for each, and the ``no-0.6-baseline`` message carries what
0.7 *did* do with the store — which is real, and is not a comparison.

The cross-repo half
-------------------
35 shell loops across 18 sessions read ``.seeds/seeds.jsonl`` directly. That
file stops being written on conversion day, so those loops break — or worse,
keep returning pre-conversion data and reporting nothing. ``--cross-repo``
therefore runs the *old* recipe (cat the committed JSONL of every repo into
DuckDB) and the *new* one (``seeds export --json`` of every converted copy into
DuckDB, the recipe ``seeds prime`` now documents) over the same repo set, and
diffs the two tables. Where they disagree because the committed JSONL was
already stale against its own SQLite, that is recorded as such — the
replacement is not merely equivalent there, it is right where the old recipe
was wrong.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import MappingProxyType

REPO_ROOT = Path(__file__).resolve().parent.parent
LEGACY_TAG = "v0.6.0"

# --- The allowlist ------------------------------------------------------------
#
# Each entry is a known-expected difference between 0.6 + SQLite and 0.7 + the
# seed-file tree, with the argument for why it is the intended consequence of a
# ruling. The classifiers below cite these names; nothing is allowlisted that
# does not match one of them on its own terms.

ALLOWLIST: dict[str, str] = {
    "fixtures-dropped": (
        "The six test fixtures @aguynamedryan ruled out on 2026-08-31 "
        "(seeds.convert.FIXTURE_IDS) are dropped by the conversion, so a repo "
        "carrying them has a smaller corpus afterwards -- this repo went 314 "
        "-> 308. The drop is conditional on the record still matching the "
        "verified profile (empty body, no edges), and the converter reports "
        "exactly which ids it dropped; only those ids are allowlisted here, "
        "never the id list as a class."
    ),
    "questioned-by-inverse": (
        "docs/storage-format.md §5.1 stores every edge at both ends and §5.2 "
        "names the inverse, so converting materializes a 'questioned-by' half "
        "for each 'questions' edge that had only a forward direction (57 edges "
        "in this repo). Relationship counts therefore rise. Allowlisted only "
        "for an added edge that is a 'questioned-by' whose matching 'questions' "
        "half exists on the far seed; any other added or removed edge is a "
        "regression."
    ),
    "body-trailing-newline": (
        "A seed file is a text file, so bodies gain a canonical trailing "
        "newline the SQLite column did not carry (282 of 314 records in this "
        "repo differed by nothing else). Allowlisted only when the two strings "
        "are equal after stripping trailing newlines AND the new one ends in "
        "one -- a body that differs anywhere else is a regression. In 'show' "
        "the same rule reads the other way round, because 0.7 rstrips the body "
        "before printing it while 0.6 printed the column verbatim: allowlisted "
        "there only when the two outputs' headers are identical line for line "
        "and their body blocks are equal after stripping blank lines off both "
        "ends."
    ),
    "body-leading-newline": (
        "docs/storage-format.md §2 says a body carries no leading and no "
        "trailing blank lines, so a pre-0.7 body that began with a newline "
        "loses it on conversion -- 5 of code_collector's 289 records did, e.g. "
        "'\\nInventoried the SAS truncated-operator idiom...' -> 'Inventoried "
        "the SAS truncated-operator idiom...'. Verified character by character "
        "as the only difference before it was ruled a normalization rather "
        "than a loss. Allowlisted only when the two strings are equal after "
        "stripping blank lines off BOTH ends AND 0.6 is the side that had the "
        "leading ones; a body differing anywhere else, or one where 0.7 grew "
        "them, is a regression. Never a blanket ignore on 'body differs'."
    ),
    "search-order": (
        "Ranked search is gone: 'seeds suggest' no longer exists and 'seeds "
        "search' is ripgrep, so results come back id-sorted instead of "
        "relevance-ranked. Accepted casualty, ruled, not a regression. "
        "Allowlisted only for a pure reordering -- the two id SETS must be "
        "equal for this rule to fire."
    ),
    "search-stemming": (
        "FTS5 applied Porter stemming, so 0.6 'merging' matched 'merge'. "
        "ripgrep is a literal/regex matcher and does not. Allowlisted only for "
        "an id 0.6 found whose seed file does NOT contain the query as a "
        "case-insensitive literal substring; if the file does contain it and "
        "0.7 missed it, that is a regression in the search path and is "
        "reported as one."
    ),
    "search-substring-broader": (
        "ripgrep matches substrings inside words where FTS5 matched whole "
        "tokens, so 0.7 finds hits 0.6 did not. A strictly larger result set "
        "for the same query is not degradation. Allowlisted only for ids found "
        "by 0.7 and not 0.6 -- the reverse direction is handled by "
        "search-stemming and is not blanket-allowlisted."
    ),
    "legacy-title-split": (
        "A pre-0.7 title was an unconstrained SQLite column, and a few hold a "
        "whole multi-paragraph thought somebody pasted into the wrong field. "
        "docs/storage-format.md §3 allows one non-empty line, so converting "
        "cuts the title and prepends the remainder to the body -- ruled "
        "2026-09-01, and it is what makes code_set_catalog (2 such titles in "
        "435 seeds) convertible at all. The harness does NOT take the "
        "converter's word for where the cut fell: it re-derives it, and "
        "allowlists a difference only when 0.7's title is a one-line prefix of "
        "0.6's multi-line one AND the two fields hold the same words in the "
        "same order across the pair, with the removed title text at the head "
        "of 0.7's body. A title cut somewhere else, a word lost, or a word "
        "reordered fails that and stays a regression. In the listing commands "
        "the same rule covers the trailing title lines 0.6 printed under the "
        "seed's line, and only those exact lines."
    ),
    "export-field-set": (
        "The exported record shape changed by exactly three fields, each with "
        "a reason: 'format_version' is gone (jsonexport.py -- a derived stream "
        "off a frozen format carries no version discriminator), 'converted_at' "
        "is new (the seed file records when it was converted), and 'parent' is "
        "new (the file carries it explicitly where the old record left it "
        "implicit in the hierarchical id). Allowlisted only for those three "
        "names, and 'parent' additionally must agree with the parent derived "
        "from the id."
    ),
    "vestigial-answers-dropped": (
        "docs/storage-format.md §5.2 retired the 'answers' relation as "
        "vestigial: 'seeds answer' stores an answer as the question-seed's own "
        "content and never made an edge, so the only route to one was a "
        "hand-run 'seeds link --type answers'. Ruled 2026-09-01 "
        "(@aguynamedryan): the converter DROPS those rows and reports the "
        "count, rather than inventing a direction for them. 5 rows survive "
        "across the unconverted repos (code_set_catalog 3, code_collector 1, "
        "habituate 1) out of 2,384 edges. Allowlisted only for a LOST edge "
        "whose rel_type the converter named in its own dropped-edge report; a "
        "lost edge of any other type, and any 'answers' edge the report did "
        "not account for, is a regression."
    ),
    "jsonl-only-recovered": (
        "The conversion reads the UNION of SQLite and the tracked JSONL, so a "
        "record that existed only in the JSONL -- never imported into the DB -- "
        "appears under 0.7 and was invisible to every 0.6 read command. "
        "Recovery, not divergence. Allowlisted only for ids present in the "
        "source JSONL and absent from the source DB."
    ),
    "prime-preamble": (
        "'seeds prime' is a hand-written instructional template plus a "
        "generated digest. The template documents the CLI surface, and the CLI "
        "surface changed by ruling (no sync/flush step, ripgrep search, the "
        "cross-repo rg recipe, 'seeds history', 'seeds export --json'). Its "
        "text differing is the point of the change, not a behavioural "
        "difference. Allowlisted only for the static half above the "
        "'## Current Seeds' heading; the generated digest below it is compared "
        "in full."
    ),
    "show-full-supersede": (
        "0.7 'seeds show' drops superseded text and keeps its heading plus a "
        "marker line; 0.6 had no such rendering and printed the body whole. "
        "Allowlisted only when 0.7 'show --full' reproduces the 0.6 'show' "
        "output exactly -- i.e. nothing was lost, only re-rendered. If neither "
        "'show' nor 'show --full' matches, it is a regression."
    ),
    "show-full-no-counterpart": (
        "'show --full' does not exist in 0.6 ('Error: No such option: --full'), "
        "so there is nothing to diff against. It is exercised under 0.7 only, "
        "and asserted non-empty and a superset of plain 'show'."
    ),
    "stale-committed-jsonl": (
        "Cross-repo only. The old recipe reads the committed .seeds/seeds.jsonl, "
        "which in several repos had already fallen behind its own SQLite before "
        "conversion (vocabulary_formats carried two seeds that lived only in the "
        "DB). Where the new recipe's answer differs from the old one AND the "
        "0.6 SQLite view agrees with the new answer, the old recipe was "
        "returning stale data and the replacement is right where it was wrong. "
        "Allowlisted only with that corroboration from the DB view."
    ),
}


# --- Findings -----------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One difference between the two runs, classified."""

    command: str
    detail: str
    rule: str | None  # allowlist key, or None for a regression

    @property
    def is_regression(self) -> bool:
        return self.rule is None


@dataclass
class Comparison:
    """One command run under both versions."""

    command: str
    vacuous: bool
    findings: list[Finding] = field(default_factory=list)


#: Why a comparison could not be made, keyed by the slug each refusal cites.
#: A refusal is an *outcome*, not an error, and the operator's next move
#: depends entirely on which of these it was: ``convert-crashed`` is a defect
#: in this checkout, ``no-0.6-baseline`` is a fact about the store that predates
#: this checkout entirely, and ``empty-corpus`` is neither. Collapsing them into
#: one "REFUSED" bucket — which is what a raw traceback does — invites exactly
#: the wrong reading, that 0.7 broke a repo 0.6 had already orphaned.
#:
#: ``tests/test_differential_harness.py`` walks this module's AST and fails if
#: any ``Refusal`` cites a slug that is not described here, or if a slug
#: described here is never raised. A convention is not a gate.
REFUSAL_REASONS: dict[str, str] = {
    "not-a-store": (
        "The path named on the command line does not hold a pre-0.7 seeds "
        "store at all -- no .seeds/, or a .seeds/ with neither seeds.db nor "
        "seeds.jsonl in it. Nothing was copied and nothing was run."
    ),
    "already-converted": (
        "The store has a .seeds/seeds/ tree already, so the pre-conversion "
        "behaviour this harness exists to compare against is gone. Refused "
        "rather than half-compared."
    ),
    "convert-crashed": (
        "seeds 0.7's own converter raised on this store, so 0.7's behaviour "
        "cannot be observed. This one IS a defect in the current checkout: the "
        "0.6 side of the comparison was never reached."
    ),
    "no-0.6-baseline": (
        "seeds 0.6 cannot read this store either -- its SQLite predates a "
        "table 0.6 requires, and 0.6 ships no migration that runs to create "
        "it. There is no 0.6 behaviour to compare against, because there never "
        "was any: the store was orphaned under 0.6, before 0.7 existed. NOT a "
        "defect in the current checkout, and the opposite of one -- 0.7 is the "
        "first version that can read the store at all. The refusal carries "
        "what 0.7 did with it, which is real but is not a comparison."
    ),
    "0.6-command-failed": (
        "seeds 0.6 exited non-zero building its side of the corpus, for some "
        "reason other than a missing table. Reported as its last error line "
        "rather than its traceback."
    ),
    "0.7-command-failed": (
        "seeds 0.7 exited non-zero building its side of the corpus, after "
        "converting it successfully. Like convert-crashed, a defect in the "
        "current checkout: 0.6 got as far as writing its side, and 0.7 did not."
    ),
    "empty-corpus": (
        "Both versions agree the store holds no seeds, or a comparison that "
        "MUST have compared something compared nothing. A clean verdict here "
        "would rest on diffing two empty strings, which is the failure mode "
        "the anti-vacuity guard exists to make impossible."
    ),
    "harness-broken": (
        "The harness could not set itself up -- the v0.6.0 archive, the fault "
        "injector, duckdb, or an output shape it parses. Says nothing about "
        "either version of seeds."
    ),
}


class Refusal(Exception):
    """The harness cannot make an honest comparison, and says which kind.

    ``reason`` is keyword-only and required: every refusal has to declare which
    of :data:`REFUSAL_REASONS` it is, so the report can separate causes that
    call for different responses instead of printing one undifferentiated wall.
    """

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


# --- Pure classifiers (unit-tested in tests/test_differential_harness.py) ------

#: A rendered seed line: a status glyph (or the ↔ relationship arrow), the id,
#: a colon. Anything else is "unkeyed" and compared as an exact sequence.
_LINE_ID = re.compile(r"^\s*\S{1,2} ([A-Za-z0-9_]+-[A-Za-z0-9]+(?:\.\d+)*): ")

PRIME_DIGEST_HEADING = "## Current Seeds"


def line_id(line: str) -> str | None:
    """The seed id a rendered line is about, or None if it is not a seed line."""
    m = _LINE_ID.match(line)
    return m.group(1) if m else None


#: 0.6 dying because the store predates a table it requires. Anchored to the
#: exception line of a Python traceback, and deliberately NOT a loose "no such
#: table" substring search: the phrase can appear in a seed body, and a body is
#: something this harness echoes.
_MISSING_TABLE = re.compile(
    r"^sqlite3\.OperationalError: no such table: (\w+)\s*$", re.MULTILINE
)


def missing_legacy_table(stderr: str) -> str | None:
    """The table 0.6 needed and this store does not have, or None.

    This is the signature of a store that predates the schema 0.6 assumes --
    ``mani``'s SQLite has no ``relationships`` table, and 0.6's own
    ``migrate_to_relationships`` (which would have built one from the legacy
    ``related_to`` column) is never called from anywhere in the v0.6.0 tree. So
    0.6 raises from inside its own ``db.py`` and there is no baseline to be
    had, as against the harness having driven it wrongly.
    """
    m = _MISSING_TABLE.search(stderr)
    return m.group(1) if m else None


def last_error_line(stderr: str) -> str:
    """The last non-empty line of a subprocess's stderr.

    A thirty-line traceback pasted into a refusal is not an outcome; the line
    at the bottom of it is the one that says what happened.
    """
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    return lines[-1] if lines else "(no output on stderr)"


def trailing_newline_only(old: str, new: str) -> bool:
    """True when the two bodies differ by trailing newlines and nothing else."""
    if old == new:
        return False
    return old.rstrip("\n") == new.rstrip("\n") and new.endswith("\n")


def leading_newline_only(old: str, new: str) -> bool:
    """True when 0.6 carried leading blank lines and nothing else differs.

    Narrow on purpose (``body-leading-newline``): the two must be the same text
    once blank lines are stripped from both ends, and 0.6 must be the side that
    had the leading ones. A body that differs by a single character anywhere,
    or one where 0.7 *grew* leading blank lines, comes back False and is
    reported as a regression.
    """
    if old == new:
        return False
    if old.lstrip("\n") == old:
        return False
    if new.lstrip("\n") != new:
        return False
    return old.strip("\n") == new.strip("\n")


@dataclass(frozen=True)
class TitleSplit:
    """One 0.6 title that 0.7 cut in two, as the harness re-derived it."""

    seed_id: str
    old_title: str
    new_title: str
    moved: str


def title_split_only(
    old_title: str, old_body: str, new_title: str, new_body: str
) -> bool:
    """True when 0.7 cut a multi-line 0.6 title and lost nothing doing it.

    Re-derived rather than taken from the converter, which is the whole point:
    a harness that asks ``seeds convert`` where it split would agree with a
    converter that split in the wrong place. The assertions are the ruling
    restated -- 0.7's title is a one-line *prefix* of 0.6's, and 0.7's body is
    the rest of that title followed by 0.6's body, word for word and in order.
    Words rather than lines, because the cut may fall mid-line; a lost,
    inserted or reordered word fails.
    """
    if "\n" not in old_title.strip("\n"):
        return False
    if not new_title.strip() or "\n" in new_title.strip("\n"):
        return False
    if not old_title.strip().startswith(new_title.strip()):
        return False
    kept = new_title.split()
    old_words = old_title.split()
    if old_words[: len(kept)] != kept:
        return False
    moved = old_words[len(kept) :]
    if not moved:
        return False
    new_words = new_body.split()
    return new_words[: len(moved)] == moved and new_words[len(moved) :] == (
        old_body.split()
    )


def title_splits(
    old_records: Mapping[str, dict], new_records: Mapping[str, dict]
) -> dict[str, TitleSplit]:
    """Every id whose 0.6 title 0.7 cut, keyed by id. Only verified splits."""
    out: dict[str, TitleSplit] = {}
    for ident, old in old_records.items():
        new = new_records.get(ident)
        if new is None:
            continue
        old_title = str(old.get("title") or "")
        new_title = str(new.get("title") or "")
        if not title_split_only(
            old_title,
            str(old.get("content") or ""),
            new_title,
            str(new.get("content") or ""),
        ):
            continue
        out[ident] = TitleSplit(
            seed_id=ident,
            old_title=old_title,
            new_title=new_title,
            moved=old_title.strip()[len(new_title.strip()) :],
        )
    return out


def derived_parent(seed_id: str) -> str | None:
    """The parent a hierarchical id implies: ``a-b.1.2`` -> ``a-b.1``."""
    head, sep, _ = seed_id.rpartition(".")
    return head if sep else None


def split_prime(text: str) -> tuple[str, str]:
    """Split ``seeds prime`` output into (static template, generated digest).

    Raises :class:`Refusal` when the digest heading is absent, rather than
    silently comparing a preamble against a whole document.
    """
    lines = text.splitlines(keepends=True)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].rstrip("\n") == PRIME_DIGEST_HEADING:
            return "".join(lines[:i]), "".join(lines[i:])
    raise Refusal(
        f"'seeds prime' output has no {PRIME_DIGEST_HEADING!r} heading, so the "
        "generated digest cannot be told apart from the static template",
        reason="harness-broken",
    )


def classify_lines(
    command: str,
    old: str,
    new: str,
    *,
    dropped_fixtures: frozenset[str],
    recovered: frozenset[str],
    splits: Mapping[str, TitleSplit] = MappingProxyType({}),
) -> list[Finding]:
    """Diff two line-oriented command outputs, keyed on the seed id per line.

    Keying on the id rather than diffing sequences is what lets the fixture and
    union-recovery rules fire on exactly the ids they cover: a line that is
    present on one side only is judged by its id, and a line present on both
    sides with different text is a regression regardless of which ids moved.
    """
    findings: list[Finding] = []
    old_keyed: dict[str, str] = {}
    new_keyed: dict[str, str] = {}
    old_order: list[str] = []
    new_order: list[str] = []
    old_plain: list[str] = []
    new_plain: list[str] = []

    for text, keyed, order, plain in (
        (old, old_keyed, old_order, old_plain),
        (new, new_keyed, new_order, new_plain),
    ):
        for raw in text.splitlines():
            ident = line_id(raw)
            if ident is None:
                plain.append(raw)
            else:
                keyed[ident] = raw
                order.append(ident)

    for ident in sorted(set(old_keyed) - set(new_keyed)):
        if ident in dropped_fixtures:
            findings.append(
                Finding(command, f"{ident} absent under 0.7", "fixtures-dropped")
            )
        else:
            findings.append(
                Finding(command, f"{ident} present under 0.6, absent under 0.7", None)
            )

    for ident in sorted(set(new_keyed) - set(old_keyed)):
        if ident in recovered:
            findings.append(
                Finding(command, f"{ident} new under 0.7", "jsonl-only-recovered")
            )
        else:
            findings.append(
                Finding(command, f"{ident} absent under 0.6, present under 0.7", None)
            )

    for ident in sorted(set(old_keyed) & set(new_keyed)):
        if old_keyed[ident] != new_keyed[ident]:
            findings.append(
                Finding(
                    command,
                    f"{ident} renders differently:\n"
                    f"      0.6: {old_keyed[ident]}\n"
                    f"      0.7: {new_keyed[ident]}",
                    None,
                )
            )

    shared_old = [i for i in old_order if i in new_keyed]
    shared_new = [i for i in new_order if i in old_keyed]
    if shared_old != shared_new:
        findings.append(
            Finding(command, "the shared seeds come back in a different order", None)
        )

    if old_plain != new_plain:
        extra_old = [line for line in old_plain if line not in new_plain]
        extra_new = [line for line in new_plain if line not in old_plain]
        moved = {
            line.strip()
            for split in splits.values()
            for line in split.moved.splitlines()
        }
        # 0.6 printed a multi-line title as the seed's line plus its trailing
        # lines, which have no id and land here. Allowlisted only when every
        # 0.6-only line is one of those exact lines and 0.7 added none. At
        # least one has to carry text: a difference that is only blank lines
        # is not evidence of a title split and is not covered by this rule.
        explained = any(line.strip() for line in extra_old) and all(
            line.strip() in moved for line in extra_old
        )
        if extra_old and not extra_new and explained:
            findings.append(
                Finding(
                    command,
                    f"{len(extra_old)} line(s) 0.6 printed under a seed are the "
                    f"tail of a multi-line title, now in that seed's body",
                    "legacy-title-split",
                )
            )
        else:
            findings.append(
                Finding(
                    command,
                    "non-seed output lines differ:\n"
                    + "\n".join(f"      0.6: {line}" for line in extra_old)
                    + "\n"
                    + "\n".join(f"      0.7: {line}" for line in extra_new),
                    None,
                )
            )
    return findings


def classify_search(
    query: str,
    old_ids: Sequence[str],
    new_ids: Sequence[str],
    file_text: Mapping[str, str],
) -> list[Finding]:
    """Classify one search query's result sets.

    ``file_text`` maps seed id -> the text of its 0.7 seed file, which is
    exactly what ripgrep scanned. That is what decides whether a hit 0.6 found
    and 0.7 missed was a stemming match (allowlisted, ruled) or a literal that
    ripgrep should have found (a regression).
    """
    command = f"search {query!r}"
    findings: list[Finding] = []
    needle = query.casefold()

    for ident in sorted(set(old_ids) - set(new_ids)):
        haystack = file_text.get(ident)
        if haystack is None:
            findings.append(
                Finding(
                    command, f"{ident} matched under 0.6 and has no seed file", None
                )
            )
        elif needle in haystack.casefold():
            findings.append(
                Finding(
                    command,
                    f"{ident} contains {query!r} literally, matched under 0.6, "
                    "and was NOT found by ripgrep under 0.7",
                    None,
                )
            )
        else:
            findings.append(
                Finding(
                    command,
                    f"{ident} matched under 0.6 without containing {query!r} "
                    "literally (Porter stem match)",
                    "search-stemming",
                )
            )

    for ident in sorted(set(new_ids) - set(old_ids)):
        findings.append(
            Finding(
                command, f"{ident} matched under 0.7 only", "search-substring-broader"
            )
        )

    if set(old_ids) == set(new_ids) and list(old_ids) != list(new_ids):
        findings.append(Finding(command, "same ids, different order", "search-order"))
    return findings


def classify_export(
    old_records: Mapping[str, dict],
    new_records: Mapping[str, dict],
    *,
    dropped_fixtures: frozenset[str],
    recovered: frozenset[str],
    dropped_edge_types: frozenset[str] = frozenset(),
    splits: Mapping[str, TitleSplit] = MappingProxyType({}),
) -> list[Finding]:
    """Field-by-field diff of the two corpora."""
    command = "export"
    findings: list[Finding] = []

    for ident in sorted(set(old_records) - set(new_records)):
        rule = "fixtures-dropped" if ident in dropped_fixtures else None
        findings.append(Finding(command, f"{ident} is not in the 0.7 corpus", rule))
    for ident in sorted(set(new_records) - set(old_records)):
        rule = "jsonl-only-recovered" if ident in recovered else None
        findings.append(Finding(command, f"{ident} is new in the 0.7 corpus", rule))

    for ident in sorted(set(old_records) & set(new_records)):
        old, new = old_records[ident], new_records[ident]
        for key in sorted(set(old) | set(new)):
            if key == "format_version" and key not in new:
                findings.append(
                    Finding(
                        command,
                        f"{ident}: 'format_version' dropped",
                        "export-field-set",
                    )
                )
                continue
            if key == "converted_at" and key not in old:
                findings.append(
                    Finding(
                        command, f"{ident}: 'converted_at' added", "export-field-set"
                    )
                )
                continue
            if key == "parent" and key not in old:
                if new.get("parent") == derived_parent(ident):
                    findings.append(
                        Finding(command, f"{ident}: 'parent' added", "export-field-set")
                    )
                else:
                    findings.append(
                        Finding(
                            command,
                            f"{ident}: 'parent' is {new.get('parent')!r}, but the id "
                            f"implies {derived_parent(ident)!r}",
                            None,
                        )
                    )
                continue
            if old.get(key) == new.get(key):
                continue
            if key in ("title", "content") and ident in splits:
                findings.append(
                    Finding(
                        command,
                        f"{ident}: {key!r} differs because the multi-line 0.6 "
                        f"title was cut and its tail moved into the body",
                        "legacy-title-split",
                    )
                )
                continue
            if key == "relationships":
                findings.extend(
                    _classify_edges(
                        ident,
                        old.get(key) or [],
                        new.get(key) or [],
                        new_records,
                        dropped_edge_types,
                    )
                )
                continue
            if isinstance(old.get(key), str) and isinstance(new.get(key), str):
                if trailing_newline_only(old[key], new[key]):
                    findings.append(
                        Finding(
                            command,
                            f"{ident}: {key!r} gained a trailing newline",
                            "body-trailing-newline",
                        )
                    )
                    continue
                if leading_newline_only(old[key], new[key]):
                    findings.append(
                        Finding(
                            command,
                            f"{ident}: {key!r} lost its leading blank line(s)",
                            "body-leading-newline",
                        )
                    )
                    continue
            findings.append(
                Finding(
                    command,
                    f"{ident}: {key!r} differs\n"
                    f"      0.6: {_clip(old.get(key))}\n"
                    f"      0.7: {_clip(new.get(key))}",
                    None,
                )
            )
    return findings


def _clip(value: object, width: int = 160) -> str:
    text = repr(value)
    return text if len(text) <= width else text[: width - 3] + "..."


def _edge_key(edge: Mapping[str, object]) -> tuple[object, object]:
    return (edge.get("target_id"), edge.get("rel_type"))


def _classify_edges(
    ident: str,
    old_edges: Iterable[Mapping[str, object]],
    new_edges: Iterable[Mapping[str, object]],
    new_records: Mapping[str, dict],
    dropped_edge_types: frozenset[str],
) -> list[Finding]:
    """An added edge is allowlisted only as a materialized 'questioned-by' half.

    A LOST edge is allowlisted only when the converter itself reported dropping
    edges of that type -- so the ruled 'answers' drop reads as a declared
    difference, and a lost edge the converter never mentioned stays a
    regression.
    """
    command = "export"
    findings: list[Finding] = []
    old_set = {_edge_key(e) for e in old_edges}
    new_set = {_edge_key(e) for e in new_edges}

    for target, rel_type in sorted(old_set - new_set, key=repr):
        rule = "vestigial-answers-dropped" if rel_type in dropped_edge_types else None
        findings.append(
            Finding(command, f"{ident}: edge {rel_type} -> {target} was lost", rule)
        )
    for target, rel_type in sorted(new_set - old_set, key=repr):
        if rel_type == "questioned-by" and _has_edge(
            new_records.get(str(target)), ident, "questions"
        ):
            findings.append(
                Finding(
                    command,
                    f"{ident}: materialized inverse questioned-by -> {target}",
                    "questioned-by-inverse",
                )
            )
        else:
            findings.append(
                Finding(command, f"{ident}: edge {rel_type} -> {target} appeared", None)
            )
    return findings


def _has_edge(record: Mapping[str, object] | None, target: str, rel_type: str) -> bool:
    if record is None:
        return False
    edges = record.get("relationships") or []
    return any(
        isinstance(e, Mapping)
        and e.get("target_id") == target
        and e.get("rel_type") == rel_type
        for e in edges  # type: ignore[union-attr]
    )


#: The line 'show' prints immediately before the body, in both versions.
CONTENT_HEADING = "Content:"


def split_show_body(text: str) -> tuple[str, str] | None:
    """``show`` output as ``(header, body)``, cut at its ``Content:`` heading.

    ``None`` when there is no heading, which is a seed with an empty body --
    there is no body block to compare, so the caller must not pretend there is.
    The FIRST such line is the heading: every header line 'show' emits is either
    'id: title' or indented, so none of them can be this, while a body line
    could be.
    """
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line == CONTENT_HEADING:
            return "\n".join(lines[: i + 1]), "\n".join(lines[i + 1 :])
    return None


def show_body_blank_lines(old: str, new: str) -> str | None:
    """The allowlist rule for a 'show' pair differing only in body blank lines.

    ``None`` when no rule applies, and it is deliberately hard to satisfy:
    the two headers must be identical line for line, and the two body blocks
    must be the same text once blank lines are stripped off BOTH ends. Only
    then is the difference attributed -- to ``body-leading-newline`` when 0.6
    is the side carrying leading blank lines, and to ``body-trailing-newline``
    when the difference is confined to the trailing end (0.7 rstrips the body
    before printing it; 0.6 printed the column verbatim).
    """
    old_parts = split_show_body(old)
    new_parts = split_show_body(new)
    if old_parts is None or new_parts is None:
        return None
    old_header, old_body = old_parts
    new_header, new_body = new_parts
    if old_header != new_header or old_body == new_body:
        return None
    if old_body.strip("\n") != new_body.strip("\n"):
        return None
    if old_body.lstrip("\n") != old_body and new_body.lstrip("\n") == new_body:
        return "body-leading-newline"
    if old_body.rstrip("\n") == new_body.rstrip("\n"):
        return "body-trailing-newline"
    return None


def show_title_split(seed_id: str, split: TitleSplit, old: str, new: str) -> bool:
    """True when the whole 'show' difference is the title cut, and nothing else.

    Reconstructs 0.6's output from 0.7's rather than comparing loosely: put the
    full multi-line title back on the header line and the header must match 0.6
    exactly, then the two body blocks must satisfy :func:`title_split_only`.
    Any other difference in the header or the body survives and is reported.
    """
    old_parts = split_show_body(old)
    new_parts = split_show_body(new)
    if old_parts is None or new_parts is None:
        return False
    restored = new_parts[0].replace(
        f"{seed_id}: {split.new_title}", f"{seed_id}: {split.old_title}", 1
    )
    if restored != old_parts[0]:
        return False
    return title_split_only(
        split.old_title, old_parts[1], split.new_title, new_parts[1]
    )


def classify_show(
    seed_id: str,
    old: str,
    new: str,
    new_full: str,
    split: TitleSplit | None = None,
) -> list[Finding]:
    """0.6 'show' against 0.7 'show', falling back to 0.7 'show --full'."""
    command = f"show {seed_id}"
    if old == new:
        return []
    if old == new_full:
        return [
            Finding(
                command,
                "0.7 'show' re-renders superseded text; 'show --full' reproduces "
                "the 0.6 output exactly",
                "show-full-supersede",
            )
        ]
    if split is not None and show_title_split(seed_id, split, old, new):
        return [
            Finding(
                command,
                "identical once the multi-line title is put back together: 0.7 "
                "moved its tail into the body",
                "legacy-title-split",
            )
        ]
    rule = show_body_blank_lines(old, new)
    if rule is not None:
        return [
            Finding(
                command,
                "identical apart from blank lines at the edges of the body block",
                rule,
            )
        ]
    return [
        Finding(
            command,
            "neither 'show' nor 'show --full' reproduces the 0.6 output:\n"
            + _first_line_diff(old, new),
            None,
        )
    ]


def _first_line_diff(old: str, new: str) -> str:
    old_lines, new_lines = old.splitlines(), new.splitlines()
    for i in range(max(len(old_lines), len(new_lines))):
        a = old_lines[i] if i < len(old_lines) else "<end>"
        b = new_lines[i] if i < len(new_lines) else "<end>"
        if a != b:
            return f"      line {i + 1}\n      0.6: {a}\n      0.7: {b}"
    return "      (identical line by line; trailing bytes differ)"


def derive_queries(records: Iterable[Mapping[str, object]], limit: int) -> list[str]:
    """Deterministic, corpus-relevant search terms.

    Words rather than a fixed list, because a fixed list is how a search
    comparison ends up VACUOUS on a corpus that never uses those words. Only
    ``[a-z]{5,}`` tokens, so every query is both a valid FTS5 term and a
    literal regex.
    """
    counts: Counter[str] = Counter()
    for record in records:
        title = record.get("title")
        if isinstance(title, str):
            counts.update(re.findall(r"[a-z]{5,}", title.casefold()))
    return [word for word, _ in sorted(counts.most_common(limit * 3))][:limit]


# --- Running the two versions -------------------------------------------------


@dataclass
class Runner:
    """Invokes one seeds version against one store."""

    argv: list[str]
    cwd: Path
    seeds_dir: Path

    def __call__(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        # uv resolves --project against a clean slate; inherited venv pointers
        # from the parent `uv run` would otherwise pick the wrong interpreter.
        for key in (
            "VIRTUAL_ENV",
            "UV_PROJECT_ENVIRONMENT",
            "PYTHONPATH",
            "PYTHONHOME",
        ):
            env.pop(key, None)
        env["SEEDS_DIR"] = str(self.seeds_dir)
        env["NO_COLOR"] = "1"
        return subprocess.run(
            [*self.argv, *args],
            cwd=self.cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )


def provision_legacy(work: Path) -> Path:
    """Extract the ``v0.6.0`` tag into ``work``.

    ``git archive`` rather than ``git worktree add``: a worktree writes into the
    shared ``.git`` of a repo this harness is only ever allowed to read, and an
    interrupted run would leave the registration behind. An archive touches
    nothing.
    """
    root = work / "seeds-0.6"
    root.mkdir(parents=True)
    archive = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "archive", LEGACY_TAG],
        capture_output=True,
        check=False,
    )
    if archive.returncode != 0:
        raise Refusal(
            f"cannot extract {LEGACY_TAG} from {REPO_ROOT}: "
            f"{archive.stderr.decode(errors='replace').strip()}",
            reason="harness-broken",
        )
    extract = subprocess.run(
        ["tar", "-x", "-C", str(root)],
        input=archive.stdout,
        capture_output=True,
        check=False,
    )
    if extract.returncode != 0:
        raise Refusal(
            f"cannot unpack {LEGACY_TAG}: {extract.stderr.decode(errors='replace')}",
            reason="harness-broken",
        )
    if not (root / "src" / "seeds" / "db.py").exists():
        raise Refusal(
            f"{LEGACY_TAG} has no src/seeds/db.py, so it is not a pre-0.7 checkout",
            reason="harness-broken",
        )
    return root


def legacy_argv(root: Path) -> list[str]:
    return ["uv", "run", "--quiet", "--project", str(root), "seeds"]


def current_argv() -> list[str]:
    console = Path(sys.executable).parent / "seeds"
    if console.exists():
        return [str(console)]
    return ["uv", "run", "--quiet", "--project", str(REPO_ROOT), "seeds"]


def read_jsonl(path: Path) -> dict[str, dict]:
    records: dict[str, dict] = {}
    if not path.exists():
        return records
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                records[record["id"]] = record
    return records


def parse_ids(text: str) -> list[str]:
    """Seed ids, in output order, from a rendered listing."""
    out = []
    for line in text.splitlines():
        ident = line_id(line)
        if ident is not None:
            out.append(ident)
    return out


# --- Fault injection ----------------------------------------------------------

INJECTIONS = ("drop-seed", "mutate-title", "truncate-body")


def inject(kind: str, files_dir: Path) -> str:
    """Make a deliberate behavioural change to the converted copy.

    The point is to prove the harness CAN fail. Each of these is a difference
    no allowlist rule covers, so a run that reports zero regressions after one
    has been applied is a broken harness, not a clean conversion.
    """
    victims = sorted(files_dir.glob("*.md"))
    if not victims:
        raise Refusal(
            "nothing to inject into: the converted tree has no seed files",
            reason="harness-broken",
        )
    victim = victims[0]
    if kind == "drop-seed":
        victim.unlink()
        return f"deleted {victim.name}"
    text = victim.read_text(encoding="utf-8")
    if kind == "mutate-title":
        new_text = re.sub(
            r"^title: (.*)$", r"title: INJECTED \1", text, count=1, flags=re.MULTILINE
        )
        if new_text == text:
            raise Refusal(
                f"{victim.name} has no 'title:' line to mutate",
                reason="harness-broken",
            )
        victim.write_text(new_text, encoding="utf-8")
        return f"rewrote the title of {victim.name}"
    if kind == "truncate-body":
        head, sep, body = text.partition("\n---\n")
        if not sep or len(body) < 40:
            raise Refusal(
                f"{victim.name} has no body long enough to truncate",
                reason="harness-broken",
            )
        victim.write_text(head + sep + body[: len(body) // 2] + "\n", encoding="utf-8")
        return f"truncated the body of {victim.name}"
    raise Refusal(f"unknown injection {kind!r}", reason="harness-broken")


# --- Per-repo run -------------------------------------------------------------


@dataclass
class RepoResult:
    repo: Path
    old_count: int = 0
    new_count: int = 0
    conversion: str = ""
    #: What 0.7 alone did to the store, in one clause, independent of any
    #: comparison. Kept apart from :attr:`conversion` because a refusal that
    #: never reaches a comparison still has this much to report, and because
    #: it must name whether the round trip was VERIFIED rather than implying it.
    conversion_headline: str = ""
    comparisons: list[Comparison] = field(default_factory=list)
    injected: str | None = None
    old_db_records: dict[str, dict] = field(default_factory=dict)
    new_records: dict[str, dict] = field(default_factory=dict)
    source_jsonl_records: dict[str, dict] = field(default_factory=dict)
    dropped_fixtures: frozenset[str] = frozenset()
    #: rel_type values the converter reported dropping as vestigial (§5.2).
    dropped_edge_types: frozenset[str] = frozenset()

    @property
    def findings(self) -> list[Finding]:
        return [f for c in self.comparisons for f in c.findings]

    @property
    def regressions(self) -> list[Finding]:
        return [f for f in self.findings if f.is_regression]


#: Comparisons that MUST produce output, or the run has proved nothing. A green
#: verdict from a harness that compared three empty strings is the failure mode
#: this list exists to make impossible.
MANDATORY = ("list --all", "show", "export")


def run_repo(
    repo: Path,
    work: Path,
    legacy_root: Path,
    *,
    injection: str | None,
    max_seeds: int | None,
    queries: int,
) -> RepoResult:
    source = repo / ".seeds"
    if not source.is_dir():
        raise Refusal(f"{repo}: no .seeds directory", reason="not-a-store")
    if (source / "seeds").is_dir():
        raise Refusal(
            f"{repo}: .seeds/seeds/ already exists, so this store is already "
            "converted; there is no pre-conversion behaviour left to compare",
            reason="already-converted",
        )
    if not (source / "seeds.db").exists() and not (source / "seeds.jsonl").exists():
        raise Refusal(
            f"{repo}: .seeds holds neither seeds.db nor seeds.jsonl",
            reason="not-a-store",
        )

    result = RepoResult(repo=repo)
    result.source_jsonl_records = read_jsonl(source / "seeds.jsonl")

    old_dir = work / "old"
    new_dir = work / "new"
    old_dir.mkdir(parents=True)
    new_dir.mkdir(parents=True)
    shutil.copytree(source, old_dir / ".seeds")
    shutil.copytree(source, new_dir / ".seeds")

    old = Runner(legacy_argv(legacy_root), old_dir, old_dir / ".seeds")
    new = Runner(current_argv(), new_dir, new_dir / ".seeds")

    # 1. Convert the copy. A converter that raises is itself the finding.
    from seeds.convert import ConversionError, convert

    try:
        report = convert(new_dir / ".seeds")
    except ConversionError as exc:
        raise Refusal(
            f"{repo}: seeds convert refused: {exc}", reason="convert-crashed"
        ) from exc
    except Exception as exc:
        raise Refusal(
            f"{repo}: seeds convert CRASHED on this store, so 0.7 behaviour cannot "
            f"be observed at all: {type(exc).__name__}: {exc}",
            reason="convert-crashed",
        ) from exc
    result.dropped_fixtures = frozenset(report.dropped_fixtures)
    result.dropped_edge_types = frozenset(report.dropped_legacy_edges)
    vestigial = ", ".join(
        f"{count} vestigial {rel_type!r} edge(s) dropped"
        for rel_type, count in sorted(report.dropped_legacy_edges.items())
    )
    result.conversion = (
        f"{report.source_ids} source id(s) -> {report.total} converted, "
        f"{len(report.dropped_fixtures)} fixture(s) dropped, "
        + (f"{vestigial}, " if vestigial else "")
        + f"{len(report.forks)} fork(s), "
        f"check {'clean' if report.clean else 'NOT CLEAN'}"
    )
    result.conversion_headline = (
        f"{report.total} seed(s) converted, {report.verified} round-trip "
        f"verified, check {'clean' if report.clean else 'NOT CLEAN'}"
    )
    if report.forks or report.check_findings:
        result.comparisons.append(
            Comparison(
                "convert",
                vacuous=False,
                findings=[
                    Finding(
                        "convert",
                        f"the conversion did not finish cleanly: {len(report.forks)} "
                        f"unresolved fork(s), {len(report.check_findings)} check "
                        "finding(s)",
                        None,
                    )
                ],
            )
        )

    if injection:
        result.injected = inject(injection, new_dir / ".seeds" / "seeds")

    # 2. The corpora. 0.6's authoritative view is its SQLite, which
    #    `sync --flush-only` writes out; 0.7's is `export --json`.
    flush = old("sync", "--flush-only")
    if flush.returncode != 0:
        absent = missing_legacy_table(flush.stderr)
        if absent is not None:
            raise Refusal(
                f"{repo}: seeds 0.6 ({LEGACY_TAG}) cannot read this store either "
                f"-- its own db.py raises 'no such table: {absent}', and 0.6 never "
                "runs the migration that would create one -- so there is no 0.6 "
                "baseline to compare against and nothing here is evidence about "
                "0.7. This store was already orphaned under 0.6, before 0.7 "
                f"existed. 0.7 does read it: {result.conversion_headline}",
                reason="no-0.6-baseline",
            )
        raise Refusal(
            f"{repo}: 0.6 'sync --flush-only' failed: {last_error_line(flush.stderr)}",
            reason="0.6-command-failed",
        )
    result.old_db_records = read_jsonl(old_dir / ".seeds" / "seeds.jsonl")
    dump = new("export", "--json")
    if dump.returncode != 0:
        raise Refusal(
            f"{repo}: 0.7 'export --json' failed: {last_error_line(dump.stderr)}",
            reason="0.7-command-failed",
        )
    result.new_records = {
        json.loads(line)["id"]: json.loads(line)
        for line in dump.stdout.splitlines()
        if line.strip()
    }
    result.old_count = len(result.old_db_records)
    result.new_count = len(result.new_records)
    if not result.old_count or not result.new_count:
        raise Refusal(
            f"{repo}: corpus is empty on one side (0.6: {result.old_count}, "
            f"0.7: {result.new_count}); there is nothing to compare",
            reason="empty-corpus",
        )

    recovered = frozenset(set(result.source_jsonl_records) - set(result.old_db_records))
    splits = title_splits(result.old_db_records, result.new_records)

    export_findings = classify_export(
        result.old_db_records,
        result.new_records,
        dropped_fixtures=result.dropped_fixtures,
        recovered=recovered,
        dropped_edge_types=result.dropped_edge_types,
        splits=splits,
    )
    result.comparisons.append(
        Comparison("export", vacuous=False, findings=export_findings)
    )

    # 3. The listing commands.
    for command in (
        ("list",),
        ("list", "--all"),
        ("ready",),
        ("deferred",),
        ("recent",),
        ("recent", "--since", "3650d", "--all"),
        ("questions",),
        ("blocked",),
    ):
        label = " ".join(command)
        o, n = old(*command), new(*command)
        if o.returncode != n.returncode:
            result.comparisons.append(
                Comparison(
                    label,
                    vacuous=False,
                    findings=[
                        Finding(
                            label,
                            "exit status differs: "
                            f"0.6 -> {o.returncode}, 0.7 -> {n.returncode}",
                            None,
                        )
                    ],
                )
            )
            continue
        result.comparisons.append(
            Comparison(
                label,
                vacuous=not o.stdout.strip() and not n.stdout.strip(),
                findings=classify_lines(
                    label,
                    o.stdout,
                    n.stdout,
                    dropped_fixtures=result.dropped_fixtures,
                    recovered=recovered,
                    splits=splits,
                ),
            )
        )

    # 4. prime: static template allowlisted, generated digest compared in full.
    o, n = old("prime"), new("prime")
    old_head, old_digest = split_prime(o.stdout)
    new_head, new_digest = split_prime(n.stdout)
    prime_findings: list[Finding] = []
    if old_head != new_head:
        prime_findings.append(
            Finding(
                "prime", "the static instructional template differs", "prime-preamble"
            )
        )
    prime_findings.extend(
        classify_lines(
            "prime (digest)",
            old_digest,
            new_digest,
            dropped_fixtures=result.dropped_fixtures,
            recovered=recovered,
            splits=splits,
        )
    )
    result.comparisons.append(
        Comparison("prime", vacuous=not new_digest.strip(), findings=prime_findings)
    )

    # 5. Per-seed: show, show --full, tree. Every seed, not a sample.
    ids = sorted(set(result.old_db_records) & set(result.new_records))
    truncated = max_seeds is not None and len(ids) > max_seeds
    if truncated:
        ids = ids[:max_seeds]
    show_findings: list[Finding] = []
    tree_findings: list[Finding] = []
    full_findings: list[Finding] = []
    show_nonempty = False
    for ident in ids:
        o_show = old("show", ident)
        n_show = new("show", ident)
        n_full = new("show", ident, "--full")
        show_nonempty = show_nonempty or bool(o_show.stdout.strip())
        show_findings.extend(
            classify_show(
                ident,
                o_show.stdout,
                n_show.stdout,
                n_full.stdout,
                splits.get(ident),
            )
        )
        if not n_full.stdout.strip():
            full_findings.append(
                Finding(f"show {ident} --full", "produced no output under 0.7", None)
            )
        elif len(n_full.stdout) < len(n_show.stdout):
            full_findings.append(
                Finding(
                    f"show {ident} --full",
                    "is shorter than plain 'show', so it is not a superset",
                    None,
                )
            )
        o_tree, n_tree = old("tree", ident), new("tree", ident)
        tree_findings.extend(
            classify_lines(
                f"tree {ident}",
                o_tree.stdout,
                n_tree.stdout,
                dropped_fixtures=result.dropped_fixtures,
                recovered=recovered,
                splits=splits,
            )
        )
    result.comparisons.append(
        Comparison("show", vacuous=not show_nonempty, findings=show_findings)
    )
    result.comparisons.append(
        Comparison("show --full", vacuous=not ids, findings=full_findings)
    )
    result.comparisons.append(
        Comparison("tree", vacuous=not ids, findings=tree_findings)
    )
    if full_findings == []:
        result.comparisons[-2].findings.append(
            Finding(
                "show --full",
                f"exercised under 0.7 on {len(ids)} seed(s); 0.6 has no such flag",
                "show-full-no-counterpart",
            )
        )

    # 6. search.
    file_text = {
        path.stem: path.read_text(encoding="utf-8")
        for path in (new_dir / ".seeds" / "seeds").glob("*.md")
    }
    search_findings: list[Finding] = []
    searched = 0
    for query in derive_queries(result.new_records.values(), queries):
        o, n = old("search", query, "--all"), new("search", query, "--all")
        if not o.stdout.strip() and not n.stdout.strip():
            continue
        searched += 1
        search_findings.extend(
            classify_search(query, parse_ids(o.stdout), parse_ids(n.stdout), file_text)
        )
    result.comparisons.append(
        Comparison("search", vacuous=searched == 0, findings=search_findings)
    )

    if truncated:
        result.conversion += f"  [PARTIAL: per-seed commands capped at {max_seeds}]"

    # The anti-vacuity guard. A verdict is only worth its denominator, and the
    # denominator here is "did the commands that MUST have compared something
    # actually compare something".
    empty = [
        c.command for c in result.comparisons if c.command in MANDATORY and c.vacuous
    ]
    if empty:
        raise Refusal(
            f"{repo}: {', '.join(empty)} produced no output on either side, so a "
            "clean verdict would rest on comparing nothing",
            reason="empty-corpus",
        )
    return result


# --- Cross-repo: the JSONL glob against the DuckDB recipe ----------------------

#: The question both recipes are asked. Deliberately field-shaped rather than
#: full-text: structured extraction is the workflow `seeds export --json`
#: replaces, and full-text search across repos is ripgrep's job now.
CROSS_REPO_QUERY = (
    "SELECT id, status, seed_type FROM read_json_auto("
    "'/dev/stdin', format='newline_delimited', union_by_name=true) ORDER BY id"
)


def duckdb_rows(stream: bytes) -> list[tuple[str, str, str]]:
    """Run :data:`CROSS_REPO_QUERY` over a JSONL byte stream on stdin."""
    proc = subprocess.run(
        ["duckdb", "-csv", "-noheader", "-c", CROSS_REPO_QUERY],
        input=stream,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise Refusal(
            f"duckdb failed: {proc.stderr.decode(errors='replace').strip()}",
            reason="harness-broken",
        )
    rows = []
    for line in proc.stdout.decode().splitlines():
        parts = line.split(",")
        if len(parts) >= 3:
            rows.append((parts[0], parts[1], parts[2]))
    return rows


def cross_repo(results: Sequence[RepoResult]) -> tuple[list[Finding], str]:
    """Diff the retired JSONL-glob recipe against the documented DuckDB one."""
    old_stream = b"".join(
        (json.dumps(r) + "\n").encode()
        for res in results
        for r in res.source_jsonl_records.values()
    )
    new_stream = b"".join(
        (json.dumps(r) + "\n").encode()
        for res in results
        for r in res.new_records.values()
    )
    if not old_stream or not new_stream:
        raise Refusal(
            "cross-repo: one of the two streams is empty; nothing compared",
            reason="empty-corpus",
        )

    old_rows = {row[0]: row for row in duckdb_rows(old_stream)}
    new_rows = {row[0]: row for row in duckdb_rows(new_stream)}

    db_view: dict[str, dict] = {}
    dropped: set[str] = set()
    for res in results:
        db_view.update(res.old_db_records)
        dropped |= set(res.dropped_fixtures)

    command = "cross-repo (JSONL glob vs seeds export --json | duckdb)"
    findings: list[Finding] = []
    for ident in sorted(set(old_rows) - set(new_rows)):
        rule = "fixtures-dropped" if ident in dropped else None
        findings.append(
            Finding(
                command, f"{ident}: in the committed JSONL, not in the new answer", rule
            )
        )
    for ident in sorted(set(new_rows) - set(old_rows)):
        rule = "stale-committed-jsonl" if ident in db_view else None
        detail = f"{ident}: in the new answer, missing from the committed JSONL"
        if rule:
            detail += " (it was in the 0.6 SQLite all along -- the JSONL was stale)"
        findings.append(Finding(command, detail, rule))
    for ident in sorted(set(old_rows) & set(new_rows)):
        if old_rows[ident] == new_rows[ident]:
            continue
        record = db_view.get(ident)
        agrees = record is not None and (
            (record.get("status"), record.get("seed_type"))
            == (new_rows[ident][1], new_rows[ident][2])
        )
        findings.append(
            Finding(
                command,
                f"{ident}: JSONL says {old_rows[ident][1:]}, new answer says "
                f"{new_rows[ident][1:]}"
                + (" (0.6 SQLite agrees with the new answer)" if agrees else ""),
                "stale-committed-jsonl" if agrees else None,
            )
        )
    summary = (
        f"{len(results)} repo(s); old recipe returned {len(old_rows)} row(s), "
        f"new recipe returned {len(new_rows)}"
    )
    return findings, summary


# --- Report -------------------------------------------------------------------


def format_repo(result: RepoResult) -> str:
    lines = [f"{result.repo}"]
    lines.append(
        f"  corpus: {result.old_count} seed(s) under 0.6, {result.new_count} under 0.7"
    )
    lines.append(f"  conversion: {result.conversion}")
    if result.injected:
        lines.append(f"  INJECTED FAULT: {result.injected}")
    vacuous = [c.command for c in result.comparisons if c.vacuous]
    lines.append(
        f"  comparisons: {len(result.comparisons)}"
        + (f" (vacuous: {', '.join(vacuous)})" if vacuous else " (none vacuous)")
    )
    hits = Counter(f.rule for f in result.findings if f.rule)
    lines.append(
        f"  differences: {len(result.findings)}  "
        f"allowlisted: {len(result.findings) - len(result.regressions)}  "
        f"REGRESSIONS: {len(result.regressions)}"
    )
    for rule, count in sorted(hits.items()):
        lines.append(f"    [{rule}] {count}")
    for finding in result.regressions:
        lines.append(f"    REGRESSION  {finding.command}: {finding.detail}")
    return "\n".join(lines)


def group_refusals(refusals: Sequence[tuple[str, str]]) -> list[tuple[str, list[str]]]:
    """Refusal messages bucketed by cause, in :data:`REFUSAL_REASONS` order.

    The order is the declaration order rather than the encounter order so the
    summary reads the same way every run, and so the causes stay side by side
    instead of interleaving with whatever order the repos were named in.
    """
    by_reason: dict[str, list[str]] = {}
    for reason, message in refusals:
        by_reason.setdefault(reason, []).append(message)
    ordered = [(r, by_reason[r]) for r in REFUSAL_REASONS if r in by_reason]
    # A reason the table does not describe would vanish here; report it rather
    # than silently dropping a refusal out of the summary.
    ordered.extend((r, m) for r, m in by_reason.items() if r not in REFUSAL_REASONS)
    return ordered


def format_refusals(refusals: Sequence[tuple[str, str]]) -> str:
    """The refusal summary: causes first, each with its argument, then repos.

    The bead this shape answers (``seeds-4co.27``) is about an operator reading
    a refusal on ``mani`` and concluding 0.7 broke the repo, when in fact 0.6
    had already orphaned it. So the cause is stated before the repos it hit,
    and stated as a reason rather than a slug -- the same discipline
    :data:`ALLOWLIST` is held to.
    """
    out: list[str] = []
    for reason, messages in group_refusals(refusals):
        out.append(f"  [{reason}] {len(messages)} repo(s)")
        why = REFUSAL_REASONS.get(reason, "UNDOCUMENTED refusal reason.")
        out.extend(f"    why: {line}" for line in why.replace(". ", ".\n").split("\n"))
        out.extend(f"    - {message}" for message in messages)
    return "\n".join(out)


def format_allowlist() -> str:
    out = ["Allowlist -- known-expected differences, each with its justification:"]
    for name, why in ALLOWLIST.items():
        out.append(f"\n  {name}")
        out.append("    " + why.replace(". ", ".\n    "))
    return "\n".join(out)


# --- Logging ------------------------------------------------------------------


class Tee:
    """Write to the terminal and to a timestamped log at the same time.

    Every diagnostic in these repos leaves a dated artifact under
    ``claude_stuff/`` so a run can be compared against last month's rather than
    living only in somebody's scrollback. Doing it here rather than in a shell
    pipeline also keeps the exit status honest: a ``cmd | tee log`` reports
    tee's status, not the harness's.
    """

    def __init__(self, stream, handle) -> None:
        self._stream = stream
        self._handle = handle

    def write(self, text: str) -> int:
        self._handle.write(text)
        return self._stream.write(text)

    def flush(self) -> None:
        self._handle.flush()
        self._stream.flush()


def log_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    directory = REPO_ROOT / "claude_stuff"
    directory.mkdir(exist_ok=True)
    return directory / f"differential-harness-{stamp}.log"


# --- Entry point --------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Diff seeds 0.6 + SQLite against seeds 0.7 + the seed-file tree, "
            "over a COPY of each named repo's store."
        )
    )
    parser.add_argument(
        "repos", nargs="*", type=Path, help="repo roots holding a .seeds/"
    )
    parser.add_argument(
        "--legacy-checkout",
        type=Path,
        help=(
            "an existing pre-0.7 checkout; default extracts "
            f"{LEGACY_TAG} into a temp dir"
        ),
    )
    parser.add_argument(
        "--inject",
        choices=INJECTIONS,
        help=(
            "self-test: make this deliberate change to the converted copy and "
            "require the harness to report it. Exit 0 only if it does."
        ),
    )
    parser.add_argument(
        "--max-seeds",
        type=int,
        help="cap the per-seed commands (show/tree). Marks the run PARTIAL.",
    )
    parser.add_argument(
        "--queries", type=int, default=8, help="search queries per repo"
    )
    parser.add_argument(
        "--no-cross-repo", action="store_true", help="skip the cross-repo recipe diff"
    )
    parser.add_argument(
        "--show-allowlist", action="store_true", help="print the allowlist and exit"
    )
    parser.add_argument(
        "--no-log", action="store_true", help="skip the timestamped claude_stuff/ log"
    )
    args = parser.parse_args(argv)

    if args.show_allowlist:
        print(format_allowlist())
        return 0
    if not args.repos:
        parser.error("name at least one repo, or pass --show-allowlist")
    if args.no_log:
        return _run(args)
    path = log_path()
    saved = sys.stdout
    with path.open("w", encoding="utf-8") as handle:
        sys.stdout = Tee(saved, handle)  # type: ignore[assignment]
        try:
            status = _run(args)
        finally:
            sys.stdout = saved
    print(f"log: {path}")
    return status


def _run(args: argparse.Namespace) -> int:

    with tempfile.TemporaryDirectory(prefix="seeds-differential-") as tmp:
        work = Path(tmp)
        try:
            legacy = args.legacy_checkout or provision_legacy(work)
            version = subprocess.run(
                [*legacy_argv(legacy), "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            print(
                f"legacy:  {version.stdout.strip() or version.stderr.strip()}"
                f"  ({legacy})"
            )
            print(f"current: {REPO_ROOT}")
            print()

            results: list[RepoResult] = []
            refusals: list[tuple[str, str]] = []
            for i, repo in enumerate(args.repos):
                try:
                    results.append(
                        run_repo(
                            repo.resolve(),
                            work / f"repo{i}",
                            legacy,
                            injection=args.inject,
                            max_seeds=args.max_seeds,
                            queries=args.queries,
                        )
                    )
                except Refusal as exc:
                    refusals.append((exc.reason, str(exc)))
                    print(f"REFUSED  [{exc.reason}] {exc}\n")
            for result in results:
                print(format_repo(result))
                print()

            cross: list[Finding] = []
            if results and not args.no_cross_repo:
                try:
                    cross, summary = cross_repo(results)
                    hits = Counter(f.rule for f in cross if f.rule)
                    regressions = [f for f in cross if f.is_regression]
                    print(f"cross-repo: {summary}")
                    print(
                        f"  differences: {len(cross)}  "
                        f"allowlisted: {len(cross) - len(regressions)}  "
                        f"REGRESSIONS: {len(regressions)}"
                    )
                    for rule, count in sorted(hits.items()):
                        print(f"    [{rule}] {count}")
                    for finding in regressions:
                        print(f"    REGRESSION  {finding.detail}")
                    print()
                except Refusal as exc:
                    refusals.append((exc.reason, str(exc)))
                    print(f"REFUSED  [{exc.reason}] {exc}\n")

            total_regressions = sum(len(r.regressions) for r in results) + len(
                [f for f in cross if f.is_regression]
            )
        except Refusal as exc:
            print(f"REFUSED  [{exc.reason}] {exc}", file=sys.stderr)
            return 2

    if args.inject:
        # The self-test: the injected fault MUST surface as a regression.
        if total_regressions:
            print(
                f"SELF-TEST PASS: the injected {args.inject!r} fault was reported as "
                f"{total_regressions} regression(s)."
            )
            return 0
        print(
            f"SELF-TEST FAIL: the injected {args.inject!r} fault was NOT reported. "
            "The harness is blind to it.",
            file=sys.stderr,
        )
        return 1

    if refusals:
        print(
            f"REFUSED on {len(refusals)} repo(s); nothing was compared for them. "
            "By cause:"
        )
        print(format_refusals(refusals))
        return 2
    if total_regressions:
        print(f"FAIL: {total_regressions} unexplained difference(s).")
        return 1
    print(
        "OK: every difference is on the allowlist. "
        "Run --show-allowlist for the reasons."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
