"""The store every command reads and writes: ``.seeds/seeds/<id>.md``.

There is one store now. :mod:`seeds.seedfile` owns the file format — it is the
only parser and the only writer, and nothing here duplicates a byte of it. What
this module adds is the *set* operations a CLI verb needs and a single file
cannot answer: list with filters, children, blocking, both-ended linking, the
project prefix, and search.

Three properties are deliberate and worth not undoing:

**A read is a file read.** :meth:`Store.get` computes the path by string
concatenation and reads one file (``docs/storage-format.md`` §1.1). It does not
scan the directory first. Only the questions that are genuinely about the whole
corpus — ``list``, ``blocked``, ``search`` — pay for the whole corpus.

**The corpus scan is memoized per process, and nothing more.** A ``seeds list``
over 300 seeds asks "is this blocked?" 300 times, and each answer needs the
children; without a cache that is a hundred thousand file reads. The cache lives
for one command invocation, is never written anywhere, and is invalidated by
every write. It is not an index (§8): nothing durable is derived, so there is
nothing that can disagree with the files.

**The prefix comes from ``.seeds/config.yaml`` and nowhere else** (§9). Not from
frontmatter — it is a property of the project, and 312 copies of one value would
only drift. Not from filenames — a repo with no seeds yet still has to know what
to name its first one.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from seeds.idgen import (
    DEFAULT_MAX_COLLISION_PROB,
    DEFAULT_MAX_HASH_LENGTH,
    DEFAULT_MIN_HASH_LENGTH,
    compute_adaptive_length,
    generate_hash_id,
    is_hash_suffix,
)
from seeds.models import (
    DEFAULT_PREFIX,
    RelationType,
    SeedStatus,
    is_valid_prefix,
    iter_id_ref_snippets,
    now_utc,
    rewrite_id_refs,
)
from seeds.seedfile import (
    FILE_SUFFIX,
    SeedEdge,
    SeedFileError,
    SeedRecord,
    expected_parent,
    inverse_relation,
    is_valid_id,
    path_for_id,
    read_seed_file,
    seed_files_dir,
    write_seed,
)

# Allow override via environment variable for testing/development.
SEEDS_DIR = os.environ.get("SEEDS_DIR", ".seeds")

CONFIG_FILE = "config.yaml"
"""Repo-level settings, tracked, alongside ``seeds/`` (§9)."""

PREFIX_KEY = "prefix"

TERMINAL_STATUSES = (SeedStatus.RESOLVED, SeedStatus.ABANDONED)


class StoreError(Exception):
    """The store could not answer, and the caller must not proceed."""


@dataclass(frozen=True)
class BodyRefChange:
    """One id reference rewritten inside a seed's own text."""

    seed_id: str
    field: str  # "title" | "body" | "resolution"
    old_snippet: str
    new_snippet: str


def find_seeds_dir(start: Path | None = None) -> Path | None:
    """The nearest ``.seeds`` directory at or above ``start`` (default: cwd)."""
    current = Path.cwd() if start is None else Path(start)
    while True:
        seeds_dir = current / SEEDS_DIR
        if seeds_dir.is_dir():
            return seeds_dir
        parent = current.parent
        if parent == current:
            return None
        current = parent


# --- Repo configuration (§9) -------------------------------------------------


def config_path(seeds_dir: Path) -> Path:
    """Where the repo-level settings live."""
    return Path(seeds_dir) / CONFIG_FILE


def read_config(seeds_dir: Path) -> dict[str, str]:
    """Parse ``.seeds/config.yaml`` into a flat mapping of strings.

    Deliberately not a YAML library: the file is a handful of ``key: value``
    lines, seeds has exactly one runtime dependency, and taking on a parser to
    read ``prefix: seeds`` would be the largest thing in the dependency tree.
    A line that is blank, a comment, or has no colon is skipped rather than
    refused — this is settings, not the seed format, and strictness here would
    turn a stray line into an unusable repo.
    """
    path = config_path(seeds_dir)
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        values[key.strip()] = value.strip().strip("'\"")
    return values


def write_prefix(seeds_dir: Path, prefix: str) -> None:
    """Record ``prefix`` in ``.seeds/config.yaml``, preserving other settings."""
    if not is_valid_prefix(prefix):
        raise StoreError(
            f"Invalid prefix {prefix!r}: must start with a lowercase letter "
            "and contain only lowercase letters, digits, and hyphens."
        )
    values = read_config(seeds_dir)
    values[PREFIX_KEY] = prefix
    path = config_path(seeds_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{key}: {value}\n" for key, value in values.items())
    path.write_text(body, encoding="utf-8")


def get_prefix(seeds_dir: Path) -> str:
    """The project prefix, or :data:`DEFAULT_PREFIX` when none is configured."""
    value = read_config(seeds_dir).get(PREFIX_KEY)
    if value and is_valid_prefix(value):
        return value
    return DEFAULT_PREFIX


def has_prefix_configured(seeds_dir: Path) -> bool:
    """Whether ``.seeds/config.yaml`` carries an explicit, valid prefix."""
    value = read_config(seeds_dir).get(PREFIX_KEY)
    return value is not None and is_valid_prefix(value)


# --- The store ---------------------------------------------------------------


class Store:
    """Every seed in one ``.seeds`` directory, read and written as files."""

    def __init__(self, seeds_dir: Path) -> None:
        self.seeds_dir = Path(seeds_dir)
        self._corpus: dict[str, SeedRecord] | None = None

    # -- Layout -------------------------------------------------------------

    @property
    def files_dir(self) -> Path:
        """The directory holding the seed files."""
        return seed_files_dir(self.seeds_dir)

    def is_initialized(self) -> bool:
        """Whether this directory holds a seed-file store."""
        return self.files_dir.is_dir()

    def path_for(self, seed_id: str) -> Path:
        """The file ``seed_id`` lives in."""
        return path_for_id(self.seeds_dir, seed_id)

    # -- Prefix -------------------------------------------------------------

    def get_prefix(self) -> str:
        """The project prefix (§9)."""
        return get_prefix(self.seeds_dir)

    def has_prefix_configured(self) -> bool:
        """Whether the prefix is explicitly recorded rather than defaulted."""
        return has_prefix_configured(self.seeds_dir)

    def set_prefix(self, prefix: str) -> None:
        """Record the project prefix. Renames no ids — see :meth:`rename_prefix`."""
        write_prefix(self.seeds_dir, prefix)

    # -- Reading ------------------------------------------------------------

    def invalidate(self) -> None:
        """Drop the memoized corpus. Every write calls this."""
        self._corpus = None

    def get(self, seed_id: str) -> SeedRecord | None:
        """One seed, or ``None`` when no file carries that id.

        One path computation and one file read (§1.1) when the corpus has not
        already been loaded for some other reason.
        """
        if self._corpus is not None:
            return self._corpus.get(seed_id)
        if not is_valid_id(seed_id):
            return None
        path = self.path_for(seed_id)
        if not path.is_file():
            return None
        return read_seed_file(path)

    def exists(self, seed_id: str) -> bool:
        """Whether a seed with this id is in the store."""
        if self._corpus is not None:
            return seed_id in self._corpus
        return is_valid_id(seed_id) and self.path_for(seed_id).is_file()

    def records(self) -> dict[str, SeedRecord]:
        """The whole corpus, by id, read once per process.

        Strict in both directions ``seeds check`` is: a filename that is not an
        id and a file the reader refuses both raise rather than being skipped.
        Skipping either would drop a seed out of the answer to a query with
        nothing on stdout to say so.
        """
        if self._corpus is None:
            if not self.files_dir.is_dir():
                raise StoreError(
                    f"no seed-file store at {self.files_dir}. Run 'seeds init' "
                    f"in a new project, or 'seeds convert' in one that still "
                    f"has {self.seeds_dir}/seeds.jsonl."
                )
            corpus: dict[str, SeedRecord] = {}
            for path in sorted(self.files_dir.glob(f"*{FILE_SUFFIX}")):
                stem = path.name[: -len(FILE_SUFFIX)]
                if not is_valid_id(stem):
                    raise StoreError(
                        f"{path}: filename stem {stem!r} is not a valid seed "
                        f"id; run 'seeds check'"
                    )
                corpus[stem] = read_seed_file(path)
            self._corpus = corpus
        return self._corpus

    def all(self) -> list[SeedRecord]:
        """Every seed, id-sorted."""
        return [self.records()[key] for key in sorted(self.records())]

    def list_seeds(
        self,
        *,
        status: SeedStatus | None = None,
        seed_type: str | None = None,
        tag: str | None = None,
        include_terminal: bool = False,
        since: datetime | None = None,
        sort_by: str = "created",
    ) -> list[SeedRecord]:
        """Seeds matching the filters, newest first.

        ``since`` keeps seeds whose ``updated_at`` is at or after it.
        ``sort_by`` is ``'created'`` or ``'updated'``; both descend.
        """
        if sort_by not in ("created", "updated"):
            raise ValueError(f"sort_by must be 'created' or 'updated', got {sort_by!r}")
        out: list[SeedRecord] = []
        for record in self.records().values():
            if status is not None:
                if record.status is not status:
                    continue
            elif not include_terminal and record.status in TERMINAL_STATUSES:
                continue
            if seed_type is not None and record.seed_type != seed_type:
                continue
            if tag is not None and tag not in record.tags:
                continue
            if since is not None and record.updated_at < since:
                continue
            out.append(record)
        key = "updated_at" if sort_by == "updated" else "created_at"
        # Id breaks ties so two seeds stamped in the same microsecond -- which
        # a converted corpus is full of -- still list in a stable order.
        out.sort(key=lambda r: (getattr(r, key), r.id), reverse=True)
        return out

    def all_tags(self) -> list[str]:
        """Every tag used anywhere, sorted."""
        tags: set[str] = set()
        for record in self.records().values():
            tags.update(record.tags)
        return sorted(tags)

    # -- Hierarchy ----------------------------------------------------------

    def get_children(self, parent_id: str) -> list[SeedRecord]:
        """Direct children of ``parent_id``, id-sorted.

        Read off the ``parent`` frontmatter field, not off the filenames: a
        glob for ``<id>.*`` also matches grandchildren, and excluding them
        means counting dots, which is parsing structure back out of a name
        (§1.1).
        """
        children = [
            record for record in self.records().values() if record.parent == parent_id
        ]
        children.sort(key=lambda r: r.id)
        return children

    def next_child_id(self, parent_id: str) -> str:
        """The next free ``<parent>.N`` id."""
        highest = 0
        for child in self.get_children(parent_id):
            suffix = child.id.rsplit(".", 1)[-1]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
        return f"{parent_id}.{highest + 1}"

    def next_id(self, prefix: str | None = None, *, seed_text: str = "") -> str:
        """Mint a free top-level id like ``seeds-k3n7``.

        Beads-style adaptive base36: the length scales with the number of
        top-level seeds, and the nonce is bumped until the candidate names no
        existing file. Ids already in use are never reissued.
        """
        if prefix is None:
            prefix = self.get_prefix()
        top_level = sum(1 for seed_id in self.records() if "." not in seed_id)
        length = compute_adaptive_length(
            top_level,
            DEFAULT_MIN_HASH_LENGTH,
            DEFAULT_MAX_HASH_LENGTH,
            DEFAULT_MAX_COLLISION_PROB,
        )
        stamp = time.time_ns()
        for nonce in range(10_000):
            candidate = generate_hash_id(prefix, seed_text, stamp, nonce, length)
            if candidate not in self.records():
                return candidate
        raise StoreError(f"could not mint a free id (prefix={prefix}, length={length})")

    # -- Blocking -----------------------------------------------------------

    def questions_for(self, seed_id: str) -> list[SeedRecord]:
        """The question-seeds asking about ``seed_id``.

        Read off the seed's own ``questioned-by`` edges — the far end of the
        directional ``questions`` type (§5.2) — so this is a read of one file's
        frontmatter rather than a scan for edges pointing here.
        """
        record = self.get(seed_id)
        if record is None:
            return []
        out: list[SeedRecord] = []
        for edge in record.relationships:
            if edge.rel_type is not RelationType.QUESTIONED_BY:
                continue
            question = self.get(edge.target_id)
            if question is not None:
                out.append(question)
        out.sort(key=lambda r: r.created_at)
        return out

    def is_blocked(self, seed_id: str) -> bool:
        """Whether unresolved children or unresolved questions hold this seed."""
        if any(not is_terminal(child) for child in self.get_children(seed_id)):
            return True
        return any(
            not is_terminal(question) for question in self.questions_for(seed_id)
        )

    def blocked(self) -> list[SeedRecord]:
        """Every non-terminal seed that something unresolved is holding."""
        return [
            record
            for record in self.list_seeds(include_terminal=False)
            if self.is_blocked(record.id)
        ]

    # -- Writing ------------------------------------------------------------

    def save(self, record: SeedRecord, *, touch: bool = True) -> Path:
        """Write one seed, atomically, and forget the memoized corpus.

        ``touch`` bumps ``updated_at``, which is what every interactive edit
        wants; pass ``touch=False`` to write a record's timestamps verbatim.
        """
        if touch:
            record.updated_at = now_utc()
        path = write_seed(self.seeds_dir, record)
        if self._corpus is not None:
            self._corpus[record.id] = record
        return path

    def create(self, record: SeedRecord) -> Path:
        """Write a seed that must not already exist."""
        if self.exists(record.id):
            raise StoreError(f"{record.id} already exists")
        return self.save(record, touch=False)

    def delete(self, seed_id: str) -> bool:
        """Remove a seed's file. Returns whether there was one."""
        path = self.path_for(seed_id)
        if not path.is_file():
            return False
        path.unlink()
        if self._corpus is not None:
            self._corpus.pop(seed_id, None)
        return True

    def link(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationType,
        *,
        created_at: datetime | None = None,
    ) -> None:
        """Write one edge at BOTH ends, then re-read both to prove it (§5.1).

        A symmetric type stores itself at the far end; a directional one stores
        its named inverse. The two halves carry the same ``created_at``, which
        is what lets ``seeds check`` pair them.

        Two writes with no transaction can leave a half-edge. That is the trade
        this format makes everywhere — SQLite mitigated it with a transaction,
        files mitigate it with detection — so the confirmation read is not
        belt-and-braces, it is the mitigation.
        """
        stamp = now_utc() if created_at is None else created_at
        source = self.get(source_id)
        target = self.get(target_id)
        if source is None:
            raise StoreError(f"{source_id} not found")
        if target is None:
            raise StoreError(f"{target_id} not found")

        _add_edge(source, SeedEdge(target_id, rel_type, stamp))
        _add_edge(target, SeedEdge(source_id, inverse_relation(rel_type), stamp))
        # updated_at records edits to the seed; adding an edge is one.
        self.save(source)
        self.save(target)

        written_source = read_seed_file(self.path_for(source_id))
        written_target = read_seed_file(self.path_for(target_id))
        if not _has_edge(written_source, target_id, rel_type):
            raise StoreError(
                f"{self.path_for(source_id)}: the edge to {target_id} did not "
                f"survive the write"
            )
        if not _has_edge(written_target, source_id, inverse_relation(rel_type)):
            raise StoreError(
                f"{self.path_for(target_id)}: the far end of the edge to "
                f"{source_id} did not survive the write"
            )

    # -- Search (bead seeds-4co.10) -----------------------------------------

    def search(self, query: str, *, include_terminal: bool = False) -> list[SeedRecord]:
        """Seeds whose file matches ``query``, via ripgrep.

        The status filter is part of the ripgrep pass rather than a Python
        post-filter: ``--files-without-match`` on the ``status:`` line narrows
        the candidate set, and the query then runs over exactly those files.
        Measured on the real corpus at 17 ms across 303 files.

        ``query`` is a ripgrep regular expression, matched case-insensitively
        over the whole file — frontmatter included. What it gives up against
        the FTS5 index it replaces is stemming ("merging" no longer finds
        "merge") and ranking. Recall is not the casualty: on a real query grep
        returned 72 hits to FTS's 77 and found one FTS missed.
        """
        return sorted(
            (
                record
                for record in (
                    self.get(_id_of(path))
                    for path in self._rg_matches(query, include_terminal)
                )
                if record is not None
            ),
            key=lambda record: record.id,
        )

    def _rg_matches(self, query: str, include_terminal: bool) -> list[Path]:
        """Paths whose file matches ``query`` and passes the status filter."""
        if not self.files_dir.is_dir():
            raise StoreError(f"no seed-file store at {self.files_dir}")
        if include_terminal:
            candidates = sorted(self.files_dir.glob(f"*{FILE_SUFFIX}"))
        else:
            terminal = f"{SeedStatus.RESOLVED.value}|{SeedStatus.ABANDONED.value}"
            candidates = _rg(
                "--files-without-match",
                "--glob",
                f"*{FILE_SUFFIX}",
                "-e",
                rf"^status: ({terminal})$",
                "--",
                str(self.files_dir),
            )
        if not candidates:
            # rg with no path arguments searches the working directory, which
            # would answer a question nobody asked. An empty candidate set is
            # an empty result.
            return []
        return _rg(
            "--files-with-matches",
            "-i",
            "-e",
            query,
            "--",
            *(str(path) for path in candidates),
        )

    # -- Bulk edits ---------------------------------------------------------

    def retype(
        self, from_type: str, to_type: str, *, dry_run: bool = False
    ) -> list[str]:
        """Change every seed carrying ``from_type`` to ``to_type``.

        Returns the ids affected, sorted. On a dry run nothing is written and
        the return value reports what *would* change. Both types are arbitrary
        strings — the vocabulary is open — so this is equally the fix for a typo
        and the tool for deliberate vocabulary evolution.
        """
        affected = sorted(
            record.id
            for record in self.records().values()
            if record.seed_type == from_type
        )
        if dry_run:
            return affected
        for seed_id in affected:
            record = self.records()[seed_id]
            record.seed_type = to_type
            self.save(record)
        return affected

    def rename_prefix(
        self,
        new_prefix: str,
        *,
        old_prefix: str | None = None,
        rewrite_bodies: bool = True,
        dry_run: bool = False,
    ) -> tuple[dict[str, str], list[BodyRefChange]]:
        """Rewrite every id carrying ``old_prefix`` to carry ``new_prefix``.

        Renames the files, and with them each record's ``id``, its ``parent``,
        and every ``target_id`` at both ends of every edge. With
        ``rewrite_bodies`` (the default) id references inside ``title``,
        ``body`` and ``resolution`` are rewritten too.

        Both id schemes are renamed — base36 hash ids (``seeds-k3n7``) and the
        grandfathered sequential ones (``seeds-112``) — because they routinely
        coexist and leaving either behind strands seeds under the old prefix.
        An id whose top-level segment is neither (``seeds-experiment``) is left
        alone.

        The rename is not an edit to the deliberation, so ``updated_at`` is
        written verbatim rather than bumped. Bumping it would erase, across the
        whole corpus at once, the ``updated_at == created_at`` test for "never
        edited" (§3).

        Returns ``(id_map, body_changes)``; on a dry run both report what
        *would* change and nothing is written.
        """
        if not is_valid_prefix(new_prefix):
            raise StoreError(
                f"Invalid prefix {new_prefix!r}: must start with a lowercase "
                "letter and contain only lowercase letters, digits, and hyphens."
            )
        if old_prefix is None:
            old_prefix = self.get_prefix()
        if old_prefix == new_prefix:
            if not dry_run:
                self.set_prefix(new_prefix)
            return {}, []

        records = self.records()
        old_lead = f"{old_prefix}-"
        id_map: dict[str, str] = {}
        for seed_id in records:
            top = seed_id.split(".", 1)[0]
            if not top.startswith(old_lead):
                continue
            suffix = top[len(old_lead) :]
            if not (
                suffix.isdigit()
                or is_hash_suffix(
                    suffix, DEFAULT_MIN_HASH_LENGTH, DEFAULT_MAX_HASH_LENGTH
                )
            ):
                continue
            id_map[seed_id] = f"{new_prefix}{seed_id[len(old_prefix) :]}"

        for new_id in id_map.values():
            if new_id in records and new_id not in id_map:
                raise StoreError(
                    f"Renaming {old_prefix!r} to {new_prefix!r} would collide "
                    f"with existing id {new_id!r}. The store has mixed "
                    "prefixes; resolve manually before retrying."
                )

        # A base36 hash is indistinguishable from an English word by shape, so
        # a hash-shaped reference is rewritten only when it names an id that is
        # actually being renamed. Children are judged by their parent.
        known_ids = {seed_id.split(".", 1)[0] for seed_id in id_map}

        body_changes: list[BodyRefChange] = []
        if rewrite_bodies:
            for record in records.values():
                for field_name, original in (
                    ("title", record.title),
                    ("body", record.body),
                    ("resolution", record.resolution),
                ):
                    body_changes.extend(
                        BodyRefChange(record.id, field_name, old_snip, new_snip)
                        for old_snip, new_snip in iter_id_ref_snippets(
                            original,
                            old_prefix,
                            new_prefix,
                            known_ids=known_ids,
                        )
                    )

        if dry_run:
            return id_map, body_changes

        renamed_away = set(id_map)
        for record in list(records.values()):
            if rewrite_bodies:
                record.title = rewrite_id_refs(
                    record.title, old_prefix, new_prefix, known_ids
                )[0]
                record.body = rewrite_id_refs(
                    record.body, old_prefix, new_prefix, known_ids
                )[0]
                record.resolution = rewrite_id_refs(
                    record.resolution, old_prefix, new_prefix, known_ids
                )[0]
            for edge in record.relationships:
                edge.target_id = id_map.get(edge.target_id, edge.target_id)
            moved_to = id_map.get(record.id)
            if moved_to is not None:
                record.id = moved_to
                record.parent = expected_parent(moved_to)

        # Write every record to its new path first, then drop the files whose
        # id moved. Doing it in this order means a kill between the two leaves
        # a duplicate, which ``seeds check`` reports -- not a hole.
        for record in records.values():
            write_seed(self.seeds_dir, record)
        for old_id in renamed_away:
            if old_id not in id_map.values():
                self.path_for(old_id).unlink(missing_ok=True)

        self.set_prefix(new_prefix)
        self.invalidate()
        return id_map, body_changes


def _id_of(path: Path) -> str:
    return path.name[: -len(FILE_SUFFIX)]


def _add_edge(record: SeedRecord, edge: SeedEdge) -> None:
    """Append ``edge`` unless the record already carries that pair."""
    if _has_edge(record, edge.target_id, edge.rel_type):
        return
    record.relationships.append(edge)


def _has_edge(record: SeedRecord, target_id: str, rel_type: RelationType) -> bool:
    return any(
        edge.target_id == target_id and edge.rel_type is rel_type
        for edge in record.relationships
    )


def is_terminal(record: SeedRecord) -> bool:
    """Whether a seed has reached a terminal status."""
    return record.status in TERMINAL_STATUSES


def has_been_edited(record: SeedRecord) -> bool:
    """Whether this seed has been written to since it was created.

    Every edit path bumps ``updated_at`` (:meth:`Store.save`), and a freshly
    created seed mirrors ``created_at`` exactly rather than taking a second
    clock reading, so ``updated_at == created_at`` means "never edited" and is
    a meaningful test (§3).
    """
    return record.updated_at != record.created_at


def relates_to(record: SeedRecord) -> list[str]:
    """The ids this seed carries a ``relates-to`` edge to, in file order."""
    return [
        edge.target_id
        for edge in record.relationships
        if edge.rel_type is RelationType.RELATES_TO
    ]


def questions_asked_about(record: SeedRecord) -> list[str]:
    """For a question-seed, the ids it asks about (its ``questions`` edges)."""
    return [
        edge.target_id
        for edge in record.relationships
        if edge.rel_type is RelationType.QUESTIONS
    ]


def new_record(
    seed_id: str,
    title: str,
    *,
    body: str = "",
    seed_type: str = "idea",
    tags: list[str] | None = None,
    status: SeedStatus = SeedStatus.CAPTURED,
) -> SeedRecord:
    """A brand-new seed, stamped once.

    ``updated_at`` mirrors ``created_at`` rather than taking a second clock
    reading: two ``now_utc()`` calls drift by microseconds, which would make
    every new seed look edited (§3).
    """
    stamp = now_utc()
    return SeedRecord(
        id=seed_id,
        title=title,
        status=status,
        seed_type=seed_type,
        created_at=stamp,
        updated_at=stamp,
        parent=expected_parent(seed_id),
        tags=list(tags or []),
        body=body,
    )


# --- ripgrep -----------------------------------------------------------------

RIPGREP = "rg"


def _rg(*args: str) -> list[Path]:
    """Run ripgrep in file-listing mode; return the paths it named.

    Exit 1 means "no matches", which is an answer and not a failure. Anything
    else -- a bad regex above all -- is raised with ripgrep's own message,
    because a search that silently returned nothing when the pattern was
    malformed is the green-while-broken shape this project refuses everywhere
    else.
    """
    if shutil.which(RIPGREP) is None:
        raise StoreError(
            "'seeds search' needs ripgrep (rg) on PATH; install it, or use "
            "'seeds export --json' and grep the stream."
        )
    proc = subprocess.run(
        [RIPGREP, "--no-messages", "--no-ignore", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 1:
        return []
    if proc.returncode != 0:
        raise StoreError(f"ripgrep failed: {proc.stderr.strip() or proc.returncode}")
    return [Path(line) for line in proc.stdout.splitlines() if line]


__all__ = [
    "CONFIG_FILE",
    "SEEDS_DIR",
    "BodyRefChange",
    "SeedFileError",
    "Store",
    "StoreError",
    "config_path",
    "find_seeds_dir",
    "get_prefix",
    "has_been_edited",
    "has_prefix_configured",
    "is_terminal",
    "new_record",
    "questions_asked_about",
    "read_config",
    "relates_to",
    "write_prefix",
]
