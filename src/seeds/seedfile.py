"""The single door to ``.seeds/seeds/<id>.md``.

Every command that reads or writes a seed file goes through this module. No
command opens one itself, because the format's guarantees — strict parse,
canonical field order, atomic replace — only hold if there is exactly one
implementation of them.

``docs/storage-format.md`` is normative and this module implements it. Where a
comment below cites a section (§3, §5.2, …) it is citing that document; if the
two disagree the document wins and this module is the bug.

Two rules shape everything here:

**Reads are strict** (§7). A value this module cannot fully understand raises
:class:`SeedFileError` naming the file, the field, and the value. It never
skips a field, coerces a value, or returns a partial record. That is only
survivable because ``seeds check`` names every bad file in one pass, so a
strict read blowing up on the first one is not the operator's only feedback
channel.

**Writes are atomic** (§7). The rendered text goes to a temp file *in the
destination directory* and is then :func:`os.replace`\\ d into position. Same
directory means same filesystem, which is what makes the replace atomic; a
temp file under ``/tmp`` silently degrades to a copy. The real path is never
opened for writing, so a concurrent reader — or a reader running after this
process is killed mid-write — sees the whole old file or the whole new one.

The YAML is parsed and emitted by hand rather than by a library. The format is
a deliberately tiny closed subset (§3, §4): a fixed key set in a fixed order,
block sequences only, no anchors, no multi-document, no flow style. A general
parser would have to be *un*-taught most of what it knows to enforce that — it
happily accepts the flow form this format calls a read error — and it cannot be
made to emit the exact byte layout the converter's idempotence requirement
depends on. Hand-parsing the subset also keeps the runtime dependency set at
``click`` alone.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from seeds.models import RelationType, SeedStatus

# --- Layout (§1) -------------------------------------------------------------

#: The seed-file directory, relative to the ``.seeds`` directory.
SEEDS_SUBDIR = "seeds"

#: Every seed file's suffix.
FILE_SUFFIX = ".md"

#: §1.1. A lowercase prefix, a base36 token (or a grandfathered decimal one),
#: and an optional dotted child path. All-lowercase keeps the filename safe on
#: case-insensitive filesystems.
ID_RE = re.compile(r"^[a-z][a-z0-9-]*-[0-9a-z]+(\.[0-9]+)*$")

# --- Frontmatter shape (§3) --------------------------------------------------

#: Emission order. Not semantic — a reader must not depend on it — but a writer
#: must produce it, so re-writing an unchanged seed is a byte-level no-op.
FIELD_ORDER = (
    "id",
    "title",
    "status",
    "type",
    "parent",
    "created_at",
    "updated_at",
    "resolved_at",
    "resolution",
    "tags",
    "relationships",
    "converted_at",
)

_REQUIRED_FIELDS = ("id", "title", "status", "type", "created_at", "updated_at")

#: The two keys whose value is a block sequence (§4). Every other key in
#: :data:`FIELD_ORDER` holds one scalar; there is no third shape.
_SEQUENCE_FIELDS = frozenset({"tags", "relationships"})

#: §5. The keys of one relationship mapping, in emission order.
EDGE_KEYS = ("target_id", "rel_type", "created_at")

#: §5.2. The closed set of ``rel_type`` values, and the type stored at the far
#: end of each. A symmetric type stores itself; a directional type stores its
#: named inverse. A directional type with no inverse cannot be represented in
#: this format at all, so adding one later means adding its inverse in the same
#: change.
_INVERSE = {
    RelationType.RELATES_TO: RelationType.RELATES_TO,
    RelationType.QUESTIONS: RelationType.QUESTIONED_BY,
    RelationType.QUESTIONED_BY: RelationType.QUESTIONS,
}


def inverse_relation(rel_type: RelationType) -> RelationType:
    """The type stored at the far end of ``rel_type`` (§5.2)."""
    return _INVERSE[rel_type]


# --- Errors ------------------------------------------------------------------


class SeedFileError(Exception):
    """A seed file could not be read, or a record could not be written.

    Always names the file. Field-level failures also name the field and the
    offending value, because "invalid frontmatter" on its own sends the
    operator back to reading the file by eye.
    """


def _fail(
    path: Path | None,
    message: str,
    *,
    field_name: str | None = None,
    value: object | None = None,
    line: int | None = None,
) -> SeedFileError:
    """Build a :class:`SeedFileError` naming file, line, field and value."""
    parts = [str(path) if path is not None else "<record>"]
    if line is not None:
        parts.append(f"line {line}")
    if field_name is not None:
        parts.append(f"field {field_name!r}")
    head = ": ".join(parts)
    tail = ""
    if field_name is not None and value is not None:
        tail = f" (value: {value!r})"
    return SeedFileError(f"{head}: {message}{tail}")


# --- Records -----------------------------------------------------------------


@dataclass
class SeedEdge:
    """One relationship, as stored in a seed file's ``relationships`` (§5).

    ``created_at`` is the *edge's* creation time — not either seed's — and is
    the same value in both files, which is what lets ``seeds check`` pair the
    two ends of one edge.
    """

    target_id: str
    rel_type: RelationType
    created_at: datetime


@dataclass
class SeedRecord:
    """Everything one ``.seeds/seeds/<id>.md`` file holds.

    A file-shaped record rather than :class:`seeds.models.Seed`: the file
    carries ``parent``, its own relationship list, and ``converted_at``, none of
    which ``Seed`` has, and the frontmatter key ``type`` maps to ``seed_type``
    (§3). Owning that translation here is the point — nothing else may guess at
    it.
    """

    id: str
    title: str
    status: SeedStatus
    seed_type: str
    created_at: datetime
    updated_at: datetime
    parent: str | None = None
    resolved_at: datetime | None = None
    resolution: str = ""
    tags: list[str] = field(default_factory=list)
    relationships: list[SeedEdge] = field(default_factory=list)
    converted_at: datetime | None = None
    body: str = ""


# --- Path <-> id (§1.1) ------------------------------------------------------


def is_valid_id(seed_id: str) -> bool:
    """Whether ``seed_id`` matches the id shape a filename may carry (§1.1)."""
    return bool(ID_RE.match(seed_id))


def seed_files_dir(seeds_dir: Path) -> Path:
    """The directory holding seed files, given the ``.seeds`` directory."""
    return Path(seeds_dir) / SEEDS_SUBDIR


def path_for_id(seeds_dir: Path, seed_id: str) -> Path:
    """The file holding ``seed_id``, given the ``.seeds`` directory.

    String concatenation, deliberately: the id is the filename stem verbatim,
    dots included, with no escaping and no per-level nesting. ``seeds show`` is
    therefore one path computation and one file read, and that property is why
    this layout was chosen over every alternative (§1.1).
    """
    if not is_valid_id(seed_id):
        raise _fail(None, "not a valid seed id", field_name="id", value=seed_id)
    return seed_files_dir(seeds_dir) / f"{seed_id}{FILE_SUFFIX}"


def id_for_path(path: Path) -> str:
    """The id a seed file's name carries — the inverse of :func:`path_for_id`."""
    path = Path(path)
    if not path.name.endswith(FILE_SUFFIX):
        raise _fail(path, f"not a seed file (expected a {FILE_SUFFIX} suffix)")
    # Not ``Path.stem``: that strips only the final suffix, which for
    # 'seeds-lcfa.6.1.md' would be right by luck, but slicing says what is
    # meant — the stem is the id verbatim, dotted child path included.
    seed_id = path.name[: -len(FILE_SUFFIX)]
    if not is_valid_id(seed_id):
        raise _fail(
            path, "filename is not a valid seed id", field_name="id", value=seed_id
        )
    return seed_id


def expected_parent(seed_id: str) -> str | None:
    """The ``parent`` a dotted id requires, or ``None`` for a top-level id (§3)."""
    if "." not in seed_id:
        return None
    return seed_id.rsplit(".", 1)[0]


# --- Scalars -----------------------------------------------------------------

# A plain scalar this module is willing to emit unquoted. Conservative on
# purpose: anything another YAML reader might resolve to a non-string, or parse
# as syntax, gets quoted instead.
_PLAIN_SAFE_RE = re.compile(r"^[A-Za-z0-9_/][^\n]*$")

# Plain scalars YAML resolves to something other than a string. A title of
# "42", "true" or "null" must be quoted or it stops being text.
_NON_STRING_PLAIN_RE = re.compile(
    r"""^(?:
        [-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?   # int / float
        |0[xXoObB][0-9a-fA-F_]+               # hex / octal / binary
        |[tT]rue|TRUE|[fF]alse|FALSE
        |[yY]es|YES|[nN]o|NO|[oO]n|ON|[oO]ff|OFF
        |[nN]ull|NULL|~
    )$""",
    re.VERBOSE,
)

# Indicator characters that start a non-plain YAML scalar, plus the flow
# openers the format rejects outright (§4).
_INDICATORS = "-?:,[]{}#&*!|>'\"%@`"


def _encode_scalar(value: str) -> str:
    """Render ``value`` as a YAML scalar this module can read back exactly.

    Plain when it is unambiguously plain, double-quoted otherwise. The
    double-quoted form is produced with :func:`json.dumps`, whose output is a
    valid YAML 1.2 double-quoted scalar; ``ensure_ascii=False`` keeps UTF-8 text
    readable in the file instead of escaping it to ``\\uXXXX``.
    """
    if (
        value
        and value == value.strip()
        and _PLAIN_SAFE_RE.match(value)
        and not _NON_STRING_PLAIN_RE.match(value)
        and ": " not in value
        and " #" not in value
        and not value.endswith(":")
    ):
        return value
    return json.dumps(value, ensure_ascii=False)


def _decode_scalar(
    path: Path | None, field_name: str, raw: str, line: int | None
) -> str:
    """Parse one YAML scalar from the text after ``key: ``.

    Accepts the plain and double-quoted forms this module emits, and nothing
    else. The flow forms get their own message because §4 singles them out.
    """
    if not raw:
        raise _fail(
            path,
            "empty value; an optional field is omitted, never written blank",
            field_name=field_name,
            line=line,
        )
    if raw[0] in "[{":
        raise _fail(
            path,
            "flow style is not part of this format; every multi-value field is "
            "a block sequence",
            field_name=field_name,
            value=raw,
            line=line,
        )
    if raw[0] == '"':
        try:
            decoded = json.loads(raw)
        except ValueError as exc:
            raise _fail(
                path,
                f"malformed double-quoted scalar ({exc})",
                field_name=field_name,
                value=raw,
                line=line,
            ) from exc
        if not isinstance(decoded, str):
            raise _fail(
                path,
                "quoted scalar did not decode to a string",
                field_name=field_name,
                value=raw,
                line=line,
            )
        return decoded
    if raw[0] in _INDICATORS:
        raise _fail(
            path,
            f"scalar starts with the YAML indicator {raw[0]!r}; quote it",
            field_name=field_name,
            value=raw,
            line=line,
        )
    if ": " in raw or raw.endswith(":") or " #" in raw:
        raise _fail(
            path,
            "ambiguous plain scalar; quote it",
            field_name=field_name,
            value=raw,
            line=line,
        )
    if raw != raw.strip():
        raise _fail(
            path,
            "plain scalar has leading or trailing whitespace",
            field_name=field_name,
            value=raw,
            line=line,
        )
    return raw


def _encode_timestamp(value: datetime) -> str:
    """Render a timestamp as §3 requires: timezone-aware, normalized to UTC."""
    return value.astimezone(UTC).isoformat()


def _decode_timestamp(
    path: Path | None, field_name: str, raw: str, line: int | None
) -> datetime:
    """Parse an ISO 8601 timestamp, rejecting naive input (§3).

    The JSONL importer reads a naive timestamp as UTC so that a third-party
    record is not lost. That leniency deliberately does not carry into this
    format — nothing but this module writes it, so a missing offset is a defect
    rather than a foreign convention. A non-UTC offset is unambiguous and is
    normalized here; whether the file's own bytes are canonical is a ``check``
    question, answered by comparing them with :func:`render_seed_file`.
    """
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise _fail(
            path,
            "not an ISO 8601 timestamp",
            field_name=field_name,
            value=raw,
            line=line,
        ) from exc
    if parsed.tzinfo is None:
        raise _fail(
            path,
            "timestamp has no UTC offset; naive timestamps are a read error",
            field_name=field_name,
            value=raw,
            line=line,
        )
    return parsed.astimezone(UTC)


# --- Frontmatter parsing (§2, §3, §4) ----------------------------------------

_KEY_RE = re.compile(r"^([a-z_]+):(?: (.*))?$")
_ITEM_RE = re.compile(r"^  - (.*)$")
_ITEM_CONT_RE = re.compile(r"^    ([a-z_]+): (.*)$")


@dataclass
class _Raw:
    """One undecoded scalar and the file line it sits on."""

    text: str
    line: int


@dataclass
class _Item:
    """One sequence entry: a scalar (``tags``) or a mapping (``relationships``)."""

    line: int
    scalar: _Raw | None = None
    mapping: dict[str, _Raw] | None = None


@dataclass
class _Block:
    """One frontmatter key's raw value: a scalar or a block sequence."""

    line: int
    scalar: _Raw | None = None
    items: list[_Item] | None = None


def _parse_frontmatter(path: Path, lines: list[str], offset: int) -> dict[str, _Block]:
    """Parse the frontmatter block into raw, per-key values.

    Shape only — no field is interpreted here. ``offset`` is the file line
    number of ``lines[0]``, so messages point at the real line.
    """
    values: dict[str, _Block] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        lineno = offset + index
        key_match = _KEY_RE.match(line)
        if not key_match:
            raise _fail(path, f"unparseable frontmatter line {line!r}", line=lineno)
        key, inline = key_match.group(1), key_match.group(2)
        if key in values:
            raise _fail(path, "duplicate key", field_name=key, line=lineno)
        if key not in FIELD_ORDER:
            raise _fail(
                path,
                "unknown frontmatter key; unknown keys are an error, not "
                "something to preserve or ignore",
                field_name=key,
                line=lineno,
            )
        index += 1
        if inline is not None:
            if key in _SEQUENCE_FIELDS:
                raise _fail(
                    path,
                    "must be a block sequence, one value per line",
                    field_name=key,
                    value=inline,
                    line=lineno,
                )
            values[key] = _Block(line=lineno, scalar=_Raw(inline, lineno))
            continue
        if key not in _SEQUENCE_FIELDS:
            raise _fail(path, "missing value", field_name=key, line=lineno)
        items, index = _parse_sequence(path, lines, offset, index, key)
        if not items:
            raise _fail(
                path,
                "empty block sequence; an empty optional field is omitted, not "
                "written out",
                field_name=key,
                line=lineno,
            )
        values[key] = _Block(line=lineno, items=items)
    return values


def _parse_sequence(
    path: Path, lines: list[str], offset: int, index: int, key: str
) -> tuple[list[_Item], int]:
    """Parse the block sequence following ``key:``; return items and next index."""
    items: list[_Item] = []
    while index < len(lines):
        item_match = _ITEM_RE.match(lines[index])
        if not item_match:
            break
        lineno = offset + index
        text = item_match.group(1)
        index += 1
        pair = _KEY_RE.match(text)
        if pair is not None and pair.group(2) is not None:
            mapping = {pair.group(1): _Raw(pair.group(2), lineno)}
            while index < len(lines):
                cont = _ITEM_CONT_RE.match(lines[index])
                if not cont:
                    break
                if cont.group(1) in mapping:
                    raise _fail(
                        path,
                        f"duplicate key {cont.group(1)!r} in a {key} entry",
                        line=offset + index,
                    )
                mapping[cont.group(1)] = _Raw(cont.group(2), offset + index)
                index += 1
            items.append(_Item(line=lineno, mapping=mapping))
        else:
            items.append(_Item(line=lineno, scalar=_Raw(text, lineno)))
    return items, index


# --- Reading -----------------------------------------------------------------


def parse_seed_file(path: Path, text: str) -> SeedRecord:
    """Parse a seed file's text into a :class:`SeedRecord`.

    ``path`` supplies the id/filename agreement check (§3) and every error
    message; the file itself is not read here.
    """
    if not text.startswith("---\n"):
        raise _fail(
            path,
            "file does not open with '---'; byte 0 is the first dash of the "
            "opening delimiter",
        )
    rest = text[4:]
    if rest.startswith("---\n"):
        head, tail = "", rest[3:]
    else:
        end = rest.find("\n---\n")
        if end == -1:
            raise _fail(path, "frontmatter is not closed by a '---' line")
        head, tail = rest[:end], rest[end + 4 :]

    lines = head.split("\n") if head else []
    values = _parse_frontmatter(path, lines, offset=2)

    if not tail.startswith("\n\n"):
        raise _fail(
            path,
            "no blank line between the closing '---' and the body; exactly one "
            "blank line separates them",
        )
    # Any further leading blank lines, and any trailing run, are whitespace this
    # reader understands perfectly well, so they are normalized rather than
    # rejected. Whether the file's bytes are canonical is a ``check`` question,
    # answered by comparing them against :func:`render_seed_file`.
    body = tail.strip("\n")
    if body:
        body += "\n"

    record = _build_record(path, values, body)
    # A malformed marker means the reader cannot tell what is retired, so it is
    # a parse failure rather than something a caller trips over at render time.
    superseded_scopes(body, path=path)
    return record


def _scalar(path: Path, values: dict[str, _Block], key: str) -> tuple[str, int] | None:
    """Decode the scalar stored under ``key``, or ``None`` when absent."""
    block = values.get(key)
    if block is None:
        return None
    if block.scalar is None:
        raise _fail(path, "expected a single value, found a sequence", field_name=key)
    raw = block.scalar
    decoded = _decode_scalar(path, key, raw.text, raw.line)
    if not decoded:
        # §3: absent and empty are the same state, and the format keeps exactly
        # one representation of it. `resolution: ""` is the other one.
        raise _fail(
            path,
            "empty value; an optional field is omitted, never written blank",
            field_name=key,
            line=raw.line,
        )
    return decoded, raw.line


def _build_record(path: Path, values: dict[str, _Block], body: str) -> SeedRecord:
    """Validate raw frontmatter values into a record. Strict throughout (§7)."""
    for key in _REQUIRED_FIELDS:
        if key not in values:
            raise _fail(path, "required frontmatter field is missing", field_name=key)
    seed_id_pair = _scalar(path, values, "id")
    assert seed_id_pair is not None
    seed_id = seed_id_pair[0]
    if not is_valid_id(seed_id):
        raise _fail(path, "not a valid seed id", field_name="id", value=seed_id)
    stem = id_for_path(path)
    if seed_id != stem:
        raise _fail(
            path,
            f"id disagrees with the filename stem {stem!r}; a mismatch is a "
            "violation, not a rename to be inferred",
            field_name="id",
            value=seed_id,
        )

    title_pair = _scalar(path, values, "title")
    assert title_pair is not None
    title = title_pair[0]
    if not title.strip() or "\n" in title:
        raise _fail(
            path, "title must be one non-empty line", field_name="title", value=title
        )

    status_pair = _scalar(path, values, "status")
    assert status_pair is not None
    try:
        status = SeedStatus(status_pair[0])
    except ValueError as exc:
        allowed = ", ".join(s.value for s in SeedStatus)
        raise _fail(
            path,
            f"status is a closed set ({allowed})",
            field_name="status",
            value=status_pair[0],
            line=status_pair[1],
        ) from exc

    type_pair = _scalar(path, values, "type")
    assert type_pair is not None
    seed_type = type_pair[0]
    if not seed_type.strip() or "\n" in seed_type:
        raise _fail(
            path, "type must be one non-empty line", field_name="type", value=seed_type
        )

    parent_pair = _scalar(path, values, "parent")
    parent = parent_pair[0] if parent_pair else None
    wanted_parent = expected_parent(seed_id)
    if parent != wanted_parent:
        if wanted_parent is None:
            raise _fail(
                path,
                "parent is forbidden on a top-level id",
                field_name="parent",
                value=parent,
            )
        raise _fail(
            path,
            f"parent must be {wanted_parent!r}, as the dotted id says",
            field_name="parent",
            value=parent,
        )

    created_pair = _scalar(path, values, "created_at")
    assert created_pair is not None
    created_at = _decode_timestamp(path, "created_at", *created_pair)
    updated_pair = _scalar(path, values, "updated_at")
    assert updated_pair is not None
    updated_at = _decode_timestamp(path, "updated_at", *updated_pair)

    resolved_pair = _scalar(path, values, "resolved_at")
    terminal = status in (SeedStatus.RESOLVED, SeedStatus.ABANDONED)
    if terminal and resolved_pair is None:
        raise _fail(
            path,
            f"resolved_at is required when status is {status.value!r}",
            field_name="resolved_at",
        )
    if not terminal and resolved_pair is not None:
        raise _fail(
            path,
            f"resolved_at is forbidden when status is {status.value!r}",
            field_name="resolved_at",
            value=resolved_pair[0],
        )
    resolved_at = (
        _decode_timestamp(path, "resolved_at", *resolved_pair)
        if resolved_pair is not None
        else None
    )

    converted_pair = _scalar(path, values, "converted_at")
    converted_at = (
        _decode_timestamp(path, "converted_at", *converted_pair)
        if converted_pair is not None
        else None
    )

    resolution_pair = _scalar(path, values, "resolution")

    return SeedRecord(
        id=seed_id,
        title=title,
        status=status,
        seed_type=seed_type,
        created_at=created_at,
        updated_at=updated_at,
        parent=parent,
        resolved_at=resolved_at,
        resolution=resolution_pair[0] if resolution_pair is not None else "",
        tags=_build_tags(path, values),
        relationships=_build_edges(path, values),
        converted_at=converted_at,
        body=body,
    )


def _build_tags(path: Path, values: dict[str, _Block]) -> list[str]:
    block = values.get("tags")
    if block is None:
        return []
    if block.items is None:
        raise _fail(path, "expected a block sequence", field_name="tags")
    tags: list[str] = []
    for item in block.items:
        if item.scalar is None:
            raise _fail(
                path,
                "tags is a sequence of strings, not of mappings",
                field_name="tags",
                line=item.line,
            )
        tag = _decode_scalar(path, "tags", item.scalar.text, item.scalar.line)
        if not tag.strip():
            raise _fail(path, "empty tag", field_name="tags", value=tag, line=item.line)
        tags.append(tag)
    return tags


def _build_edges(path: Path, values: dict[str, _Block]) -> list[SeedEdge]:
    block = values.get("relationships")
    if block is None:
        return []
    if block.items is None:
        raise _fail(path, "expected a block sequence", field_name="relationships")
    edges: list[SeedEdge] = []
    for item in block.items:
        mapping = item.mapping
        if mapping is None:
            raise _fail(
                path,
                "each relationship is a mapping of target_id, rel_type and created_at",
                field_name="relationships",
                line=item.line,
            )
        missing = [key for key in EDGE_KEYS if key not in mapping]
        if missing:
            raise _fail(
                path,
                f"relationship is missing {', '.join(missing)}",
                field_name="relationships",
                line=item.line,
            )
        extra = sorted(key for key in mapping if key not in EDGE_KEYS)
        if extra:
            raise _fail(
                path,
                f"unknown relationship key(s): {', '.join(extra)}",
                field_name="relationships",
                line=item.line,
            )
        target = mapping["target_id"]
        target_id = _decode_scalar(
            path, "relationships.target_id", target.text, target.line
        )
        if not is_valid_id(target_id):
            raise _fail(
                path,
                "not a valid seed id",
                field_name="relationships.target_id",
                value=target_id,
                line=target.line,
            )
        kind = mapping["rel_type"]
        kind_text = _decode_scalar(path, "relationships.rel_type", kind.text, kind.line)
        try:
            rel_type = RelationType(kind_text)
        except ValueError as exc:
            allowed = ", ".join(t.value for t in RelationType)
            raise _fail(
                path,
                f"rel_type is a closed set ({allowed})",
                field_name="relationships.rel_type",
                value=kind_text,
                line=kind.line,
            ) from exc
        stamp = mapping["created_at"]
        created_at = _decode_timestamp(
            path,
            "relationships.created_at",
            _decode_scalar(path, "relationships.created_at", stamp.text, stamp.line),
            stamp.line,
        )
        edges.append(
            SeedEdge(target_id=target_id, rel_type=rel_type, created_at=created_at)
        )
    return edges


def read_seed_file(path: Path) -> SeedRecord:
    """Read one seed file. Raises :class:`SeedFileError` on anything unclear."""
    path = Path(path)
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise _fail(path, "file starts with a UTF-8 BOM; the format is BOM-less")
    if b"\r\n" in raw:
        raise _fail(path, "file has CRLF line endings; the format is LF-only")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _fail(path, f"file is not valid UTF-8 ({exc})") from exc
    return parse_seed_file(path, text)


def read_seed(seeds_dir: Path, seed_id: str) -> SeedRecord:
    """Read the seed named ``seed_id`` out of the ``.seeds`` directory."""
    return read_seed_file(path_for_id(seeds_dir, seed_id))


# --- Rendering and writing ---------------------------------------------------


def render_seed_file(record: SeedRecord) -> str:
    """Render ``record`` as the canonical bytes of its seed file.

    Validates as it goes, so an invalid record cannot reach the disk. Exposed
    separately from :func:`write_seed_file` so ``seeds check`` can compare a
    file's bytes with the canonical form without writing anything.
    """
    _validate_for_write(record)
    out: list[str] = ["---"]
    out.append(f"id: {_encode_scalar(record.id)}")
    out.append(f"title: {_encode_scalar(record.title)}")
    out.append(f"status: {_encode_scalar(record.status.value)}")
    out.append(f"type: {_encode_scalar(record.seed_type)}")
    if record.parent is not None:
        out.append(f"parent: {_encode_scalar(record.parent)}")
    out.append(f"created_at: {_encode_timestamp(record.created_at)}")
    out.append(f"updated_at: {_encode_timestamp(record.updated_at)}")
    if record.resolved_at is not None:
        out.append(f"resolved_at: {_encode_timestamp(record.resolved_at)}")
    if record.resolution:
        out.append(f"resolution: {_encode_scalar(record.resolution)}")
    if record.tags:
        out.append("tags:")
        out.extend(f"  - {_encode_scalar(tag)}" for tag in record.tags)
    if record.relationships:
        out.append("relationships:")
        for edge in record.relationships:
            out.append(f"  - target_id: {_encode_scalar(edge.target_id)}")
            out.append(f"    rel_type: {_encode_scalar(edge.rel_type.value)}")
            out.append(f"    created_at: {_encode_timestamp(edge.created_at)}")
    if record.converted_at is not None:
        out.append(f"converted_at: {_encode_timestamp(record.converted_at)}")
    out.append("---")
    body = record.body.strip("\n")
    return "\n".join(out) + "\n\n" + (body + "\n" if body else "")


def _validate_for_write(record: SeedRecord) -> None:
    """Reject a record the reader would refuse, before it can reach the disk."""
    if not is_valid_id(record.id):
        raise _fail(None, "not a valid seed id", field_name="id", value=record.id)
    if not record.title.strip() or "\n" in record.title:
        raise _fail(
            None,
            "title must be one non-empty line",
            field_name="title",
            value=record.title,
        )
    if not record.seed_type.strip() or "\n" in record.seed_type:
        raise _fail(
            None,
            "type must be one non-empty line",
            field_name="type",
            value=record.seed_type,
        )
    wanted_parent = expected_parent(record.id)
    if record.parent != wanted_parent:
        raise _fail(
            None,
            f"parent must be {wanted_parent!r}, as the dotted id says",
            field_name="parent",
            value=record.parent,
        )
    for name, stamp in (
        ("created_at", record.created_at),
        ("updated_at", record.updated_at),
    ):
        if stamp.tzinfo is None:
            raise _fail(
                None, "timestamp has no UTC offset", field_name=name, value=stamp
            )
    terminal = record.status in (SeedStatus.RESOLVED, SeedStatus.ABANDONED)
    if terminal and record.resolved_at is None:
        raise _fail(
            None,
            f"resolved_at is required when status is {record.status.value!r}",
            field_name="resolved_at",
        )
    if not terminal and record.resolved_at is not None:
        raise _fail(
            None,
            f"resolved_at is forbidden when status is {record.status.value!r}",
            field_name="resolved_at",
            value=record.resolved_at,
        )
    for tag in record.tags:
        if not tag.strip() or "\n" in tag:
            raise _fail(
                None, "tag must be one non-empty line", field_name="tags", value=tag
            )
    for edge in record.relationships:
        if not is_valid_id(edge.target_id):
            raise _fail(
                None,
                "not a valid seed id",
                field_name="relationships.target_id",
                value=edge.target_id,
            )
        if edge.created_at.tzinfo is None:
            raise _fail(
                None,
                "timestamp has no UTC offset",
                field_name="relationships.created_at",
                value=edge.created_at,
            )
    # A body whose markers will not parse must not reach the disk either.
    superseded_scopes(record.body)


def write_seed_file(path: Path, record: SeedRecord) -> None:
    """Write ``record`` to ``path`` atomically (§7).

    Temp file in the destination directory, then :func:`os.replace`. Same
    directory means same filesystem, which is what makes the replace atomic;
    the real path is never opened for writing, so no reader can ever observe a
    truncated file — including one running after this process is killed
    mid-write.
    """
    path = Path(path)
    stem = id_for_path(path)
    if record.id != stem:
        raise _fail(
            path,
            f"record id does not match the filename stem {stem!r}",
            field_name="id",
            value=record.id,
        )
    text = render_seed_file(record)
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)
    handle, tmp_name = tempfile.mkstemp(
        dir=directory, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def write_seed(seeds_dir: Path, record: SeedRecord) -> Path:
    """Write ``record`` into the ``.seeds`` directory; return the path written."""
    path = path_for_id(seeds_dir, record.id)
    write_seed_file(path, record)
    return path


# --- The supersede marker (§6) -----------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6}) ")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_MARKER_PREFIX = "> [!SUPERSEDED]"
_MARKER_RE = re.compile(r"^> \[!SUPERSEDED\] (\d{4}-\d{2}-\d{2}) —(?: (.*))?$")


@dataclass
class SupersededScope:
    """One retired position: its heading, its marker, and the text it covers.

    Line numbers index into ``body.split("\\n")``. ``start`` and ``stop`` bound
    the *covered text* — everything from just after the marker to the next
    heading of the same or higher level (§6.2) — so the heading and the marker
    themselves sit outside it and survive a live render.
    """

    heading_line: int
    level: int
    marker_line: int
    marker_end: int
    start: int
    stop: int
    retired_on: date
    reason: str


def superseded_scopes(body: str, path: Path | None = None) -> list[SupersededScope]:
    """Find every supersede marker in ``body``, and the scope each one covers.

    Raises :class:`SeedFileError` on a marker that does not follow §6.1 —
    malformed, missing its mandatory reason clause, or floating rather than
    sitting immediately under the heading it retires. A floating marker has no
    determinable scope, so there is nothing to be lenient *with*.

    A ``#`` inside a fenced code block is not a heading and does not close a
    scope; a marker inside a fence is example text, not a marker. A parser that
    ignores fences truncates scopes at the first shell comment in an example.
    """
    lines = body.split("\n")
    scopes: list[SupersededScope] = []
    pending: tuple[int, int] | None = None  # (heading line, heading level)
    fence: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            token = fence_match.group(1)[0]
            fence = token if fence is None else (None if token == fence else fence)
            index += 1
            continue
        if fence is not None:
            index += 1
            continue
        heading = _HEADING_RE.match(line)
        if heading:
            pending = (index, len(heading.group(1)))
            index += 1
            continue
        if line.startswith(_MARKER_PREFIX):
            index = _record_marker(lines, index, pending, scopes, path)
            pending = None
            continue
        if line.strip():
            pending = None
        index += 1
    return scopes


def _record_marker(
    lines: list[str],
    index: int,
    pending: tuple[int, int] | None,
    scopes: list[SupersededScope],
    path: Path | None,
) -> int:
    """Validate the marker at ``lines[index]``; append its scope, return next index."""
    line = lines[index]
    if pending is None:
        raise _fail(
            path,
            f"body line {index + 1}: a supersede marker must be the first "
            "non-blank line after the heading it retires; there is no floating "
            "supersession",
        )
    marker = _MARKER_RE.match(line)
    if not marker:
        raise _fail(
            path,
            f"body line {index + 1}: malformed supersede marker {line!r}; "
            "expected '> [!SUPERSEDED] YYYY-MM-DD — reason'",
        )
    try:
        retired_on = date.fromisoformat(marker.group(1))
    except ValueError as exc:
        raise _fail(
            path,
            f"body line {index + 1}: supersede marker carries an impossible "
            f"date {marker.group(1)!r}",
        ) from exc
    # The marker may wrap onto further blockquote lines; the reason clause is
    # everything from the em dash to the end of the blockquote (§6.1).
    parts = [(marker.group(2) or "").strip()]
    marker_end = index
    probe = index + 1
    while probe < len(lines) and lines[probe].startswith(">"):
        parts.append(lines[probe].lstrip(">").strip())
        marker_end = probe
        probe += 1
    reason = " ".join(part for part in parts if part).strip()
    if not reason:
        raise _fail(
            path,
            f"body line {index + 1}: supersede marker has no reason clause, and "
            "the reason clause is mandatory",
        )
    heading_line, level = pending
    scopes.append(
        SupersededScope(
            heading_line=heading_line,
            level=level,
            marker_line=index,
            marker_end=marker_end,
            start=marker_end + 1,
            stop=_scope_end(lines, marker_end + 1, level),
            retired_on=retired_on,
            reason=reason,
        )
    )
    return probe


def _scope_end(lines: list[str], start: int, level: int) -> int:
    """The first line at or after ``start`` that closes a scope opened at ``level``.

    §6.2: scope runs to the next heading of the same or higher level, or to the
    end of the body. Deeper subsections fall inside it, along with their text.
    """
    fence: str | None = None
    for index in range(start, len(lines)):
        line = lines[index]
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            token = fence_match.group(1)[0]
            fence = token if fence is None else (None if token == fence else fence)
            continue
        if fence is not None:
            continue
        heading = _HEADING_RE.match(line)
        if heading and len(heading.group(1)) <= level:
            return index
    return len(lines)


def render_body(body: str, *, full: bool = False) -> str:
    """Render a seed body — live by default (§7, "the RENDER is what is selective").

    ``full=True`` returns the body unchanged: nothing is ever destroyed on disk,
    so everything is still there to render. The default drops the text inside
    every superseded scope while keeping each retired heading and its marker, so
    a reader can see that something was retired and why.
    """
    if full:
        return body
    scopes = superseded_scopes(body)
    if not scopes:
        return body
    lines = body.split("\n")
    dropped: set[int] = set()
    for scope in scopes:
        dropped.update(range(scope.start, scope.stop))
    kept = [line for index, line in enumerate(lines) if index not in dropped]
    out = "\n".join(kept)
    if body.endswith("\n") and out and not out.endswith("\n"):
        out += "\n"
    return out
