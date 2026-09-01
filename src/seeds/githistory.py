"""Reading the seed-file store's git history.

``seeds check`` has two tiers that cannot be answered from the files alone.
``--smells`` wants to know how many commits a seed's body has survived, and
``--against-git`` wants every field's value at the previous commit. Both are
history questions, and git is the only store that holds the answer — the point
of ``seeds-wurl`` is that when both live stores agreed and both were wrong,
git was the only thing that still held the truth (``docs/storage-format.md``
§11).

This is a sibling of :mod:`seeds.gitstage`, not part of it: that module is
scoped to "what is staged right now", answers ``None`` for everything it
cannot determine, and must never be the reason ``seeds sync`` crashes. The
contract here is the opposite for ``--against-git``, and deliberately so — a
comparison the operator explicitly asked for that silently could not run is
the "green while broken" shape this whole subsystem exists to prevent. So a
missing git, or a directory that is not inside a work tree, raises
:class:`GitUnavailable` and the caller decides. An *unborn* ``HEAD`` is not one
of those cases: "there is no previous commit" is a real, complete answer, and
the caller models it as an empty before-state.

``_subprocess_env`` is shared with :mod:`seeds.gitstage` because it describes
git's hook contract — a hook has ``GIT_DIR`` and friends pointing at the commit
in progress, which is exactly the wrong repository to answer a question about
some other directory.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path

from seeds.gitstage import _subprocess_env

__all__ = [
    "GitUnavailable",
    "commit_counts",
    "read_blobs",
    "repo_root",
    "rev_exists",
    "tree_files",
]

# git's own name for "the empty tree", stable since the beginning of the
# format. Not used to read anything -- an unborn HEAD is modelled as an empty
# mapping instead -- but named here so a reader looking for it stops here.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


class GitUnavailable(Exception):
    """git could not answer at all: not installed, or not in a work tree."""


def _git_text(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env=_subprocess_env(),
        )
    except OSError as exc:  # git not installed, cwd gone
        raise GitUnavailable(f"could not run git: {exc}") from exc


def _git_bytes(
    cwd: Path, *args: str, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    """As :func:`_git_text`, but for output that is blob content, not text.

    Seed files are UTF-8 by the format, but a corrupted one in history is
    exactly the sort of thing a checker is asked about, so the bytes are
    decoded with replacement at the point of use rather than here.
    """
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            check=False,
            input=stdin,
            env=_subprocess_env(),
        )
    except OSError as exc:
        raise GitUnavailable(f"could not run git: {exc}") from exc


def repo_root(path: Path) -> Path:
    """The work tree containing ``path``, or raise :class:`GitUnavailable`."""
    path = Path(path)
    if not path.is_dir():
        raise GitUnavailable(f"{path} is not a directory")
    proc = _git_text(path, "rev-parse", "--show-toplevel")
    if proc.returncode != 0 or not proc.stdout.strip():
        raise GitUnavailable(
            f"{path} is not inside a git work tree, so there is no history "
            f"to compare against"
        )
    return Path(proc.stdout.strip()).resolve()


def rev_exists(root: Path, rev: str) -> bool:
    """Whether ``rev`` names a commit — ``False`` for an unborn HEAD."""
    proc = _git_text(root, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    return proc.returncode == 0


def commit_counts(root: Path, reldir: str) -> dict[str, int]:
    """How many commits in ``HEAD``'s history touched each path under ``reldir``.

    Keyed by repo-relative POSIX path. A path with no entry has never been
    committed — a seed jotted since the last commit, which is not a seed with a
    long history, so the absence is the right answer rather than a gap.
    """
    proc = _git_text(root, "log", "--pretty=format:", "--name-only", "--", reldir)
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
    proc = _git_text(root, "ls-tree", "-r", "-z", rev, "--", reldir)
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
    proc = _git_bytes(root, "cat-file", "--batch", stdin=stdin)
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
