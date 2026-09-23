"""``seeds candidates`` — which seeds did recently-closed beads discharge?

The ``resolve-seeds-from-beads`` skill closes the loop from execution back to
deliberation. Its weak point was never the verification — it was *finding
something to verify*. The skill assumed the agent had been present when the
work shipped and could simply recall which seeds it came from, so run cold,
weeks later, it had nowhere to start. This module is the deterministic half it
was missing, extracted per the ratified split in seed seeds-152.5: anything
mechanical inside a skill is a smell, and becomes a tested verb the skill calls.

**This verb reads beads without knowing beads exists.** Records arrive as JSON
on stdin::

    bd list --status=closed --closed-after=2026-08-15 --json | seeds candidates -

Nothing here shells out to ``bd``, and seeds gains no dependency on it. That is
partly principle — seeds ships to people who do not use beads — and partly that
a function taking a list of dicts can be tested against a fixture, where one
that spawns a tracker cannot.

**Lineage has three strengths and they are not interchangeable.** A bead's
``Source:`` field names the seeds that finishing it DISCHARGES; ``Context:``
names seeds merely cited. A ``Context:``-only seed must never surface as a
resolution candidate — that is the whole reason the two labels are separate,
and honouring it here is what makes the split worth writing. Everything else is
prose, which is the weak fallback.

**Prose is the common case, not the exception.** Measured on this project
2026-09-13: 0 of 175 beads carried a ``Source:`` field, while 103 mentioned a
seed-shaped ID somewhere in prose. Treating the structured field as the normal
path would have produced an empty answer on a corpus with twelve real
candidates in it.

**A prose mention can be disambiguated even though the shapes collide.** Bead
IDs and seed IDs are identical in form — both tools derive the prefix from the
project name — so shape alone can never say which one a token names. Existence
can: an ID that resolves to a seed file and NOT to a bead is a seed reference.
On this corpus that decided all 171 mentioned IDs with zero ambiguity (80
seed-only, 60 bead-only, 31 neither). Seed seeds-4co.22 would retire this rule by
giving seed IDs a tilde separator; until it ships, this is what works.

**A mention is not a discharge, and this module never claims otherwise.** It
emits candidates with the evidence class attached precisely so the skill can
say how strong the link is. The skill's step 2 — go and find the code — is what
turns a candidate into a resolution, and nothing here is a substitute for it.
The false positive that step exists for (seeds-lcfa.1.1, reported shipped in
2026-08 because every bead mentioning it had closed, when the closing bead had
shipped something else entirely) is exactly what a prose-evidence candidate
looks like from here.

**The window is stateless.** Thirty days by default, ``--since`` to override,
no marker file (ruled by @aguynamedryan 2026-09-13). The accepted cost is that
a gap longer than the window silently misses its early span, so the window used
is ALWAYS printed — that line is the only thing standing between the operator
and an invisible hole in the sweep.

**This verb writes nothing.** It reads and prints, like ``winnow``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from seeds.models import find_id_ref_candidates, now_utc
from seeds.seedfile import SeedRecord
from seeds.store import TERMINAL_STATUSES

#: One bead as ``bd list --json`` emits it. Deliberately untyped beyond this:
#: seeds does not model beads' schema, it reads four keys out of whatever it is
#: handed and tolerates the rest.
BeadRecord = dict[str, Any]

#: The default window, in days. Long enough that an infrequent operator is
#: unlikely to run past it, short enough that a sweep stays one feature-set
#: rather than a corpus audit (which is ``winnow``'s job, not this one).
DEFAULT_SINCE_DAYS = 30

#: Evidence classes, strongest first. The skill reports these verbatim.
EVIDENCE_SOURCE = "source"
EVIDENCE_PROSE = "prose"

#: The lineage grammar written by ``seeds-to-beads``: a label, exactly one
#: space, then IDs joined by ", ". Anchored to the start of a line so a
#: sentence that happens to contain the word "Source:" mid-paragraph cannot
#: masquerade as the field.
_LINEAGE_RE = re.compile(r"^(Source|Context):[ \t]*(.*)$", re.MULTILINE)

#: ``Source: none`` is a deliberate assertion that a bead has no originating
#: seed — distinct from an absent field, which only says the bead predates the
#: convention. Both yield no candidates, but only the first means "we checked".
_LINEAGE_NONE = "none"


@dataclass(frozen=True)
class BeadRef:
    """One closed bead that cites a seed."""

    bead_id: str
    title: str
    closed_at: datetime | None


@dataclass(frozen=True)
class Candidate:
    """A seed that a recently-closed bead claims to have discharged.

    ``evidence`` is :data:`EVIDENCE_SOURCE` or :data:`EVIDENCE_PROSE`. It is
    carried all the way to the output rather than collapsed, because the
    skill's first report to the operator has to state how strong the link is,
    and a candidate that arrived by text-matching is a materially weaker claim
    than one a human recorded at conversion time.
    """

    seed_id: str
    seed_title: str
    seed_status: str
    evidence: str
    beads: tuple[BeadRef, ...]

    @property
    def latest_close(self) -> datetime | None:
        """The most recent close among the citing beads, if any is dated."""
        dated = [b.closed_at for b in self.beads if b.closed_at is not None]
        return max(dated) if dated else None


@dataclass
class CandidatesReport:
    """What the sweep found, and what it deliberately did not offer."""

    since: datetime
    now: datetime
    beads_in: int = 0
    beads_in_window: int = 0
    candidates: list[Candidate] = field(default_factory=list)
    #: Seeds named on a ``Context:`` line and nowhere stronger. Withheld on
    #: purpose; reported so the withholding is visible rather than silent.
    cited_only: list[str] = field(default_factory=list)
    #: Referenced seeds already resolved or abandoned — nothing left to close.
    already_terminal: list[str] = field(default_factory=list)
    #: Tokens that named neither a live seed nor a bead. Usually a seed from
    #: another project's store quoted in prose, sometimes a hallucinated ID.
    unresolved_refs: list[str] = field(default_factory=list)


class CandidatesError(Exception):
    """Raised when the bead records on stdin cannot be read at all."""


def parse_lineage(notes: str) -> tuple[list[str], list[str]]:
    """Return ``(source_ids, context_ids)`` from a bead's notes field.

    Both labels follow one grammar — ``Source: <id>[, <id>]*`` — and either may
    be absent. ``Source: none`` parses to an empty list, the same as an absent
    field: the distinction between "no seed" and "we do not know" matters to a
    human reading the bead, but neither produces a candidate here.

    Repeated labels are unioned rather than ranked. The convention says one
    line each, but a bead edited by hand can end up with two, and dropping the
    second silently would lose lineage the writer meant to record.
    """
    if not notes:
        return [], []
    found: dict[str, list[str]] = {"Source": [], "Context": []}
    for match in _LINEAGE_RE.finditer(notes):
        label, rest = match.group(1), match.group(2).strip()
        if not rest or rest.lower() == _LINEAGE_NONE:
            continue
        for token in rest.split(","):
            token = token.strip()
            if token and token not in found[label]:
                found[label].append(token)
    return found["Source"], found["Context"]


def _closed_at(record: BeadRecord) -> datetime | None:
    """Parse a bead's close timestamp, tolerating absence and junk.

    An undated record is NOT dropped — it is kept out of the window filter and
    reported as undated. A bead whose timestamp seeds cannot parse is still a
    closed bead, and silently discarding it is exactly the kind of invisible
    narrowing this module's window line exists to prevent.
    """
    raw = record.get("closed_at") or record.get("closedAt")
    if not isinstance(raw, str) or not raw:
        return None
    text = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        from datetime import UTC

        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def load_bead_records(text: str) -> list[BeadRecord]:
    """Parse ``bd``'s JSON output into a list of bead records.

    Accepts the two shapes ``bd`` emits — a bare array, or an object with an
    ``issues`` key — plus JSONL, so a hand-assembled file works as well as a
    pipe. Raises :class:`CandidatesError` when none of them parse; an empty
    input is an empty list, not an error, because "no beads closed in the
    window" is a perfectly ordinary answer.
    """
    text = text.strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except ValueError:
        records: list[BeadRecord] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except ValueError as exc:
                raise CandidatesError(
                    f"input is neither JSON nor JSONL: {exc}"
                ) from exc
            if isinstance(parsed, dict):
                records.append(parsed)
        return records
    if isinstance(payload, dict):
        payload = payload.get("issues", payload.get("records", []))
    if not isinstance(payload, list):
        raise CandidatesError(
            "expected a JSON array of bead records, or an object with an "
            f"'issues' key; got {type(payload).__name__}"
        )
    return [r for r in payload if isinstance(r, dict)]


def find_candidates(
    records: Sequence[BeadRecord],
    seed_records: Iterable[SeedRecord],
    *,
    prefix: str,
    since: datetime,
    now: datetime | None = None,
    seeds_dir: Path | None = None,
) -> CandidatesReport:
    """Work out which seeds the closed beads in ``records`` may have discharged.

    ``records`` should be the FULL set of beads the caller is willing to show,
    not only those inside the window: every ID in it contributes to telling a
    bead reference apart from a seed reference, and a narrow input makes that
    disambiguation weaker. ``seeds_dir`` is accepted and ignored: it used to add
    the local ``.beads/issues.jsonl`` export, retired on 2026-09-13 and frozen
    wherever it survived (bead seeds-dlq). The records piped in from ``bd list``
    are the authoritative set.
    """
    now = now or now_utc()
    seeds_by_id = {r.id: r for r in seed_records}

    bead_ids = {r["id"] for r in records if isinstance(r.get("id"), str)}

    report = CandidatesReport(since=since, now=now, beads_in=len(records))

    # seed id -> (evidence class, [citing beads]). A seed cited by two beads,
    # one structurally and one in passing, keeps the stronger class.
    hits: dict[str, tuple[str, list[BeadRef]]] = {}
    cited_only: set[str] = set()
    terminal: set[str] = set()
    unresolved: set[str] = set()

    for record in records:
        # Every record contributes its ID to `bead_ids` above, but only a
        # CLOSED one can discharge a seed. Callers are told to pipe the full
        # set precisely so disambiguation is strong, so the filter has to live
        # here rather than being delegated to the caller's `bd` invocation.
        if str(record.get("status") or "").lower() != "closed":
            continue
        closed_at = _closed_at(record)
        if closed_at is not None and closed_at < since:
            continue
        report.beads_in_window += 1

        notes = record.get("notes") or ""
        source_ids, context_ids = parse_lineage(notes)
        cited_only.update(context_ids)

        if source_ids:
            evidence, refs = EVIDENCE_SOURCE, source_ids
        else:
            prose = find_id_ref_candidates(
                f"{record.get('description') or ''}\n{notes}", prefix
            )
            # A bead's own ID appears in its prose often enough to matter, and
            # `Context:` seeds are cited rather than discharged — neither is a
            # candidate.
            evidence = EVIDENCE_PROSE
            refs = [r for r in prose if r not in bead_ids and r not in context_ids]

        bead = BeadRef(
            bead_id=record.get("id") or "?",
            title=record.get("title") or "",
            closed_at=closed_at,
        )
        for ref in refs:
            seed = seeds_by_id.get(ref)
            if seed is None:
                unresolved.add(ref)
                continue
            if seed.status in TERMINAL_STATUSES:
                terminal.add(ref)
                continue
            held, citing = hits.setdefault(ref, (evidence, []))
            if evidence == EVIDENCE_SOURCE and held != EVIDENCE_SOURCE:
                hits[ref] = (EVIDENCE_SOURCE, citing)
            citing.append(bead)
            cited_only.discard(ref)

    for seed_id, (evidence, beads) in hits.items():
        seed = seeds_by_id[seed_id]
        report.candidates.append(
            Candidate(
                seed_id=seed_id,
                seed_title=seed.title,
                seed_status=seed.status.value,
                evidence=evidence,
                beads=tuple(beads),
            )
        )

    # Strongest evidence first, then most recently closed, then by ID so the
    # output is stable enough to diff between runs.
    report.candidates.sort(
        key=lambda c: (
            c.evidence != EVIDENCE_SOURCE,
            -(c.latest_close.timestamp() if c.latest_close else 0),
            c.seed_id,
        )
    )
    report.cited_only = sorted(cited_only - set(hits))
    report.already_terminal = sorted(terminal)
    report.unresolved_refs = sorted(unresolved)
    return report


def report_as_dict(report: CandidatesReport) -> dict[str, Any]:
    """Render ``report`` as plain data for ``--json``."""
    return {
        "window": {
            "since": report.since.isoformat(),
            "now": report.now.isoformat(),
        },
        "beads_in": report.beads_in,
        "beads_in_window": report.beads_in_window,
        "candidates": [
            {
                "seed_id": c.seed_id,
                "title": c.seed_title,
                "status": c.seed_status,
                "evidence": c.evidence,
                "beads": [
                    {
                        "id": b.bead_id,
                        "title": b.title,
                        "closed_at": b.closed_at.isoformat() if b.closed_at else None,
                    }
                    for b in c.beads
                ],
            }
            for c in report.candidates
        ],
        "cited_only": report.cited_only,
        "already_terminal": report.already_terminal,
        "unresolved_refs": report.unresolved_refs,
    }


def format_report(report: CandidatesReport) -> str:
    """Render ``report`` for a terminal.

    The window line comes first and is never omitted, including on an empty
    result: "nothing found" and "nothing looked at" are different answers, and
    only the window separates them.
    """
    lines: list[str] = []
    span = (report.now - report.since).days
    lines.append(
        f"window: beads closed since {report.since.date().isoformat()} "
        f"({span}d) — {report.beads_in_window} in window, "
        f"of {report.beads_in} bead(s) read"
    )
    lines.append("")

    if not report.candidates:
        lines.append("No candidate seeds — nothing to reconcile in this window.")
    for c in report.candidates:
        cites = ", ".join(
            f"{b.bead_id}"
            + (f" (closed {b.closed_at.date().isoformat()})" if b.closed_at else "")
            for b in c.beads
        )
        lines.append(f"{c.seed_id}  [{c.evidence}]  {c.seed_title}")
        lines.append(f"    status: {c.seed_status}")
        lines.append(f"    cited by: {cites}")
        lines.append("")

    if report.candidates and any(
        c.evidence == EVIDENCE_PROSE for c in report.candidates
    ):
        lines.append(
            "A [prose] candidate was found by text-matching a seed ID out of a "
            "bead's description. That a bead MENTIONS a seed is not evidence it "
            "implemented one — verify against shipped code before resolving."
        )
        lines.append("")

    if report.cited_only:
        lines.append(
            "Cited but not discharged (Context: lines) — not candidates: "
            + ", ".join(report.cited_only)
        )
    if report.already_terminal:
        lines.append(
            "Already resolved or abandoned: " + ", ".join(report.already_terminal)
        )
    if report.unresolved_refs:
        lines.append(
            "Referenced but not a seed here (another store, or a bad ID): "
            + ", ".join(report.unresolved_refs)
        )
    return "\n".join(lines).rstrip() + "\n"
