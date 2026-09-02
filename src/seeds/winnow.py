"""``seeds winnow`` — is the *thinking* healthy?

Three commands sit on one boundary and it is worth keeping clean:

* ``seeds check``  — are the FILES valid?    (format: a title that is a path,
  an edge written at one end only)
* ``seeds doctor`` — is the STORE healthy?   (operational: dangling edges, a
  recorded prefix, a corpus that reads)
* ``seeds winnow`` — is the THINKING healthy? (semantic: a deferral nobody came
  back to, a conclusion resting on a figure that has moved, two resolved seeds
  that cannot both be right)

Folding this into either of the first two was considered and rejected
(seed seeds-163). They gate; this does not, and a semantic finding that can fail
a commit is a semantic finding people learn to bypass.

**THE detection rule.** *Contradictions live inside clusters, not across the
corpus.* Two seeds can only contradict each other if they are about the same
thing, and parent/child plus ``relates-to`` edges already encode exactly that.
So the candidate set is **the edge set, not the cross product**: measured on
this project's own store, 314 seeds and 692 edges — 692 comparisons rather than
roughly 49,000. There is no corpus-wide pairwise scan here and there is no
sampling; the unit of review is an edge.

**Hard findings and scoped candidates are separate, and the separation is the
design.** A fact needs no judgment and is fully testable: a deferral untouched
for eight months either is or is not. A candidate is the verb *narrowing* — it
says "these two might conflict; go and read them", and it is allowed to be
wrong. Printing them in one list would let one soft false positive discredit
the factual half, which is how a detector loses the credibility that is the
only thing making it worth running.

**Why the contradiction rule is not just "both endpoints resolved".** That
status test alone flags every agreeing parent and child in the corpus, and a
detector that cries wolf on agreement is worse than no detector. So a status
gate narrows to edges worth looking at, and then a **polarity clash** narrows
again: one endpoint asserting X where the other asserts not-X, over a shared
subject. Both halves are deterministic and both are tested — including the case
that matters most, two related seeds that AGREE and must not be flagged.

**Age is never evidence of staleness.** An old seed is an old seed. What makes
a resolved seed a staleness candidate is that it rests on a *checkable premise*
— a version, a measurement — which somebody can go and re-check. Age is used
only to narrow which of those to look at first, never to raise one.

**This verb writes nothing.** It reads the corpus and prints. Everything it
finds is for a person or a skill to act on.

This module is itself code that can be silently wrong, so it is tested the way
a detector is tested: hand-built corpora with hand-computed answers, and a
false-positive control for every flavor that can produce one.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from seeds.beads import load_bead_ids
from seeds.models import (
    RelationType,
    SeedStatus,
    find_id_ref_candidates,
    is_allowlisted_prose,
    now_utc,
)
from seeds.seedfile import SeedRecord
from seeds.textmatch import containment, content_tokens, overlap

__all__ = [
    "CANDIDATE_FLAVORS",
    "FACT_FLAVORS",
    "FLAVORS",
    "Edge",
    "Finding",
    "WinnowReport",
    "edges",
    "format_report",
    "report_as_dict",
    "winnow",
]

#: A deferral untouched for this long is a neglected one. Overridable with
#: ``--since``; three months is the point at which "later" has stopped meaning
#: anything.
NEGLECT_DAYS = 90

#: An exploring or captured seed untouched for this long is long-unresolved.
UNRESOLVED_DAYS = 180

#: How far back a resolved seed's premise must be to be worth re-checking. This
#: NARROWS a candidate set the premise already raised — it never raises one.
STALE_DAYS = 180

FACT_FLAVORS = ("neglect", "unblocked", "unresolved")
CANDIDATE_FLAVORS = ("contradiction", "staleness", "outcome")
FLAVORS = FACT_FLAVORS + CANDIDATE_FLAVORS

FACT = "fact"
CANDIDATE = "candidate"


@dataclass(frozen=True)
class Finding:
    """One thing winnow noticed, in either tier.

    One type for both tiers, for the reason :class:`seeds.check.Finding` gives:
    a candidate is not a weaker kind of object, it is the same object reported
    without the claim that it is settled, and a second class would mean a second
    formatter that could drift from this one.

    ``action`` is mandatory and carries the tier's difference. For a fact it is
    the fix. For a candidate it is **the judgment somebody still has to make** —
    the verb has narrowed and stopped, and saying so on every line is what keeps
    a candidate from being read as a verdict.
    """

    tier: str
    flavor: str
    code: str
    seed_ids: tuple[str, ...]
    message: str
    action: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class Edge:
    """One undirected relationship between two seeds, de-duplicated.

    Every stored edge exists at both ends (``docs/storage-format.md`` §5.1) and
    a parent is recorded on the child, so the same relationship reaches this
    module two or three ways. It is normalized to one entry with the ids
    sorted, because the unit of review is the relationship, not either file's
    view of it.
    """

    a: str
    b: str
    kind: str


def edges(records: Iterable[SeedRecord]) -> list[Edge]:
    """The corpus's edge set: parent/child plus every stored relationship.

    Both edge sources are included because both encode "these two are about the
    same thing", which is the only property the contradiction rule needs. An
    edge whose far end is not in the corpus is dropped — that is a dangling
    reference, which is ``seeds doctor``'s finding, not this module's.
    """
    by_id = {record.id: record for record in records}
    found: dict[tuple[str, str, str], Edge] = {}

    def add(left: str, right: str, kind: str) -> None:
        if left == right or left not in by_id or right not in by_id:
            return
        first, second = sorted((left, right))
        found.setdefault((first, second, kind), Edge(first, second, kind))

    for record in by_id.values():
        if record.parent:
            add(record.parent, record.id, "parent")
        for edge in record.relationships:
            if edge.rel_type is RelationType.RELATES_TO:
                add(record.id, edge.target_id, "relates-to")
            else:
                add(record.id, edge.target_id, "questions")
    return sorted(found.values(), key=lambda e: (e.a, e.b, e.kind))


# --- Hard findings -----------------------------------------------------------


def _days(since: datetime, now: datetime) -> int:
    return max(0, (now - since).days)


def _neglect(
    records: Sequence[SeedRecord], *, cutoff: datetime, now: datetime
) -> list[Finding]:
    """Deferred, and untouched since the cutoff. A fact, not a judgment."""
    out: list[Finding] = []
    for record in records:
        if record.status is not SeedStatus.DEFERRED:
            continue
        if record.updated_at >= cutoff:
            continue
        out.append(
            Finding(
                tier=FACT,
                flavor="neglect",
                code="neglected-deferral",
                seed_ids=(record.id,),
                message=(
                    f"deferred and untouched for "
                    f"{_days(record.updated_at, now)} days "
                    f"(last touched {record.updated_at.date().isoformat()}): "
                    f"{record.title}"
                ),
                action=(
                    f"pick it back up (`seeds explore {record.id}`) or let it go "
                    f"(`seeds abandon {record.id}`) — 'later' has stopped meaning "
                    f"anything"
                ),
            )
        )
    return out


def _unblocked(records: Sequence[SeedRecord]) -> list[Finding]:
    """Everything that was holding this seed is closed, and it is still open.

    ``seeds`` has no ``blocked`` status — being blocked is derived from
    unresolved children and unresolved questions (:meth:`seeds.store.Store.
    is_blocked`). So "blocked while every blocker is closed" is: a seed that had
    blockers, all of which have since reached a terminal status, that nobody
    came back to. The moment it became workable is recorded — it is when the
    last blocker closed.
    """
    by_id = {record.id: record for record in records}
    holders: dict[str, list[SeedRecord]] = {}
    for record in records:
        if record.parent and record.parent in by_id:
            holders.setdefault(record.parent, []).append(record)
        for edge in record.relationships:
            if edge.rel_type is RelationType.QUESTIONS and edge.target_id in by_id:
                holders.setdefault(edge.target_id, []).append(record)

    out: list[Finding] = []
    for seed_id, blockers in sorted(holders.items()):
        record = by_id[seed_id]
        if record.status in (SeedStatus.RESOLVED, SeedStatus.ABANDONED):
            continue
        if any(
            blocker.status
            not in (
                SeedStatus.RESOLVED,
                SeedStatus.ABANDONED,
            )
            for blocker in blockers
        ):
            continue
        closed = [b.resolved_at or b.updated_at for b in blockers]
        freed = max(closed)
        out.append(
            Finding(
                tier=FACT,
                flavor="unblocked",
                code="unblocked-and-open",
                seed_ids=(seed_id,),
                message=(
                    f"all {len(blockers)} blocker(s) closed by "
                    f"{freed.date().isoformat()}, still {record.status.value}: "
                    f"{record.title}"
                ),
                action=(
                    f"nothing is holding it — resolve it "
                    f"(`seeds resolve {seed_id}`) or say what is still open"
                ),
                evidence=tuple(
                    f"{b.id} ({b.status.value}): {b.title}" for b in blockers
                ),
            )
        )
    return out


def _unresolved(
    records: Sequence[SeedRecord],
    edge_list: Sequence[Edge],
    *,
    cutoff: datetime,
    now: datetime,
) -> list[Finding]:
    """Exploring or captured well past the threshold, with its graph position.

    The graph position is reported because it is what decides the response: an
    isolated captured seed is a note somebody can drop, while an exploring seed
    with six edges is a live thread that stalled.
    """
    degree: dict[str, int] = {}
    for edge in edge_list:
        degree[edge.a] = degree.get(edge.a, 0) + 1
        degree[edge.b] = degree.get(edge.b, 0) + 1
    children: dict[str, int] = {}
    for record in records:
        if record.parent:
            children[record.parent] = children.get(record.parent, 0) + 1

    out: list[Finding] = []
    for record in records:
        if record.status not in (SeedStatus.EXPLORING, SeedStatus.CAPTURED):
            continue
        if record.updated_at >= cutoff:
            continue
        out.append(
            Finding(
                tier=FACT,
                flavor="unresolved",
                code="long-unresolved",
                seed_ids=(record.id,),
                message=(
                    f"{record.status.value} for {_days(record.updated_at, now)} "
                    f"days, {degree.get(record.id, 0)} edge(s), "
                    f"{children.get(record.id, 0)} child(ren): {record.title}"
                ),
                action=(
                    "close the loop: resolve it, defer it with a reason, or "
                    "abandon it — an open seed nobody touches is a claim nobody "
                    "is checking"
                ),
            )
        )
    return out


# --- Scoped candidates -------------------------------------------------------

#: Words that flip a claim. Read against a SHARED subject: on their own they
#: mean nothing, since half the corpus contains "not".
_NEGATION_RE = re.compile(
    r"\b(?:not|never|no|none|cannot|can't|won't|don't|doesn't|isn't|aren't|"
    r"without|instead|rather|rejected|reject|refuse[ds]?|drop(?:ped|s)?|"
    r"remove[ds]?|avoid(?:ed|s)?|abandon(?:ed|s)?|stop(?:ped|s)?|"
    r"deliberately not|must not|do not)\b",
    re.IGNORECASE,
)

#: Shared content words two lines need before their polarity is worth comparing.
_SUBJECT_TOKENS = 3

#: And how alike they must be. Below this the two lines mention the same nouns
#: while talking about different things.
_SUBJECT_OVERLAP = 0.34

#: Evidence lines are quoted, so they are bounded.
_EVIDENCE_CLIP = 160

_MIN_CLAIM_LEN = 20
_MAX_CLAIM_LEN = 300


_PARAGRAPH_RE = re.compile(r"\n\s*\n")
#: A sentence end, allowing for the markdown that trails it. Without the
#: character class a bolded sentence — ``...across the corpus.** The candidate
#: set...`` — never splits, and the negation in its first half is then read as
#: governing the second.
_SENTENCE_RE = re.compile(r"""(?<=[.!?])["'*_`)\]]*\s+""")


def _claims(record: SeedRecord) -> list[str]:
    """The assertions a seed makes: its title, resolution, and each sentence.

    Sentence by sentence, because polarity is a property of one sentence. A
    whole body contains both "we considered X" and "we rejected X", and reading
    polarity off the bag would make every seed both positive and negative at
    once.

    **Paragraphs are rejoined before they are split.** Seed bodies are
    hard-wrapped at about 76 columns, so a raw ``splitlines()`` yields
    fragments, not sentences — and a fragment carries the subject of a claim
    without the negation that governs it, or the reverse. Measured on this
    project's own corpus before the fix, 5 of 7 contradiction candidates were
    two halves of one wrapped sentence facing each other.
    """
    out: list[str] = []
    for source in (record.title, record.resolution, record.body):
        for paragraph in _PARAGRAPH_RE.split(source):
            joined = " ".join(paragraph.split())
            if not joined:
                continue
            for sentence in _SENTENCE_RE.split(joined):
                # Markdown furniture, not content: a heading hash, a quote
                # caret, a bullet. Each character is stripped independently,
                # which is what is wanted -- "## - **Decision**" is all leader.
                text = sentence.lstrip("#>-* ").strip()
                if _MIN_CLAIM_LEN <= len(text) <= _MAX_CLAIM_LEN:
                    out.append(text)
    return out


#: How much of the shared subject a negation must govern before the sentence
#: counts as DENYING it. Below this the negation is contrastive — "X, not Y"
#: asserts X while denying only the alternative — and reading it as a denial of
#: the whole sentence is what made 5 of 7 candidates false positives on this
#: project's own corpus.
_NEGATION_SCOPE = 0.6

#: Where a negation's reach ends. A negation governs its own clause, not the
#: rest of the sentence: in "not across the corpus, the candidate set is the
#: edge set" the second half is an assertion, and letting "not" run to the full
#: stop makes an agreeing seed look like a denial.
_CLAUSE_END_RE = re.compile(
    r"[,;:]"
    r"|\s+[\u2013\u2014-]+\s+"
    r"|\s+(?:and|but|or|because|so|which)\s+"
)


def _denies(sentence: str, subject: set[str]) -> bool:
    """Whether ``sentence`` denies ``subject``, rather than merely containing "not".

    Polarity is meaningless in the abstract — half the corpus contains a
    negation. What matters is whether the negation *governs the subject the two
    lines share*, so the scope is taken as everything from the negation word to
    the end of the sentence and the subject is asked how much of it landed
    inside.

    "Repo will live under the org, not a personal account" and "should the repo
    live under the org or a personal account?" share seven words, one of which
    is inside the negation's scope. They are not in conflict, and this is the
    test that says so.
    """
    match = _NEGATION_RE.search(sentence)
    if match is None:
        return False
    tail = sentence[match.start() :]
    clause = _CLAUSE_END_RE.search(tail, match.end() - match.start())
    if clause is not None:
        tail = tail[: clause.start()]
    return containment(subject, content_tokens(tail)) >= _NEGATION_SCOPE


def _resolved_after(record: SeedRecord, other: SeedRecord) -> bool:
    """Whether ``other`` was captured after ``record`` was resolved."""
    stamp = record.resolved_at
    return stamp is not None and other.created_at > stamp


def _edge_is_worth_reading(left: SeedRecord, right: SeedRecord) -> bool:
    """The status gate from the bead: both settled, or one settled then revisited.

    It is a *narrowing*, not a finding. On its own it flags every agreeing
    parent and child in the corpus, which is why the polarity test below exists.
    """
    resolved = SeedStatus.RESOLVED
    if left.status is resolved and right.status is resolved:
        return True
    if left.status is resolved and _resolved_after(left, right):
        return True
    return right.status is resolved and _resolved_after(right, left)


def _clash(left: SeedRecord, right: SeedRecord) -> tuple[str, str] | None:
    """The most-overlapping pair of lines that assert opposite things, or ``None``.

    Two conditions, both required. **A shared subject**: at least three content
    words in common and a third of the combined vocabulary, which is what makes
    the two lines about one thing rather than merely about the same nouns.
    **Opposite stance toward that subject**: one line denies what the other
    asserts, with the negation scoped to the shared words (:func:`_denies`).

    Two seeds that agree share the subject and share the stance, so they produce
    nothing here. That is the whole crying-wolf guard and it has its own test.
    """
    left_lines = [(line, content_tokens(line)) for line in _claims(left)]
    right_lines = [(line, content_tokens(line)) for line in _claims(right)]
    best: tuple[float, str, str] | None = None
    for l_text, l_tokens in left_lines:
        for r_text, r_tokens in right_lines:
            shared = l_tokens & r_tokens
            if len(shared) < _SUBJECT_TOKENS:
                continue
            score = overlap(l_tokens, r_tokens)
            if score < _SUBJECT_OVERLAP:
                continue
            if _denies(l_text, shared) == _denies(r_text, shared):
                continue
            if best is None or score > best[0]:
                best = (score, l_text, r_text)
    if best is None:
        return None
    return (best[1], best[2])


def _clip(text: str, limit: int = _EVIDENCE_CLIP) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _contradictions(
    records: Sequence[SeedRecord], edge_list: Sequence[Edge]
) -> list[Finding]:
    """Edge pairs whose endpoints assert opposite things about one subject."""
    by_id = {record.id: record for record in records}
    out: list[Finding] = []
    for edge in edge_list:
        left, right = by_id[edge.a], by_id[edge.b]
        if not _edge_is_worth_reading(left, right):
            continue
        clash = _clash(left, right)
        if clash is None:
            continue
        out.append(
            Finding(
                tier=CANDIDATE,
                flavor="contradiction",
                code="contradiction-candidate",
                seed_ids=(edge.a, edge.b),
                message=(
                    f"{edge.a} and {edge.b} are linked ({edge.kind}) and assert "
                    f"opposite things about one subject"
                ),
                action=(
                    "read both and decide whether they genuinely conflict; if "
                    "they do, which one stands, and mark the other superseded"
                ),
                evidence=(
                    f"{edge.a}: {_clip(clash[0])}",
                    f"{edge.b}: {_clip(clash[1])}",
                ),
            )
        )
    return out


#: What makes a premise CHECKABLE: somebody can go and look at it again.
_PREMISE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "version",
        re.compile(
            r"\b(?:v\d+\.\d+(?:\.\d+)?"
            r"|\d+\.\d+\.\d+"
            r"|python\s*3\.\d+"
            r"|[<>=!]=\s*\d+(?:\.\d+)*"
            r"|>=\s*\d+(?:\.\d+)*)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "measurement",
        re.compile(
            r"\b\d[\d,]*(?:\.\d+)?\s*(?:of|/|out of|vs\.?|->|→)\s*\d"
            r"|\b\d[\d,]*(?:\.\d+)?\s*(?:%|[KMG]B|ms|seconds?|minutes?|hours?|"
            r"files?|seeds?|beads?|rows?|lines?|edges?|commits?|records?|tests?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "as-of",
        re.compile(
            r"\b(?:measured|benchmarked|timed|counted|as of)\b[^.]{0,40}"
            r"\b\d{4}-\d{2}-\d{2}\b",
            re.IGNORECASE,
        ),
    ),
)


def _premise(record: SeedRecord) -> tuple[str, str] | None:
    """``(kind, line)`` for the first checkable premise a seed cites."""
    for line in _claims(record):
        for kind, pattern in _PREMISE_PATTERNS:
            if pattern.search(line):
                return (kind, line)
    return None


def _staleness(
    records: Sequence[SeedRecord], *, cutoff: datetime, now: datetime
) -> list[Finding]:
    """Resolved seeds resting on something somebody can go and re-check.

    **Age is not the evidence and must never become it.** The evidence is the
    premise; the cutoff only decides which premises to put in front of a
    reviewer first. A resolved seed with no version, figure or dated
    measurement in it is never raised here however old it is — that case has
    its own test.
    """
    out: list[Finding] = []
    for record in records:
        if record.status is not SeedStatus.RESOLVED:
            continue
        stamp = record.resolved_at or record.updated_at
        if stamp >= cutoff:
            continue
        premise = _premise(record)
        if premise is None:
            continue
        kind, line = premise
        out.append(
            Finding(
                tier=CANDIDATE,
                flavor="staleness",
                code="staleness-candidate",
                seed_ids=(record.id,),
                message=(
                    f"resolved {stamp.date().isoformat()} "
                    f"({_days(stamp, now)} days ago) on a checkable "
                    f"{kind}: {record.title}"
                ),
                action=(
                    "go and re-check the premise below; if it has moved, the "
                    "conclusion resting on it may have moved too"
                ),
                evidence=(f"{kind}: {_clip(line)}",),
            )
        )
    return out


_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _outcomes(
    records: Sequence[SeedRecord], *, seeds_dir: Path | None, prefix: str
) -> list[Finding]:
    """Resolved seeds that name downstream work, surfaced as prompts only.

    Whether the shipped thing did what the seed hoped **cannot be read out of
    the corpus** — it is in the code, the tests, and whoever used it. So this
    flavor does not detect an outcome; it finds the seeds where asking about one
    is worth somebody's time, and says so.
    """
    if seeds_dir is None:
        return []
    bead_ids = load_bead_ids(seeds_dir)
    if not bead_ids:
        return []
    seed_ids = {record.id for record in records}
    out: list[Finding] = []
    for record in records:
        if record.status is not SeedStatus.RESOLVED:
            continue
        text = f"{record.title}\n{record.resolution}\n{record.body}"
        downstream = [
            ref
            for ref in find_id_ref_candidates(text, prefix)
            if ref in bead_ids
            and ref not in seed_ids
            and not is_allowlisted_prose(ref, prefix)
        ]
        if not downstream:
            continue
        out.append(
            Finding(
                tier=CANDIDATE,
                flavor="outcome",
                code="outcome-candidate",
                seed_ids=(record.id,),
                message=(
                    f"resolved, and names {len(downstream)} downstream bead(s): "
                    f"{record.title}"
                ),
                action=(
                    "the work shipped — ask whether it did what this seed hoped, "
                    "and record the answer back in the seed"
                ),
                evidence=(", ".join(sorted(downstream)),),
            )
        )
    return out


# --- Running the whole thing -------------------------------------------------


@dataclass
class WinnowReport:
    """Everything one run found, with the two tiers kept apart."""

    seeds: int
    edges: int
    flavors: tuple[str, ...]
    facts: list[Finding] = field(default_factory=list)
    candidates: list[Finding] = field(default_factory=list)


def winnow(
    records: Sequence[SeedRecord],
    *,
    flavors: Sequence[str] = FLAVORS,
    since: datetime | None = None,
    now: datetime | None = None,
    seeds_dir: Path | None = None,
    prefix: str = "seeds",
) -> WinnowReport:
    """Walk the graph and report. Reads only; writes nothing, ever.

    ``since`` replaces every age cutoff with one explicit point, so a reviewer
    asking "what has gone quiet since the last release?" gets one answer rather
    than three thresholds.
    """
    now = now or now_utc()
    chosen = tuple(f for f in FLAVORS if f in set(flavors or FLAVORS))
    edge_list = edges(records)
    ordered = sorted(records, key=lambda record: record.id)

    neglect_cutoff = since or (now - timedelta(days=NEGLECT_DAYS))
    unresolved_cutoff = since or (now - timedelta(days=UNRESOLVED_DAYS))
    stale_cutoff = since or (now - timedelta(days=STALE_DAYS))

    facts: list[Finding] = []
    if "neglect" in chosen:
        facts += _neglect(ordered, cutoff=neglect_cutoff, now=now)
    if "unblocked" in chosen:
        facts += _unblocked(ordered)
    if "unresolved" in chosen:
        facts += _unresolved(ordered, edge_list, cutoff=unresolved_cutoff, now=now)

    candidates: list[Finding] = []
    if "contradiction" in chosen:
        candidates += _contradictions(ordered, edge_list)
    if "staleness" in chosen:
        candidates += _staleness(ordered, cutoff=stale_cutoff, now=now)
    if "outcome" in chosen:
        candidates += _outcomes(ordered, seeds_dir=seeds_dir, prefix=prefix)

    return WinnowReport(
        seeds=len(ordered),
        edges=len(edge_list),
        flavors=chosen,
        facts=facts,
        candidates=candidates,
    )


def report_as_dict(report: WinnowReport) -> dict[str, object]:
    """The report as plain data, for ``--json`` and for the reviewing skill."""

    def render(finding: Finding) -> dict[str, object]:
        return {
            "tier": finding.tier,
            "flavor": finding.flavor,
            "code": finding.code,
            "seed_ids": list(finding.seed_ids),
            "message": finding.message,
            "action": finding.action,
            "evidence": list(finding.evidence),
        }

    return {
        "corpus": {"seeds": report.seeds, "edges": report.edges},
        "flavors": list(report.flavors),
        "facts": [render(finding) for finding in report.facts],
        "candidates": [render(finding) for finding in report.candidates],
    }


def format_report(report: WinnowReport) -> str:
    """Two sections, never one.

    A soft-flavor false positive must not be able to discredit the factual
    section, and the only reliable way to stop that is to never let the two
    share a list. Every candidate line carries the judgment still to be made,
    so nothing here can be misread as a verdict.
    """
    out = [
        f"seeds winnow: {report.seeds} seed(s), {report.edges} edge(s), "
        f"flavors: {', '.join(report.flavors) or 'none'}."
    ]
    out.append("")
    out.append(f"FACTS ({len(report.facts)}) — no judgment needed")
    if not report.facts:
        out.append("  (none)")
    for finding in report.facts:
        out.extend(_render(finding))

    out.append("")
    out.append(
        f"CANDIDATES ({len(report.candidates)}) — for review; winnow narrows, "
        f"it does not conclude"
    )
    if not report.candidates:
        out.append("  (none)")
    for finding in report.candidates:
        out.extend(_render(finding))
    out.append("")
    return "\n".join(out)


def _render(finding: Finding) -> list[str]:
    lines = [f"  {finding.code}  {' ↔ '.join(finding.seed_ids)}"]
    lines.append(f"    {finding.message}")
    lines.extend(f"    · {item}" for item in finding.evidence)
    lines.append(f"    → {finding.action}")
    return lines
