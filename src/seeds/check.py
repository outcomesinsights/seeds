"""``seeds check`` — violations, smells, and the comparison against git.

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

Three tiers live here now.

* **Violations** (the default) exit non-zero and block a commit. Each one is
  either a file the reader would refuse, or a value that parses fine and is not
  plausible.
* **Smells** (``seeds check --smells``) report and never fail: an empty body, a
  long unsuperseded body, a duplicated body, a resolution on a seed that never
  reached a terminal status, a file whose bytes are not the canonical ones, and
  a repo-wide tool configured without excluding the store. The tier exists
  because some
  things worth noticing cannot support being a gate — a long body with no
  ``[!SUPERSEDED]`` marker is a *candidate for attention*, never an error, and
  naming the tier keeps discipline-shaped checks from being promoted into gates
  they cannot carry. It is also all that survives of the designed-but-never-
  built ``tend`` verb (@aguynamedryan, 2026-08-31: *"let's remove suggest/tend
  for now … tend never really got used"*): with supersession marked at write
  time by the agent that learned it, nothing editorial is left, only noticing.
  **There is no ``tend`` verb and there is not to be one.**
* **Against git** (``seeds check --against-git``) compares every field of every
  seed with its value at the previous commit and flags one field rewritten
  across a large fraction of the corpus. That is the ``seeds-wurl`` shape
  exactly, and it *does* gate: a commit rewriting 87 files has no cheap human
  review, and demanding confirmation for it subsumes gating ``D`` and ``R`` in
  ``git diff --name-status`` — a deleted seed counts here as changing every
  field, so ``rm <seed-file>`` at scale trips the same rule. Detection at commit
  is not immutability, and that is accepted: it bounds the damage to one
  working session rather than five weeks.

Two things deliberately absent, so a later reader does not file them as gaps:

* **An empty body is a smell, not a violation** (@aguynamedryan, 2026-08-31).
  ``seeds jot`` creates a title-only seed by design and 31 of this repo's 314
  seeds have none, so as a violation it would fail on 10% of the corpus and on
  the output of the primary capture verb.
* **Non-canonical bytes are a smell, not a violation.** §2 fixes the exact byte
  layout and :func:`seeds.seedfile.render_seed_file` produces it for
  comparison, but the reader deliberately normalizes leading and trailing blank
  lines, so a file can be readable and non-canonical at once. Gating on it
  would have failed on 282 of the 314 pre-conversion records, which differed by
  a trailing newline alone — the same shape of mistake the empty-body ruling
  corrected. The converter normalizes, so the standing count on this repo's
  309 converted files is zero (measured 2026-09-01), and that zero is the
  point: it makes the smell a *positive assertion* that no tool has rewritten a
  seed file's layout, whatever the tool was and whether or not anyone thought
  to exclude it. A rewrite confined to the body's own text is outside its
  reach, and belongs to ``--against-git``.

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
import tomllib
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from seeds.githistory import (
    GitUnavailable,
    commit_counts,
    read_blobs,
    repo_root,
    rev_exists,
    tree_files,
)
from seeds.models import SeedStatus
from seeds.seedfile import (
    FILE_SUFFIX,
    SeedFileError,
    SeedRecord,
    expected_parent,
    inverse_relation,
    is_valid_id,
    parse_seed_file,
    read_seed_file,
    render_seed_file,
    seed_files_dir,
    superseded_scopes,
)

__all__ = [
    "Finding",
    "GitComparison",
    "GitUnavailable",
    "check_against_git",
    "check_corpus",
    "check_record",
    "check_smells",
    "check_violations",
    "format_findings",
]


@dataclass(frozen=True)
class Finding:
    """One finding: the file it is in, what is wrong, and how to fix it.

    ``code`` is the stable machine-readable name — the converter and the tests
    match on it, never on ``message``. ``remediation`` is mandatory and is the
    reason this is a dataclass rather than a string: a finding that names a
    problem without naming its fix sends the operator back to reading the file
    by eye, which is what the pre-0.7 divergence report did.

    All three tiers use this one type. A smell is not a weaker kind of object,
    it is the same object reported without an exit code, and giving it its own
    class would have meant a second formatter that could drift from this one.
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
                    "with 'seeds init' in a new project, or run 'seeds convert' "
                    "in one that still has .seeds/seeds.jsonl"
                ),
            )
        ]

    entries, findings = _load_store(files_dir)
    findings.extend(check_corpus(entries, now=now))
    return sorted(findings, key=lambda f: (str(f.path), f.code, f.message))


def _load_store(files_dir: Path) -> tuple[list[tuple[Path, SeedRecord]], list[Finding]]:
    """Read every seed file under ``files_dir``: the records, and what refused.

    Shared by all three tiers so there is exactly one walk of the store and one
    call into the reader. The smells tier discards the second half of the pair:
    a file that will not parse is the violations tier's business, and reporting
    it twice under two headings would make the same corpus look worse than it
    is.
    """
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
    return entries, findings


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


# --- The smells tier ---------------------------------------------------------

# A body this many bytes or more counts as long. Measured, not guessed: over
# this repo's 308 converted seeds the median body is 1197 bytes and the 75th
# percentile is 2621, so 2000 selects roughly the top third (104 of 308). It is
# deliberately permissive because it is only ever half of an AND — on its own a
# long body is a well-deliberated seed, which is the point of the tool.
LONG_BODY_BYTES = 2000

# …and this many commits or more counts as a long history. A body that has
# survived five commits has been edited across several sessions, which is when
# a position gets moved past without anyone marking it. Below that, "nobody has
# superseded anything yet" is simply true.
MANY_COMMITS = 5

# The two statuses §3 calls terminal, and the only two a `resolution` is
# meaningful alongside.
_TERMINAL_STATUSES = (SeedStatus.RESOLVED, SeedStatus.ABANDONED)


def check_smells(seeds_dir: Path, *, now: datetime | None = None) -> list[Finding]:
    """Everything worth noticing in the store that must never fail a build.

    Nothing here is an error, and the caller must not let any of it reach an
    exit code. The empty-body smell alone stands at ~25 entries on this repo's
    own corpus — most of them legitimately-open ``question`` seeds where the
    title *is* the question — and a tier that fails on 8% of a healthy corpus
    trains everyone to pass ``--no-verify``, which is how a real violation
    later goes through unread.

    Two of the six rules are expected to score **zero** on a healthy store, and
    that is what makes them worth running: ``non-canonical-bytes`` and
    ``tool-config-includes-store`` are positive assertions that nothing has
    reached into the store, not observations about how it was written. Both
    stood at zero on this repo's 309 converted files when they landed
    (2026-09-01), so a single line from either is a real event.

    ``now`` is accepted and unused, so the three tiers share one signature and
    a caller can pass a pinned clock without special-casing this one.
    """
    del now
    files_dir = seed_files_dir(seeds_dir)
    if not files_dir.is_dir():
        return []
    entries, _ = _load_store(files_dir)

    findings: list[Finding] = []
    findings.extend(_empty_bodies(entries))
    findings.extend(_unsuperseded_long_bodies(seeds_dir, files_dir, entries))
    findings.extend(_duplicate_bodies(entries))
    findings.extend(_resolutions_without_a_terminal_status(entries))
    findings.extend(_non_canonical_files(entries))
    findings.extend(_unexcluded_tool_configs(seeds_dir))
    return sorted(findings, key=lambda f: (str(f.path), f.code, f.message))


def _empty_bodies(entries: Sequence[tuple[Path, SeedRecord]]) -> list[Finding]:
    """A seed with no deliberation under its title (§6.4).

    Moved out of the violations tier by ruling (@aguynamedryan, 2026-08-31):
    ``seeds jot`` creates a title-only seed by design — ``Seed(id=…,
    title=thought)`` with no body at all — so as a violation this would fail on
    the output of the primary capture verb.
    """
    findings = []
    for path, record in entries:
        if record.body.strip():
            continue
        findings.append(
            Finding(
                path=path,
                code="empty-body",
                message="the seed has a title and no body",
                remediation=(
                    "often correct — 'seeds jot' makes title-only seeds by "
                    "design, and for a question-type seed the title IS the "
                    "question. Worth a look only if the thinking happened "
                    "somewhere else and never landed here"
                ),
                seed_id=record.id,
            )
        )
    return findings


def _unsuperseded_long_bodies(
    seeds_dir: Path, files_dir: Path, entries: Sequence[tuple[Path, SeedRecord]]
) -> list[Finding]:
    """A long body, edited across many commits, carrying no supersede marker.

    The clearest thing that could not survive being a gate. A seed can be long
    and much-edited and still hold no retired position — plenty of deliberation
    only ever accumulates — so this is a candidate for attention and nothing
    more.

    The commit count is the half that makes it worth reading. Length alone
    selects a third of this corpus; length *plus* a history of separate edits
    is the shape where a claim was replaced and the replacement was written as
    if the old one had never been made.

    Silent when git cannot answer: with no history there is no second half of
    the AND, and inventing one from length alone would report the third of the
    corpus this deliberately refuses to report.
    """
    try:
        root = repo_root(seeds_dir)
        counts = commit_counts(root, _relpath(root, files_dir))
    except (GitUnavailable, ValueError):
        return []
    if not counts:
        return []

    findings = []
    for path, record in entries:
        size = len(record.body.encode("utf-8"))
        if size < LONG_BODY_BYTES:
            continue
        try:
            commits = counts.get(_relpath(root, path), 0)
        except ValueError:  # pragma: no cover - path is under files_dir
            continue
        if commits < MANY_COMMITS:
            continue
        if superseded_scopes(record.body, path):
            continue
        findings.append(
            Finding(
                path=path,
                code="unsuperseded-long-body",
                message=(
                    f"{size} bytes of body across {commits} commits, with no "
                    f"[!SUPERSEDED] marker anywhere in it"
                ),
                remediation=(
                    "read it for a position that was moved past and never "
                    "marked; if you find one, mark it in place under its "
                    "heading with '> [!SUPERSEDED] YYYY-MM-DD — reason' (§6.1). "
                    "A seed that genuinely only accumulated is fine as it is"
                ),
                seed_id=record.id,
            )
        )
    return findings


def _duplicate_bodies(entries: Sequence[tuple[Path, SeedRecord]]) -> list[Finding]:
    """Two seeds holding byte-identical bodies.

    Either one seed was copied over another, or two seeds are the same
    deliberation recorded twice and one should point at the other. Empty bodies
    are excluded: they are all identical to each other by definition, and
    ``_empty_bodies`` already reports them one by one.
    """
    by_body: dict[str, list[tuple[Path, SeedRecord]]] = defaultdict(list)
    for path, record in entries:
        if record.body.strip():
            by_body[record.body].append((path, record))

    findings = []
    for group in by_body.values():
        if len(group) < 2:
            continue
        ids = [record.id for _, record in group]
        for path, record in group:
            others = [other for other in ids if other != record.id]
            findings.append(
                Finding(
                    path=path,
                    code="duplicate-body",
                    message=(
                        f"body is byte-identical to {len(others)} other seed(s): "
                        f"{', '.join(others)}"
                    ),
                    remediation=(
                        "if one was copied over the other, git holds the "
                        "original — `git log -p " + str(path) + "`. If they are "
                        "genuinely the same deliberation, keep one and link the "
                        "rest to it"
                    ),
                    seed_id=record.id,
                )
            )
    return findings


def _resolutions_without_a_terminal_status(
    entries: Sequence[tuple[Path, SeedRecord]],
) -> list[Finding]:
    """A ``resolution`` on a seed whose status is not terminal (§3).

    §3 states the rule and states the tier in the same breath: "only meaningful
    alongside a terminal ``status``, but carrying one on a non-terminal seed is
    a smell rather than a violation — it is usually a seed someone reopened".
    Reopening is the ordinary lifecycle of a seed and the resolution text is
    the record of what the *last* conclusion was, so deleting it on reopen
    would throw away the deliberation this tool exists to keep. Nothing here
    asks for it to be deleted; the finding only asks whether the status is the
    stale half of the pair.
    """
    findings = []
    for path, record in entries:
        if not record.resolution:
            continue
        if record.status in _TERMINAL_STATUSES:
            continue
        findings.append(
            Finding(
                path=path,
                code="resolution-on-non-terminal",
                message=(
                    f"status is {record.status.value} but the seed carries a "
                    f"resolution: {_clip(record.resolution)}"
                ),
                remediation=(
                    "usually a seed that was reopened, and then the resolution "
                    "is the previous conclusion and is worth keeping (§3). "
                    "Worth a look only if it is the status that is stale — "
                    "'seeds resolve' restamps both together"
                ),
                seed_id=record.id,
            )
        )
    return findings


def _non_canonical_files(
    entries: Sequence[tuple[Path, SeedRecord]],
) -> list[Finding]:
    """A file whose bytes are not what :func:`render_seed_file` would write.

    The **positive assertion** half of the store's defence against repo-wide
    tooling. ``tool-config-includes-store`` covers the tools somebody thought
    to name; this one needs no list, because a file that has been rewritten no
    longer matches the render of itself. It is also what ``seeds convert``'s
    byte-idempotence rests on: a file off canonical form makes the next
    conversion report a diff nobody made.

    **What it does and does not see, measured rather than assumed.** The
    comparison is the file against the canonical render *of what the file now
    says*, so what it catches is every rewrite of the file's **serialization**:
    a second trailing newline, inserted or removed blank lines around the body,
    reordered frontmatter keys, a re-encoded scalar. It does **not** catch a
    rewrite of the body's own text while the layout stays canonical — ruff 0.16
    reformatting a Python block inside a markdown body is exactly that shape
    (``seeds-dv6r``, the incident that prompted this), and so is trimming
    trailing whitespace off a body line. That case is ``--against-git``'s,
    which compares the body field itself. Both halves are pinned by tests; do
    not read this rule as covering more than it does.

    It cannot be a violation. The reader deliberately normalizes leading and
    trailing blank lines, so a readable file can be non-canonical — 282 of the
    314 pre-conversion records differed by a trailing newline alone, and gating
    on that would have failed on 90% of a healthy corpus. The bytes the reader
    *does* refuse — a BOM, CRLF — never arrive here at all; they are
    violations, and reporting them twice would make the corpus look worse than
    it is.

    A record the writer would refuse is skipped for the same reason: the
    violations tier already names it, and ``render_seed_file`` validates before
    it renders, so there are no canonical bytes to compare against.
    """
    findings = []
    for path, record in entries:
        try:
            canonical = render_seed_file(record).encode("utf-8")
        except SeedFileError:
            continue
        try:
            raw = path.read_bytes()
        except OSError:  # pragma: no cover - _load_store already read it
            continue
        if raw == canonical:
            continue
        findings.append(
            Finding(
                path=path,
                code="non-canonical-bytes",
                message=(
                    f"the file's bytes are not the canonical form "
                    f"({len(raw)} bytes on disk, {len(canonical)} canonical): "
                    f"{_first_difference(raw, canonical)}"
                ),
                remediation=(
                    "something rewrote the file — a formatter, a linter's "
                    "--fix, or a hand edit. Check `git diff` first: if the "
                    "content is right and only the layout moved, any 'seeds' "
                    "write of this seed restores the canonical bytes (§2). If "
                    "a repo-wide tool did it, exclude '.seeds/' from that tool "
                    "as well — ruff 0.16 reached in this way (seeds-dv6r)"
                ),
                seed_id=record.id,
            )
        )
    return findings


def _first_difference(raw: bytes, canonical: bytes) -> str:
    """Name the first line where the two forms part company.

    A byte count alone sends the reader back to diffing by eye, which is what
    every remediation in this module exists to avoid.
    """
    got = raw.decode("utf-8", errors="replace").split("\n")
    want = canonical.decode("utf-8", errors="replace").split("\n")
    for number, (a, b) in enumerate(zip(got, want, strict=False), 1):
        if a != b:
            return f"line {number} is {_clip(a)!r}, canonical is {_clip(b)!r}"
    if len(got) > len(want):
        return f"{len(got) - len(want)} trailing line(s) the canonical form has not"
    if len(want) > len(got):
        return f"{len(want) - len(got)} line(s) short of the canonical form"
    return "the two forms differ in bytes that are not line content"


def _clip(text: str, limit: int = 60) -> str:
    """``text`` on one line, short enough to sit in a terminal report."""
    flat = text.replace("\n", "\\n")
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


# --- Repo-wide tools that must not reach into the store ----------------------

# The token a config has to name for the store to be excluded. Matching on the
# directory name rather than a parsed exclude list is deliberate: five config
# dialects would mean five more parsers in a module whose whole argument is
# that a second implementation of a format can disagree with the first. This
# layer names the tools we can think of; `non-canonical-bytes` is the layer
# that catches the tool nobody thought of, which is why the looseness here is
# affordable.
_STORE_TOKEN = ".seeds"


@dataclass(frozen=True)
class _ToolConfig:
    """One repo-wide tool, where its config lives, and how it is told to stop.

    ``files`` and ``ignores`` are globs relative to the project root. The split
    matters because several of these tools carry no exclusion in their config
    at all — prettier and markdownlint are told what to skip in a companion
    ignore file — so a config present with no ignore file anywhere is exactly
    the unexcluded case.
    """

    tool: str
    files: tuple[str, ...]
    ignores: tuple[str, ...]
    knob: str
    pyproject_table: str | None = None


# Only tools that walk a whole repo AND can read or rewrite markdown are here.
# mypy, pytest and hatch are configured in this repo's pyproject too and are
# deliberately absent: they are pointed at a path list, they never see
# .seeds/, and reporting them would spend the tier's credibility on findings
# with no fix.
_TOOL_CONFIGS: tuple[_ToolConfig, ...] = (
    _ToolConfig(
        tool="ruff",
        files=("ruff.toml", ".ruff.toml"),
        ignores=(),
        knob='extend-exclude = [".seeds/"] under [tool.ruff]',
        pyproject_table="ruff",
    ),
    _ToolConfig(
        tool="prettier",
        files=(".prettierrc", ".prettierrc.*", "prettier.config.*"),
        ignores=(".prettierignore",),
        knob="a '.seeds/' line in .prettierignore",
    ),
    _ToolConfig(
        tool="markdownlint",
        files=(".markdownlint.*", ".markdownlintrc", ".markdownlint-cli2.*"),
        ignores=(".markdownlintignore",),
        knob="a '.seeds/' line in .markdownlintignore, or an 'ignores' entry",
    ),
    _ToolConfig(
        tool="cspell",
        files=("cspell.json", "cspell.jsonc", ".cspell.json", "cspell.config.*"),
        ignores=(".cspellignore",),
        knob="'.seeds/**' in ignorePaths",
    ),
    _ToolConfig(
        tool="codespell",
        files=(".codespellrc",),
        ignores=(),
        knob='skip = ".seeds"',
        pyproject_table="codespell",
    ),
    _ToolConfig(
        tool="EditorConfig",
        files=(".editorconfig",),
        ignores=(),
        knob=(
            "a [.seeds/**] section turning off trim_trailing_whitespace and "
            "anything else that rewrites on save"
        ),
    ),
)


def _unexcluded_tool_configs(seeds_dir: Path) -> list[Finding]:
    """A repo-wide tool configured here that has not been told to skip the store.

    Asked for by @aguynamedryan on 2026-09-01, and it is preemptive on purpose:
    the store looks like 309 markdown files to every formatter, linter and
    spell-checker in the repo, and the one that found it did so within minutes.
    ruff 0.16 formats Python code blocks inside markdown, so the moment the
    converted tree landed its file count went 65 -> 385 and it offered to
    reformat a seed body (``seeds-dv6r``). With ``--fix`` instead of
    ``--check`` that is somebody's deliberation edited by a formatter, silently.

    A smell rather than a gate for the same reason the rest of this tier is:
    the answer to it lives in another tool's config file, and a check that
    fails a commit over a file it does not own — one that a fresh clone or a
    new dev-tool can introduce without touching a seed — is a check people
    learn to bypass.
    """
    root = seeds_dir.parent
    findings = []
    for config in _TOOL_CONFIGS:
        present = _config_files(root, config)
        table = _pyproject_table(root, config.pyproject_table)
        if not present and table is None:
            continue
        if table is not None and _STORE_TOKEN in table:
            continue
        if any(_mentions_store(path) for path in present):
            continue
        if any(_mentions_store(path) for path in _ignore_files(root, config)):
            continue
        where = present[0] if present else root / "pyproject.toml"
        findings.append(
            Finding(
                path=where,
                code="tool-config-includes-store",
                message=(
                    f"{config.tool} is configured for this repo and nothing "
                    f"excludes {_STORE_TOKEN}/ from it"
                ),
                remediation=(
                    f"add {config.knob}, with a comment saying why. The store "
                    f"is DATA, not source: ruff 0.16 offered to reformat a seed "
                    f"body within minutes of this repo's conversion, and a "
                    f"reformatted body also breaks the byte-idempotence "
                    f"'seeds convert' rests on (seeds-dv6r)"
                ),
            )
        )
    return findings


def _config_files(root: Path, config: _ToolConfig) -> list[Path]:
    """Every config file of ``config``'s tool that this repo actually has."""
    found: list[Path] = []
    for pattern in config.files:
        found.extend(path for path in sorted(root.glob(pattern)) if path.is_file())
    return found


def _ignore_files(root: Path, config: _ToolConfig) -> list[Path]:
    return [root / name for name in config.ignores if (root / name).is_file()]


def _pyproject_table(root: Path, name: str | None) -> str | None:
    """``[tool.<name>]`` from pyproject.toml, flattened, or ``None`` if absent.

    An unparseable pyproject is not this module's business — it is a Python
    packaging error the packaging tools will report far more usefully — so it
    reads as "no table" rather than a finding about the seed store.
    """
    if name is None:
        return None
    path = root / "pyproject.toml"
    if not path.is_file():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    tools = data.get("tool")
    if not isinstance(tools, dict) or name not in tools:
        return None
    return str(tools[name])


def _mentions_store(path: Path) -> bool:
    """Whether ``path``'s text names the seed store at all."""
    try:
        return _STORE_TOKEN in path.read_text(encoding="utf-8", errors="replace")
    except OSError:  # pragma: no cover - the caller checked is_file()
        return False


def _relpath(root: Path, path: Path) -> str:
    """``path`` as a repo-relative POSIX path, which is how git names things."""
    return path.resolve().relative_to(root).as_posix()


# --- The against-git tier ----------------------------------------------------

# A field has to change on at least this fraction of the corpus before the
# shape counts as a mass rewrite. seeds-wurl was 83 of 306 titles = 27.1%, so
# 20% clears the real incident with margin while leaving ordinary bulk work
# alone: retyping a dozen seeds in a 300-seed store is 4%.
MASS_CHANGE_FRACTION = 0.20

# …and at least this many seeds in absolute terms, so a three-seed store cannot
# trip the rule by having one seed edited.
MASS_CHANGE_MINIMUM = 10

# The fields compared, as (attribute, the name the format calls it). ``id`` is
# absent because it is the join key, not a value: a seed whose id changed is a
# different file, and shows up here as a deletion plus an addition.
_COMPARED_FIELDS: tuple[tuple[str, str], ...] = (
    ("title", "title"),
    ("status", "status"),
    ("seed_type", "type"),
    ("created_at", "created_at"),
    ("updated_at", "updated_at"),
    ("parent", "parent"),
    ("resolved_at", "resolved_at"),
    ("resolution", "resolution"),
    ("tags", "tags"),
    ("relationships", "relationships"),
    ("converted_at", "converted_at"),
    ("body", "body"),
)


@dataclass
class GitComparison:
    """What ``--against-git`` compared, and what it found.

    The two revisions are reported even when nothing is found, because "no
    findings" is only reassuring once you know what was actually compared. A
    checker that quietly compared a commit with itself and printed a clean line
    is the failure mode the whole tier exists to prevent.
    """

    before: str
    after: str
    corpus: int
    findings: list[Finding] = field(default_factory=list)


def check_against_git(seeds_dir: Path) -> GitComparison:
    """Flag any one field rewritten across a large fraction of the corpus.

    Compares the working store against ``HEAD`` — which is what a pre-commit
    hook needs, since there "the previous commit" is ``HEAD`` and the state
    being committed is on disk. When the store is identical to ``HEAD`` there
    is nothing uncommitted to gate, so it falls back to ``HEAD~1`` against
    ``HEAD`` and audits the commit that just landed. seeds-wurl needed exactly
    that second reading: the rewrite was committed and then survived three days
    and three further commits, so a tool that only ever looked at uncommitted
    work would have had nothing to say for any of them.

    Raises :class:`GitUnavailable` when there is no git to ask. An unborn
    ``HEAD`` is not that case — it means the before-state is empty, nothing can
    have been rewritten, and the answer is a clean comparison against nothing.
    """
    files_dir = seed_files_dir(seeds_dir)
    root = repo_root(seeds_dir)
    reldir = _relpath(root, files_dir)

    after = _state_on_disk(files_dir)
    if not rev_exists(root, "HEAD"):
        return _compare(reldir, {}, after, "the empty tree", "the working tree")

    before = _state_at_rev(root, "HEAD", reldir)
    if before == after and rev_exists(root, "HEAD~1"):
        return _compare(
            reldir,
            _state_at_rev(root, "HEAD~1", reldir),
            _state_at_rev(root, "HEAD", reldir),
            "HEAD~1",
            "HEAD",
        )
    return _compare(reldir, before, after, "HEAD", "the working tree")


def _state_on_disk(files_dir: Path) -> dict[str, SeedRecord]:
    """Every seed the store currently holds, keyed by id."""
    if not files_dir.is_dir():
        return {}
    entries, _ = _load_store(files_dir)
    return {record.id: record for _, record in entries}


def _state_at_rev(root: Path, rev: str, reldir: str) -> dict[str, SeedRecord]:
    """Every seed the store held at ``rev``, keyed by id.

    A file that will not parse at ``rev`` is skipped rather than reported: the
    violations tier owns whether the store is well-formed *now*, and history is
    not editable, so a finding about it would name no fix.
    """
    blobs = tree_files(root, rev, reldir)
    texts = read_blobs(root, list(blobs.values()))
    out: dict[str, SeedRecord] = {}
    for relpath, sha in blobs.items():
        path = root / relpath
        if not path.name.endswith(FILE_SUFFIX):
            continue
        if not is_valid_id(path.name[: -len(FILE_SUFFIX)]):
            continue
        text = texts.get(sha)
        if text is None:
            continue
        try:
            record = parse_seed_file(path, text)
        except SeedFileError:
            continue
        out[record.id] = record
    return out


def _field_value(record: SeedRecord, attr: str) -> object:
    """One field, normalized so that only a real change reads as a change.

    ``tags`` and ``relationships`` are compared order-insensitively. A reordered
    block sequence is the same set of tags and the same set of edges, and a
    detector that counted a reorder as a rewrite would report a mass change for
    a no-op — the one thing this tier must never do, because it gates a commit.
    """
    value = getattr(record, attr)
    if attr == "tags":
        return sorted(value)
    if attr == "relationships":
        return sorted(
            (edge.target_id, edge.rel_type.value, edge.created_at.isoformat())
            for edge in value
        )
    return value


def _compare(
    reldir: str,
    before: dict[str, SeedRecord],
    after: dict[str, SeedRecord],
    before_label: str,
    after_label: str,
) -> GitComparison:
    """Score one field at a time across the whole before-corpus."""
    comparison = GitComparison(
        before=before_label, after=after_label, corpus=len(before)
    )
    if not before:
        return comparison

    deleted = sorted(seed_id for seed_id in before if seed_id not in after)
    changed: dict[str, list[str]] = defaultdict(list)
    for seed_id, record in before.items():
        current = after.get(seed_id)
        if current is None:
            continue
        for attr, _ in _COMPARED_FIELDS:
            if _field_value(record, attr) != _field_value(current, attr):
                changed[attr].append(seed_id)

    total = len(before)
    for attr, label in _COMPARED_FIELDS:
        rewritten = sorted(changed[attr])
        # A deleted seed lost every field, so it counts against every one of
        # them. That is what makes this rule subsume gating D and R: there is
        # no delete verb, and `rm` over a large slice of the store trips the
        # same threshold as a mass rewrite does.
        affected = len(rewritten) + len(deleted)
        if affected < MASS_CHANGE_MINIMUM:
            continue
        if affected / total < MASS_CHANGE_FRACTION:
            continue
        comparison.findings.append(
            _mass_finding(
                reldir, label, rewritten, deleted, total, before_label, after_label
            )
        )
    return comparison


def _mass_finding(
    reldir: str,
    label: str,
    rewritten: Sequence[str],
    deleted: Sequence[str],
    total: int,
    before_label: str,
    after_label: str,
) -> Finding:
    affected = len(rewritten) + len(deleted)
    percent = 100.0 * affected / total
    detail = f"{len(rewritten)} rewritten"
    if deleted:
        detail += f", {len(deleted)} deleted"
    sample = ", ".join(list(rewritten)[:5] or list(deleted)[:5])
    if affected > 5:
        sample += ", …"
    return Finding(
        path=Path(reldir),
        code="mass-field-rewrite",
        message=(
            f"{label} differs on {affected} of {total} seeds ({percent:.0f}% of "
            f"the corpus, {detail}) between {before_label} and {after_label}: "
            f"{sample}"
        ),
        remediation=(
            f"a change this wide has no cheap human review, so it needs an "
            f"explicit decision rather than a glance. If it was not intended, "
            f"`git diff {before_label} -- {reldir}` shows it and "
            f"`git checkout {before_label} -- {reldir}` puts it back — this is "
            f"the shape that replaced 83 of 306 titles with a scratchpad path "
            f"and went unread for three days (seeds-wurl)"
        ),
    )


# --- Reporting ---------------------------------------------------------------


def format_findings(findings: Iterable[Finding], *, marker: str = "✗") -> str:
    """Render findings for a terminal, grouped by file, with every fix shown.

    ``marker`` is what separates a violation from a smell on screen. The smells
    tier passes a warning sign, so a reader scanning the output cannot mistake
    a line that failed the run for one that did not.
    """
    grouped: dict[Path, list[Finding]] = {}
    for finding in findings:
        grouped.setdefault(finding.path, []).append(finding)
    out: list[str] = []
    for path, group in grouped.items():
        out.append(str(path))
        for finding in group:
            out.append(f"  {marker} {finding.code}: {finding.message}")
            out.append(f"    → {finding.remediation}")
        out.append("")
    return "\n".join(out)
