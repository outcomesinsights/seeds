#!/usr/bin/env python3
"""Gate a commit on ``seeds check`` (bead seeds-4co.13).

Claude Code's ``PostToolUse`` hooks fire on the Write/Edit *tools*. An agent
that reaches a file through ``bash -c 'cat > …'``, ``sed -i`` or a Python
one-liner never touches those tools and never fires the hook -- and that is
most agent file access in practice. So tool-level hooks are advisory. **The git
pre-commit hook is the only gate that holds, because everything reaches a
commit eventually.**

@aguynamedryan, on making detection rather than prevention the strategy:
*"we should check to see if metadata is being violated somehow and whatever
other adherence we might want to enforce … a check that's easily done."*

What this adds over ``seeds check`` itself is exactly two things, and it
delegates everything else to the command:

1. **A missing store is not a failure here.** Before the conversion to
   ``.seeds/seeds/`` lands, ``seeds check`` reports a ``store-missing``
   violation and exits 1 -- correct for a checker whose job is to say the
   deliverable is not there, and wrong for a gate that would then refuse every
   commit in the repo. The finding's ``code`` is the cue: exactly one finding,
   ``store-missing``, means there is nothing to gate yet.

2. **It names the escape hatch when it blocks.** ``--against-git`` fails on a
   mass single-field rewrite precisely because such a change has no cheap
   review, so the operator has to *confirm* it rather than be stopped by it.
   The confirmation is pre-commit's own ``SKIP``; ``git commit --no-verify`` is
   not an option here, because it would also skip the beads export and the git
   config sanity check.

Everything else -- which tiers run, what they print, what fails -- stays in
``seeds check``. Reimplementing any of it here would create a second copy that
drifts, and the drift would be invisible: this hook only speaks up when it
fails.

Accepted limitation: this is detection *at commit*, not immutability. An agent
can read corrupt state at any point before the commit fires. That is not
closable, and it still bounds the damage to one working session rather than the
five weeks seeds-wurl went unread.
"""

from __future__ import annotations

import subprocess
import sys

from seeds.check import check_violations
from seeds.db import find_seeds_dir

# The full three-tier run. --against-git is not optional here: without it,
# `rm <seed-file>` is the de facto delete verb (the format has no delete verb
# at all), and a mass deletion would pass every violation check by being, in
# the surviving files, perfectly well formed.
CHECK_ARGS = ("check", "--against-git", "--smells")

CONFIRMATION = """
────────────────────────────────────────────────────────────────────────────
`seeds check` refused this commit. If this is a mass rewrite you intended,
confirm it explicitly -- that confirmation is the whole point of the gate:

    SKIP=seeds-check git commit …

Use SKIP, not `git commit --no-verify`: --no-verify also skips the beads
export and the git config sanity check, which have nothing to do with this.
────────────────────────────────────────────────────────────────────────────"""


def main() -> int:
    """Run the gate against the store found from the current directory.

    Takes no arguments: unlike ``scripts/check_git_config_sanity.py``, which is
    pointed at hand-built config files, every case here needs a whole store and
    a real git repository, so the suite builds those in ``tmp_path`` and chdirs
    into them exactly as the hook is invoked.
    """
    seeds_dir = find_seeds_dir()
    if seeds_dir is None:
        print("seeds check: no .seeds/ directory here — nothing to gate.")
        return 0

    # The store-missing cue. Deliberately asked of check_violations rather than
    # tested with `files_dir.is_dir()`: that would be a second definition of
    # "there is no store", free to drift from the one in seeds.check.
    findings = check_violations(seeds_dir)
    if len(findings) == 1 and findings[0].code == "store-missing":
        print("seeds check: no seed-file store yet — nothing to gate.")
        return 0

    result = subprocess.run(
        [sys.executable, "-m", "seeds.cli", *CHECK_ARGS],
        check=False,
    )
    if result.returncode != 0:
        print(CONFIRMATION, file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
