"""``seeds check`` — the violations tier.

Under files-as-truth there is no second store, so nearly everything today's
``seeds doctor`` verifies — JSONL readable, JSONL and DB agreeing, no
divergence — has nothing left to compare. What replaces it is a different job:
**content plausibility, not format validity**.

The proof is ``seeds-wurl``. On 2026-08-31 an agent's bulk sweep replaced the
title of 83 of 306 seeds with a scratchpad path. Every record parsed perfectly,
a path is valid free text, and both stores agreed — so every divergence check
was correctly green while the corpus was wrong, for three days and three
commits. Format validity had nothing to say about it.

``docs/storage-format.md`` §10 is the other half of the argument: that format
buys its simplicity by moving guarantees SQLite enforced *structurally* — a
foreign key, a transaction, a closed status column — into verification after
the fact. This module is where those guarantees now live. A rule in the spec
with no check here is enforced by nothing.

Two tiers are planned; this module is the first.

* **Violations** (here) exit non-zero and block a commit. Each one is either a
  file the reader would refuse, or a value that parses fine and is not
  plausible.
* **Smells** (``seeds check --smells``, bead ``seeds-4co.4``) report and never
  fail: an empty body, a long unsuperseded body, a duplicated body.

Two things deliberately absent, so a later reader does not file them as gaps:

* **An empty body is a smell, not a violation** (@aguynamedryan, 2026-08-31).
  ``seeds jot`` creates a title-only seed by design and 31 of this repo's 314
  seeds have none, so as a violation it would fail on 10% of the corpus and on
  the output of the primary capture verb.
* **Non-canonical bytes are not checked here.** §2 fixes the exact byte layout
  and :func:`seeds.seedfile.render_seed_file` can produce it for comparison,
  but the reader deliberately normalizes leading and trailing blank lines and
  §2 calls canonicality "a ``check`` question, not a parse question" without
  saying which tier. It belongs to smells: 282 of 314 records differ from
  canonical form by a trailing newline alone, which is the same shape of
  mistake the empty-body ruling just corrected.

The reading is not done here. :mod:`seeds.seedfile` is the single door to a
seed file, and it already fails strictly, naming file, line, field and value.
A second parser in the checker would be a second implementation of the format
that could disagree with the first — which is the exact failure the spec was
frozen to prevent.

**This module is itself code that can be silently wrong**, and it gates the
conversion. It is therefore tested the way a detector is tested: hand-built bad
files with hand-computed findings, and scored over a whole corpus rather than a
sample.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from seeds.seedfile import (
    FILE_SUFFIX,
    SeedFileError,
    SeedRecord,
    expected_parent,
    inverse_relation,
    is_valid_id,
    read_seed_file,
    seed_files_dir,
)

__all__ = [
    "Finding",
    "check_corpus",
    "check_record",
    "check_violations",
    "format_findings",
]


@dataclass(frozen=True)
class Finding:
    """One violation: the file it is in, what is wrong, and how to fix it.

    ``code`` is the stable machine-readable name — the converter and the tests
    match on it, never on ``message``. ``remediation`` is mandatory and is the
    reason this is a dataclass rather than a string: a finding that names a
    problem without naming its fix sends the operator back to reading the file
    by eye, which is what the pre-0.7 divergence report did.
    """

    path: Path
    code: str
    message: str
    remediation: str
    seed_id: str | None = None
    line: int | None = None


# --- Conflict markers --------------------------------------------------------

# The three markers git writes at the start of a line. `|||||||` appears only
# in diff3 style, which several of this repo's hosts have configured, so it is
# matched too.
_CONFLICT_EDGE_RE = re.compile(r"^(?:<{7}|\|{7}|>{7})(?: |$)")

# The separator is matched only in a file that already carries an opening
# marker. On its own `=======` is a setext H1 underline in ordinary markdown,
# and flagging one would be a false positive in a body that never conflicted.
_CONFLICT_MID_RE = re.compile(r"^={7}$")


def _conflict_lines(text: str) -> list[int]:
    """1-based line numbers of every git conflict marker in ``text``."""
    lines = text.split("\n")
    edges = [n for n, line in enumerate(lines, 1) if _CONFLICT_EDGE_RE.match(line)]
    if not edges:
        return []
    mids = [n for n, line in enumerate(lines, 1) if _CONFLICT_MID_RE.match(line)]
    return sorted(edges + mids)


# --- Title plausibility ------------------------------------------------------

# A whole title that is one URL. Anchored at both ends: a title that merely
# *mentions* a link is prose, and prose is not what seeds-wurl produced.
_URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://\S*$")

# The leading forms that make a token a path no matter what follows.
_PATH_PREFIX_RE = re.compile(r"^(?:/|\./|\.\./|~/|[A-Za-z]:[\\/])")

# A trailing file extension, which is what turns a slashed relative token like
# 'src/seeds/cli.py' into a path rather than a phrase like 'seeds/beads'.
_PATH_EXT_RE = re.compile(r"\.[A-Za-z0-9]{1,8}$")


def _title_violation(title: str) -> tuple[str, str] | None:
    """``(code, what)`` when ``title`` is not plausibly a title, else ``None``.

    Deliberately conservative: a title containing any whitespace is prose and
    is never flagged. ``seeds-wurl`` replaced whole titles with a single path
    token, and a checker that also guessed at prose would spend its credibility
    on false positives — a detector nobody trusts is a detector nobody runs.
    """
    stripped = title.strip()
    if not stripped:
        return ("title-empty", "empty")
    if any(char.isspace() for char in stripped):
        return None
    if _URL_RE.match(stripped):
        return ("title-is-url", "a URL")
    if _PATH_PREFIX_RE.match(stripped):
        return ("title-is-path", "a filesystem path")
    if "/" in stripped and _PATH_EXT_RE.search(stripped):
        return ("title-is-path", "a filesystem path")
    return None


_TITLE_FIX = (
    "restore the real title; git holds it — "
    "`git log -p {path}` (seeds-wurl replaced 83 titles with paths this way)"
)


# --- Per-record checks -------------------------------------------------------

_TIMESTAMP_FIELDS = ("created_at", "updated_at", "resolved_at", "converted_at")


def check_record(path: Path, record: SeedRecord, *, now: datetime) -> list[Finding]:
    """Violations visible in one record alone — no other file consulted.

    The cross-file rules (a parent that exists, an edge's far end) are in
    :func:`check_corpus`, because they cannot be decided from one file.
    """
    findings: list[Finding] = []

    title = _title_violation(record.title)
    if title is not None:
        code, what = title
        findings.append(
            Finding(
                path=path,
                code=code,
                message=f"title is {what}, not a title: {record.title!r}",
                remediation=_TITLE_FIX.format(path=path),
                seed_id=record.id,
            )
        )

    if record.updated_at < record.created_at:
        findings.append(
            Finding(
                path=path,
                code="updated-before-created",
                message=(
                    f"updated_at {record.updated_at.isoformat()} is before "
                    f"created_at {record.created_at.isoformat()}"
                ),
                remediation=(
                    "a seed cannot be edited before it exists; one of the two "
                    "stamps was written by hand or copied from another seed — "
                    "recover both from git history"
                ),
                seed_id=record.id,
            )
        )

    for field_name in _TIMESTAMP_FIELDS:
        stamp = getattr(record, field_name)
        if stamp is not None and stamp > now:
            findings.append(_future(path, record.id, field_name, stamp, now))
    for edge in record.relationships:
        if edge.created_at > now:
            findings.append(
                _future(
                    path,
                    record.id,
                    f"relationships[{edge.target_id}].created_at",
                    edge.created_at,
                    now,
                )
            )

    wanted = expected_parent(record.id)
    if record.parent != wanted:
        findings.append(
            Finding(
                path=path,
                code="parent-mismatch",
                message=(
                    f"parent is {record.parent!r} but the dotted id says {wanted!r}"
                ),
                remediation=(
                    "the id is authoritative — a dotted id carries its prefix "
                    "as parent, a top-level id carries no parent key at all"
                ),
                seed_id=record.id,
            )
        )

    return findings


def _future(
    path: Path, seed_id: str, field_name: str, stamp: datetime, now: datetime
) -> Finding:
    return Finding(
        path=path,
        code="future-timestamp",
        message=(
            f"{field_name} is in the future: {stamp.isoformat()} "
            f"(now {now.isoformat()})"
        ),
        remediation=(
            "a stamp ahead of the clock means a bad hand edit or a host with a "
            "skewed clock; correct it to the real time from git history"
        ),
        seed_id=seed_id,
    )


# --- Cross-file checks -------------------------------------------------------


def check_corpus(
    entries: Sequence[tuple[Path, SeedRecord]], *, now: datetime | None = None
) -> list[Finding]:
    """Every violation decidable from a set of already-parsed records.

    Takes parsed records rather than a directory so the cross-file rules can be
    tested on hand-built corpora that no reader would accept — a parent cycle,
    for one, cannot exist in a set of files the strict reader will parse (§3
    pins ``parent`` to the dotted id, so every chain is a shrinking prefix).
    The rule is still implemented and still tested, because the spec requires
    it and the walk is what makes "no cycle" true rather than assumed.
    """
    now = now or datetime.now(UTC)
    by_id = {record.id: record for _, record in entries}
    path_of = {record.id: path for path, record in entries}
    findings: list[Finding] = []

    for path, record in entries:
        findings.extend(check_record(path, record, now=now))
        findings.extend(_check_parent(path, record, by_id))
        findings.extend(_check_edges(path, record, by_id, path_of))

    return findings


def _check_parent(
    path: Path, record: SeedRecord, by_id: dict[str, SeedRecord]
) -> list[Finding]:
    """The parent names a file that exists, and no chain closes on itself (§3)."""
    if record.parent is None:
        return []
    if record.parent not in by_id:
        return [
            Finding(
                path=path,
                code="parent-missing",
                message=f"parent {record.parent!r} has no file",
                remediation=(
                    f"restore {record.parent}{FILE_SUFFIX} from git, or re-home "
                    f"this seed under a parent that exists (which renames it, "
                    f"because the id carries the hierarchy)"
                ),
                seed_id=record.id,
            )
        ]
    seen = {record.id}
    cursor: str | None = record.parent
    while cursor is not None:
        if cursor in seen:
            return [
                Finding(
                    path=path,
                    code="parent-cycle",
                    message=(
                        f"parent chain forms a cycle: "
                        f"{' -> '.join(_chain(record, by_id))}"
                    ),
                    remediation=(
                        "a hierarchy with a cycle has no root and cannot be "
                        "walked; break it by re-homing one seed in the loop"
                    ),
                    seed_id=record.id,
                )
            ]
        seen.add(cursor)
        parent = by_id.get(cursor)
        cursor = parent.parent if parent is not None else None
    return []


def _chain(record: SeedRecord, by_id: dict[str, SeedRecord]) -> list[str]:
    """The parent walk from ``record``, stopping the moment it repeats."""
    out = [record.id]
    seen = {record.id}
    cursor: str | None = record.parent
    while cursor is not None:
        out.append(cursor)
        if cursor in seen:
            break
        seen.add(cursor)
        parent = by_id.get(cursor)
        cursor = parent.parent if parent is not None else None
    return out


def _check_edges(
    path: Path,
    record: SeedRecord,
    by_id: dict[str, SeedRecord],
    path_of: dict[str, Path],
) -> list[Finding]:
    """Every edge names a real file and is written at both ends (§5.1, §5.2).

    The both-ends rule is the trade the format makes: SQLite mitigated a
    half-written pair with a transaction, files mitigate it with detection. So
    the detection has to actually exist, and it has to compare ``created_at``
    too — the edge's own stamp is the same value in both files, and that is
    what pairs the two ends of *one* edge rather than two edges that happen to
    point at each other.
    """
    findings: list[Finding] = []
    for edge in record.relationships:
        target = by_id.get(edge.target_id)
        if target is None:
            findings.append(
                Finding(
                    path=path,
                    code="relationship-target-missing",
                    message=(
                        f"relationship names {edge.target_id!r}, which has no file"
                    ),
                    remediation=(
                        f"restore {edge.target_id}{FILE_SUFFIX} from git, or "
                        f"drop this edge from both ends"
                    ),
                    seed_id=record.id,
                )
            )
            continue
        wanted = inverse_relation(edge.rel_type)
        back = [
            other
            for other in target.relationships
            if other.target_id == record.id and other.rel_type == wanted
        ]
        if not back:
            findings.append(
                Finding(
                    path=path,
                    code="one-sided-edge",
                    message=(
                        f"{edge.rel_type.value} edge to {edge.target_id} has no "
                        f"counterpart: {path_of[edge.target_id]} holds no "
                        f"{wanted.value} edge back to {record.id}"
                    ),
                    remediation=(
                        f"every edge is stored at both ends — add the "
                        f"{wanted.value} edge to {edge.target_id} with the same "
                        f"created_at, or remove this one"
                    ),
                    seed_id=record.id,
                )
            )
            continue
        if not any(other.created_at == edge.created_at for other in back):
            findings.append(
                Finding(
                    path=path,
                    code="edge-timestamp-mismatch",
                    message=(
                        f"{edge.rel_type.value} edge to {edge.target_id} is "
                        f"stamped {edge.created_at.isoformat()}, but the "
                        f"counterpart is stamped "
                        f"{', '.join(o.created_at.isoformat() for o in back)}"
                    ),
                    remediation=(
                        "an edge's created_at is the edge's own, and is the "
                        "same value at both ends; make the two agree"
                    ),
                    seed_id=record.id,
                )
            )
    return findings


# --- The whole store ---------------------------------------------------------

# A strict-read failure carries a code from seedfile for the cases the spec
# calls out by name; anything else lands under this one.
_PARSE_FIX = {
    "status-unknown": (
        "status is a closed set and stays closed — it drives list, ready, "
        "blocked and every lifecycle transition, so an arbitrary value breaks "
        "them silently (§3, seeds-ebg1). Set one of captured, exploring, "
        "deferred, resolved, abandoned"
    ),
    "title-empty": "give the seed a one-line, non-empty, plain-text title (§3)",
    "parent-mismatch": (
        "the id is authoritative — a dotted id carries its prefix as parent, a "
        "top-level id carries no parent key at all (§3)"
    ),
    "supersede-position": (
        "move the marker directly under the heading it retires; there is no "
        "floating supersession, because a floating marker has no determinable "
        "scope (§6.1). If it retires nothing, it is a correction — make the "
        "fix in place instead"
    ),
    "supersede-malformed": (
        "the grammar is '> [!SUPERSEDED] YYYY-MM-DD — reason', with a real "
        "date and a space-em-dash-space before the reason (§6.1)"
    ),
    "supersede-no-reason": (
        "the reason clause is mandatory: a conclusion without its reason "
        "invites re-litigation, and a heading saying 'Python' invites an agent "
        "to propose Go next month (§6.1)"
    ),
    "parse-error": (
        "reads are strict by design (§7) — the message names the file, the "
        "line, the field and the value; fix that field"
    ),
}


def check_violations(seeds_dir: Path, *, now: datetime | None = None) -> list[Finding]:
    """Every violation in the seed-file store under ``seeds_dir``.

    Scores the **whole** store, not a sample: the point of a checker that gates
    a conversion is that exiting clean means the deliverable is clean.
    """
    now = now or datetime.now(UTC)
    files_dir = seed_files_dir(seeds_dir)
    if not files_dir.is_dir():
        return [
            Finding(
                path=files_dir,
                code="store-missing",
                message="no seed-file store here",
                remediation=(
                    "the store is the directory listing itself (§1); create it "
                    "with 'seeds init', or convert a pre-0.7 store into it"
                ),
            )
        ]

    findings: list[Finding] = []
    entries: list[tuple[Path, SeedRecord]] = []
    for path in sorted(files_dir.glob(f"*{FILE_SUFFIX}")):
        stem = path.name[: -len(FILE_SUFFIX)]
        if not is_valid_id(stem):
            findings.append(
                Finding(
                    path=path,
                    code="bad-filename",
                    message=f"filename stem {stem!r} is not a valid seed id",
                    remediation=(
                        "the filename stem is the id verbatim, dots included "
                        "(§1.1); rename the file to its id, or move the file "
                        "out of the store"
                    ),
                )
            )
            continue
        record = _read_one(path, findings)
        if record is not None:
            entries.append((path, record))

    findings.extend(check_corpus(entries, now=now))
    return sorted(findings, key=lambda f: (str(f.path), f.code, f.message))


def _read_one(path: Path, findings: list[Finding]) -> SeedRecord | None:
    """Read one file, recording a finding instead of raising when it will not."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        findings.append(
            Finding(
                path=path,
                code="unreadable",
                message=f"cannot read the file ({exc})",
                remediation="check the file's permissions and that it is a file",
            )
        )
        return None

    conflicts = _conflict_lines(text)
    if conflicts:
        findings.append(
            Finding(
                path=path,
                code="conflict-markers",
                message=(
                    f"git conflict markers left in the file, on "
                    f"{len(conflicts)} line(s): "
                    f"{', '.join(str(n) for n in conflicts)}"
                ),
                remediation=(
                    "finish the merge: keep the text that belongs and delete "
                    "the <<<<<<< / ======= / >>>>>>> lines"
                ),
                line=conflicts[0],
            )
        )

    try:
        return read_seed_file(path)
    except SeedFileError as exc:
        # A conflicted file almost never parses, and the parse error is a
        # consequence of the conflict rather than a second thing to fix.
        if not conflicts:
            code = exc.code
            findings.append(
                Finding(
                    path=path,
                    code=code,
                    message=str(exc),
                    remediation=_PARSE_FIX.get(code, _PARSE_FIX["parse-error"]),
                )
            )
        return None


# --- Reporting ---------------------------------------------------------------


def format_findings(findings: Iterable[Finding]) -> str:
    """Render findings for a terminal, grouped by file, with every fix shown."""
    grouped: dict[Path, list[Finding]] = {}
    for finding in findings:
        grouped.setdefault(finding.path, []).append(finding)
    out: list[str] = []
    for path, group in grouped.items():
        out.append(str(path))
        for finding in group:
            out.append(f"  ✗ {finding.code}: {finding.message}")
            out.append(f"    → {finding.remediation}")
        out.append("")
    return "\n".join(out)
