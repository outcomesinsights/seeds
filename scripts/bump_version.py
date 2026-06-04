#!/usr/bin/env python3
"""Bump the seeds version everywhere it must appear (see bead seeds-5uw).

The canonical version lives in ``src/seeds/__init__.py`` (``__version__``);
``pyproject.toml`` derives it via hatchling and never needs editing. The two
Claude Code plugin manifests hold a *literal* version string — Claude Code reads
them as static JSON, so they cannot be runtime-dynamic — and this script keeps
them in lockstep with the canonical source.

Run via ``just bump-version X.Y.Z``. ``tests/test_version_sync.py`` fails the
build if any manifest is ever left behind.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_PY = REPO_ROOT / "src" / "seeds" / "__init__.py"
PLUGIN_JSON = REPO_ROOT / "src/seeds/plugin/claude-plugin/.claude-plugin/plugin.json"
MARKETPLACE_JSON = REPO_ROOT / "src/seeds/plugin/.claude-plugin/marketplace.json"

# Accepts X.Y.Z with an optional pre-release/build suffix (e.g. 1.2.3, 1.2.3rc1).
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-.][0-9A-Za-z.]+)?$")


def _replace_once(path: Path, pattern: str, replacement: str) -> None:
    """Replace exactly one occurrence of ``pattern`` in ``path``; fail loudly."""
    text = path.read_text()
    new_text, count = re.subn(pattern, replacement, text)
    assert count == 1, (
        f"expected exactly one version field in {path.relative_to(REPO_ROOT)}, "
        f"found {count}"
    )
    path.write_text(new_text)


def bump(version: str) -> None:
    assert VERSION_RE.match(version), f"not a valid version: {version!r}"
    _replace_once(INIT_PY, r'__version__\s*=\s*"[^"]*"', f'__version__ = "{version}"')
    _replace_once(PLUGIN_JSON, r'"version":\s*"[^"]*"', f'"version": "{version}"')
    _replace_once(MARKETPLACE_JSON, r'"version":\s*"[^"]*"', f'"version": "{version}"')
    print(f"Bumped seeds to {version}:")
    print(f"  {INIT_PY.relative_to(REPO_ROOT)}  (canonical; pyproject derives it)")
    print(f"  {PLUGIN_JSON.relative_to(REPO_ROOT)}")
    print(f"  {MARKETPLACE_JSON.relative_to(REPO_ROOT)}")


def main() -> None:
    assert len(sys.argv) == 2, "usage: bump_version.py X.Y.Z"
    bump(sys.argv[1])


if __name__ == "__main__":
    main()
