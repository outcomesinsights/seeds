"""``seeds glean`` — the deterministic half of harvesting a session transcript.

A working session produces deliberation faster than anyone files it, and the
record of it already exists: Claude Code writes every turn to
``~/.claude/projects/<slug>/<session-id>.jsonl``. This module reads that file
and answers one question — *what was worked out here that the corpus does not
already hold?*

**Why this is a verb and not a skill reading the file.** Two reasons, both
settled before the code was written (seed seeds-74.2.1):

1. **Cost.** Measured on titan 2026-09-01: one ordinary session's transcript is
   502KB across 256 turns, and 866 of its 3041 lines are tool results. Handing
   that to a model raw so it can find a handful of gaps is the wrong shape.
   Filtering happens *here*; the consumer never receives the transcript.
2. **Testability.** A verb gets pytest coverage. A skill gets none, and a
   candidate extractor that has quietly gone blind reports "nothing to capture"
   — the same green-while-broken failure :mod:`seeds.check` exists to refuse.

**This module calls no model and does no prompting.** That is the whole point
of the split: the deterministic work is a verb, the judgment — is this
candidate worth a seed, and what should it say? — is a skill. Nothing here
concludes anything; it narrows.

**Session resolution is not a heuristic.** ``$CLAUDE_CODE_SESSION_ID`` is in
the agent's environment and names the transcript directly (verified on titan
2026-09-01). There is deliberately no most-recently-modified guessing: the
newest file in that directory belongs to whichever session last wrote, which on
a host running several agents is routinely not this one, and a wrong answer
there is silent.

**Marker phrases are a signal, never a requirement.** ``Decision:``,
``Tangent:`` and ``TODO:`` raise a candidate's confidence where they appear,
and nothing in the extraction depends on them (seed seeds-74.2.3) — the
transcripts that most need gleaning are exactly the ones nobody annotated.

**Where the gleaned marker lives.** ``.seeds/gleaned.jsonl``: one JSON object
per gleaned transcript, appended. It sits beside ``config.yaml`` as repo-level
state (``docs/storage-format.md`` §9) rather than inside ``.seeds/seeds/``, so
the corpus scan never sees it and ``seeds check`` has nothing to say about it.
It is not a derived artifact and §8's ban on those does not reach it: nothing
in it is computed from the seed files, so there is no second copy of anything
that could disagree with them.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from seeds.models import SeedStatus, now_utc
from seeds.seedfile import SeedRecord
from seeds.store import Store, new_record
from seeds.textmatch import containment, content_tokens

__all__ = [
    "AUTO_TAG",
    "GLEANED_FILE",
    "Candidate",
    "GleanError",
    "GleanReport",
    "Suppressed",
    "Turn",
    "extract_candidates",
    "format_report",
    "glean_transcript",
    "list_transcripts",
    "mark_gleaned",
    "parse_transcript",
    "project_slug",
    "read_gleaned",
    "resolve_session_id",
    "suppress_captured",
    "transcript_path",
    "transcripts_dir",
]


class GleanError(Exception):
    """Something glean needed was not there: a session id, a transcript."""


#: The environment variable Claude Code sets for the running session.
SESSION_ENV_VAR = "CLAUDE_CODE_SESSION_ID"

TRANSCRIPT_SUFFIX = ".jsonl"

#: Appended to by :func:`mark_gleaned`; read by :func:`read_gleaned`.
GLEANED_FILE = "gleaned.jsonl"

#: Every seed ``--auto`` creates carries this, so an unattended bulk pass can
#: be audited or reverted without hand-sorting it out of the corpus
#: (@aguynamedryan's guardrail on the ``--auto`` ruling, 2026-09-01).
AUTO_TAG = "auto-gleaned"


# --- Locating a transcript ---------------------------------------------------


def _home() -> Path:
    """The home directory holding ``.claude/projects``.

    A function rather than an inlined ``Path.home()`` so tests can point the
    whole module at a fixture tree. Nothing in the suite may read the real
    ``~/.claude``.
    """
    return Path.home()


def project_slug(cwd: Path) -> str:
    """The ``~/.claude/projects`` directory name for a working directory.

    Claude Code flattens the absolute path into one name, replacing every
    character that is not alphanumeric or an underscore with a hyphen.
    Underscores survive — ``/home/ryan/projects/outins/code_collector`` is
    stored as ``-home-ryan-projects-outins-code_collector``, and a leading
    slash becomes a leading hyphen.
    """
    return re.sub(r"[^A-Za-z0-9_]", "-", str(Path(cwd).resolve()))


def transcripts_dir(cwd: Path, *, home: Path | None = None) -> Path:
    """Where Claude Code keeps this project's transcripts."""
    root = home if home is not None else _home()
    return root / ".claude" / "projects" / project_slug(cwd)


def resolve_session_id(env: dict[str, str] | None = None) -> str:
    """The running session's id, from the environment. No guessing.

    Raises :class:`GleanError` when the variable is absent — which means glean
    is not running inside a Claude Code session, and the caller must name a
    session with ``--session``.
    """
    source = os.environ if env is None else env
    session = source.get(SESSION_ENV_VAR, "").strip()
    if not session:
        raise GleanError(
            f"${SESSION_ENV_VAR} is not set, so there is no current session to "
            f"glean. Pass --session=<id>, or --all for every transcript this "
            f"project has."
        )
    return session


def transcript_path(session_id: str, cwd: Path, *, home: Path | None = None) -> Path:
    """The transcript file for ``session_id``, whether or not it exists."""
    return transcripts_dir(cwd, home=home) / f"{session_id}{TRANSCRIPT_SUFFIX}"


def list_transcripts(
    cwd: Path, *, home: Path | None = None, since: datetime | None = None
) -> list[Path]:
    """Every transcript for this project, oldest first.

    ``since`` bounds a historical pass by the file's modification time. The
    transcript's own timestamps would be a truer clock, but reading 300 files
    to decide which 300 files to read is a worse trade than trusting the one
    the filesystem already recorded.
    """
    directory = transcripts_dir(cwd, home=home)
    if not directory.is_dir():
        return []
    paths = sorted(
        (path for path in directory.glob(f"*{TRANSCRIPT_SUFFIX}") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
    )
    if since is None:
        return paths
    cutoff = since.timestamp()
    return [path for path in paths if path.stat().st_mtime >= cutoff]


# --- Reading a transcript ----------------------------------------------------


@dataclass(frozen=True)
class Turn:
    """One conversational turn, reduced to the text a human said or wrote."""

    index: int
    speaker: str
    text: str
    timestamp: datetime | None = None


#: Harness scaffolding that arrives inside a user turn's content. None of it
#: was written by the user, so none of it can be deliberation.
_SCAFFOLD_TAGS = (
    "local-command-caveat",
    "command-name",
    "command-message",
    "command-args",
    "command-contents",
    "system-reminder",
    "user-prompt-submit-hook",
)

_SCAFFOLD_RE = re.compile(
    r"<(" + "|".join(_SCAFFOLD_TAGS) + r")>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)
_BARE_TAG_RE = re.compile(
    r"</?(" + "|".join(_SCAFFOLD_TAGS) + r")>",
    re.IGNORECASE,
)


def _strip_scaffold(text: str) -> str:
    """Remove the harness's own markup from a turn's text."""
    cleaned = _SCAFFOLD_RE.sub(" ", text)
    cleaned = _BARE_TAG_RE.sub(" ", cleaned)
    return cleaned.strip()


def _entry_text(entry: dict[str, object]) -> str:
    """The human-readable text of one transcript entry, or ``''``.

    ``tool_use``, ``tool_result`` and ``thinking`` blocks are dropped. Tool
    results are the bulk of a transcript and are raw data rather than anything
    anyone concluded; thinking is not a stated position, and treating it as one
    would file seeds for arguments the session went on to reject.
    """
    message = entry.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return _strip_scaffold(content)
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str):
            parts.append(text)
    return _strip_scaffold("\n".join(parts))


def _entry_timestamp(entry: dict[str, object]) -> datetime | None:
    raw = entry.get("timestamp")
    if not isinstance(raw, str):
        return None
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)


def parse_transcript(path: Path) -> list[Turn]:
    """The user and assistant turns of one transcript, in order.

    Sidechain entries — a sub-agent's own conversation — are skipped: they are
    a different session's deliberation, and the sub-agent's transcript is
    gleanable on its own terms. ``isMeta`` entries are harness bookkeeping.

    An unparseable line is skipped rather than fatal. A transcript is an append
    log written by another process and its last line may be half-written; the
    alternative is a glean that refuses to run because the session it is
    reading is still going.
    """
    if not path.is_file():
        raise GleanError(f"no transcript at {path}")
    turns: list[Turn] = []
    index = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict):
                continue
            if entry.get("type") not in ("user", "assistant"):
                continue
            if entry.get("isSidechain") or entry.get("isMeta"):
                continue
            text = _entry_text(entry)
            if not text:
                continue
            index += 1
            turns.append(
                Turn(
                    index=index,
                    speaker=str(entry["type"]),
                    text=text,
                    timestamp=_entry_timestamp(entry),
                )
            )
    return turns


# --- Extraction --------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    """One thing worth considering for capture. Never a conclusion."""

    kind: str
    text: str
    turn: int
    speaker: str
    signals: tuple[str, ...] = ()


#: Marker phrases. Where one appears it is strong evidence, and nothing below
#: requires one: every rule that follows stands on its own, and a transcript
#: with no markers in it at all is extracted exactly as fully. What a marker
#: buys is a line of the ASSISTANT's prose that the speaker rule would
#: otherwise drop.
_MARKER_RE = re.compile(
    r"^\s*(?:[-*>]\s*)?\**\s*"
    r"(tangent|decision|decided|ruling|ruled|todo|open question|question|"
    r"conclusion|takeaway|caveat|risk)\b\s*\**\s*:",
    re.IGNORECASE,
)

#: Marker word → the kind it names. Anything unlisted lands as a note.
_MARKER_KIND = {
    "decision": "decision",
    "decided": "decision",
    "ruling": "decision",
    "ruled": "decision",
    "question": "question",
    "open question": "question",
}

#: Commitment language. Deliberately NOT the general modal vocabulary a report
#: is written in: "must not", "never", "rather than" and "instead of" describe
#: a constraint as easily as they announce a choice, and on the real transcript
#: they fired on most of the prose. What is left names an act of deciding.
_DECISION_RE = re.compile(
    r"\b(?:"
    r"we(?:'ll| will| decided| agreed| are going to)|"
    r"let's|i'd (?:rather|prefer)|i want|decided to|decide to|"
    r"the decision is|settled on|going with|go with|"
    r"rejected|chose|picked"
    r")\b",
    re.IGNORECASE,
)

#: A figure alone is not a discovery — "312 seeds" appears in every status
#: line. What makes one is a COMPARISON (83 of 306, 65 -> 385, 6 vs 13) or a
#: verb saying somebody went and looked. Both are shapes a report of routine
#: work does not have.
_COMPARISON_RE = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\s*(?:of|/|out of|vs\.?|->|→|to)\s*\d",
    re.IGNORECASE,
)

_MEASURED_RE = re.compile(
    r"\b(?:measured|measurement|benchmark(?:ed)?|timed|profiled|counted|"
    r"verified|reproduced|observed)\b",
    re.IGNORECASE,
)

_FIGURE_RE = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\s*(?:%|[KMG]B|ms|sec|seconds?|minutes?|hours?|days?|"
    r"files?|seeds?|beads?|turns?|rows?|lines?|edges?|commits?|records?|"
    r"tests?|entries|comparisons?)\b",
    re.IGNORECASE,
)


def _is_measurement(sentence: str) -> bool:
    """Whether a sentence reports a figure somebody actually went and found."""
    if _COMPARISON_RE.search(sentence):
        return True
    return bool(_FIGURE_RE.search(sentence) and _MEASURED_RE.search(sentence))


_CLARIFICATION_RE = re.compile(
    r"\b(?:actually|to be clear|i meant|i mean|correction|that's wrong|"
    r"that is wrong|misread|not quite|no[,.]|nope|wrong\b|"
    r"what i (?:want|meant)|the point is)\b",
    re.IGNORECASE,
)

#: Shortest and longest a candidate sentence may be. Below the floor there is
#: nothing to judge ("ok?", "sure."). The ceiling is doing real work: a stated
#: position is short, and a 300-character sentence is a paragraph of report
#: prose that happens to contain a modal verb. Quoting those back defeats the
#: purpose of not forwarding the transcript.
_MIN_LEN = 25
_MAX_LEN = 220

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def _sentences(text: str) -> list[str]:
    """Split a turn into candidate-sized units."""
    out: list[str] = []
    for chunk in _SENTENCE_SPLIT_RE.split(text):
        stripped = " ".join(chunk.split())
        if stripped:
            out.append(stripped)
    return out


def _markers(sentence: str) -> tuple[str, ...]:
    match = _MARKER_RE.match(sentence)
    return (f"marker:{match.group(1).lower()}",) if match else ()


def _marker_kind(signals: tuple[str, ...]) -> str:
    for signal in signals:
        if signal.startswith("marker:"):
            return _MARKER_KIND.get(signal[len("marker:") :], "note")
    return "note"


def _classify(
    sentence: str, speaker: str, *, ends_turn: bool
) -> tuple[str, tuple[str, ...]] | None:
    """``(kind, signals)`` for a sentence worth offering, else ``None``.

    **The speaker rule, and why it is not squeamishness about assistant text.**
    A decision is a commitment, and in these sessions the person with the
    authority to commit is the user. The assistant's prose is overwhelmingly a
    *report of work done* — and it is written in exactly the same modal voice a
    decision uses ("we'll keep", "rather than", "never"), so a phrase-only
    classifier cannot tell the two apart. Measured against this project's own
    5.3MB transcript on 2026-09-02: classifying both speakers alike produced
    475 candidates from 251 turns, 247 of them "decisions", and an 82KB report
    — a filtered transcript rather than a candidate list, which fails the one
    thing the verb exists to do.

    So the assistant contributes three things and no more: a **figure it went
    and measured** (the assistant is the one that runs the tools, so data
    discoveries genuinely originate there), a line it **marked** itself, and a
    **question that ends its turn** — which is how an agent asks for a ruling.
    Every user-side rule and two of those three need no marker at all, so
    nothing here *depends* on markers; they only add lines that would otherwise
    be dropped.

    Within the user's own turns the order is deliberate: a question mark makes
    a sentence a question whatever else it holds, a correction outranks a
    decision, and a decision outranks a figure quoted in support of it.
    """
    if not (_MIN_LEN <= len(sentence) <= _MAX_LEN):
        return None
    signals = _markers(sentence)
    is_question = sentence.endswith("?") and len(sentence.split()) >= 5

    if speaker != "user":
        if is_question and ends_turn:
            return ("question", (*signals, "ends-turn-?"))
        if signals:
            return (_marker_kind(signals), signals)
        if _is_measurement(sentence):
            return ("measurement", ("figure",))
        return None

    if is_question:
        return ("question", (*signals, "ends-with-?"))
    if _CLARIFICATION_RE.search(sentence):
        return ("clarification", (*signals, "correction-phrase"))
    if _DECISION_RE.search(sentence):
        return ("decision", (*signals, "decision-phrase"))
    if _is_measurement(sentence):
        return ("measurement", (*signals, "figure"))
    if signals:
        return (_marker_kind(signals), signals)
    return None


#: How far ahead of a question an answer-and-decision may sit and still be read
#: as the same thread. Six turns is three exchanges.
_CHAIN_WINDOW = 6

#: Shared content words needed to call a later decision the resolution of an
#: earlier question.
_CHAIN_OVERLAP = 3


def _build_chains(candidates: Sequence[Candidate]) -> list[Candidate]:
    """Fold question→decision pairs into single ``chain`` candidates.

    A question that the session went on to settle is worth more than either
    half alone: it carries the deliberation *and* its outcome, which is the
    shape a seed wants. The constituents are consumed, so nothing is offered
    twice.
    """
    questions = [c for c in candidates if c.kind == "question"]
    decisions = [c for c in candidates if c.kind == "decision"]
    consumed: set[int] = set()
    chains: list[Candidate] = []
    for question in questions:
        q_tokens = content_tokens(question.text)
        for decision in decisions:
            if id(decision) in consumed:
                continue
            gap = decision.turn - question.turn
            if not 0 <= gap <= _CHAIN_WINDOW:
                continue
            if len(q_tokens & content_tokens(decision.text)) < _CHAIN_OVERLAP:
                continue
            consumed.add(id(question))
            consumed.add(id(decision))
            chains.append(
                Candidate(
                    kind="chain",
                    text=f"{question.text}  →  {decision.text}",
                    turn=question.turn,
                    speaker=question.speaker,
                    signals=tuple(
                        dict.fromkeys(question.signals + decision.signals + ("chain",))
                    ),
                )
            )
            break
    kept = [c for c in candidates if id(c) not in consumed]
    return sorted(kept + chains, key=lambda c: (c.turn, c.kind))


def extract_candidates(turns: Iterable[Turn]) -> list[Candidate]:
    """Every candidate the turns support, de-duplicated, chains folded in."""
    found: list[Candidate] = []
    seen: set[tuple[str, str]] = set()
    for turn in turns:
        sentences = _sentences(turn.text)
        for position, sentence in enumerate(sentences):
            classified = _classify(
                sentence,
                turn.speaker,
                ends_turn=position == len(sentences) - 1,
            )
            if classified is None:
                continue
            kind, signals = classified
            key = (kind, " ".join(sentence.lower().split()))
            if key in seen:
                continue
            seen.add(key)
            found.append(
                Candidate(
                    kind=kind,
                    text=sentence,
                    turn=turn.index,
                    speaker=turn.speaker,
                    signals=signals,
                )
            )
    return _build_chains(found)


# --- The corpus diff ---------------------------------------------------------


@dataclass(frozen=True)
class Suppressed:
    """A candidate the corpus already holds, and the seed that holds it."""

    candidate: Candidate
    seed_id: str


#: Fraction of a candidate's content words that must already appear in one line
#: of one seed before the candidate counts as captured. Deliberately high: a
#: glean that hides a real gap is worse than one that offers something twice,
#: because the second is visible to the reviewer and the first is not.
_CAPTURED_CONTAINMENT = 0.8

#: Floor on candidate size for suppression. Below it the ratio is decided by
#: three or four common words and means nothing.
_CAPTURED_MIN_TOKENS = 4


def _record_lines(record: SeedRecord) -> list[str]:
    """The comparable units of a seed: its title and each line of its body.

    Line by line rather than the whole body as one bag: a 4000-word body
    contains almost every common word, so containment against it would suppress
    nearly anything. A body line is the granularity a candidate sentence
    actually competes with.
    """
    lines = [record.title, record.resolution]
    lines.extend(record.body.splitlines())
    return [line for line in lines if line.strip()]


def suppress_captured(
    candidates: Sequence[Candidate], records: Iterable[SeedRecord]
) -> tuple[list[Candidate], list[Suppressed]]:
    """Split candidates into what is new and what the corpus already holds."""
    corpus = [
        (record.id, [content_tokens(line) for line in _record_lines(record)])
        for record in records
    ]
    kept: list[Candidate] = []
    already: list[Suppressed] = []
    for candidate in candidates:
        tokens = content_tokens(candidate.text)
        match: str | None = None
        if len(tokens) >= _CAPTURED_MIN_TOKENS:
            for seed_id, line_tokens in corpus:
                for line in line_tokens:
                    if not line:
                        continue
                    if containment(tokens, line) >= _CAPTURED_CONTAINMENT:
                        match = seed_id
                        break
                if match:
                    break
        if match:
            already.append(Suppressed(candidate=candidate, seed_id=match))
        else:
            kept.append(candidate)
    return kept, already


# --- The gleaned marker ------------------------------------------------------


def gleaned_path(seeds_dir: Path) -> Path:
    """Where the record of gleaned transcripts lives."""
    return Path(seeds_dir) / GLEANED_FILE


def read_gleaned(seeds_dir: Path) -> dict[str, datetime]:
    """Session id → when it was gleaned. Empty when nothing has been.

    An unreadable or malformed line is skipped: this file gates a *skip*, and
    losing one entry means re-offering a transcript, which the reviewer can
    see. Refusing to run because a marker file is bent would be the worse
    failure.
    """
    path = gleaned_path(seeds_dir)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    out: dict[str, datetime] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        session = entry.get("session")
        if not isinstance(session, str) or not session:
            continue
        raw = entry.get("gleaned_at")
        stamp = now_utc()
        if isinstance(raw, str):
            try:
                parsed = datetime.fromisoformat(raw)
            except ValueError:
                parsed = stamp
            stamp = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        out[session] = stamp
    return out


def mark_gleaned(
    seeds_dir: Path, session: str, *, candidates: int, created: int = 0
) -> None:
    """Append the record that ``session`` has been gleaned."""
    path = gleaned_path(seeds_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "session": session,
        "gleaned_at": now_utc().isoformat(),
        "candidates": candidates,
        "created": created,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


# --- One transcript, start to finish -----------------------------------------


@dataclass
class GleanReport:
    """What one transcript yielded."""

    session: str
    path: Path
    turns: int
    candidates: list[Candidate]
    suppressed: list[Suppressed]
    created: list[str]
    skipped: bool = False


def glean_transcript(
    path: Path, records: Iterable[SeedRecord], *, session: str | None = None
) -> GleanReport:
    """Parse, extract and diff one transcript. Writes nothing."""
    turns = parse_transcript(path)
    candidates = extract_candidates(turns)
    kept, already = suppress_captured(candidates, records)
    return GleanReport(
        session=session or path.stem,
        path=path,
        turns=len(turns),
        candidates=kept,
        suppressed=already,
        created=[],
    )


#: Candidate kind → the seed type ``--auto`` files it under.
_AUTO_TYPE = {
    "question": "question",
    "decision": "decision",
    "chain": "decision",
    "measurement": "exploration",
    "clarification": "idea",
    "note": "idea",
}

_TITLE_LIMIT = 90


def _auto_title(candidate: Candidate) -> str:
    """A one-line title for an auto-filed seed.

    Truncated on a word boundary and never left as a bare path or URL, both of
    which ``seeds check`` correctly refuses as titles.
    """
    text = " ".join(candidate.text.split())
    if len(text) > _TITLE_LIMIT:
        text = text[:_TITLE_LIMIT].rsplit(" ", 1)[0] + "…"
    if " " not in text:
        text = f"gleaned: {text}"
    return text


def auto_create(
    store: Store, report: GleanReport, *, extra_tags: Sequence[str] = ()
) -> list[str]:
    """File every candidate as a seed, tagged so the pass can be undone.

    ``--auto`` is an opt-in for bulk historical passes, and @aguynamedryan's
    condition on it (2026-09-01) is that what it created stays distinguishable
    afterwards: ``seeds list --tag auto-gleaned`` is the audit, and the whole
    pass can be reverted without hand-sorting it out of a 300-file corpus.
    """
    created: list[str] = []
    for candidate in report.candidates:
        seed_id = store.next_id(seed_text=candidate.text)
        body = (
            f"{candidate.text}\n\n"
            f"Gleaned from session {report.session}, turn {candidate.turn} "
            f"({candidate.speaker}). Signals: "
            f"{', '.join(candidate.signals) or 'none'}."
        )
        record = new_record(
            seed_id,
            _auto_title(candidate),
            body=body,
            seed_type=_AUTO_TYPE.get(candidate.kind, "idea"),
            tags=[AUTO_TAG, *extra_tags],
            status=SeedStatus.CAPTURED,
        )
        store.create(record)
        created.append(seed_id)
    report.created = created
    return created


# --- Rendering ---------------------------------------------------------------

_KIND_ORDER = ("chain", "decision", "question", "clarification", "measurement", "note")


def format_report(report: GleanReport, *, show_suppressed: bool = True) -> str:
    """The compact candidate list. Never the transcript.

    Grouped by kind rather than by turn, because the reviewer's question is
    "what decisions came out of this?", not "what happened at turn 112". The
    turn number is still on every line, so anything can be looked up.
    """
    out: list[str] = []
    header = (
        f"seeds glean: session {report.session} — {report.turns} turn(s), "
        f"{len(report.candidates)} candidate(s)"
    )
    if report.suppressed:
        header += f", {len(report.suppressed)} already captured"
    out.append(header + ".")

    by_kind: dict[str, list[Candidate]] = {}
    for candidate in report.candidates:
        by_kind.setdefault(candidate.kind, []).append(candidate)
    for kind in _KIND_ORDER:
        group = by_kind.get(kind)
        if not group:
            continue
        out.append("")
        out.append(f"{kind} ({len(group)})")
        for candidate in group:
            out.append(f"  turn {candidate.turn} · {candidate.speaker}")
            out.append(f"    {candidate.text}")

    if show_suppressed and report.suppressed:
        out.append("")
        out.append(f"already captured ({len(report.suppressed)})")
        for item in report.suppressed:
            out.append(
                f"  turn {item.candidate.turn} ≈ {item.seed_id}: "
                f"{_clip(item.candidate.text)}"
            )

    if report.created:
        out.append("")
        out.append(
            f"created {len(report.created)} seed(s), tagged {AUTO_TAG!r}: "
            f"{', '.join(report.created)}"
        )
    return "\n".join(out)


def _clip(text: str, limit: int = 70) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"
