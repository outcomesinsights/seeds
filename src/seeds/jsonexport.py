"""The machine-readable view of the corpus: JSON on stdout, never a file.

``.seeds/seeds.jsonl`` stops being written on conversion day
(``docs/storage-format.md`` §11), and what it took with it was *availability*,
not speed. Today ``grep`` and a DuckDB ``read_json_auto`` both answer questions
about a repo's seeds with seeds not installed and no parser written by the
caller; 13 repos of cross-project query depend on that. The 35 ms
frontmatter-scan measurement answered a different objection — it proved reading
markdown is fast, not that anything other than ``seeds`` can read it.

So this module is the replacement channel, and its shape is chosen for that
consumer:

**One JSON object per line, to stdout.** A pipe, not a tracked file: nothing to
diverge from the seed files, nothing to keep in sync, nothing to destroy. And
JSONL rather than a single array, deliberately, for three reasons — ``grep`` on
a line still returns a whole record, the output of several repos concatenates
into one valid stream, and DuckDB's ``read_json_auto`` reads it either way, so
the array form would buy nothing and cost both of the others.

**All of it, or none of it.** The whole store is read and validated before the
first byte is written. A stream that stops halfway through, having already
emitted 200 good records, is indistinguishable downstream from a repo that
genuinely has 200 seeds — a silently short answer to a query, which is the exact
failure the strict reader exists to prevent. A refusal here is loud and total.

**Field names carry over from the retired JSONL.** ``content``, ``seed_type``
and the ``relationships`` mappings keep the names the pre-0.7 export used, so
the queries written against that file keep running. ``parent`` and
``converted_at`` are new because the seed files carry them and the old records
did not. ``format_version`` is *not* emitted: this is a derived stream off a
frozen format (§8), and a version discriminator on it would be a promise to
keep versioning something that has no versions.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from seeds.seedfile import (
    FILE_SUFFIX,
    SeedFileError,
    SeedRecord,
    is_valid_id,
    read_seed_file,
    seed_files_dir,
)


class ExportError(Exception):
    """The corpus could not be exported, so nothing was written.

    Raised before any output, never during it — see the module docstring on why
    a partial stream is worse than no stream.
    """


def _stamp(value: datetime | None) -> str | None:
    """An ISO 8601 timestamp, or ``None``. Never a bare date, never naive."""
    return None if value is None else value.isoformat()


def record_to_dict(record: SeedRecord) -> dict[str, Any]:
    """One seed as the JSON object the pipe emits.

    Key order is the emission order and is fixed for the same reason the
    frontmatter's is (§3): it is not semantic, but a stable one makes a diff of
    two runs readable. A consumer must not depend on it.
    """
    return {
        "id": record.id,
        "title": record.title,
        "content": record.body,
        "status": record.status.value,
        "seed_type": record.seed_type,
        "parent": record.parent,
        "tags": list(record.tags),
        "created_at": _stamp(record.created_at),
        "updated_at": _stamp(record.updated_at),
        "resolved_at": _stamp(record.resolved_at),
        "resolution": record.resolution,
        "converted_at": _stamp(record.converted_at),
        "relationships": [
            {
                "target_id": edge.target_id,
                "rel_type": edge.rel_type.value,
                "created_at": _stamp(edge.created_at),
            }
            for edge in record.relationships
        ],
    }


def read_corpus(seeds_dir: Path) -> list[SeedRecord]:
    """Every seed in the store under ``seeds_dir``, in id order.

    Strict in both directions ``seeds check`` is: a file the reader refuses and
    a filename that is not an id both raise :class:`ExportError` rather than
    being skipped. Skipping either would drop a seed out of the answer to a
    query with nothing on stdout to say so.

    Sorted by id so two runs of an unchanged store produce byte-identical
    output, which is what lets a caller diff them.
    """
    files_dir = seed_files_dir(seeds_dir)
    if not files_dir.is_dir():
        raise ExportError(
            f"no seed-file store at {files_dir} -- 'seeds export' reads "
            f"{files_dir.name}/, not the database"
        )

    records: list[SeedRecord] = []
    for path in sorted(files_dir.glob(f"*{FILE_SUFFIX}")):
        stem = path.name[: -len(FILE_SUFFIX)]
        if not is_valid_id(stem):
            raise ExportError(
                f"{path}: filename stem {stem!r} is not a valid seed id; "
                f"run 'seeds check' -- nothing was exported"
            )
        try:
            records.append(read_seed_file(path))
        except SeedFileError as exc:
            raise ExportError(
                f"{exc}\nrun 'seeds check' for every such file at once -- "
                f"nothing was exported"
            ) from exc

    records.sort(key=lambda record: record.id)
    return records


def iter_json_lines(records: list[SeedRecord]) -> Iterator[str]:
    """``records`` as JSONL text, one newline-terminated line each.

    ``ensure_ascii=False`` because seed bodies are full of em dashes and
    typographic quotes, and escaping them turns a greppable line into one no
    human search matches.
    """
    for record in records:
        yield json.dumps(record_to_dict(record), ensure_ascii=False) + "\n"


def export_json(seeds_dir: Path, stream: TextIO) -> int:
    """Write the whole corpus to ``stream`` as JSONL; return the record count.

    Creates no file, here or anywhere: the stream is the deliverable.
    """
    records = read_corpus(seeds_dir)
    for line in iter_json_lines(records):
        stream.write(line)
    return len(records)
