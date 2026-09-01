"""Reading the seed-file store's git history.

``seeds check`` has two tiers that cannot be answered from the files alone.
``--smells`` wants to know how many commits a seed's body has survived, and
``--against-git`` wants every field's value at the previous commit. Both are
history questions, and git is the only store that holds the answer — the point
of ``seeds-wurl`` is that when both live stores agreed and both were wrong,
git was the only thing that still held the truth (``docs/storage-format.md``
§11).

The contract for ``--against-git`` is loud, deliberately: a comparison the
operator explicitly asked for that silently could not run is the "green while
broken" shape this whole subsystem exists to prevent. So a missing git, or a
directory that is not inside a work tree, raises :class:`GitUnavailable` and
the caller decides. An *unborn* ``HEAD`` is not one of those cases: "there is
no previous commit" is a real, complete answer, and the caller models it as an
empty before-state.

Every git process this module starts comes from :mod:`seeds.gitstage`, which is
the single door: it strips the repo-pinning ``GIT_*`` variables git exports into
hooks, so a question asked about some other directory cannot be answered about
the commit in progress. ``GitUnavailable`` and ``repo_root`` live there for the
same reason and are re-exported here, where their callers already look for them.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from seeds.gitstage import GitUnavailable, git_bytes, git_text, repo_root

__all__ = [
    "Commit",
    "GitUnavailable",
    "commit_counts",
    "path_commits",
    "read_blobs",
    "repo_root",
    "rev_exists",
    "show_file",
    "tree_files",
]

# git's own name for "the empty tree", stable since the beginning of the
# format. Not used to read anything -- an unborn HEAD is modelled as an empty
# mapping instead -- but named here so a reader looking for it stops here.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def rev_exists(root: Path, rev: str) -> bool:
    """Whether ``rev`` names a commit — ``False`` for an unborn HEAD."""
    proc = git_text(root, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    return proc.returncode == 0


def commit_counts(root: Path, reldir: str) -> dict[str, int]:
    """How many commits in ``HEAD``'s history touched each path under ``reldir``.

    Keyed by repo-relative POSIX path. A path with no entry has never been
    committed — a seed jotted since the last commit, which is not a seed with a
    long history, so the absence is the right answer rather than a gap.
    """
    proc = git_text(root, "log", "--pretty=format:", "--name-only", "--", reldir)
    if proc.returncode != 0:
        return {}
    counts: Counter[str] = Counter(
        line.strip() for line in proc.stdout.splitlines() if line.strip()
    )
    return dict(counts)


def tree_files(root: Path, rev: str, reldir: str) -> dict[str, str]:
    """Every file under ``reldir`` at ``rev``, as ``{relpath: blob sha}``.

    ``-z`` rather than the default listing: the terminator is unambiguous, so a
    path git would otherwise quote and escape cannot be misread.
    """
    proc = git_text(root, "ls-tree", "-r", "-z", rev, "--", reldir)
    if proc.returncode != 0:
        return {}
    out: dict[str, str] = {}
    for entry in proc.stdout.split("\0"):
        if not entry:
            continue
        meta, _, path = entry.partition("\t")
        parts = meta.split()
        if len(parts) < 3 or parts[1] != "blob":
            continue
        out[path] = parts[2]
    return out


def read_blobs(root: Path, shas: list[str]) -> dict[str, str]:
    """The text of every blob named, as ``{sha: text}``.

    One ``git cat-file --batch`` rather than a ``git show`` per file: the
    comparison runs over the whole corpus on every commit, and a checker that
    is slow enough to be skipped is a checker that does not run.
    """
    if not shas:
        return {}
    stdin = ("\n".join(shas) + "\n").encode()
    proc = git_bytes(root, "cat-file", "--batch", stdin=stdin)
    if proc.returncode != 0:
        return {}
    out: dict[str, str] = {}
    data = proc.stdout
    pos = 0
    while pos < len(data):
        end = data.find(b"\n", pos)
        if end == -1:
            break
        header = data[pos:end].decode("utf-8", errors="replace").split()
        # "<sha> missing" for anything git does not have; skip it rather than
        # guessing at a length that is not there.
        if len(header) != 3 or header[1] != "blob":
            break
        sha, size = header[0], int(header[2])
        start = end + 1
        out[sha] = data[start : start + size].decode("utf-8", errors="replace")
        pos = start + size + 1  # the trailing newline cat-file adds
    return out


# --- Per-path history (seeds history) ----------------------------------------

# Field separator inside one log line. US (0x1f) rather than a printable
# character because every one of the four fields is free text a commit author
# chose -- an author name with a tab in it, or a subject with a pipe, would
# otherwise silently shift the columns. git's own %x escape emits it, so no
# quoting scheme is involved on either side.
_LOG_SEP = "\x1f"

_LOG_FORMAT = _LOG_SEP.join(("%H", "%ad", "%at", "%an", "%s"))


@dataclass(frozen=True)
class Commit:
    """One commit, reduced to what a reader of a seed's history needs.

    ``date`` is the *author* date rendered short, because that is when the
    deliberation happened; ``timestamp`` is the same instant as a unix time, so
    a caller can order or bound a list without re-parsing the rendering.
    """

    sha: str
    date: str
    timestamp: int
    author: str
    subject: str


def path_commits(root: Path, relpath: str) -> list[Commit]:
    """Every commit that touched ``relpath``, **oldest first**.

    Oldest first because the caller is walking an evolution forward and diffing
    each revision against the one before it; reversing afterwards would mean
    holding the whole list twice for no gain.

    An empty list means git could answer and the answer is "never committed" --
    a seed jotted since the last commit, or a path that does not exist. That is
    a real answer, not a failure, so it is not raised.
    """
    proc = git_text(
        root,
        "log",
        "--reverse",
        f"--format={_LOG_FORMAT}",
        "--date=short",
        "--",
        relpath,
    )
    if proc.returncode != 0:
        return []
    commits: list[Commit] = []
    for line in proc.stdout.splitlines():
        parts = line.split(_LOG_SEP)
        if len(parts) != 5:
            continue
        sha, date, timestamp, author, subject = parts
        commits.append(
            Commit(
                sha=sha,
                date=date,
                timestamp=int(timestamp),
                author=author,
                subject=subject,
            )
        )
    return commits


def show_file(root: Path, rev: str, relpath: str) -> str | None:
    """``relpath``'s content at ``rev``, or ``None`` when it is not there.

    ``None`` is the honest answer for "this path did not exist at that commit",
    which is the ordinary case when walking back past a file's creation. Bytes
    are decoded with replacement for the same reason :func:`read_blobs` does it:
    a file that will not decode is a thing history can hold, and a crash here
    would make the whole history unreadable over one bad revision.
    """
    proc = git_bytes(root, "show", f"{rev}:{relpath}")
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", errors="replace")
