"""Tests for ``seeds glean`` (bead seeds-3l4).

Every transcript here is hand-built and every expected candidate list was
worked out by hand. Nothing in this file reads the real ``~/.claude`` or this
project's own ``.seeds/``: the fixture home is a temp directory the test
creates, and :func:`seeds.glean._home` is redirected at it.

The controls that matter:

* ``test_resolution_does_not_guess_by_modification_time`` — a *newer*
  transcript sits beside the one the environment names, and the named one must
  still win. That is the whole reason session resolution reads
  ``$CLAUDE_CODE_SESSION_ID`` instead of picking the freshest file.
* ``test_markers_are_a_signal_not_a_requirement`` — an unannotated decision is
  still found. A detector that only sees ``Decision:`` would score perfectly on
  annotated transcripts and be blind on every transcript that needs it.
* ``test_the_report_never_carries_tool_output`` — the point of the verb is that
  the consumer gets candidates, not 502KB of tool results.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from seeds.cli import main
from seeds.glean import (
    AUTO_TAG,
    GLEANED_FILE,
    Candidate,
    GleanError,
    extract_candidates,
    format_report,
    glean_transcript,
    list_transcripts,
    mark_gleaned,
    parse_transcript,
    project_slug,
    read_gleaned,
    resolve_session_id,
    suppress_captured,
    transcript_path,
    transcripts_dir,
)
from seeds.models import SeedStatus
from seeds.store import SEEDS_DIR, Store, new_record

SESSION = "4b57e1b1-0c96-4f4c-b19f-55274e7d30da"
OTHER_SESSION = "0369a117-138a-4f0d-a7b6-fda5814a8539"


# --- Fixture transcripts -----------------------------------------------------


def user(text: str, **extra: object) -> dict[str, object]:
    """One user turn, as Claude Code writes it."""
    return {
        "type": "user",
        "message": {"role": "user", "content": text},
        "timestamp": "2026-09-01T12:00:00.000Z",
        **extra,
    }


def assistant(*blocks: dict[str, object], **extra: object) -> dict[str, object]:
    """One assistant turn from explicit content blocks."""
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": list(blocks)},
        "timestamp": "2026-09-01T12:00:01.000Z",
        **extra,
    }


def text_block(text: str) -> dict[str, object]:
    return {"type": "text", "text": text}


def thinking_block(text: str) -> dict[str, object]:
    return {"type": "thinking", "thinking": text}


def tool_use_block(name: str) -> dict[str, object]:
    return {"type": "tool_use", "name": name, "input": {"command": "ls"}}


def tool_result(payload: str) -> dict[str, object]:
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "content": payload}],
        },
        "timestamp": "2026-09-01T12:00:02.000Z",
    }


def write_transcript(path: Path, entries: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8"
    )
    return path


@pytest.fixture
def fake_home(tmp_path):
    """A temp home directory standing in for ``~``. Never the real one."""
    home = tmp_path / "home"
    (home / ".claude" / "projects").mkdir(parents=True)
    return home


@pytest.fixture
def project(tmp_path):
    """A project root with an initialized store."""
    root = tmp_path / "project"
    store = Store(root / ".seeds")
    store.files_dir.mkdir(parents=True)
    store.set_prefix("seeds")
    return root


# --- Session resolution ------------------------------------------------------


def test_project_slug_flattens_the_path_and_keeps_underscores():
    assert project_slug(Path("/a/b.c/d_e")) == "-a-b-c-d_e"
    assert project_slug(Path("/x/code_collector")) == "-x-code_collector"


def test_resolve_session_id_reads_the_environment():
    assert resolve_session_id({"CLAUDE_CODE_SESSION_ID": SESSION}) == SESSION


def test_resolve_session_id_refuses_to_guess_when_unset():
    with pytest.raises(GleanError) as exc:
        resolve_session_id({})
    assert "--session" in str(exc.value)


def test_transcript_path_is_the_session_id_under_the_project_slug(fake_home, project):
    path = transcript_path(SESSION, project, home=fake_home)
    assert path.parent == transcripts_dir(project, home=fake_home)
    assert path.name == f"{SESSION}.jsonl"
    assert project_slug(project) in str(path)


def test_resolution_does_not_guess_by_modification_time(fake_home, project):
    """The named session wins even when another transcript is newer.

    This is the control on the rule the bead states outright: no
    most-recently-modified heuristic. On a host running several agents the
    freshest file in the directory is routinely somebody else's session, and
    gleaning it would be silently wrong.
    """
    directory = transcripts_dir(project, home=fake_home)
    named = write_transcript(directory / f"{SESSION}.jsonl", [user("hello there")])
    newer = write_transcript(
        directory / f"{OTHER_SESSION}.jsonl", [user("a different session entirely")]
    )
    old = datetime.now(UTC) - timedelta(days=3)
    os.utime(named, (old.timestamp(), old.timestamp()))

    resolved = transcript_path(
        resolve_session_id({"CLAUDE_CODE_SESSION_ID": SESSION}), project, home=fake_home
    )
    assert resolved == named
    assert resolved != newer


def test_list_transcripts_is_bounded_by_since(fake_home, project):
    directory = transcripts_dir(project, home=fake_home)
    stale = write_transcript(directory / "aaa.jsonl", [user("old work")])
    fresh = write_transcript(directory / "bbb.jsonl", [user("new work")])
    old = datetime.now(UTC) - timedelta(days=30)
    os.utime(stale, (old.timestamp(), old.timestamp()))

    everything = list_transcripts(project, home=fake_home)
    assert set(everything) == {stale, fresh}

    cutoff = datetime.now(UTC) - timedelta(days=7)
    assert list_transcripts(project, home=fake_home, since=cutoff) == [fresh]


def test_list_transcripts_on_a_project_with_no_history(fake_home, project):
    assert list_transcripts(project, home=fake_home) == []


# --- Parsing -----------------------------------------------------------------


def test_parse_keeps_only_what_a_person_said(tmp_path):
    path = write_transcript(
        tmp_path / "t.jsonl",
        [
            {"type": "mode", "sessionId": SESSION},
            user("We should settle the storage question before anything else."),
            assistant(
                thinking_block("The user probably wants me to search the repo first."),
                text_block("Agreed. I will look at the two proposals."),
                tool_use_block("Bash"),
            ),
            tool_result("total 482\ndrwxr-xr-x 12 ryan ryan 4096 Sep  1 12:00 src"),
            user("a sub-agent said this", isSidechain=True),
            user("harness bookkeeping", isMeta=True),
        ],
    )
    turns = parse_transcript(path)
    assert [turn.speaker for turn in turns] == ["user", "assistant"]
    assert turns[0].index == 1
    assert "storage question" in turns[0].text
    assert turns[1].text == "Agreed. I will look at the two proposals."
    joined = " ".join(turn.text for turn in turns)
    assert "drwxr-xr-x" not in joined
    assert "probably wants me to search" not in joined
    assert "sub-agent" not in joined
    assert "bookkeeping" not in joined


def test_parse_strips_harness_scaffolding(tmp_path):
    path = write_transcript(
        tmp_path / "t.jsonl",
        [
            user(
                "<command-name>/clear</command-name>\n"
                "<command-message>clear</command-message>"
            ),
            user(
                "<system-reminder>ignore me</system-reminder>"
                "Let's go with files-as-truth for the store."
            ),
        ],
    )
    turns = parse_transcript(path)
    assert len(turns) == 1
    assert turns[0].text == "Let's go with files-as-truth for the store."


def test_parse_survives_a_half_written_line(tmp_path):
    path = tmp_path / "t.jsonl"
    path.write_text(
        json.dumps(user("We decided to keep the edge set as the candidate set."))
        + "\n"
        + '{"type": "assistant", "message": {"role"\n',
        encoding="utf-8",
    )
    turns = parse_transcript(path)
    assert len(turns) == 1


def test_parse_names_the_missing_transcript(tmp_path):
    with pytest.raises(GleanError) as exc:
        parse_transcript(tmp_path / "nope.jsonl")
    assert "nope.jsonl" in str(exc.value)


# --- Extraction --------------------------------------------------------------


def _kinds(candidates: list[Candidate]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for candidate in candidates:
        out.setdefault(candidate.kind, []).append(candidate.text)
    return out


def test_extracts_the_five_shapes(tmp_path):
    path = write_transcript(
        tmp_path / "t.jsonl",
        [
            user("Should the candidate set be the edge set or the cross product?"),
            assistant(
                text_block(
                    "Measured this morning: 314 seeds and 692 edges in the corpus."
                )
            ),
            user("Actually, I meant the parent edges too, not just relates-to."),
            user("We will walk the whole edge set, not the cross product."),
        ],
    )
    kinds = _kinds(extract_candidates(parse_transcript(path)))
    assert any("692 edges" in text for text in kinds["measurement"])
    assert any("I meant" in text for text in kinds["clarification"])
    # The question and the decision that answered it fold into one chain, so
    # the deliberation and its outcome are offered together rather than twice.
    assert any(
        "cross product" in text and "→" in text for text in kinds.get("chain", [])
    )


def test_markers_are_a_signal_not_a_requirement(tmp_path):
    """An unannotated decision is found; an annotated aside is found too."""
    path = write_transcript(
        tmp_path / "t.jsonl",
        [
            user("We will store the gleaned marker beside the config file."),
            assistant(
                text_block(
                    "Tangent: the transcript directory name is the flattened cwd."
                )
            ),
        ],
    )
    candidates = extract_candidates(parse_transcript(path))
    kinds = _kinds(candidates)
    unannotated = [text for text in kinds["decision"] if "gleaned marker" in text]
    assert unannotated, "a decision with no marker phrase must still be offered"
    assert not any(
        signal.startswith("marker:")
        for candidate in candidates
        if "gleaned marker" in candidate.text
        for signal in candidate.signals
    )
    tangent = [c for c in candidates if c.text.startswith("Tangent:")]
    assert tangent and "marker:tangent" in tangent[0].signals


def test_a_question_and_its_later_decision_fold_into_one_chain(tmp_path):
    path = write_transcript(
        tmp_path / "t.jsonl",
        [
            user("Where should the gleaned marker for each transcript live?"),
            assistant(text_block("Two options, both durable.")),
            user(
                "We will put the gleaned marker in a small file beside the "
                "config, one line per transcript."
            ),
        ],
    )
    candidates = extract_candidates(parse_transcript(path))
    chains = [c for c in candidates if c.kind == "chain"]
    assert len(chains) == 1
    assert "→" in chains[0].text
    assert "Where should" in chains[0].text
    assert "one line per transcript" in chains[0].text
    # The halves were consumed, so nothing is offered twice.
    assert not any(c.kind in ("question", "decision") for c in candidates)


def test_the_assistant_contributes_findings_not_report_prose(tmp_path):
    """The speaker rule, which is what makes the list compact.

    Assistant prose is a report of work written in the same modal voice a
    decision uses. Measured against this project's own 5.3MB transcript: with
    both speakers classified alike, 251 turns produced 475 candidates and an
    82KB report; with this rule, 96 candidates and 13KB. The assistant still
    contributes what only it has — a figure it went and measured, a line it
    marked, and a question that ends its turn.
    """
    path = write_transcript(
        tmp_path / "t.jsonl",
        [
            assistant(
                text_block(
                    "We will keep the converter idempotent, rather than "
                    "rewriting the tree on every run."
                ),
                text_block("Measured just now: 83 of 306 titles are paths."),
            ),
            assistant(
                text_block("Decision: the edge set is the candidate set."),
                text_block("Which of these do you want to rule on first?"),
            ),
        ],
    )
    kinds = _kinds(extract_candidates(parse_transcript(path)))
    assert "83 of 306" in kinds["measurement"][0]
    assert kinds["decision"] == ["Decision: the edge set is the candidate set."]
    assert kinds["question"] == ["Which of these do you want to rule on first?"]
    assert not any(
        "converter idempotent" in text for group in kinds.values() for text in group
    )


def test_a_figure_alone_is_not_a_discovery(tmp_path):
    """A status line carries figures; it is not a measurement.

    Without this the flavor swamps everything else — "doctor green at 312
    seeds" appears in most assistant turns, and on the real transcript a
    figure-only rule produced 198 of 301 candidates.
    """
    path = write_transcript(
        tmp_path / "t.jsonl",
        [
            assistant(text_block("Committed as 1a3ab55; doctor green at 312 seeds.")),
            assistant(text_block("Verified the run: 747 tests passed, mypy clean.")),
        ],
    )
    kinds = _kinds(extract_candidates(parse_transcript(path)))
    assert kinds.get("measurement") == [
        "Verified the run: 747 tests passed, mypy clean."
    ]


def test_trivia_is_not_a_candidate(tmp_path):
    path = write_transcript(
        tmp_path / "t.jsonl",
        [user("ok?"), assistant(text_block("Sure.")), user("thanks")],
    )
    assert extract_candidates(parse_transcript(path)) == []


# --- The corpus diff ---------------------------------------------------------


def test_a_candidate_the_corpus_already_holds_is_suppressed(project):
    store = Store(project / ".seeds")
    store.create(
        new_record(
            "seeds-aaa",
            "The candidate set is the edge set",
            body=(
                "The candidate set is the edge set and never the cross product, "
                "because contradiction needs two seeds about the same thing."
            ),
        )
    )
    candidates = [
        Candidate(
            kind="decision",
            text="The candidate set is the edge set and never the cross product.",
            turn=3,
            speaker="user",
        ),
        Candidate(
            kind="decision",
            text="Gleaned transcripts are recorded so a repeat run skips them.",
            turn=9,
            speaker="user",
        ),
    ]
    kept, already = suppress_captured(candidates, store.all())
    assert [c.turn for c in kept] == [9]
    assert [(s.candidate.turn, s.seed_id) for s in already] == [(3, "seeds-aaa")]


def test_a_long_body_does_not_swallow_an_unrelated_candidate(project):
    """Containment is per body LINE, not against the whole body as one bag.

    A 300-word seed contains most common words, so scoring a candidate against
    the whole body would suppress nearly anything — which is the failure that
    hides a real gap and leaves nothing on screen to say so.
    """
    store = Store(project / ".seeds")
    store.create(
        new_record(
            "seeds-bbb",
            "A long deliberation",
            body="\n".join(
                f"Line {n} about storage, edges, sessions, transcripts and gleaning."
                for n in range(60)
            ),
        )
    )
    candidate = Candidate(
        kind="decision",
        text="We will tag every seed the automatic pass files, so it can be undone.",
        turn=1,
        speaker="user",
    )
    kept, already = suppress_captured([candidate], store.all())
    assert kept == [candidate]
    assert already == []


# --- The gleaned marker ------------------------------------------------------


def test_the_gleaned_marker_round_trips(project):
    seeds_dir = project / ".seeds"
    assert read_gleaned(seeds_dir) == {}
    mark_gleaned(seeds_dir, SESSION, candidates=4)
    recorded = read_gleaned(seeds_dir)
    assert set(recorded) == {SESSION}
    assert (seeds_dir / GLEANED_FILE).is_file()


def test_a_bent_marker_line_does_not_stop_the_run(project):
    seeds_dir = project / ".seeds"
    (seeds_dir / GLEANED_FILE).write_text(
        "not json\n" + json.dumps({"session": SESSION}) + "\n", encoding="utf-8"
    )
    assert set(read_gleaned(seeds_dir)) == {SESSION}


def test_the_marker_lives_outside_the_corpus(project):
    """Nothing glean writes may land where the corpus scan will read it."""
    store = Store(project / ".seeds")
    mark_gleaned(store.seeds_dir, SESSION, candidates=1)
    assert store.all() == []
    assert not (store.files_dir / GLEANED_FILE).exists()


# --- End to end --------------------------------------------------------------


def test_glean_transcript_reports_turns_candidates_and_suppressions(project, tmp_path):
    store = Store(project / ".seeds")
    store.create(
        new_record(
            "seeds-ccc",
            "Session resolution reads the environment variable",
            body="Let's have session resolution read the environment variable.",
        )
    )
    path = write_transcript(
        tmp_path / "t.jsonl",
        [
            user("Let's have session resolution read the environment variable."),
            user("We will emit a compact candidate list, not the file."),
            tool_result("SECRET-TOOL-OUTPUT " + "x" * 400),
        ],
    )
    report = glean_transcript(path, store.all(), session=SESSION)
    assert report.session == SESSION
    assert report.turns == 2
    assert [c.kind for c in report.candidates] == ["decision"]
    assert [s.seed_id for s in report.suppressed] == ["seeds-ccc"]


def test_the_report_never_carries_tool_output(project, tmp_path):
    store = Store(project / ".seeds")
    path = write_transcript(
        tmp_path / "t.jsonl",
        [
            user("We will keep the filtering inside the verb."),
            tool_result("SECRET-TOOL-OUTPUT " + "y" * 2000),
        ],
    )
    rendered = format_report(glean_transcript(path, store.all(), session=SESSION))
    assert "SECRET-TOOL-OUTPUT" not in rendered
    assert len(rendered) < 500


# --- The CLI -----------------------------------------------------------------


@pytest.fixture
def cli_project(monkeypatch):
    """A chdir'd project plus a fake home, with glean pointed at both."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        home = root / "home"
        (home / ".claude" / "projects").mkdir(parents=True)
        work = root / "work"
        store = Store(work / SEEDS_DIR)
        store.files_dir.mkdir(parents=True)
        store.set_prefix("seeds")
        monkeypatch.setattr("seeds.glean._home", lambda: home)
        original = os.getcwd()
        os.chdir(work)
        try:
            yield work, home
        finally:
            os.chdir(original)


def _seed_transcript(work: Path, home: Path, session: str = SESSION) -> Path:
    return write_transcript(
        transcripts_dir(work, home=home) / f"{session}.jsonl",
        [
            user("Should the gleaned marker be committed with the corpus?"),
            user("We will record every gleaned transcript so a repeat run skips it."),
            assistant(
                text_block("Measured on titan: 502KB across 256 turns per session.")
            ),
            tool_result("SECRET-TOOL-OUTPUT " + "z" * 1000),
        ],
    )


def test_glean_cli_reports_candidates_and_records_the_session(cli_project):
    work, home = cli_project
    _seed_transcript(work, home)
    runner = CliRunner()
    result = runner.invoke(
        main, ["glean"], env={"CLAUDE_CODE_SESSION_ID": SESSION}, catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert SESSION in result.output
    assert "SECRET-TOOL-OUTPUT" not in result.output
    assert "Nothing above has been written." in result.output
    assert set(read_gleaned(work / SEEDS_DIR)) == {SESSION}
    # Read-only with respect to the corpus.
    assert Store(work / SEEDS_DIR).all() == []


def test_glean_cli_skips_a_recorded_transcript_until_forced(cli_project):
    work, home = cli_project
    _seed_transcript(work, home)
    runner = CliRunner()
    env = {"CLAUDE_CODE_SESSION_ID": SESSION}
    first = runner.invoke(main, ["glean"], env=env, catch_exceptions=False)
    assert first.exit_code == 0

    second = runner.invoke(main, ["glean"], env=env, catch_exceptions=False)
    assert second.exit_code == 0
    assert "was gleaned" in second.output
    assert "--force" in second.output

    forced = runner.invoke(main, ["glean", "--force"], env=env, catch_exceptions=False)
    assert forced.exit_code == 0
    assert "candidate(s)" in forced.output
    assert "was gleaned" not in forced.output


def test_glean_cli_without_a_session_id_says_what_to_do(cli_project):
    work, home = cli_project
    _seed_transcript(work, home)
    result = CliRunner().invoke(main, ["glean"], env={"CLAUDE_CODE_SESSION_ID": ""})
    assert result.exit_code == 1
    assert "--session" in result.output


def test_glean_cli_named_session(cli_project):
    work, home = cli_project
    _seed_transcript(work, home, session=OTHER_SESSION)
    result = CliRunner().invoke(
        main, ["glean", "--session", OTHER_SESSION], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert OTHER_SESSION in result.output


def test_glean_cli_all_is_bounded_by_since(cli_project):
    work, home = cli_project
    fresh = _seed_transcript(work, home)
    stale = _seed_transcript(work, home, session=OTHER_SESSION)
    old = datetime.now(UTC) - timedelta(days=30)
    os.utime(stale, (old.timestamp(), old.timestamp()))

    result = CliRunner().invoke(
        main, ["glean", "--all", "--since", "7d"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert fresh.stem in result.output
    assert stale.stem not in result.output
    assert "1 transcript(s) gleaned" in result.output


def test_glean_auto_tags_every_seed_it_files(cli_project):
    work, home = cli_project
    _seed_transcript(work, home)
    result = CliRunner().invoke(
        main,
        ["glean", "--auto"],
        env={"CLAUDE_CODE_SESSION_ID": SESSION},
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    store = Store(work / SEEDS_DIR)
    created = store.all()
    assert created, "auto should have filed the candidates"
    assert all(AUTO_TAG in record.tags for record in created)
    assert all(record.status is SeedStatus.CAPTURED for record in created)
    assert store.list_seeds(tag=AUTO_TAG) == store.list_seeds()


def test_glean_rejects_session_with_all(cli_project):
    result = CliRunner().invoke(main, ["glean", "--session", SESSION, "--all"])
    assert result.exit_code == 1
    assert "mutually exclusive" in result.output


def test_glean_is_in_the_help():
    result = CliRunner().invoke(main, ["--help"])
    assert "glean" in result.output
