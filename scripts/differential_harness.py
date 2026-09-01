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
        "one -- a body that differs anywhere else is a regression."
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


class Refusal(Exception):
    """The harness cannot make an honest comparison and says so."""


# --- Pure classifiers (unit-tested in tests/test_differential_harness.py) ------

#: A rendered seed line: a status glyph (or the ↔ relationship arrow), the id,
#: a colon. Anything else is "unkeyed" and compared as an exact sequence.
_LINE_ID = re.compile(r"^\s*\S{1,2} ([A-Za-z0-9_]+-[A-Za-z0-9]+(?:\.\d+)*): ")

PRIME_DIGEST_HEADING = "## Current Seeds"


def line_id(line: str) -> str | None:
    """The seed id a rendered line is about, or None if it is not a seed line."""
    m = _LINE_ID.match(line)
    return m.group(1) if m else None


def trailing_newline_only(old: str, new: str) -> bool:
    """True when the two bodies differ by trailing newlines and nothing else."""
    if old == new:
        return False
    return old.rstrip("\n") == new.rstrip("\n") and new.endswith("\n")


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
        "generated digest cannot be told apart from the static template"
    )


def classify_lines(
    command: str,
    old: str,
    new: str,
    *,
    dropped_fixtures: frozenset[str],
    recovered: frozenset[str],
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
        findings.append(
            Finding(
                command,
                "non-seed output lines differ:\n"
                + "\n".join(
                    f"      0.6: {line}" for line in old_plain if line not in new_plain
                )
                + "\n"
                + "\n".join(
                    f"      0.7: {line}" for line in new_plain if line not in old_plain
                ),
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
            if key == "relationships":
                findings.extend(
                    _classify_edges(
                        ident, old.get(key) or [], new.get(key) or [], new_records
                    )
                )
                continue
            if (
                isinstance(old.get(key), str)
                and isinstance(new.get(key), str)
                and trailing_newline_only(old[key], new[key])
            ):
                findings.append(
                    Finding(
                        command,
                        f"{ident}: {key!r} gained a trailing newline",
                        "body-trailing-newline",
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
) -> list[Finding]:
    """An added edge is allowlisted only as a materialized 'questioned-by' half."""
    command = "export"
    findings: list[Finding] = []
    old_set = {_edge_key(e) for e in old_edges}
    new_set = {_edge_key(e) for e in new_edges}

    for target, rel_type in sorted(old_set - new_set, key=repr):
        findings.append(
            Finding(command, f"{ident}: edge {rel_type} -> {target} was lost", None)
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


def classify_show(seed_id: str, old: str, new: str, new_full: str) -> list[Finding]:
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
            f"{archive.stderr.decode(errors='replace').strip()}"
        )
    extract = subprocess.run(
        ["tar", "-x", "-C", str(root)],
        input=archive.stdout,
        capture_output=True,
        check=False,
    )
    if extract.returncode != 0:
        raise Refusal(
            f"cannot unpack {LEGACY_TAG}: {extract.stderr.decode(errors='replace')}"
        )
    if not (root / "src" / "seeds" / "db.py").exists():
        raise Refusal(
            f"{LEGACY_TAG} has no src/seeds/db.py, so it is not a pre-0.7 checkout"
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
        raise Refusal("nothing to inject into: the converted tree has no seed files")
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
            raise Refusal(f"{victim.name} has no 'title:' line to mutate")
        victim.write_text(new_text, encoding="utf-8")
        return f"rewrote the title of {victim.name}"
    if kind == "truncate-body":
        head, sep, body = text.partition("\n---\n")
        if not sep or len(body) < 40:
            raise Refusal(f"{victim.name} has no body long enough to truncate")
        victim.write_text(head + sep + body[: len(body) // 2] + "\n", encoding="utf-8")
        return f"truncated the body of {victim.name}"
    raise Refusal(f"unknown injection {kind!r}")


# --- Per-repo run -------------------------------------------------------------


@dataclass
class RepoResult:
    repo: Path
    old_count: int = 0
    new_count: int = 0
    conversion: str = ""
    comparisons: list[Comparison] = field(default_factory=list)
    injected: str | None = None
    old_db_records: dict[str, dict] = field(default_factory=dict)
    new_records: dict[str, dict] = field(default_factory=dict)
    source_jsonl_records: dict[str, dict] = field(default_factory=dict)
    dropped_fixtures: frozenset[str] = frozenset()

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
        raise Refusal(f"{repo}: no .seeds directory")
    if (source / "seeds").is_dir():
        raise Refusal(
            f"{repo}: .seeds/seeds/ already exists, so this store is already "
            "converted; there is no pre-conversion behaviour left to compare"
        )
    if not (source / "seeds.db").exists() and not (source / "seeds.jsonl").exists():
        raise Refusal(f"{repo}: .seeds holds neither seeds.db nor seeds.jsonl")

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
        raise Refusal(f"{repo}: seeds convert refused: {exc}") from exc
    except Exception as exc:
        raise Refusal(
            f"{repo}: seeds convert CRASHED on this store, so 0.7 behaviour cannot "
            f"be observed at all: {type(exc).__name__}: {exc}"
        ) from exc
    result.dropped_fixtures = frozenset(report.dropped_fixtures)
    result.conversion = (
        f"{report.source_ids} source id(s) -> {report.total} converted, "
        f"{len(report.dropped_fixtures)} fixture(s) dropped, "
        f"{len(report.forks)} fork(s), "
        f"check {'clean' if report.clean else 'NOT CLEAN'}"
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
        raise Refusal(f"{repo}: 0.6 'sync --flush-only' failed: {flush.stderr.strip()}")
    result.old_db_records = read_jsonl(old_dir / ".seeds" / "seeds.jsonl")
    dump = new("export", "--json")
    if dump.returncode != 0:
        raise Refusal(f"{repo}: 0.7 'export --json' failed: {dump.stderr.strip()}")
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
            f"0.7: {result.new_count}); there is nothing to compare"
        )

    recovered = frozenset(set(result.source_jsonl_records) - set(result.old_db_records))

    export_findings = classify_export(
        result.old_db_records,
        result.new_records,
        dropped_fixtures=result.dropped_fixtures,
        recovered=recovered,
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
            classify_show(ident, o_show.stdout, n_show.stdout, n_full.stdout)
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
            "clean verdict would rest on comparing nothing"
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
        raise Refusal(f"duckdb failed: {proc.stderr.decode(errors='replace').strip()}")
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
        raise Refusal("cross-repo: one of the two streams is empty; nothing compared")

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
            refusals: list[str] = []
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
                    refusals.append(str(exc))
                    print(f"REFUSED  {exc}\n")
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
                    refusals.append(str(exc))
                    print(f"REFUSED  {exc}\n")

            total_regressions = sum(len(r.regressions) for r in results) + len(
                [f for f in cross if f.is_regression]
            )
        except Refusal as exc:
            print(f"REFUSED  {exc}", file=sys.stderr)
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
        print(f"REFUSED on {len(refusals)} repo(s); nothing was proved about them.")
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
