#!/usr/bin/env python3
"""One-off audit: did pre-conversion corruption get baked into a store?

Bead ``seeds-4co.15``. **This is not a feature.** It ships no verb, no ``just``
recipe and no documentation, because the question it asks stops being askable.
The oracle it descends from was "two stores agree and are both wrong, so git is
the third opinion" -- and after conversion there is exactly one store, so that
shape is structurally impossible. @aguynamedryan ruled it on 2026-09-01: run it
once, report per repo, close the bead. The standing coverage already exists and
is not this -- ``seeds check --against-git`` gates the mass-sweep shape,
``body-rewritten-in-place`` gates a single quiet rewrite, and ``seeds history``
reads any one seed's real past.

The question
------------
``seeds-wurl`` proved that both live stores can agree and BOTH be wrong: on
2026-08-31 commit ``4144e8f`` replaced the title of 83 of 305 seeds with a
scratchpad path, identically in SQLite and in the JSONL, and every divergence
check was correctly green for three days. That one was repaired in ``1afc51c``.
The residual question is whether a *different* such sweep is still sitting in
some store, having been carried forward by conversion or by daily use because
nothing ever compared the store against its own history.

What counts as a finding, and what deliberately does not
--------------------------------------------------------
A field legitimately changes constantly, so "differs from an old value" is not
a defect and reporting every historical edit would be worthless. Two signatures
are scored, and only two:

**A sweep of implausible values that survived.** One field rewritten across at
least :data:`SWEEP_FRACTION` of the corpus and at least :data:`SWEEP_MINIMUM`
seeds in a single commit -- the thresholds ``seeds check --against-git`` already
uses -- where the values the sweep introduced are ones
:func:`seeds.check._title_violation` calls not-plausibly-a-title, AND those
values are still what the store holds today. The plausibility tier is imported
rather than reimplemented on purpose: a second copy of the rule is a second
thing to be wrong.

**A value the current store holds that is not plausible.** The same tier, run
over today's store. Cheap, and it is the direct question.

Everything else is reported as CONTEXT, not as a finding, and the distinction
is load-bearing. A mass sweep of *plausible* values is what a legitimate bulk
edit looks like -- an attribution pass, a retype, a prefix rename -- so each is
listed with its commit subject for a human to read against, and none of them
moves a repo's verdict. Manufacturing a threshold that turned those into
findings is exactly the "green while broken" inversion this project keeps
naming, in the other direction.

**What this CANNOT see.** A body quietly corrupted into plausible-looking prose
is indistinguishable, by any automatic rule, from a body someone edited. There
is no detector here for it and there should not be a pretend one. The honest
scope of this audit is: values that are self-evidently wrong, and values that
changed without the commit accounting for them.

The walk
--------
:mod:`seeds.githistory` already materializes the JSONL at each commit that
touched it; this reuses it rather than writing a third git walker. For the one
converted repo the current state is read from the seed files; for the rest it
is the working ``.seeds/seeds.jsonl``. Both project through
:func:`seeds.jsonexport.record_to_dict`'s key names, which is what makes one
comparison possible across the boundary.

**Read-only, everywhere.** Every ``.seeds/`` under ``~/projects/outins`` is
real deliberation. This process only ever runs ``git log`` and ``git show`` and
opens files for reading.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from seeds.check import _title_violation
from seeds.githistory import Commit, GitUnavailable, path_commits, repo_root, show_file
from seeds.jsonexport import record_to_dict
from seeds.legacy import JSONL_FILE
from seeds.seedfile import (
    FILE_SUFFIX,
    SeedFileError,
    parse_seed_file,
    seed_files_dir,
)

DEFAULT_ROOT = Path.home() / "projects" / "outins"

# The thresholds `seeds check --against-git` gates on, reused so the audit and
# the standing gate cannot disagree about what "a sweep" is.
SWEEP_FRACTION = 0.20
SWEEP_MINIMUM = 10

# Compared only where both revisions carry the key. A field that did not exist
# in the older format cannot have been corrupted between the two, and treating
# its arrival as a change would report every format bump as a corpus-wide
# rewrite -- the retired JSONL grew `resolution`, `relationships` (from
# `related_to`) and `parent` over its life. Schema movement is reported on its
# own line instead.
FIELDS = (
    "title",
    "content",
    "status",
    "seed_type",
    "tags",
    "created_at",
    "updated_at",
    "resolved_at",
    "resolution",
    "parent",
    "relationships",
)

Record = dict[str, Any]
State = dict[str, Record]


def norm(record: Record, name: str) -> str | None:
    """``record``'s ``name`` as a stable string, or ``None`` when absent.

    ``tags`` and ``relationships`` are order-insensitive for the same reason
    ``check._field_value`` makes them so: a reordered list is the same set, and
    counting a reorder as a rewrite would report a mass change for a no-op.
    """
    if name not in record:
        return None
    value = record[name]
    if name == "tags" and isinstance(value, list):
        value = sorted(str(item) for item in value)
    if name == "relationships" and isinstance(value, list):
        value = sorted(json.dumps(item, sort_keys=True, default=str) for item in value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def implausible(record: Record) -> tuple[str, str] | None:
    """The plausibility tier's verdict on this record's title."""
    title = record.get("title")
    if not isinstance(title, str):
        return None
    return _title_violation(title)


# --- Reading the two sides ---------------------------------------------------


def jsonl_state(text: str) -> State:
    """Every record in one JSONL blob, keyed by id.

    A line that will not parse is skipped: history is not editable, so a
    finding about a malformed old revision would name no fix.
    """
    out: State = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and isinstance(record.get("id"), str):
            out[record["id"]] = record
    return out


def files_state(files_dir: Path) -> State:
    """Every seed file in a converted store, projected through the JSONL names."""
    out: State = {}
    for path in sorted(files_dir.glob(f"*{FILE_SUFFIX}")):
        try:
            record = parse_seed_file(path, path.read_text(encoding="utf-8"))
        except (SeedFileError, OSError):
            continue
        out[record.id] = record_to_dict(record)
    return out


@dataclass
class Sweep:
    """One field rewritten across a large slice of the corpus in one commit."""

    commit: Commit
    name: str
    changed: list[str]
    total: int
    implausible_ids: list[str]
    surviving: list[str]

    @property
    def fraction(self) -> float:
        return len(self.changed) / self.total

    @property
    def verdict(self) -> str:
        if not self.implausible_ids:
            return "CONTEXT (values are plausible; read the subject)"
        if self.surviving:
            return f"BAKED IN ({len(self.surviving)} still in the store)"
        return "REPAIRED (none of the swept values survive)"


@dataclass
class QuietRewrite:
    """A body that moved while ``updated_at`` did not."""

    commit: Commit
    seed_ids: list[str]
    surviving: list[str]


@dataclass
class RepoReport:
    name: str
    path: Path
    status: str = "audited"
    detail: str = ""
    converted: bool = False
    history_commits: int = 0
    first_date: str = ""
    corpus_now: int = 0
    corpus_last_history: int = 0
    sweeps: list[Sweep] = field(default_factory=list)
    deletions: list[tuple[Commit, int, int]] = field(default_factory=list)
    schema_moves: list[tuple[Commit, str]] = field(default_factory=list)
    quiet: list[QuietRewrite] = field(default_factory=list)
    bad_now: list[tuple[str, str, str]] = field(default_factory=list)
    emptied: list[str] = field(default_factory=list)

    @property
    def findings(self) -> int:
        return len(self.bad_now) + sum(
            1 for sweep in self.sweeps if sweep.verdict.startswith("BAKED IN")
        )

    @property
    def verdict(self) -> str:
        if self.status != "audited":
            return self.status.upper()
        return "CORRUPT" if self.findings else "CLEAN"


# --- The audit ---------------------------------------------------------------


def audit(repo: Path) -> RepoReport:
    report = RepoReport(name=repo.name, path=repo)
    seeds_dir = repo / ".seeds"
    if not seeds_dir.is_dir():
        report.status = "no-store"
        report.detail = "no .seeds/ directory"
        return report

    try:
        root = repo_root(seeds_dir)
    except (GitUnavailable, ValueError) as exc:
        report.status = "not-auditable"
        report.detail = f"git could not answer: {exc}"
        return report

    jsonl_rel = (seeds_dir / JSONL_FILE).resolve().relative_to(root).as_posix()
    commits = path_commits(root, jsonl_rel)
    if not commits:
        report.status = "not-auditable"
        report.detail = (
            f"nothing in this repository's history touches {jsonl_rel}; the "
            f"store has no committed past to be the third opinion"
        )
        return report

    files_dir = seed_files_dir(seeds_dir)
    report.converted = files_dir.is_dir()
    if report.converted:
        current = files_state(files_dir)
    else:
        jsonl = seeds_dir / JSONL_FILE
        current = (
            jsonl_state(jsonl.read_text(encoding="utf-8")) if jsonl.is_file() else {}
        )
    if not current:
        report.status = "not-auditable"
        report.detail = "the current store holds no readable records"
        return report

    report.status = "audited"
    report.history_commits = len(commits)
    report.first_date = commits[0].date
    report.corpus_now = len(current)

    previous: State = {}
    for commit in commits:
        text = show_file(root, commit.sha, jsonl_rel)
        state = jsonl_state(text) if text is not None else {}
        if previous:
            _score(report, commit, previous, state, current)
        previous = state
    report.corpus_last_history = len(previous)

    for seed_id, record in sorted(current.items()):
        bad = implausible(record)
        if bad is not None:
            report.bad_now.append((seed_id, bad[0], str(record.get("title"))))

    return report


def _score(
    report: RepoReport,
    commit: Commit,
    previous: State,
    state: State,
    current: State,
) -> None:
    """Everything one commit-to-commit step contributes to the report."""
    common = sorted(set(previous) & set(state))
    total = len(previous)
    if not total:
        return

    gone = len(set(previous) - set(state))
    if gone >= SWEEP_MINIMUM and gone / total >= SWEEP_FRACTION:
        report.deletions.append((commit, gone, total))

    appeared = set().union(*(set(r) for r in state.values())) if state else set()
    had = set().union(*(set(r) for r in previous.values())) if previous else set()
    moved = (appeared - had) | (had - appeared)
    if moved:
        report.schema_moves.append((commit, ", ".join(sorted(moved))))

    for name in FIELDS:
        changed = [
            seed_id
            for seed_id in common
            if (before := norm(previous[seed_id], name)) is not None
            and (after := norm(state[seed_id], name)) is not None
            and before != after
        ]
        if len(changed) < SWEEP_MINIMUM or len(changed) / total < SWEEP_FRACTION:
            continue
        bad = (
            [seed_id for seed_id in changed if implausible(state[seed_id]) is not None]
            if name == "title"
            else []
        )
        surviving = [
            seed_id
            for seed_id in bad
            if seed_id in current
            and norm(current[seed_id], name) == norm(state[seed_id], name)
        ]
        report.sweeps.append(
            Sweep(
                commit=commit,
                name=name,
                changed=changed,
                total=total,
                implausible_ids=bad,
                surviving=surviving,
            )
        )

    quiet = [
        seed_id
        for seed_id in common
        if norm(previous[seed_id], "content") != norm(state[seed_id], "content")
        and norm(previous[seed_id], "content") is not None
        and norm(state[seed_id], "content") is not None
        and norm(previous[seed_id], "updated_at") is not None
        and norm(previous[seed_id], "updated_at") == norm(state[seed_id], "updated_at")
    ]
    if quiet:
        report.quiet.append(
            QuietRewrite(
                commit=commit,
                seed_ids=quiet,
                surviving=[
                    seed_id
                    for seed_id in quiet
                    if seed_id in current
                    and norm(current[seed_id], "content")
                    == norm(state[seed_id], "content")
                ],
            )
        )

    for seed_id in common:
        before = previous[seed_id].get("content")
        if not isinstance(before, str) or not before.strip():
            continue
        now = current.get(seed_id, {}).get("content")
        if isinstance(now, str) and not now.strip() and seed_id not in report.emptied:
            report.emptied.append(seed_id)


# --- Reporting ---------------------------------------------------------------


def sample(ids: list[str], limit: int = 5) -> str:
    shown = ", ".join(ids[:limit])
    return shown + (", …" if len(ids) > limit else "")


def render(reports: list[RepoReport]) -> Iterator[str]:
    yield "seeds-4co.15 — conversion-era audit: store vs. its own git history"
    yield f"ran {datetime.now().astimezone().isoformat(timespec='seconds')}"
    yield ""
    yield "A FINDING is an implausible value the store holds now, or a sweep of"
    yield "implausible values that survived. A sweep of plausible values is CONTEXT:"
    yield "it is what a legitimate bulk edit looks like, and no automatic rule"
    yield "separates it from a corrupting one — read its subject."
    yield ""

    for report in reports:
        yield f"═══ {report.name}  [{report.verdict}]"
        if report.status != "audited":
            yield f"    {report.detail}"
            yield ""
            continue
        store = (
            f"{report.corpus_now} seed files (converted)"
            if report.converted
            else f"{report.corpus_now} JSONL records (unconverted)"
        )
        yield (
            f"    history: {report.history_commits} commits touching "
            f".seeds/{JSONL_FILE}, from {report.first_date}; "
            f"{report.corpus_last_history} seeds at its last revision"
        )
        yield f"    now:     {store}"

        yield f"    implausible values in the store NOW: {len(report.bad_now)}"
        for seed_id, code, title in report.bad_now:
            yield f"      ✗ {seed_id}  {code}: {title!r}"

        yield f"    mass sweeps in history: {len(report.sweeps)}"
        for sweep in report.sweeps:
            yield (
                f"      {sweep.commit.sha[:7]} {sweep.commit.date} "
                f"{sweep.commit.author}  {sweep.name}: "
                f"{len(sweep.changed)}/{sweep.total} "
                f"({100 * sweep.fraction:.0f}%), "
                f"implausible={len(sweep.implausible_ids)}, "
                f"surviving={len(sweep.surviving)}"
            )
            yield f"        subject: {sweep.commit.subject}"
            yield f"        verdict: {sweep.verdict}"
            if sweep.implausible_ids:
                yield f"        ids: {sample(sweep.implausible_ids)}"

        if report.deletions:
            yield f"    mass deletions in history: {len(report.deletions)}"
            for commit, gone, total in report.deletions:
                yield (
                    f"      {commit.sha[:7]} {commit.date}  {gone}/{total} seeds "
                    f"removed — {commit.subject}"
                )

        quiet_total = sum(len(item.seed_ids) for item in report.quiet)
        surviving = sum(len(item.surviving) for item in report.quiet)
        yield (
            f"    bodies moved with updated_at frozen: {quiet_total} across "
            f"{len(report.quiet)} commits ({surviving} of those bodies survive "
            f"into the current store)"
        )
        for item in report.quiet:
            yield (
                f"      {item.commit.sha[:7]} {item.commit.date}  "
                f"{len(item.seed_ids)} seeds ({len(item.surviving)} surviving) "
                f"— {item.commit.subject}"
            )
            yield f"        ids: {sample(item.seed_ids)}"

        yield (
            f"    bodies non-empty in history and empty now: "
            f"{len(report.emptied)}"
            + (f" — {sample(report.emptied)}" if report.emptied else "")
        )
        if report.schema_moves:
            yield f"    format changes (keys added/removed): {len(report.schema_moves)}"
            for commit, keys in report.schema_moves:
                yield f"      {commit.sha[:7]} {commit.date}  {keys}"
        yield ""

    audited = [r for r in reports if r.status == "audited"]
    corrupt = [r for r in audited if r.verdict == "CORRUPT"]
    yield "═══ SUMMARY"
    yield f"    audited:       {len(audited)} of {len(reports)} repos"
    for report in reports:
        if report.status != "audited":
            yield f"    not audited:   {report.name} — {report.detail}"
    yield f"    corrupt:       {len(corrupt)}"
    for report in corrupt:
        yield f"      {report.name}: {report.findings} findings"


def repos(root: Path) -> list[Path]:
    """Every project under ``root`` holding a store.

    Dot-prefixed directories are skipped: ``~/projects/outins`` carries
    ``.backup-<repo>-<stamp>`` copies of whole checkouts, and auditing one
    would report a snapshot of another repo under its own name.
    """
    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir()
        and not path.name.startswith(".")
        and (path / ".seeds").is_dir()
    )


# --- Proving the detectors can fire -----------------------------------------

_STAMP_A = "2026-08-01T00:00:00+00:00"
_STAMP_B = "2026-08-02T00:00:00+00:00"


def _synthetic(title: str, content: str, updated: str) -> Record:
    return {
        "id": "x",
        "title": title,
        "content": content,
        "status": "captured",
        "updated_at": updated,
    }


def self_check() -> list[str]:
    """Fire every detector on hand-built input, with hand-computed answers.

    A detector that reports zero because it *cannot* report anything is the
    exact inversion this repo keeps naming, and three of the four tiers below
    came back zero on the real corpus. The seeds repo is the fourth's positive
    control -- ``4144e8f`` is a real title sweep of 83 implausible values -- so
    only the other three need a constructed one. Hand-computed: 12 seeds
    changed out of 12, which clears both thresholds; 11 would clear them too;
    9 would not.
    """
    commit = Commit(
        sha="0" * 40, date="2026-08-02", timestamp=0, author="t", subject="s"
    )
    ids = [f"s-{n}" for n in range(12)]
    failures: list[str] = []

    # 1. A sweep of implausible titles that SURVIVES into the current store.
    before = {i: _synthetic("A real title", "body", _STAMP_A) for i in ids}
    after = {i: _synthetic(f"/tmp/scratch/{i}.md", "body", _STAMP_B) for i in ids}
    report = RepoReport(name="synthetic", path=Path("."))
    _score(report, commit, before, after, after)
    sweeps = [s for s in report.sweeps if s.name == "title"]
    if not sweeps or sweeps[0].verdict[:8] != "BAKED IN":
        failures.append(f"surviving implausible sweep not flagged: {sweeps}")
    if len(sweeps) == 1 and len(sweeps[0].implausible_ids) != 12:
        got = len(sweeps[0].implausible_ids)
        failures.append(f"expected 12 implausible, got {got}")

    # …and the same sweep, repaired before today: same history, clean present.
    report = RepoReport(name="synthetic", path=Path("."))
    _score(report, commit, before, after, before)
    sweeps = [s for s in report.sweeps if s.name == "title"]
    if not sweeps or not sweeps[0].verdict.startswith("REPAIRED"):
        failures.append(f"repaired sweep misreported: {sweeps}")

    # 2. Below threshold: 9 of 12 changed is 75%, but the ABSOLUTE minimum is
    #    what a small corpus needs, so drop to 9 of 40 (23%, under 10 seeds).
    wide = [f"s-{n}" for n in range(40)]
    before = {i: _synthetic("A real title", "body", _STAMP_A) for i in wide}
    after = dict(before)
    for i in wide[:9]:
        after[i] = _synthetic(f"/tmp/scratch/{i}.md", "body", _STAMP_B)
    report = RepoReport(name="synthetic", path=Path("."))
    _score(report, commit, before, after, after)
    if report.sweeps:
        failures.append(f"9 of 40 should be under threshold, got {report.sweeps}")

    # 3. A body that moved while updated_at did not.
    before = {i: _synthetic("A real title", "original", _STAMP_A) for i in ids}
    after = {i: _synthetic("A real title", "reformatted", _STAMP_A) for i in ids}
    report = RepoReport(name="synthetic", path=Path("."))
    _score(report, commit, before, after, after)
    if not report.quiet or len(report.quiet[0].seed_ids) != 12:
        failures.append(f"quiet body rewrite not flagged: {report.quiet}")
    if report.quiet and len(report.quiet[0].surviving) != 12:
        failures.append("quiet rewrite survival not counted")
    #    …and NOT flagged when the stamp moved with it.
    after = {i: _synthetic("A real title", "reformatted", _STAMP_B) for i in ids}
    report = RepoReport(name="synthetic", path=Path("."))
    _score(report, commit, before, after, after)
    if report.quiet:
        failures.append("a stamped edit was reported as a quiet rewrite")

    # 4. A body that history holds and the current store has emptied.
    report = RepoReport(name="synthetic", path=Path("."))
    _score(
        report,
        commit,
        before,
        before,
        {i: _synthetic("A real title", "", _STAMP_B) for i in ids},
    )
    if len(report.emptied) != 12:
        failures.append(f"emptied bodies not flagged: {report.emptied}")

    # 5. The plausibility tier, on today's values.
    if implausible(_synthetic("/tmp/x/y.md", "b", _STAMP_A)) is None:
        failures.append("a path title was called plausible")
    if implausible(_synthetic("A real title", "b", _STAMP_A)) is not None:
        failures.append("a real title was called implausible")

    if failures:
        return [f"SELF-CHECK FAILED: {line}" for line in failures]
    return ["self-check: every detector fires on hand-built input"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repos", nargs="*", type=Path)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--log-dir", type=Path, default=Path("claude_stuff"))
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="prove every detector fires on hand-built input, then exit",
    )
    args = parser.parse_args(argv)

    if args.self_check:
        lines = self_check()
        name = "conversion-audit-selfcheck"
    else:
        targets = args.repos or repos(args.root)
        lines = list(render([audit(repo.resolve()) for repo in targets]))
        name = "conversion-audit"
    text = "\n".join(lines)
    print(text)

    # Every run of a diagnostic leaves a dated record, so a later reading can
    # be compared with this one rather than reconstructed from a scrollback.
    args.log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log = args.log_dir / f"{name}-{stamp}.log"
    log.write_text(text + "\n", encoding="utf-8")
    print(f"\nlog: {log}")
    return 1 if any(line.startswith("SELF-CHECK FAILED") for line in lines) else 0


if __name__ == "__main__":
    raise SystemExit(main())
